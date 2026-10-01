// RVKS WEB - Service Worker for Offline Static Asset Caching (Network-First Strategy)
const CACHE_NAME = "rvks-farm-cache-v6";
const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/css/style.css",
  "/css/components.css",
  "/css/pages.css",
  "/css/responsive.css",
  "/css/index.css",
  "/js/main.js",
  "/js/components.js",
  "/js/auth.js",
  "/js/dashboard.js",
  "/js/utils.js",
  "/js/api.js",
  "/js/charts.js",
  "/js/offline_sync.js",
  "/js/app.js",
  "/components/navbar.html",
  "/components/sidebar.html",
  "/components/footer.html",
  "/components/modals.html",
  "/components/toast.html",
  "/pages/dashboard.html",
  "/pages/payments.html",
  "/pages/workers.html",
  "/pages/login.html",
  "/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ServiceWorker] Pre-caching static assets (v6)...");
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
  // Let API requests go directly to network
  if (e.request.url.includes("/api/")) {
    return;
  }

  // Network-First strategy: Always fetch freshest assets from server when online; fallback to cache if offline
  e.respondWith(
    fetch(e.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && e.request.method === "GET") {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, responseToCache));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(e.request).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
          if (e.request.mode === "navigate") {
            return caches.match("/index.html");
          }
        });
      })
  );
});
