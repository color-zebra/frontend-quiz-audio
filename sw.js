// Тестовый Service Worker: если MP3 скачан на телефон, отдаёт его из кэша — целиком или кусками для перемотки.
const CACHE = "audio-check";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

async function tell(text) {
  for (const client of await self.clients.matchAll()) client.postMessage(text);
}

self.addEventListener("fetch", (event) => {
  if (!event.request.url.endsWith(".mp3")) return;
  event.respondWith(
    (async () => {
      const cached = await (await caches.open(CACHE)).match(event.request.url);
      if (!cached) return fetch(event.request);
      const blob = await cached.blob();
      const type = cached.headers.get("content-type") || "audio/mpeg";
      const range = event.request.headers.get("range");
      if (!range) {
        tell("играет с телефона (целиком)");
        return new Response(blob, { status: 200, headers: { "Content-Type": type, "Content-Length": String(blob.size) } });
      }
      const [, startText, endText] = /bytes=(\d*)-(\d*)/.exec(range) || [];
      const start = Number(startText || 0);
      const end = endText ? Number(endText) : blob.size - 1;
      tell(`играет с телефона: кусок ${start}–${end}`);
      return new Response(blob.slice(start, end + 1), {
        status: 206,
        headers: {
          "Content-Type": type,
          "Content-Range": `bytes ${start}-${end}/${blob.size}`,
          "Content-Length": String(end - start + 1),
          "Accept-Ranges": "bytes",
        },
      });
    })(),
  );
});
