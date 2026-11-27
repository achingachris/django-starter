// Simple offline-first service worker.
// PWA feature #1: caches key assets so the app still loads (with an offline
// fallback page) when the network is unavailable.

// Bump the version to drop every cache an older worker created (see the activate handler).
const CACHE_NAME = "chrisdevcode-cache-v2";
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

// Only this site's own static files are cached; they are public and the same for every user.
const isStaticAsset = (url) => url.origin === self.location.origin && url.pathname.startsWith("/static/");

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

  // Stale-while-revalidate for static assets: answer from the cache when possible, and refresh the
  // cached copy in the background so a deploy (e.g. a security fix to site.js) reaches returning
  // browsers on their next visit. Only successful responses are stored.
  if (isStaticAsset(new URL(request.url))) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cached) => {
          const network = fetch(request)
            .then((response) => {
              if (response.ok) {
                cache.put(request, response.clone());
              }
              return response;
            })
            .catch(() => cached);
          if (cached) {
            event.waitUntil(network);
            return cached;
          }
          return network;
        })
      )
    );
  }
});
