const CACHE = 'allalarm-6a4701ca12765655';
const CORE = ['/', '/offline.html', '/style.css', '/app.js', '/pwa.js', '/manifest.webmanifest', '/fonts/LINESeedJP_OTF_Rg.woff2', '/fonts/LINESeedJP_OTF_Bd.woff2', '/assets/cybersecurity-news.png', '/icons/app/icon-192.png', '/icons/app/icon-512.png'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE))));
self.addEventListener('activate', event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('allalarm-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  // Prefer current news and assets; cached news is only a fallback when disconnected.
  event.respondWith(fetch(req).then(response => {
    if (response.ok) { const copy = response.clone(); event.waitUntil(caches.open(CACHE).then(cache => cache.put(req, copy))); }
    return response;
  }).catch(async () => {
    const cached = await caches.match(req);
    if (cached) return cached;
    if (req.mode === 'navigate') return caches.match('/offline.html');
    return Response.error();
  }));
});
