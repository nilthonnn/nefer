/* Proyectos integradores: una máquina completa.

   Línea de transferencia: las cajas llegan por la faja 1, un cilindro
   neumático las empuja a la faja 2 y esta las despacha. Tres sensores
   (fin de faja 1, entrada de faja 2 y fin de carrera del cilindro) y un
   cuarto al final de la faja 2 para contar.

   El MODELO DE PLANTA mueve las cajas de verdad: avanzan con la faja, se
   detienen contra el tope, viajan con el vástago y caen en la faja 2. Y
   detecta lo que en planta es un problema: una caja que llega contra el
   vástago extendido, o dos cajas que chocan en la transferencia. */

/* Se carga después de energia.js (usa HM, PLANTAS y maniobra) pero va antes de esa ruta. */
(function () {
  var i = NIVELES.findIndex(function (n) { return n.id === "energia"; });
  NIVELES.splice(i < 0 ? NIVELES.length : i, 0, { id: "proyectos", nombre: "Proyectos integradores", desc: "Una máquina completa: fajas, sensores y cilindro neumático." });
})();

var LINEA = {
  L: 0.16,        // largo de una caja, en fracciones del largo de la faja
  V1: 0.25,       // faja 1, fracción por segundo
  V2: 0.07,       // faja 2: más lenta, por eso hace falta el sensor 2
  SALIDA: 700,    // ms que tarda el cilindro en salir
  ENTRADA: 600,   // ms que tarda en volver (resorte)
  ZONA2: 0.20,    // lo que ve el sensor 2 al inicio de la faja 2
  FIN: 0.98,      // donde está el fin de carrera: ahí la caja ya quedó sobre la faja 2
  CADA: 1200      // ms entre cajas que llegan a la faja 1: se forma cola
};

