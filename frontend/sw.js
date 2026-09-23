// RVKS WEB - Service Worker for Offline Static Asset Caching
const CACHE_NAME = "rvks-farm-cache-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/css/index.css",
  "/js/app.js",
  "/js/api.js",
  "/js/offline_sync.js",
  "/js/charts.js",
  "/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ServiceWorker] Pre-caching static assets for offline capability...");
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn("[ServiceWorker] Failed to cache some assets:", err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[ServiceWorker] Removing old cache:", key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Let API requests go directly to network or handled by app logic
  if (e.request.url.includes("/api/")) {
    return;
  }

  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(e.request).catch(() => {
        if (e.request.mode === "navigate") {
          return caches.match("/index.html");
        }
      });
    })
  );
});
