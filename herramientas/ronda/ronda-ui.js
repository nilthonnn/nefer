<script>
/* La pantalla. Tres decisiones que vienen del guante y del socavon:
 *
 * UN PUNTO A LA VEZ, A PANTALLA COMPLETA. Una lista de cinco filas con
 * casillas chicas se despacha con cinco toques sin levantar la vista, que es
 * lo contrario de una ronda. Un punto a la vez obliga a mirar la maquina.
 *
 * «NO PUDE VER» DEL MISMO TAMANO QUE «OK». Si es mas chico o esta mas
 * abajo, el operador marca OK, y un OK falso contamina la ronda entera.
 *
 * EL RELOJ NO AMENAZA. Mide y se guarda, pero no hay cuenta atras ni aviso
 * de «vas lento». Un reloj que castiga produce rondas rapidas, no rondas
 * buenas. Lo que se detecta es lo contrario, y se le dice al supervisor al
 * final, no al operador a mitad de la maquina.
 */
/* ronda:demo:inicio */
var PAUTA_DEMO = null;
/* ronda:demo:fin */

var app = document.getElementById("app");
var pauta = null, ejecucion = null, indice = 0, entroEn = 0, arranque = 0, reloj = null;

function esc(s) {
  return String(s === undefined || s === null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function mmss(s) {
  s = Math.max(0, Math.floor(s));
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}
function hoy() { return new Date().toISOString().slice(0, 10); }

// ------------------------------------------------------------- pantallas

function verInicio(error) {
  document.body.classList.remove("en-punto");
  pauta = null; ejecucion = null;
  if (reloj) { clearInterval(reloj); reloj = null; }
  app.innerHTML =
    '<h1>Ronda CIL</h1>' +
    '<p class="tenue">Limpiar · Inspeccionar · Lubricar. Medio minuto al ' +
    'arranque del turno. Limpiar <em>es</em> inspeccionar: la fuga y el perno ' +
    'flojo se ven cuando se quita la mugre, no antes.</p>' +
    (error ? '<div class="aviso peligro">' + esc(error) + '</div>' : '') +
    '<h2>Cargar la pauta</h2>' +
    '<button id="archivo" class="grande primary">Abrir pauta del equipo</button>' +
    '<p class="tenue">Un archivo <code>.json</code> que le pasa mantenimiento. ' +
    'No hace falta red.</p>' +
    (PAUTA_DEMO ? '<button id="demo">Probar con una pauta de ejemplo' +
      '<span class="tenue">' +
      'Es un taller inventado: la excavadora EX-220 no existe. Sirve para ' +
      'ver como funciona, no para registrar nada.</span></button>' : '') +
    '<div class="crece"></div>' +
    '<p class="tenue">FixMate · la ronda no sale de este telefono hasta que ' +
    'usted la exporte.</p>';

  var inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json"; inp.className = "oculto";
  document.body.appendChild(inp);
  document.getElementById("archivo").onclick = function () { inp.click(); };
  inp.onchange = function () {
    var f = inp.files && inp.files[0];
    if (!f) return;
    var lector = new FileReader();
    lector.onload = function () {
      try { empezar(JSON.parse(lector.result)); }
      catch (e) { verInicio("Ese archivo no es una pauta legible: " + e.message); }
    };
    lector.readAsText(f);
  };
  if (PAUTA_DEMO) {
    document.getElementById("demo").onclick = function () {
      empezar(JSON.parse(JSON.stringify(PAUTA_DEMO)));
    };
  }
}

function empezar(p) {
  if (!p || !p.puntos || !p.puntos.length) {
    return verInicio("La pauta no trae puntos.");
  }
  normalizarPauta(p);   // los ids los pone la regla, no la pantalla
  for (var i = 0; i < p.puntos.length; i++) {
    var q = p.puntos[i];
    if (!q.criterio) {
      return verInicio("El punto «" + (q.punto || q.id) + "» no tiene criterio " +
                       "de aceptacion. Sin criterio, cada operador juzga otra " +
                       "cosa y la pauta no mide nada.");
    }
  }
  pauta = p;
  verOperador();
}

function verOperador() {
  app.innerHTML =
    '<h1>' + esc(pauta.activo_codigo || "") + '</h1>' +
    '<p class="tenue">' + esc(pauta.nombre || "") + ' · ' +
    pauta.puntos.length + ' puntos</p>' +
    '<div class="tarjeta"><label><span class="tenue">Quien ejecuta</span>' +
    '<input type="text" id="op" placeholder="Nombre o ficha" autocomplete="name">' +
    '</label><p class="tenue" style="margin-top:8px">Una ronda sin responsable ' +
    'no se puede discutir despues.</p></div>' +
    '<button id="ir" class="grande primary">Empezar la ronda</button>' +
    '<div class="crece"></div>' +
    '<button id="volver">Cambiar de pauta</button>';
  document.getElementById("volver").onclick = function () { verInicio(); };
  document.getElementById("ir").onclick = function () {
    var nombre = (document.getElementById("op").value || "").trim();
    if (!nombre) { document.getElementById("op").focus(); return; }
    ejecucion = {
      id: (pauta.id || "ronda") + "-" + hoy() + "-" +
          Math.random().toString(36).slice(2, 7),
      checklist_id: pauta.id || "", activo_codigo: pauta.activo_codigo || "",
      operador: nombre, fecha: hoy(), items: [], anomalias: []
    };
    indice = 0; arranque = Date.now(); entroEn = Date.now();
    reloj = setInterval(function () {
      var e = document.getElementById("reloj");
      if (e) e.textContent = mmss((Date.now() - arranque) / 1000);
    }, 1000);
    verPunto();
  };
}

function verPunto() {
  if (indice >= pauta.puntos.length) return verResumen();
  document.body.classList.add("en-punto");
  var p = pauta.puntos[indice];
  var clase = CLASES[p.clase] || p.clase;
  app.innerHTML =
    '<div class="pie"><span>' + esc(pauta.activo_codigo) + ' · <b id="paso">' +
    (indice + 1) + ' / ' + pauta.puntos.length + '</b></span>' +
    '<span id="reloj">' + mmss((Date.now() - arranque) / 1000) + '</span></div>' +
    '<div class="progreso"><i style="width:' +
    (indice / pauta.puntos.length * 100) + '%"></i></div>' +
    '<span class="chip">' + esc(String(p.clase).toUpperCase()) + '</span>' +
    '<div class="punto">' + esc(p.punto) + '</div>' +
    '<div class="criterio">' + esc(p.criterio) + '</div>' +
    '<p class="tenue">' + esc(clase) + (p.segundos ? ' · ' + p.segundos + ' s previstos' : '') +
    ' · ' + (p.alcance_operador === false
      ? 'si hay algo, va el tecnico' : 'si hay algo, lo resuelve usted') + '</p>' +
    '<div class="crece"></div>' +
    '<button class="grande b-ok" data-r="ok">OK<span class="tenue">Cumple el criterio</span></button>' +
    '<button class="grande b-mal" data-r="nok">ANOMALIA<span class="tenue">Algo no esta como debe</span></button>' +
    '<button class="grande b-sin" data-r="sin_acceso">NO PUDE VER<span class="tenue">Guarda, marcha, altura</span></button>';
  Array.prototype.forEach.call(app.querySelectorAll("button[data-r]"), function (b) {
    b.onclick = function () { responder(b.getAttribute("data-r")); };
  });
}

/** Los segundos se toman AL TOCAR el boton, antes de abrir el dialogo: lo
 *  que tarda en escribir la nota no es tiempo de inspeccion. */
function responder(resultado) {
  var seg = Math.max(0, Math.round((Date.now() - entroEn) / 1000));
  if (resultado === "ok") return anotar("ok", "", seg);
  verNota(resultado, seg);
}

function anotar(resultado, observacion, segundos) {
  var p = pauta.puntos[indice];
  ejecucion.items.push({ punto_id: p.id, resultado: resultado,
                         observacion: observacion, segundos: segundos });
  indice += 1; entroEn = Date.now();
  verPunto();
}

var MOTIVOS = ["Guarda cerrada", "Maquina en marcha", "Sin acceso fisico", "Falta andamio"];

function verNota(resultado, seg) {
  var p = pauta.puntos[indice];
  var esAnomalia = resultado === "nok";
  var velo = document.createElement("div");
  velo.className = "velo";
  velo.innerHTML = '<div>' +
    '<p class="tenue">' + (esAnomalia ? 'Anomalia en' : 'No se pudo ver') + '</p>' +
    '<h3>' + esc(p.punto) + '</h3>' +
    (esAnomalia
      ? '<label><span class="tenue">Que vio</span><textarea id="nota" rows="3" ' +
        'placeholder="En sus palabras. No se normaliza."></textarea></label>' +
        '<p class="tenue" style="margin-top:8px">' +
        (p.alcance_operador === false
          ? 'Este punto esta fuera de su alcance en la pauta: la anomalia sale ' +
            'marcada para que vaya el tecnico.'
          : 'Este punto es de su alcance: resuelvalo y avise. Queda registrado igual.') +
        '</p>'
      : '<p class="tenue">Registrarlo vale. Un punto que nunca se puede ver no ' +
        'es un descuido suyo: es un defecto de la maquina o de la pauta, y asi ' +
        'se detecta.</p><div class="fila" id="motivos"></div>' +
        '<input type="text" id="nota" placeholder="O escriba el motivo" ' +
        'style="margin-top:10px">') +
    '<div class="fila" style="margin-top:12px">' +
    '<button id="atras">Volver</button>' +
    '<button id="listo" class="' + (esAnomalia ? 'b-mal' : 'b-sin') + '">' +
    (esAnomalia ? 'Etiquetar' : 'Registrar') + '</button></div></div>';
  document.body.appendChild(velo);

  if (!esAnomalia) {
    var cont = velo.querySelector("#motivos");
    MOTIVOS.forEach(function (m) {
      var b = document.createElement("button");
      b.textContent = m; b.style.fontSize = "14px";
      b.onclick = function () { velo.querySelector("#nota").value = m; };
      cont.appendChild(b);
    });
  }
  velo.querySelector("#atras").onclick = function () { velo.remove(); };
  velo.querySelector("#listo").onclick = function () {
    var txt = (velo.querySelector("#nota").value || "").trim();
    velo.remove();
    anotar(resultado, txt, seg);
  };
}

/* ------------------------------------------------- sacar el archivo
 *
 * Dentro del APK hay un puente nativo, y hace falta: en un WebView una
 * descarga que la propia pagina inicia —un enlace con `download` y una URL
 * `blob:`— no llega a ninguna parte, y ni siquiera dispara el escuchador de
 * descargas de Android. El boton pareceria funcionar y la ronda del turno no
 * se guardaria en ningun sitio. Asi que ahi los bytes se entregan y los
 * escribe Java en Descargas; en un navegador, el camino de siempre.
 */
var puente = (typeof window.PuenteFixMate !== "undefined" && window.PuenteFixMate)
             || null;

/** El puente habla base64, que es lo unico que cruza limpio de JavaScript a
 *  Java. Se trocea: `apply` con medio millon de argumentos tumba la pila. */
function aBase64(texto) {
  var bytes = new TextEncoder().encode(texto);
  var binario = "";
  var trozo = 0x8000;
  for (var i = 0; i < bytes.length; i += trozo) {
    binario += String.fromCharCode.apply(null, bytes.subarray(i, i + trozo));
  }
  return btoa(binario);
}

function avisarGuardado(texto, mal) {
  var caja = document.getElementById("aviso-guardado");
  if (!caja) return;
  caja.className = mal ? "aviso peligro" : "aviso";
  caja.textContent = texto;
  caja.style.display = "";
}

function guardarRonda(nombre, contenido) {
  if (puente) {
    var fallo = puente.guardar(nombre, aBase64(contenido), "application/json");
    // Cadena vacia es que salio bien. Cualquier otra cosa es el motivo, y se
    // dice: un operador mirando un boton que no hizo nada vuelve a tocarlo.
    if (fallo) return avisarGuardado(fallo, true);
    return avisarGuardado("Guardado en Descargas: " + nombre, false);
  }
  var blob = new Blob([contenido], { type: "application/json" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nombre;
  document.body.appendChild(a); a.click();
  setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  avisarGuardado("Archivo generado: " + nombre, false);
}

/** El boton de atras del telefono, cuando la ronda corre dentro del APK.
 *
 * Devuelve cierto si habia algo que cerrar. Falso deja que Android aplique su
 * regla de dos toques para salir: cerrar de un toque a mitad de una ronda
 * seria perder el turno entero, y el operador no tiene como recuperarlo.
 */
function atras() {
  var velo = document.querySelector(".velo");
  if (velo) { velo.remove(); return true; }
  return false;
}

function verResumen() {
  document.body.classList.remove("en-punto");
  if (reloj) { clearInterval(reloj); reloj = null; }
  var e = estadoRonda(ejecucion, pauta);
  var anomalias = anomaliasDe(ejecucion, pauta);
  ejecucion.anomalias = anomalias.map(function (a) { return a.id; });

  var html =
    '<h1>' + esc(pauta.activo_codigo) + '</h1>' +
    '<p class="tenue">' + esc(ejecucion.operador) + ' · ' + mmss(e.segundos) +
    ' en maquina' + (e.presupuesto_seg ? ' · presupuesto ' + mmss(e.presupuesto_seg) : '') +
    '</p>' +
    '<div class="tarjeta ' + (e.completa ? 'res-ok' : 'res-mal') + '">' +
    '<div class="titular">' +
    (e.completa ? 'Ronda completa' : 'Ronda incompleta') + '</div>' +
    '<p style="margin:6px 0 0">' + e.ok + ' OK · ' + e.nok + ' anomalia(s) · ' +
    e.sin_acceso + ' sin ver</p>' +
    (e.sin_acceso
      ? '<p class="tenue" style="margin-top:6px">Un punto que no se pudo ver no ' +
        'cuenta como visto. La ronda no vale como completa aunque esten los demas.</p>'
      : '') + '</div>';

  if (e.sospechosa_de_firma) {
    html += '<div class="aviso peligro"><b>▲ Demasiado rapida para haber sido ' +
      'ejecutada.</b> ' + e.segundos + ' s sobre un presupuesto de ' +
      e.presupuesto_seg + ' s. Criterio configurable de la planta, no una norma ' +
      '— pero conviene mirarlo antes de darla por buena.</div>';
  }

  if (anomalias.length) {
    html += '<h2>Anomalias</h2>';
    anomalias.forEach(function (a) {
      var tec = a.severidad === "detiene";
      html += '<div class="tarjeta ' + (tec ? 'peligro' : '') + '">' +
        '<span class="chip ' + (tec ? 'grave' : 'obs') + '">' +
        esc(SEVERIDADES[a.severidad] || a.severidad) + '</span>' +
        '<div style="font-weight:800;margin-top:6px">' + esc(a.componente) + '</div>' +
        '<p style="margin:4px 0 0">' + esc(a.descripcion) + '</p></div>';
    });
  } else {
    html += '<p class="tenue">Sin anomalias. Nada que etiquetar.</p>';
  }

  html += '<h2>Mandar a la oficina</h2>' +
    '<button id="bajar" class="grande primary">Guardar el archivo de la ronda</button>' +
    '<div id="aviso-guardado" class="aviso" style="display:none"></div>' +
    '<p class="tenue">Un <code>.json</code> que se manda por WhatsApp o correo. ' +
    'Ahi la oficina lo cruza con el analisis RCM: el telefono no lo hace porque ' +
    'el analisis no esta aqui.</p>' +
    '<div class="crece"></div>' +
    '<button id="otra">Otra maquina</button>';

  app.innerHTML = html;
  document.getElementById("otra").onclick = function () { verInicio(); };
  document.getElementById("bajar").onclick = function () {
    var datos = { ejecucion: ejecucion, anomalias: anomalias, estado: e };
    guardarRonda(ejecucion.id + ".json", JSON.stringify(datos, null, 2));
  };
}

verInicio();
</script>
</body>
</html>
