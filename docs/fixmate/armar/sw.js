/* Trabajador de servicio de Armar: guarda la pantalla en el telefono
   para que abra sin señal, que es la condicion para la que se hizo.

   Lo genera `herramientas/piel.py` a partir de la plantilla, con la misma
   logica que el de la app de diagnostico: la navegacion va primero a la red
   para recoger una version nueva y cae a la copia guardada en cuanto no hay
   señal, que es lo normal en el patio.

   Solo funciona servido por http(s). Desde un archivo suelto el navegador no
   registra ninguno, y ahi el respaldo es el propio archivo, que ya lo trae
   todo dentro.

   El nombre del cache lleva la huella de la pantalla: cuando cambia una
   linea, el telefono se trae la nueva en vez de quedarse con la vieja para
   siempre. */

var CACHE = "armar-6852988eb008";
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