PLANTAS.linea = {
  model: function (e) {
    var s = e.ps, L = LINEA.L, dt = e.dt;
    if (!s.b1) { s.b1 = [0.66, 0.42]; s.b2 = []; s.c = 0; s.att = null; s.prox = LINEA.CADA; s.despachadas = 0; s.empujes = 0; }
    var f1 = !!e.v["%Q0.1"], f2 = !!e.v["%Q0.0"], ord = !!e.v["%Q0.2"];

    /* cilindro de simple efecto: sale con aire, vuelve por resorte. Trabado: no pasa de la mitad. */
    var tope = e.pressed["%I0.4"] && e.tags.some(function (t) { return t.addr === "%I0.4" && t.falla; }) ? 0.5 : 1;
    s.c = ord ? Math.min(tope, s.c + dt / LINEA.SALIDA) : Math.max(0, s.c - dt / LINEA.ENTRADA);

    /* la caja que está contra el tope se va con el vástago */
    if (!s.att && s.b1.length && s.b1[0] >= 0.999 && s.c > 0.05) { s.b1.shift(); s.att = 1; }
    /* la caja queda en la faja 2 en el mismo punto donde actúa el fin de carrera:
       si el sensor actuara antes, el retorno cortaría el aire con la caja a medio camino */
    if (s.att && s.c >= LINEA.FIN) {
      for (var k = 0; k < s.b2.length; k++) if (s.b2[k] < L) e.fault = "Choque en la transferencia: la faja 2 todavía tenía una caja en la entrada";
      s.b2.push(0); s.att = null; s.empujes++;
    } else if (s.att && s.c < 0.02) { s.b1.unshift(1); s.att = null; }

    /* faja 1: las cajas avanzan juntas, sin montarse, hasta el tope */
    if (f1) for (var i = 0; i < s.b1.length; i++) {
      var antes = s.b1[i], lim = i === 0 ? 1 : s.b1[i - 1] - L;
      s.b1[i] = Math.min(lim, antes + LINEA.V1 * dt / 1000);
      if (i === 0 && antes < 0.999 && s.b1[0] >= 0.999 && s.c > 0.1)
        e.fault = "Una caja llegó contra el vástago extendido del cilindro";
    }
    /* faja 2: hacia el despacho */
    var s4 = false;
    if (f2) for (var j = 0; j < s.b2.length; j++) s.b2[j] += LINEA.V2 * dt / 1000;
    for (var m = s.b2.length - 1; m >= 0; m--) {
      if (s.b2[m] >= 0.9 && s.b2[m] < 1) s4 = true;
      if (s.b2[m] >= 1) { s.b2.splice(m, 1); s.despachadas++; }
    }
    /* llegan cajas nuevas a la faja 1 cuando hay sitio */
    s.prox += dt;
    if (s.prox >= LINEA.CADA) {
      var ult = s.b1.length ? s.b1[s.b1.length - 1] : 1;
      if (ult >= 2 * L + 0.02) { s.b1.push(L); s.prox = 0; }
    }

    e.forced["%I0.2"] = ((s.b1.length && s.b1[0] >= 0.999) || (s.att && s.c < 0.3)) ? 1 : 0;
    e.forced["%I0.3"] = s.b2.some(function (y) { return y < LINEA.ZONA2; }) ? 1 : 0;
    e.forced["%I0.4"] = s.c >= LINEA.FIN ? 1 : 0;
    e.forced["%I0.5"] = s4 ? 1 : 0;
  },

  hmi: function (e) {
    var s = e.ps, L = LINEA.L, X0 = 30, LARGO = 270, A = L * LARGO, c = s.c || 0;
    var off = -((e.t / 25) % 20);
    var faja = function (x1, x2, y, on, n) {
      return '<rect x="' + x1 + '" y="' + (y - 26) + '" width="' + (x2 - x1) + '" height="52" rx="6" style="fill:var(--box);stroke:var(--line)"/>' +
        '<line x1="' + (x1 + 6) + '" y1="' + (y + 22) + '" x2="' + (x2 - 6) + '" y2="' + (y + 22) + '" style="stroke:' + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:3;stroke-dasharray:10 8;stroke-dashoffset:' + (on ? off : 0) + '"/>' +
        HM.tx(x1 + 4, y - 31, n, { a: "start", w: 700, s: 10.5 }) + HM.tx(x2 - 4, y - 31, on ? "marcha" : "parada", { a: "end", s: 9.5, c: on ? "var(--on)" : "var(--ink3)" });
    };
    var caja = function (x, y) {
      return '<rect x="' + x + '" y="' + (y - 20) + '" width="' + (A - 4) + '" height="40" rx="3" style="fill:#C8914F;stroke:#8A5A25;stroke-width:1.5"/><line x1="' + x + '" y1="' + (y - 4) + '" x2="' + (x + A - 4) + '" y2="' + (y - 4) + '" style="stroke:#8A5A25;opacity:.6"/>';
    };
    var sensor = function (x, y, on, n, ancla) {
      return '<circle cx="' + x + '" cy="' + y + '" r="6" style="fill:' + (on ? "#FFC83D" : "var(--lamp)") + ';stroke:var(--ink2)"/>' + HM.tx(x + (ancla === "end" ? -10 : 10), y + 4, n, { a: ancla || "start", s: 9.5, w: 700, c: on ? "#B07800" : "var(--ink3)" });
    };
    var y1 = 62, y2 = 178, finX = X0 + LARGO, h = "";
    h += faja(X0, finX, y1, e.v["%Q0.1"], "Faja 1 (llegada)") + faja(X0, finX, y2, e.v["%Q0.0"], "Faja 2 (despacho) ←");
    (s.b1 || []).forEach(function (p) { h += caja(X0 + p * LARGO - A + 2, y1); });
    (s.b2 || []).forEach(function (q) { var xr = finX - q * LARGO; h += caja(xr - A + 2, y2); });
    if (s.att) h += caja(finX - A + 2, y1 + c * (y2 - y1));
    /* cilindro: cuerpo sobre el fin de la faja 1, el vástago empuja hacia abajo */
    var cx = finX - A / 2, punta = y1 - 22 + c * (y2 - y1);
    h += '<rect x="' + (cx - 16) + '" y="2" width="32" height="' + (y1 - 26) + '" rx="4" style="fill:var(--canvas);stroke:var(--ink2);stroke-width:2"/>' +
      '<line x1="' + cx + '" y1="' + (y1 - 24) + '" x2="' + cx + '" y2="' + punta + '" style="stroke:var(--ink);stroke-width:5"/>' +
      '<rect x="' + (cx - 20) + '" y="' + (punta - 3) + '" width="40" height="5" rx="2" style="fill:var(--ink)"/>' +
      HM.tx(cx - 24, 18, "Cilindro", { a: "end", s: 10, w: 700 }) + HM.tx(cx - 24, 30, e.v["%Q0.2"] ? "sale" : c > 0.02 ? "vuelve" : "recogido", { a: "end", s: 9.5, c: e.v["%Q0.2"] ? "var(--on)" : "var(--ink3)" });
    h += sensor(finX + 14, y1, e.v["%I0.2"], "S1 fin faja 1") + sensor(finX + 14, y2 - 6, e.v["%I0.3"], "S2 entrada faja 2") +
      sensor(finX + 14, y2 - 44, e.v["%I0.4"], "S3 fin de carrera") + sensor(X0 + 8, y2 + 36, e.v["%I0.5"], "S4 salida");
    h += HM.tx(395, 236, "Cajas despachadas: " + (s.despachadas || 0), { a: "end", w: 800, s: 12 });
    if (e.v["%Q0.3"]) h += HM.lamp(150, 232, true, "Lote completo", "var(--on)");
    if (e.v["%Q0.4"]) h += HM.lamp(150, 232, true, "Falla del cilindro", "var(--bad)");
    return HM.svg(250, h + HM.falla(e, 248));
  }
};

