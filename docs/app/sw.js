/* Trabajador de servicio: guarda la aplicación en el teléfono para que abra
   sin señal. Sólo funciona servida por http(s); desde un archivo local el
   navegador no registra ninguno, y ahí el respaldo es el propio archivo. */

// La versión cambia con lo que se guarda: al subir, el trabajador nuevo
// descarta la caché vieja y trae la tipografía.
var CACHE = "nefer-v2";
var PIEZAS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icono-192.png",
  "./icono-512.png",
  "./apple-touch-icon.png",
  // Sin esto la tipografía sólo estaría la primera vez, con señal.
  "./tipografia/barlow-400.woff2",
  "./tipografia/barlow-600.woff2",
  "./tipografia/barlow-700.woff2",
  "./tipografia/barlow-cond-600.woff2",
  "./tipografia/barlow-cond-700.woff2"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE)
      .then(function (c) { return c.addAll(PIEZAS); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (nombres) {
        return Promise.all(nombres.map(function (n) {
          return n === CACHE ? null : caches.delete(n);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var pedido = e.request;
  if (pedido.method !== "GET") return;

  // La navegación va primero a la red para recoger una versión nueva, y cae a
  // la copia guardada en cuanto no hay señal, que es lo normal en el patio.
  if (pedido.mode === "navigate") {
    e.respondWith(
      fetch(pedido)
        .then(function (r) {
          var copia = r.clone();
          caches.open(CACHE).then(function (c) { c.put("./index.html", copia); });
          return r;
        })
        .catch(function () {
          return caches.match("./index.html").then(function (r) {
            return r || caches.match("./");
          });
        })
    );
    return;
  }

  // El resto —iconos, manifiesto— desde la copia, que no cambia.
  e.respondWith(
    caches.match(pedido).then(function (r) {
      return r || fetch(pedido).then(function (red) {
        if (red && red.status === 200 && red.type === "basic") {
          var copia = red.clone();
          caches.open(CACHE).then(function (c) { c.put(pedido, copia); });
        }
        return red;
      });
    })
  );
});
