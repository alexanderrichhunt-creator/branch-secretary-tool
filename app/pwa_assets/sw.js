/* Branch Secretary service worker.
 *
 * Caches the app shell and static files only. Navigations and every
 * authenticated or dynamic response (HTML pages, /api/, /auth/) are
 * network-only so a phone cannot show stale data or another user's data.
 */
const CACHE = "branch-secretary-static-v1";

const PRECACHE_URLS = [
  "/offline.html",
  "/manifest.webmanifest",
  "/static/app.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-192.png",
  "/static/icons/icon-maskable-512.png",
  "/static/icons/apple-touch-icon.png",
];

const STATIC_EXTENSIONS = /\.(?:css|js|png|jpe?g|webp|gif|svg|ico|woff2?)$/i;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function isCacheableAsset(url) {
  if (url.origin !== self.location.origin) return false;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) return false;
  if (url.pathname === "/offline.html" || url.pathname === "/manifest.webmanifest") return true;
  if (!url.pathname.startsWith("/static/")) return false;
  return STATIC_EXTENSIONS.test(url.pathname);
}

async function networkOrOffline(request) {
  try {
    return await fetch(request);
  } catch (_error) {
    const cached = await caches.match("/offline.html");
    if (cached) return cached;
    return new Response("Offline", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response && response.ok && response.type === "basic") {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);
  if (cached) return cached;
  const fresh = await network;
  if (fresh) return fresh;
  return new Response("", { status: 504, statusText: "Offline" });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (request.mode === "navigate") {
    event.respondWith(networkOrOffline(request));
    return;
  }
  if (!isCacheableAsset(url)) return;
  event.respondWith(staleWhileRevalidate(request));
});
