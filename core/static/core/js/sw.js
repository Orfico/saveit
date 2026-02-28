// ============================================================================
// SERVICE WORKER - PWA Offline Support
// ============================================================================
// Enables offline functionality by caching:
// 1. Static assets (CSS, JS, icons)
// 2. Loyalty card pages for offline viewing
// 3. Barcode images (both Supabase and local /media/)
// ============================================================================

// Cache version - increment this to force cache refresh on all clients
const CACHE_VERSION = 'saveit-v4';

// Cache names for different content types
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const BARCODE_CACHE = `${CACHE_VERSION}-barcodes`;

// Static assets that should always be cached during install
const STATIC_ASSETS = [
  '/',
  '/static/core/css/dashboard.css',
  '/static/core/js/utils.js',
  '/static/core/icons/icon-192.png'
];

// ============================================================================
// INSTALL EVENT - Pre-cache essential static assets
// ============================================================================
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker v3...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// ============================================================================
// ACTIVATE EVENT - Clean up old caches from previous versions
// ============================================================================
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker v3...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name.startsWith('saveit-') && 
                         name !== STATIC_CACHE && 
                         name !== DYNAMIC_CACHE && 
                         name !== BARCODE_CACHE)
          .map(name => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// ============================================================================
// FETCH EVENT - Apply different caching strategies based on request type
// ============================================================================
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignore requests to other origins (except for barcodes from Supabase or local media)
  const isSameOrigin = url.origin === self.location.origin;
  const isSupabaseBarcode = url.hostname.includes('supabase.co') && url.pathname.includes('/barcodes/');
  
  if (!isSameOrigin && !isSupabaseBarcode) {
    return;
  }

  // ------------------------------------------------------------------------
  // STRATEGY 1: Barcode Images - Cache First (Offline Priority)
  // ------------------------------------------------------------------------
  // Both Supabase barcodes and local /media/barcodes/ should be cached
  const isLocalBarcode = url.pathname.startsWith('/media/barcodes/');
  
  if ((isSupabaseBarcode || isLocalBarcode) && request.method === 'GET') {
    event.respondWith(
      caches.open(BARCODE_CACHE).then(cache => {
        return cache.match(request).then(cachedResponse => {
          if (cachedResponse) {
            console.log('[SW] Serving barcode from cache:', url.pathname);
            return cachedResponse;
          }
          
          // Not in cache, fetch and cache for future offline use
          return fetch(request).then(response => {
            if (response && response.status === 200) {
              const responseClone = response.clone();
              cache.put(request, responseClone);
              console.log('[SW] Cached barcode:', url.pathname);
            }
            return response;
          }).catch(() => {
            console.log('[SW] Barcode unavailable offline');
            return new Response('Barcode unavailable offline', { status: 503 });
          });
        });
      })
    );
    return;
  }

  // ------------------------------------------------------------------------
  // STRATEGY 2: API Mutations - Network Only (No Cache)
  // ------------------------------------------------------------------------
  if (url.pathname.includes('/create/') || url.pathname.includes('/delete/')) {
    event.respondWith(fetch(request));
    return;
  }

  // ------------------------------------------------------------------------
  // STRATEGY 3: Loyalty Card Pages - Network First with Cache Fallback
  // ------------------------------------------------------------------------
  if (url.pathname.startsWith('/loyalty-cards/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => {
              cache.put(request, responseClone);
              console.log('[SW] Cached loyalty card page:', url.pathname);
            });
          }
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
              console.log('[SW] Serving cached loyalty card page:', url.pathname);
              return cachedResponse;
            }
            // No cache available, show fallback
            return new Response('Page unavailable offline', { 
              status: 503,
              headers: { 'Content-Type': 'text/html' }
            });
          });
        })
    );
    return;
  }

  // ------------------------------------------------------------------------
  // DEFAULT STRATEGY: Network First with Cache Fallback
  // ------------------------------------------------------------------------
  event.respondWith(
    fetch(request)
      .then(response => {
        if (response && response.status === 200 && request.method === 'GET') {
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE).then(cache => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request);
      })
  );
});