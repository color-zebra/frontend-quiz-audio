"""Сборка аудио урока: текст для озвучки → MP3.

Запуск из корня репозитория:
    .venv/Scripts/python tools/build.py system-design-basics/sdb-intro-2.txt

Текст — разделы урока через строку «=== раздел ===». Каждый раздел озвучивается отдельным запросом голосом
Светлана (edge-tts), по одному и с паузой: доступ неофициальный, долбить его нельзя. Озвученные разделы
кэшируются в _raw/<курс>/sections/ по хэшу текста — после правки одного раздела переозвучивается только он.
Склейка — ffmpeg: тишина между разделами, громкость около −17 LUFS, MP3 моно 48 кГц 64 кбит/с.
Итог — рядом с текстом, с тем же именем и расширением .mp3.
"""

import asyncio
import hashlib
import pathlib
import re
import shutil
import subprocess
import sys
import time

import edge_tts

VOICE = "ru-RU-SvetlanaNeural"
SECTION_MARK = "=== раздел ==="
PAUSE_BETWEEN_SECTIONS = 0.2  # с; Светлана сама оставляет ~0,6 с тишины по краям, на стыке выходит ~1,4 с
REQUEST_PAUSE = 5  # с между запросами
MIN_CHARS_PER_SECOND = 20  # быстрее — значит, звук оборвался (Светлана читает ~14 знаков в секунду)
# Сервис иногда молча не отвечает, и запрос висит часами (2026-10-23 — почти час): свой предел на раздел целиком
SECTION_TIMEOUT_BASE = 120  # с
SECTION_TIMEOUT_PER_CHAR = 0.1  # с на знак: раздел в 1600 знаков — до ~4,5 минуты
ROOT = pathlib.Path(__file__).resolve().parent.parent


def tool(name):
    path = shutil.which(name)
    if not path:
        sys.exit(f"Нет {name}: поставить ffmpeg (winget install Gyan.FFmpeg) и открыть терминал заново")
    return path


FFMPEG, FFPROBE = tool("ffmpeg"), tool("ffprobe")


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


async def synthesize(text, path):
    """Один раздел; до трёх попыток с нарастающей паузой, если запрос упал, завис или звук оборвался."""
    timeout = SECTION_TIMEOUT_BASE + SECTION_TIMEOUT_PER_CHAR * len(text)
    for attempt in range(1, 4):
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, VOICE).save(str(path)), timeout)
        except asyncio.TimeoutError:
            print(f"    завис: нет ответа за {timeout:.0f} с")
        except Exception as error:
            print(f"    ошибка: {type(error).__name__}")
        if path.exists() and duration(path) > len(text) / MIN_CHARS_PER_SECOND:
            return
        print(f"    попытка {attempt} не удалась, жду")
        time.sleep(15 * attempt)
    path.unlink(missing_ok=True)
    sys.exit(f"Раздел не озвучился: {text[:60]}…")


async def main(text_file):
    text_file = (ROOT / text_file).resolve()
    course = text_file.parent.name
    sections = [s.strip() for s in text_file.read_text(encoding="utf-8").split(SECTION_MARK) if s.strip()]
    cache = ROOT / "_raw" / course / "sections"
    cache.mkdir(parents=True, exist_ok=True)

    files, requested = [], False
    for i, section in enumerate(sections, 1):
        key = hashlib.sha1(f"{VOICE}\n{section}".encode()).hexdigest()[:12]
        path = cache / f"{key}.mp3"
        fresh = not path.exists()
        if fresh:
            if requested:
                time.sleep(REQUEST_PAUSE)
            await synthesize(section, path)
            requested = True
        print(f"  {i:02d}  {len(section):5} зн  {duration(path):6.1f} с  {'новый' if fresh else 'из кэша'}")
        files.append(path)

    # Название урока и курса — из первой фразы «Курс «…». Урок «…».» — в метаданные файла.
    head = re.match(r"Курс «(.+?)»\. Урок «(.+?)»\.", sections[0])
    album, title = head.groups() if head else ("", text_file.stem)

    args, chain, inputs = [], "", 0
    for n, path in enumerate(files):
        args += ["-i", str(path)]
        chain += f"[{inputs}:a]"
        inputs += 1
        if n < len(files) - 1:
            args += ["-f", "lavfi", "-t", str(PAUSE_BETWEEN_SECTIONS), "-i", "anullsrc=r=24000:cl=mono"]
            chain += f"[{inputs}:a]"
            inputs += 1
    chain += f"concat=n={inputs}:v=0:a=1[c];[c]loudnorm=I=-17:TP=-2:LRA=11,aresample=48000[o]"
    out = text_file.with_suffix(".mp3")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", chain,
                    "-map", "[o]", "-ac", "1", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "64k",
                    "-id3v2_version", "3", "-metadata", f"title={title}", "-metadata", f"album={album}", str(out)],
                   check=True)

    loud = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true:framelog=quiet",
                           "-f", "null", "-"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stderr  # ffmpeg пишет название урока в UTF-8, не в cp1251
    level = re.search(r"I:\s+(-?[\d.]+) LUFS", loud)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", loud)
    minutes, seconds = divmod(round(duration(out)), 60)
    print(f"{out.relative_to(ROOT)}: {minutes}:{seconds:02d}, {out.stat().st_size / 1e6:.1f} МБ, "
          f"{level.group(1) if level else '?'} LUFS, пики {peak.group(1) if peak else '?'} dBFS")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Использование: python tools/build.py <курс>/<имя>.txt")
    sys.stdout.reconfigure(line_buffering=True)  # строки сразу в журнал — иначе зависание видно только в конце урока
    asyncio.run(main(sys.argv[1]))
