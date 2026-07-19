// Simple offline-first service worker.
// PWA feature #1: caches key assets so the app still loads (with an offline
// fallback page) when the network is unavailable.

const CACHE_NAME = "chrisdevcode-cache-v1";
const OFFLINE_URL = "/offline/";

const PRECACHE_URLS = [OFFLINE_URL];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only handle GET requests for pages/assets; let everything else (POST forms, etc.) pass through.
  if (request.method !== "GET") {
    return;
  }

  if (request.mode === "navigate") {
    // Network-first for page navigations, falling back to a cached offline page.
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Cache-first for static assets (CSS/JS/images) so the app shell loads instantly and offline.
  if (request.url.includes("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          return response;
        }).catch(() => cached);
      })
    );
  }
});
