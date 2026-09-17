/* Trabajador de servicio de FixMate: guarda la app en el teléfono para que
   abra sin señal, que es la condición para la que se hizo. Sólo funciona
   servida por http(s); desde un archivo suelto el navegador no registra
   ninguno, y ahí el respaldo es el propio archivo.

   No cachea la tipografía porque esta app no aloja ninguna: usa la del
   aparato, que a contraluz y con guantes se lee igual y cuesta cero bytes. */

var CACHE = "fixmate-2026-09-17";
var PIEZAS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icono-192.png",
  "./icono-512.png",
  "./icono-512-recortable.png",
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

  // La navegación va primero a la red para recoger una versión nueva, y cae
  // a la copia guardada en cuanto no hay señal, que es lo normal en el patio.
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