/* ---------------- variables de la línea ---------------- */
function TAGS_LINEA(extra) {
  return [TAG("%I0.0", "Parada", "push", "NA: pulsar = parar"), TAG("%I0.1", "Partida", "push"),
    TAG("%I0.2", "Sensor_1", "plant"), TAG("%I0.3", "Sensor_2", "plant"), TAG("%I0.4", "Sensor_3", "plant"),
    TAG("%M0.1", "Sistema"), TAG("%M0.2", "Retorno"),
    TAG("%Q0.0", "Faja_2"), TAG("%Q0.1", "Faja_1"), TAG("%Q0.2", "Cilindro")].concat(extra || []);
}
function SEG_LINEA() {
  return [SEG("Sistema en marcha (autorretención)", S(P([NO("%I0.1")], [NO("%M0.1")]), NC("%I0.0"), COIL("%M0.1"))),
    SEG("Faja 2: despacho", S(NO("%M0.1"), COIL("%Q0.0"))),
    SEG("Faja 1: avanza si no hay caja en el tope, la entrada de la faja 2 está libre y el cilindro está recogido", S(NO("%M0.1"), NC("%I0.2"), NC("%I0.3"), NC("%Q0.2"), COIL("%Q0.1"))),
    SEG("Cilindro: sale con la caja en el tope y se mantiene hasta el fin de carrera", S(NO("%M0.1"), P([NO("%I0.2")], [NO("%Q0.2")]), NC("%M0.2"), COIL("%Q0.2"))),
    SEG("Retorno: el fin de carrera manda a recoger el cilindro", S(NO("%I0.4"), COIL("%M0.2")))];
}
/* el corrector: arranca, deja trabajar la línea y exige cajas despachadas sin fallas */
function PASOS_LINEA(final) {
  return [
    { in: {}, t: 500, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "Línea parada: nada se mueve." },
    { in: { "%I0.1": 1 }, t: 200, ex: { "%M0.1": 1, "%Q0.0": 1, "%Q0.1": 1 }, d: "Partida: arrancan las dos fajas." },
    { in: { "%I0.1": 0 }, t: 1600, ex: { "%M0.1": 1, "%Q0.1": 0, "%Q0.2": 1 }, d: "Llega la primera caja al tope: la faja 1 para y el cilindro sale." },
    { in: {}, t: 900, ex: { "%Q0.2": 0, "@empujes": 1 }, d: "El cilindro llegó al fin de carrera, dejó la caja en la faja 2 y vuelve." },
    { in: {}, t: 30000, ex: { "@empujes": [5, 99], "@despachadas": [2, 99] }, d: "30 s de producción: al menos 5 cajas transferidas y 2 despachadas, sin choques." }
  ].concat(final || [
    { in: { "%I0.0": 1 }, t: 200, ex: { "%M0.1": 0, "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "Parada: todo se detiene." },
    { in: { "%I0.0": 0 }, t: 1000, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Al soltar Parada no arranca sola." }
  ]);
}

LECCIONES.push(
/* ==================================================================== */
{ id: "linea", nivel: "proyectos", titulo: "Proyecto: transferencia entre fajas con cilindro", min: 40,
  teoria: `
<p>Hasta aquí cada lección era una pieza. Esta es una <b>máquina completa</b>, de las que se ven en una planta de
envasado, en el despacho de un almacén o moviendo las cajas de testigos en el laboratorio de una mina:</p>
<ol>
  <li>Las cajas llegan por la <b>faja 1</b> hasta un <b>tope</b>. Ahí las ve el <b>sensor 1</b>.</li>
  <li>Un <b>cilindro neumático</b> empuja la caja a la <b>faja 2</b>. El <b>sensor 3</b> es su <b>fin de carrera</b>: avisa que el vástago llegó afuera.</li>
  <li>La faja 2 se lleva la caja. El <b>sensor 2</b> vigila su entrada: mientras haya una caja ahí, no se debe empujar otra.</li>
</ol>
<h3>El programa, segmento por segmento</h3>
<table class="t">
<tr><th>Segmento</th><th>Qué hace</th><th>Lo aprendiste en</th></tr>
<tr><td>Sistema <code>%M0.1</code></td><td>Partida con autorretención, Parada la corta</td><td>Marcha‑paro</td></tr>
<tr><td>Faja 2 <code>%Q0.0</code></td><td>Corre mientras el sistema esté en marcha</td><td>Contactos</td></tr>
<tr><td>Faja 1 <code>%Q0.1</code></td><td>Corre si <b>no</b> hay caja en el tope, <b>no</b> hay caja en la entrada de la faja 2 y el cilindro está <b>recogido</b>: tres contactos NC en serie = tres permisos</td><td>Serie y paralelo</td></tr>
<tr><td>Cilindro <code>%Q0.2</code></td><td>Sale con el sensor 1 y <b>se mantiene a sí mismo</b> (autorretención con su propio contacto) hasta que llega el retorno</td><td>Autorretención</td></tr>
<tr><td>Retorno <code>%M0.2</code></td><td>El fin de carrera corta la autorretención del cilindro y este vuelve por resorte</td><td>Contactos NC</td></tr>
</table>
<div class="tip"><b>¿Por qué el cilindro necesita su propia autorretención?</b> En cuanto la caja se mueve, el sensor 1
deja de verla. Sin el contacto <code>%Q0.2</code> en paralelo, el cilindro volvería a mitad de camino y la caja se quedaría
entre las dos fajas.</div>
<div class="tip"><b>¿Y el NC del sensor 1 en la faja 1?</b> Es redundante con el NC del cilindro (en cuanto el sensor 1
ve la caja, el cilindro sale y eso ya para la faja), pero es <b>defensa en profundidad</b>: si alguien cambia el segmento del
cilindro, la faja igual no arrastra la caja contra el tope.</div>
<div class="tip"><b>¿Y por qué la faja 1 espera al sensor 2?</b> La faja 2 es más lenta. Si la faja 1 trae la siguiente caja
antes de que la anterior salga de la entrada, el cilindro empujaría una caja encima de otra.</div>
<p><b>Ojo con la Parada:</b> en esta máquina el pulsador de parada está cableado <b>NA</b> y en el programa se usa un
contacto <b>NC</b>. Funciona, pero si se corta el cable nadie puede pararla. En planta se prefiere el paro cableado NC
(lección <i>Marcha‑paro</i>) y la emergencia por un circuito de seguridad.</p>
<p>El ejemplo es el programa completo. Pulsa <b>Partida</b> y mira el HMI: las cajas avanzan, el cilindro empuja, la faja 2
despacha. Prueba a borrar un contacto en modo Editar y verás qué falla en la planta.</p>`,
  ejemplo: { planta: "linea", tags: TAGS_LINEA(), prog: SEG_LINEA() },
  reto: { planta: "linea",
    enunciado: "Programa la línea completa desde cero, con las variables de la tabla. <b>Sistema</b> <code>%M0.1</code>: Partida con autorretención, Parada (NA en campo) la corta. <b>Faja 2</b> <code>%Q0.0</code> con el sistema. <b>Faja 1</b> <code>%Q0.1</code> con el sistema, sin caja en el tope (<code>Sensor_1</code>), con la entrada de la faja 2 libre (<code>Sensor_2</code>) y con el cilindro recogido. <b>Cilindro</b> <code>%Q0.2</code>: sale con la caja en el tope y se mantiene hasta el <b>Retorno</b> <code>%M0.2</code>, que da el fin de carrera <code>Sensor_3</code>. <i>El modelo de planta detecta cajas contra el vástago y choques en la transferencia.</i>",
    tags: TAGS_LINEA(),
    inicio: [SEG("Sistema en marcha", S(P([NO("%I0.1")], [NO("%M0.1")]), NC("%I0.0"), COIL("%M0.1"))), SEG("Faja 2", S()), SEG("Faja 1", S()), SEG("Cilindro", S()), SEG("Retorno", S())],
    solucion: SEG_LINEA(),
    pasos: PASOS_LINEA() },
  quiz: [
    { q: "¿Por qué el cilindro tiene un contacto de su propia salida en paralelo con el sensor 1?", o: ["Para que salga más rápido", "Porque el sensor 1 deja de ver la caja al moverse y el cilindro volvería a mitad de camino", "Por estética"], a: 1, e: "La autorretención lo mantiene hasta el fin de carrera." },
    { q: "La faja 1 tiene tres contactos NC en serie. Eso significa que…", o: ["Basta que uno se cumpla para que corra", "Corre solo si se cumplen los tres permisos", "Nunca corre"], a: 1, e: "Serie = AND: tope libre, entrada de faja 2 libre y cilindro recogido." },
    { q: "¿Qué pasa si la faja 1 sigue corriendo mientras el cilindro está afuera?", o: ["Nada", "La siguiente caja llega contra el vástago", "La faja 2 se detiene"], a: 1, e: "Por eso la faja 1 lleva el NC de Cilindro." },
    { q: "El fin de carrera (sensor 3) sirve para…", o: ["Contar cajas", "Saber que el vástago llegó afuera y mandarlo a volver", "Arrancar la faja 2"], a: 1, e: "Sin él, el cilindro no sabría cuándo volver." }
  ] },
/* ==================================================================== */
{ id: "diagnostico", nivel: "proyectos", titulo: "Reto de diagnóstico: encuentra los errores", min: 25,
  teoria: `
<p>En planta casi nunca se programa desde cero: se <b>encuentra la falla</b> en un programa que alguien más escribió. El
programa de esta lección <b>parece</b> el de la línea, pero tiene <b>dos errores</b>. Tu trabajo es encontrarlos y corregirlos.</p>
<h3>Método</h3>
<ol>
  <li><b>Observa el síntoma</b> en el HMI: ¿qué hace la máquina que no debería?</li>
  <li><b>Sigue la corriente</b> en el segmento de la salida que se porta mal: ¿qué contacto conduce cuando no debería, o al revés?</li>
  <li><b>Compara con la intención</b>: ¿ese contacto debía ser NA o NC? ¿Falta una rama?</li>
  <li><b>Corrige una cosa a la vez</b> y vuelve a probar.</li>
</ol>
<div class="tip">Pistas, si las necesitas: uno de los errores hace que el cilindro vuelva antes de tiempo y la caja se quede
entre las fajas. El otro hace que la faja 1 se comporte justo al revés de lo que debe frente a la faja 2.</div>
<p>Arranca el ejemplo y observa. Luego ve al reto, corrige y comprueba.</p>`,
  ejemplo: { planta: "linea", tags: TAGS_LINEA(), prog: (function () { var p = SEG_LINEA(); p[2].net = S(NO("%M0.1"), NC("%I0.2"), NO("%I0.3"), NC("%Q0.2"), COIL("%Q0.1")); p[3].net = S(NO("%M0.1"), NO("%I0.2"), NC("%M0.2"), COIL("%Q0.2")); return p; })() },
  reto: { planta: "linea",
    enunciado: "Este programa tiene <b>dos errores</b>. Encuéntralos con el HMI y la vista online, corrígelos y comprueba. La línea debe funcionar igual que en el proyecto anterior.",
    tags: TAGS_LINEA(),
    inicio: (function () { var p = SEG_LINEA(); p[2].net = S(NO("%M0.1"), NC("%I0.2"), NO("%I0.3"), NC("%Q0.2"), COIL("%Q0.1")); p[3].net = S(NO("%M0.1"), NO("%I0.2"), NC("%M0.2"), COIL("%Q0.2")); return p; })(),
    solucion: SEG_LINEA(),
    pasos: PASOS_LINEA() },
  quiz: [
    { q: "Al diagnosticar, ¿qué haces primero?", o: ["Borrar el programa", "Observar el síntoma y seguir la corriente hasta la salida que falla", "Cambiar la CPU"], a: 1, e: "Síntoma → segmento → contacto." },
    { q: "Un contacto NA donde debía ir uno NC hace que la salida…", o: ["Funcione igual", "Se comporte al revés frente a esa señal", "No compile"], a: 1, e: "Conduce cuando debía bloquear, y al revés." }
  ] },
/* ==================================================================== */
{ id: "lote", nivel: "proyectos", titulo: "Reto: lotes de 5 cajas con contador", min: 30,
  teoria: `
<p>El cliente quiere despachar en <b>lotes de 5 cajas</b>. Al final de la faja 2 hay un <b>sensor 4</b> que ve pasar cada caja.</p>
<ul>
  <li>Un <b>CTU</b> cuenta los flancos del sensor 4 (cada caja que sale).</li>
  <li>Al llegar a 5, la <b>faja 1 deja de traer cajas</b> y se enciende la luz <b>Lote completo</b>.</li>
  <li>El operario cambia el pallet y pulsa <b>Nuevo lote</b>, que pone la cuenta a cero y todo sigue.</li>
</ul>
<div class="tip">Es la lección de contadores puesta a trabajar: el <code>Q</code> del contador se usa como un permiso más (un
contacto NC en serie) en la faja 1, y como la bobina de la luz.</div>`,
  ejemplo: { planta: "linea", tags: TAGS_LINEA([TAG("%I0.5", "Sensor_4", "plant"), TAG("%I0.6", "Nuevo_Lote", "push"), TAG("%Q0.3", "Lote_Completo")]), prog: SEG_LINEA().concat([SEG("Cuenta las cajas que salen (sin usar todavía)", S(NO("%I0.5"), CTU("C_Lote", "%I0.6", 5)))]) },
  reto: { planta: "linea",
    enunciado: "Agrega a la línea el control de lotes: cuenta con un <b>CTU</b> <code>C_Lote</code> las cajas que pasan por <code>Sensor_4</code> <code>%I0.5</code>, con <b>PV = 5</b> y reset con <code>Nuevo_Lote</code> <code>%I0.6</code>. Con el lote completo, la <b>faja 1 se detiene</b> y se enciende <code>Lote_Completo</code> <code>%Q0.3</code>. <i>La faja 2 sigue despachando lo que ya lleva.</i>",
    tags: TAGS_LINEA([TAG("%I0.5", "Sensor_4", "plant"), TAG("%I0.6", "Nuevo_Lote", "push"), TAG("%Q0.3", "Lote_Completo")]),
    inicio: SEG_LINEA().concat([SEG("Contar cajas", S()), SEG("Luz de lote completo", S())]),
    solucion: (function () { var p = SEG_LINEA(); p[2].net.items.splice(4, 0, NC("C_Lote.Q"));
      return p.concat([SEG("Contar cajas", S(NO("%I0.5"), CTU("C_Lote", "%I0.6", 5))), SEG("Luz de lote completo", S(NO("C_Lote.Q"), COIL("%Q0.3")))]); })(),
    pasos: [
      { in: {}, t: 300, ex: { "%Q0.3": 0 }, d: "Línea parada, sin lote." },
      { in: { "%I0.1": 1 }, t: 200, ex: { "%Q0.0": 1, "%Q0.1": 1 }, d: "Partida." },
      { in: { "%I0.1": 0 }, t: 20000, ex: { "%Q0.3": 0, "@despachadas": [1, 4] }, d: "20 s: van menos de 5 cajas despachadas; el lote sigue abierto." },
      { in: {}, t: 30000, ex: { "%Q0.3": 1, "%Q0.1": 0, "@despachadas": [5, 99] }, d: "Al pasar la 5.ª caja: lote completo y la faja 1 detenida." },
      { in: {}, t: 1100, ex: { "%Q0.3": 1, "%Q0.1": 0 }, d: "La faja 1 sigue detenida esperando al operario…" },
      { in: {}, t: 1100, ex: { "%Q0.1": 0 }, d: "…detenida…" },
      { in: {}, t: 1100, ex: { "%Q0.1": 0 }, d: "…detenida…" },
      { in: {}, t: 1100, ex: { "%Q0.1": 0 }, d: "…detenida…" },
      { in: {}, t: 1100, ex: { "%Q0.3": 1, "%Q0.1": 0 }, d: "…y detenida mientras no llegue el operario." },
      { in: { "%I0.6": 1 }, t: 200, ex: { "%Q0.3": 0 }, d: "Nuevo lote: la cuenta vuelve a cero." },
      { in: { "%I0.6": 0 }, t: 1500, ex: { "%Q0.3": 0, "%M0.1": 1 }, d: "La línea sigue trabajando." }
    ] },
  quiz: [
    { q: "¿Qué cuenta el CTU en este reto?", o: ["El tiempo", "Los flancos del sensor 4: una cuenta por caja", "Las veces que sale el cilindro"], a: 1, e: "CU cuenta flancos positivos." },
    { q: "¿Dónde conviene usar C_Lote.Q para detener la llegada de cajas?", o: ["En la faja 2", "Como contacto NC en serie en la faja 1", "En el retorno"], a: 1, e: "Es un permiso más de la faja 1." }
  ] },
/* ==================================================================== */
{ id: "falla_cilindro", nivel: "proyectos", titulo: "Reto: el cilindro se traba", min: 30,
  teoria: `
<p>Un cilindro neumático puede <b>trabarse</b>: falta de aire, un vástago doblado, una caja atascada. Con el programa del
proyecto, la máquina se quedaría esperando un fin de carrera que nunca llega: el cilindro afuera a medias y la faja 1
detenida, sin que nadie sepa por qué.</p>
<h3>Supervisión por tiempo</h3>
<ul>
  <li>Si el cilindro tiene la orden de salir y el <b>fin de carrera no llega en 2 s</b>, es una falla.</li>
  <li>La falla se <b>memoriza</b> (Set), <b>retira la orden</b> del cilindro (que vuelve por resorte) y <b>detiene la faja 1</b>.</li>
  <li>El operario revisa, y con <b>Reconocer</b> se borra la alarma y la línea sigue.</li>
</ul>
<div class="tip">Es la misma idea que la supervisión de discrepancia de interruptores de la ruta minera: una orden sin su
confirmación en un tiempo razonable es una falla, no algo que esperar para siempre.</div>
<p>En el simulador, el botón de <code>Sensor_3</code> dice <i>pulsa = el cilindro se traba</i>: con él pulsado, el vástago no pasa de la mitad.</p>`,
  ejemplo: { planta: "linea", tags: TAGS_LINEA().map(function (t) { return t.addr === "%I0.4" ? TAG("%I0.4", "Sensor_3", "plant", "pulsa = el cilindro se traba", { falla: 1 }) : t; }), prog: SEG_LINEA() },
  reto: { planta: "linea",
    enunciado: "Supervisa el cilindro: si <code>Cilindro</code> <code>%Q0.2</code> está activo y <code>Sensor_3</code> no llega en <b>2 s</b>, haz Set de <code>Falla_Cilindro</code> <code>%Q0.4</code>. La falla retira la orden del cilindro y detiene la faja 1. <code>Reconocer</code> <code>%I0.6</code> borra la alarma. <i>Pulsa Sensor_3 en el simulador para trabar el cilindro.</i>",
    tags: TAGS_LINEA([TAG("%I0.6", "Reconocer", "push"), TAG("%Q0.4", "Falla_Cilindro")]).map(function (t) { return t.addr === "%I0.4" ? TAG("%I0.4", "Sensor_3", "plant", "pulsa = el cilindro se traba", { falla: 1 }) : t; }),
    inicio: SEG_LINEA().concat([SEG("Supervisión del cilindro", S()), SEG("Reconocer", S())]),
    solucion: (function () { var p = SEG_LINEA(); p[2].net.items.splice(4, 0, NC("%Q0.4")); p[3].net.items.splice(3, 0, NC("%Q0.4"));
      return p.concat([SEG("Supervisión del cilindro", S(NO("%Q0.2"), NC("%I0.4"), TON("T_Cil", "T#2s"), SET("%Q0.4"))), SEG("Reconocer", S(NO("%I0.6"), RST("%Q0.4")))]); })(),
    pasos: [
      { in: {}, t: 300, ex: { "%Q0.4": 0 }, d: "Línea parada, sin falla." },
      { in: { "%I0.1": 1 }, t: 200, ex: { "%Q0.1": 1 }, d: "Partida." },
      { in: { "%I0.1": 0 }, t: 12000, ex: { "%Q0.4": 0, "@empujes": [2, 99] }, d: "Trabajo normal: el cilindro va y vuelve sin alarma." },
      { in: { "%I0.4": 1 }, t: 8000, ex: { "%Q0.4": 1, "%Q0.2": 0, "%Q0.1": 0 }, d: "El cilindro se traba: a los 2 s, alarma, orden retirada y faja 1 detenida." },
      { in: {}, t: 3000, ex: { "%Q0.4": 1, "%Q0.1": 0 }, d: "Sigue detenida hasta que alguien reconozca." },
      { in: { "%I0.4": 0, "%I0.6": 1 }, t: 300, ex: { "%Q0.4": 0 }, d: "Reparado y reconocido: alarma borrada." },
      { in: { "%I0.6": 0 }, t: 10000, ex: { "%Q0.4": 0, "@empujes": [4, 99] }, d: "La línea vuelve a trabajar normalmente." }
    ] },
  quiz: [
    { q: "¿Qué detecta la supervisión por tiempo?", o: ["Que el cilindro va muy rápido", "Una orden de salir sin fin de carrera en un tiempo razonable", "Que la faja está vacía"], a: 1, e: "Orden sin confirmación = falla." },
    { q: "Al detectar la falla, ¿por qué se retira la orden del cilindro?", o: ["Para que vuelva por resorte y no siga forzando", "Para ahorrar aire", "No hace falta"], a: 0, e: "Insistir con una pieza trabada la daña más." }
  ] }
);

/* orden pedagógico: los proyectos después del nivel avanzado y antes de la ruta minera */
(function () {
  var energia = LECCIONES.filter(function (l) { return l.nivel === "energia"; });
  var resto = LECCIONES.filter(function (l) { return l.nivel !== "energia"; });
  LECCIONES.length = 0; resto.concat(energia).forEach(function (l) { LECCIONES.push(l); });
})();
