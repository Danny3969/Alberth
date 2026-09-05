// Alberth PWA Offline Service Worker (v4.2)
const CACHE_NAME = 'alberth-v4.2-cache';
const ASSETS = [
  '/floating',
  '/floating.html',
  '/index.html',
  '/api/canvas'
];

self.addEventListener('install', (evt) => {
  evt.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (evt) => {
  evt.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (evt) => {
  evt.respondWith(
    caches.match(evt.request).then((cachedResp) => {
      return cachedResp || fetch(evt.request).catch(() => caches.match('/floating.html'));
    })
  );
});
