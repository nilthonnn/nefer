/* Guarda la app en el equipo para que abra sin conexión. El progreso vive en
   localStorage, así que abrir desde la copia no pierde nada. */
var CACHE = "ladderlab-2026-11-07b";
var PIEZAS = ["./", "./index.html", "./lecciones.js", "./energia.js", "./manifest.webmanifest", "./icono.svg", "./icono-192.png", "./icono-512.png"];

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
  // Red primero para recoger la versión nueva; sin señal, la copia guardada.
  e.respondWith(fetch(p).then(function (r) {
    if (r && r.ok && new URL(p.url).origin === self.location.origin) {
      var copia = r.clone();
      caches.open(CACHE).then(function (c) { c.put(p, copia); });
    }
    return r;
  }).catch(function () {
    return caches.match(p).then(function (r) { return r || (p.mode === "navigate" ? caches.match("./index.html") : undefined); });
  }));
});
