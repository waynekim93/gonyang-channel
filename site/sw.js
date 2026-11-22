// 고냥이 AI 일터 — 앱 설치용 서비스 워커. 화면 파일은 네트워크 우선(새 버전 바로 반영), 꺼져 있으면 저장본.
// 실시간 현황(api.github.com Gist)은 다른 주소라 건드리지 않음.
const CACHE = "gonyang-office-v1";
const SHELL = ["/office", "/fonts/Pretendard-ExtraBold.otf", "/icons/icon-192.png", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("/office")))
  );
});
