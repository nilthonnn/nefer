/* Trabajador de servicio: guarda la app en el teléfono para que abra sin
   señal. En el camal no hay cobertura, así que esto no es una mejora: es la
   condición para que la jornada se pueda registrar.

   Sólo funciona servida por http(s). Abierta como archivo suelto, el navegador
   no registra ninguno; ahí el respaldo es el propio archivo, que ya trae todo
   dentro. */

// La versión cambia con lo que se guarda: al subir, el trabajador nuevo
// descarta la caché vieja.
var CACHE = "camal-2026-09-17";
var PIEZAS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icono-192.png",
  "./icono-512.png",
  "./apple-touch-icon.png"
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

  // La navegación va primero a la red, para recoger una versión nueva, y cae a
  // la copia guardada en cuanto no hay señal. La jornada vive en el teléfono
  // —en localStorage—, así que abrir desde la copia no pierde nada.
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
