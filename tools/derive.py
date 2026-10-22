"""Текст для озвучки из чистого текста урока: подстановка словаря Светланы.

Запуск из корня репозитория:
    python tools/derive.py system-design-basics/sdb-api.clean.txt

Пишет рядом sdb-api.txt (вход для tools/build.py) и печатает, что осталось проверить глазами: латиницу и места,
опасные для голоса. Замены — записи из dictionary-svetlana.md, которые можно сделать механически. Синонимы для
омографов, пересказ кода и таблиц, числа словами делают в самом .clean.txt — здесь их не угадать.
Новая запись в словаре — новая строка в REPLACE, если её можно подставлять без чтения контекста.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Порядок важен: сначала сочетания с падежом, потом слово само по себе.
REPLACE = [
    (r"\bWebSocket\b", "вэб-сокет"), (r"\bWebView\b", "вэб-вью"), (r"\bWi-Fi\b", "вай-фай"),
    (r"ISO/IEC", "ай-эс-о"), (r"\bISO\b", "ай-эс-о"),
    (r"\bavailability\b", "эвэйлабилити"), (r"\baccessibility\b", "эксэсибилити"),
    (r"\bAvailability\b", "Эвэйлабилити"), (r"\bAccessibility\b", "Эксэсибилити"),
    (r"\bsecurity\b", "секьюрити"), (r"\bsafety\b", "сэйфти"), (r"\biframe\b", "айфрэйм"),
    (r"([Ээ])ндпоинт", r"\1нд-поинт"),
    (r"Content Security Policy", "контент секьюрити полиси"), (r"Feature-Sliced Design", "фича-слайсд дизайн"),
    (r"\bWCAG\b", "дабл-ю-си-эй-джи"), (r"\bLCP\b", "эл-си-пи"), (r"\bINP\b", "ай-эн-пи"), (r"\bCLS\b", "си-эл-эс"),
    # названия с React внутри — до склонения реакта, иначе выйдет «в реакте Router»
    (r"\bReact Router\b", "реакт-роутер"), (r"\bReact Hook Form\b", "реакт-хук-форм"),
    # реакт и ридакс склоняются: «документация реакта», «в реакте», «в ридаксе»
    (r"\b([Дд]окументаци[яиюей]|[Кк]онтекст[ау]?|[Кк]омпонента|[Пп]равил[оа]|[Фф]илософия|[Мм]ире|[Пп]ровайдер[ау]?) React\b",
     r"\1 реакта"),
    (r"\b([Дд]окументаци[яиюей]|[Хх]ранилище|вроде|в) Redux\b",
     lambda m: m.group(1) + (" ридаксе" if m.group(1) == "в" else " ридакса")),
    (r"\bк Docker\b", "к докеру"), (r"\bвроде XState\b", "вроде икс-стейта"),
    (r"\b([Нн]а|[Вв]) React\b", r"\1 реакте"), (r"\b(без|для|из|у|от) React\b", r"\1 реакта"),
    (r"\b(с|над) React\b", r"\1 реактом"), (r"\b(к|по) React\b", r"\1 реакту"), (r"\bReact\b", "реакт"),
    (r"\bRedux\b", "ридакс"), (r"\bZustand\b", "зустанд"), (r"\bGraphQL\b", "графкуэль"),
    (r"\bIndexedDB\b", "индексд-ди-би"), (r"\bADR\b", "а-дэ-эр"), (r"\bTypeScript\b", "тайпскрипт"),
    (r"\bDocker\b", "докер"), (r"\bSOLID\b", "соль-ид"), (r"\bSun Microsystems\b", "Сан Майкросистемс"),
    (r"\bSun\b", "Сан"), (r"буква D\b", "буква ди"), (r"\bXState\b", "икс-стейт"),
    (r"\bURL\b", "ю-эр-эль"), (r"([Бб])экенд", r"\1эк-энд"), (r"([Мм])икрофронтенд", r"\1икро-фронтэнд"),
    (r"\bDefaultValue\b", "Дефолт-вэлью"), (r"\bdefaultValue\b", "дефолт-вэлью"),
    (r"\bValue\b", "Вэлью"), (r"\bvalue\b", "вэлью"),
    (r"\bOnChange\b", "Он-чейндж"), (r"\bonChange\b", "он-чейндж"), (r"\bonClose\b", "он-клоуз"),
    (r"\bnull\b", "нал"), (r"\bundefined\b", "андефайнд"),
    (r"\buseState\b", "юз-стейт"), (r"\buseEffect\b", "юз-эффект"), (r"\buseMemo\b", "юз-мемо"),
    (r"\buseReducer\b", "юз-редьюсер"),
    (r"\bWAI-ARIA\b", "вай-ария"), (r"\bW3C\b", "дабл-ю-три-си"), (r"Shift\+Tab", "шифт-таб"), (r"\bTab\b", "таб"),
    (r"\blocalStorage\b", "локал-сторэдж"), (r"\bsessionStorage\b", "сешн-сторэдж"),
    (r"TanStack Query", "тан-стэк квери"),
    (r"\bpushState\b", "пуш-стейт"), (r"\breplaceState\b", "риплэйс-стейт"), (r"\bpopstate\b", "поп-стейт"),
    (r"\bbeforeunload\b", "бифор-анлоуд"), (r"\bunload\b", "анлоуд"), (r"\bvisibilitychange\b", "визибилити-чейндж"),
    (r"JSON-RPC", "джисон-эр-пи-си"), (r"\bgRPC\b", "джи-эр-пи-си"), (r"\btRPC\b", "ти-эр-пи-си"),
    (r"\bRPC\b", "эр-пи-си"),
    (r"\bCQRS\b", "си-кью-эр-эс"), (r"\bCQS\b", "си-кью-эс"), (r"\bRFC\b", "эр-эф-си"),
    (r"\bPUT\b", "пут"), (r"\bPATCH\b", "патч"), (r"\bPOST-запрос", "пост-запрос"), (r"\bGET-запрос", "гет-запрос"),
    (r"Nielsen Norman Group", "Нильсен Норман Груп"),
    (r"\bPerl\b", "перл"), (r"C\+\+", "си-плюс-плюс"), (r"\bJava\b", "джава"),
    (r"\bspike\b", "спайк"), (r"\bprops\b", "пропсы"),
]

# Что голос читает неверно и что механически не заменить: омографы, множественное «адреса/места/цвета»,
# единицы цифрами, отсылки к экрану. Печатается для ручной правки .clean.txt.
RISKY = re.compile(
    r"(?<![А-Яа-яЁё])(стоит|стоят|стоило|поля|окна|права|дорога|дорог|дорогой|включит|кеширован\w*|адреса|места|цвета"
    r"|поднял|начат(?!ь)\w*|обеспеч\w*|ниже|выше|строки|числа|полям|полях|полями)(?![А-Яа-яЁё])"
    r"|\d\s?(мс|с|МБ|КБ|ГБ|Мбит/с)(?![А-Яа-яЁё])|₽|руб\.|2,5 секунд|\b\d{4,}\b")  # числа от 4 цифр — номера стандартов цифрами голос склоняет


def derive(text):
    for pattern, replacement in REPLACE:
        text = re.sub(pattern, replacement, text)
    # после замены латиницы предложение может начаться со строчной: «сешн-сторэдж переживает…»
    return re.sub(r"(^|[.!?…]\s+|\n)([а-яё])", lambda m: m.group(1) + m.group(2).upper(), text)


def main(clean_file):
    clean_file = (ROOT / clean_file).resolve()
    if not clean_file.name.endswith(".clean.txt"):
        sys.exit("Нужен чистый текст урока: <курс>/<id урока>.clean.txt")
    text = derive(clean_file.read_text(encoding="utf-8"))
    out = clean_file.with_name(clean_file.name.replace(".clean.txt", ".txt"))
    out.write_text(text, encoding="utf-8")

    latin = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9/+.-]*[A-Za-z0-9]|[A-Za-z]", text)))
    print(f"{out.relative_to(ROOT)}: {len(text)} знаков")
    print("латиница — сверить со словарём:", ", ".join(latin) or "нет")
    for m in RISKY.finditer(text):
        print(f"  проверить «{m.group(0)}»: …{text[max(0, m.start() - 35):m.end() + 25]}…".replace("\n", " "))
    questions = text.count("?")
    if questions:
        print(f"  вопросительных знаков: {questions} — вопрос с ответом на слух не различить, оставлять только в цитатах")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Использование: python tools/derive.py <курс>/<id урока>.clean.txt")
    main(sys.argv[1])
