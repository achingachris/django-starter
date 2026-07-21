{% load static %}{% load django_vite %}
// Sokoni service worker — app-shell caching + offline fallback.
// Bump this version whenever the precached shell assets change, to force
// old clients to pick up the new cache instead of serving stale files.
const CACHE_VERSION = 'sokoni-v1';
const SHELL_CACHE = CACHE_VERSION + '-shell';

const OFFLINE_URL = '{% url "web:offline" %}';

const PRECACHE_URLS = [
  '/',
  OFFLINE_URL,
  '{% vite_asset_url "assets/styles/site-base.css" %}',
  '{% vite_asset_url "assets/styles/site-tailwind.css" %}',
  '{% vite_asset_url "assets/javascript/site.js" %}',
  '{% static "images/favicons/favicon.svg" %}',
  '{% static "images/favicons/apple-touch-icon.png" %}',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith('sokoni-') && key !== SHELL_CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Page navigations: network-first, falling back to a cached offline page.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Static assets (built CSS/JS/images): cache-first, falling back to network.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return response;
        });
      })
    );
  }
});
