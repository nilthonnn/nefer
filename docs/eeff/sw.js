/* Guarda la app en el equipo para que abra sin conexión. Los saldos viven
   en localStorage, así que abrir desde la copia no pierde nada. */
var CACHE = "eeff-mype-2026-10-03";
var PIEZAS = ["./", "./index.html", "./manifest.webmanifest", "./icono.svg", "./icono-192.png", "./icono-512.png"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE)
    .then(function (c) { return c.addAll(PIEZAS); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys()
    .then(function (ns) { return Promise.all(ns.map(function (n) { return n === CACHE ? null : caches.delete(n); })); })
    .then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var p = e.request;
  if (p.method !== "GET") return;
  // La página va primero a la red, para recoger la versión nueva, y cae a la copia sin señal.
  if (p.mode === "navigate") {
    e.respondWith(fetch(p).then(function (r) {
      var copia = r.clone();
      caches.open(CACHE).then(function (c) { c.put("./index.html", copia); });
      return r;
    }).catch(function () {
      return caches.match("./index.html").then(function (r) { return r || caches.match("./"); });
    }));
    return;
  }
  e.respondWith(caches.match(p).then(function (r) { return r || fetch(p); }));
});
