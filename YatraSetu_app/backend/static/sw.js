// Minimal service worker so the app is installable (PWA). Network-first; API calls are never cached.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()))
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone(); caches.open('ys-v1').then((c) => c.put(e.request, copy)); return r
  }).catch(() => caches.match(e.request)))
})
