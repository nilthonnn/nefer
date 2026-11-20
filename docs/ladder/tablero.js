/* Tablero de transferencia automática con tres interruptores, de básico a
   avanzado. Modelo inspirado en un tablero real de obra: relé de protección
   con display y LED de estado, CB-001 (red), CB-002 (grupo), CB-003 (salida
   al MCC MC-011), modo Manual/Automático y selector Local/Remoto con llave.

   Es una INTERPRETACIÓN DIDÁCTICA hecha desde una fotografía del frente del
   tablero: no reproduce el esquema ni la lógica real de ese equipo. En el
   equipo real esta lógica suele estar programada dentro del relé (CFC); aquí
   se practica en LAD, que es la misma lógica. */

(function () {
  var i = NIVELES.findIndex(function (n) { return n.id === "energia"; });
  NIVELES.splice(i < 0 ? NIVELES.length : i, 0, { id: "tablero", nombre: "Tablero de transferencia", desc: "Un tablero TTA de tres interruptores, de las luces de estado a la transferencia automática." });
})();

/* ---------------- planta: red, grupo, tres interruptores ---------------- */
PLANTAS.tta3 = {
  model: function (e) {
    var s = e.ps;
    s.run = e.v["%Q0.3"] ? (s.run || 0) + e.dt : 0;
    var gen = s.run >= 3000 && !e.pressed["%I0.1"];
    e.forced["%I0.1"] = gen ? 1 : 0;
    var red = !!e.v["%I0.0"], c1 = !!e.forced["%I0.2"], c2 = !!e.forced["%I0.3"], c3 = !!e.forced["%I0.4"];
    var barra = (red && c1) || (gen && c2);
    /* tensión residual de los motores del MCC si está conectado (CB-003 cerrado) */
    s.vres = barra ? 1 : (c3 ? (s.vres || 0) * Math.exp(-e.dt / 400) : 0);
    maniobra(e, s, "t1", "%Q0.0", "%I0.2", 100);
    maniobra(e, s, "t2", "%Q0.1", "%I0.3", 100, gen);
    maniobra(e, s, "t3", "%Q0.2", "%I0.4", 100);
    if (!gen && e.forced["%I0.3"]) e.forced["%I0.3"] = 0;
    var n1 = !!e.forced["%I0.2"], n2 = !!e.forced["%I0.3"];
    if (n1 && n2) e.fault = "CB-001 y CB-002 cerrados a la vez: red y grupo en paralelo sin sincronizar";
    if (!barra && s.vres > 0.25 && ((n1 && !c1 && !n2) || (n2 && !c2 && !n1)))
      e.fault = "Cierre contra la tensión residual de los motores del MCC (" + Math.round(s.vres * 100) + " %)";
  },
  hmi: function (e) {
    var v = function (a) { return !!e.v[a]; }, conLeds = e.tags.some(function (t) { return t.addr === "%Q1.0"; });
    var red = v("%I0.0"), gen = v("%I0.1"), c1 = v("%I0.2"), c2 = v("%I0.3"), c3 = v("%I0.4"), auto = v("%I0.5"), rem = v("%I0.6");
    /* los LED los enciende el programa del alumno; si la lección no los programa, se ven desde las señales */
    var leds = [["CB-001 Abierto", "%Q1.0", !c1], ["CB-001 Cerrado", "%Q1.1", c1], ["CB-002 Abierto", "%Q1.2", !c2], ["CB-002 Cerrado", "%Q1.3", c2],
      ["CB-003 Abierto", "%Q1.4", !c3], ["CB-003 Cerrado", "%Q1.5", c3], ["En Manual", "%Q1.6", !auto], ["En Automático", "%Q1.7", auto],
      ["Tensión red normal", "%Q2.0", red], ["Tensión red emerg.", "%Q2.1", gen]];
    var h = '<rect x="4" y="4" width="148" height="236" rx="6" style="fill:var(--box);stroke:var(--line)"/>';
    leds.forEach(function (l, i) {
      var on = conLeds ? v(l[1]) : l[2], y = 22 + i * 21;
      h += '<circle cx="18" cy="' + y + '" r="5" style="fill:' + (on ? "#3DDC74" : "var(--lamp)") + ';stroke:var(--line)"/>' + HM.tx(30, y + 3.5, l[0], { a: "start", s: 9.5, w: 600, c: on ? "var(--ink)" : "var(--ink3)" });
    });
    var bx = 170, by = 26, barra = (red && c1) || (gen && c2), cargaOn = barra && c3;
    h += '<rect x="160" y="4" width="236" height="196" rx="6" style="fill:var(--canvas);stroke:var(--ink3);stroke-width:2"/>' +
      HM.tx(278, 20, "Transferencia automática", { w: 800, s: 11 }) +
      HM.tx(bx, 36, "VR " + (red ? "480 V · 60 Hz" : "0 V"), { a: "start", s: 9.5, m: 1, c: red ? "var(--on)" : "var(--bad)" }) +
      HM.tx(390, 36, "VG " + (gen ? "480 V · 60 Hz" : "0 V"), { a: "end", s: 9.5, m: 1, c: gen ? "var(--on)" : "var(--ink3)" }) +
      HM.tx(215, 56, "RED", { w: 700, s: 10 }) + HM.ln(215, 60, 215, 82, red) + HM.brk(215, 92, c1, "CB-001") + HM.ln(215, 102, 215, 128, red && c1) +
      HM.gen(340, 64, gen, "") + HM.ln(340, 81, 340, 82, gen) + HM.brk(340, 92, c2, "CB-002") + HM.ln(340, 102, 340, 128, gen && c2) +
      HM.ln(205, 128, 350, 128, barra, 5) +
      HM.ln(278, 128, 278, 140, barra) + HM.brk(278, 150, c3, "CB-003") + HM.ln(278, 160, 278, 178, cargaOn) +
      HM.tx(278, 192, "MCC MC-011", { w: 700, s: 9.5, c: cargaOn ? "var(--on)" : "var(--ink3)" });
    h += HM.tx(170, 222, "Modo:", { a: "start", s: 10 }) + HM.tx(205, 222, auto ? "AUTOMÁTICO" : "MANUAL", { a: "start", s: 10, w: 800, c: auto ? "var(--on)" : "#B07800" }) +
      HM.tx(300, 222, "Llave:", { a: "start", s: 10 }) + HM.tx(335, 222, rem ? "REMOTO" : "LOCAL", { a: "start", s: 10, w: 800 });
    return HM.svg(250, h + HM.falla(e, 246));
  }
};
/* la lección de señalización usa el mismo frente, sin modelo: las señales las mueve el alumno */
PLANTAS.tta3vista = { hmi: PLANTAS.tta3.hmi };

/* ---------------- variables ---------------- */
var T3 = {
  red: TAG("%I0.0", "Red_Presente", "switch", "relé de tensión de red", { def: 1 }),
  gen: TAG("%I0.1", "Gen_Presente", "plant", "pulsa = el grupo no da tensión", { falla: 1 }),
  c1: TAG("%I0.2", "CB001_Cerrado", "plant"), c2: TAG("%I0.3", "CB002_Cerrado", "plant"), c3: TAG("%I0.4", "CB003_Cerrado", "plant"),
  auto: TAG("%I0.5", "Modo_Auto", "switch", "1 = automático"), rem: TAG("%I0.6", "Remoto", "switch", "llave: 1 = remoto"),
  q1: TAG("%Q0.0", "Cmd_CB001"), q2: TAG("%Q0.1", "Cmd_CB002"), q3: TAG("%Q0.2", "Cmd_CB003"), qg: TAG("%Q0.3", "Arranque_Gen")
};
var LEDS3 = [TAG("%Q1.0", "LED_CB001_Abierto"), TAG("%Q1.1", "LED_CB001_Cerrado"), TAG("%Q1.2", "LED_CB002_Abierto"), TAG("%Q1.3", "LED_CB002_Cerrado"),
  TAG("%Q1.4", "LED_CB003_Abierto"), TAG("%Q1.5", "LED_CB003_Cerrado"), TAG("%Q1.6", "LED_En_Manual"), TAG("%Q1.7", "LED_En_Automatico"),
  TAG("%Q2.0", "LED_Tension_Red"), TAG("%Q2.1", "LED_Tension_Emerg")];
function SEGS_LEDS() {
  return [SEG("CB-001 abierto", S(NC("%I0.2"), COIL("%Q1.0"))), SEG("CB-001 cerrado", S(NO("%I0.2"), COIL("%Q1.1"))),
    SEG("CB-002 abierto", S(NC("%I0.3"), COIL("%Q1.2"))), SEG("CB-002 cerrado", S(NO("%I0.3"), COIL("%Q1.3"))),
    SEG("CB-003 abierto", S(NC("%I0.4"), COIL("%Q1.4"))), SEG("CB-003 cerrado", S(NO("%I0.4"), COIL("%Q1.5"))),
    SEG("En manual", S(NC("%I0.5"), COIL("%Q1.6"))), SEG("En automático", S(NO("%I0.5"), COIL("%Q1.7"))),
    SEG("Presencia de tensión en red normal", S(NO("%I0.0"), COIL("%Q2.0"))), SEG("Presencia de tensión en red de emergencia", S(NO("%I0.1"), COIL("%Q2.1")))];
}
var MANUAL3 = [TAG("%I1.0", "Cerrar_CB001", "push"), TAG("%I1.1", "Abrir_CB001", "push"), TAG("%I1.2", "Cerrar_CB002", "push"), TAG("%I1.3", "Abrir_CB002", "push"),
  TAG("%I1.4", "Arrancar_Gen", "push"), TAG("%I1.5", "Parar_Gen", "push"), TAG("%M0.0", "Mando_Local")];
function SEGS_MANUAL() {
  return [SEG("Mando manual habilitado: modo Manual y llave en Local", S(NC("%I0.5"), NC("%I0.6"), COIL("%M0.0"))),
    SEG("CB-001 red: cerrar en manual local, abrir siempre, nunca con CB-002 cerrado", S(P([NO("%M0.0"), NO("%I1.0")], [NO("%Q0.0")]), NC("%I1.1"), NC("%I0.3"), NO("%I0.0"), COIL("%Q0.0"))),
    SEG("CB-002 grupo: cerrar en manual local con tensión de grupo, nunca con CB-001 cerrado", S(P([NO("%M0.0"), NO("%I1.2")], [NO("%Q0.1")]), NC("%I1.3"), NC("%I0.2"), NO("%I0.1"), COIL("%Q0.1"))),
    SEG("Grupo: arranque y parada manual", S(P([NO("%M0.0"), NO("%I1.4")], [NO("%Q0.3")]), NC("%I1.5"), COIL("%Q0.3"))),
    SEG("CB-003: salida al MCC siempre conectada", S(COIL("%Q0.2")))];
}
function SEGS_AUTO() {
  return [SEG("LED En manual", S(NC("%I0.5"), COIL("%Q1.6"))), SEG("LED En automático", S(NO("%I0.5"), COIL("%Q1.7"))),
    SEG("Falla de red confirmada (3 s)", S(NC("%I0.0"), TON("T_Falla", "T#3s"), COIL("%M0.0"))),
    SEG("Red estable (10 s)", S(NO("%I0.0"), TON("T_Estable", "T#10s"), COIL("%M0.1"))),
    SEG("Pedir grupo (solo en automático)", S(NO("%I0.5"), NO("%M0.0"), SET("%M0.2"))),
    SEG("Liberar grupo (solo en automático)", S(NO("%I0.5"), NO("%M0.1"), RST("%M0.2"))),
    SEG("Arranque del grupo + enfriamiento", S(NO("%M0.2"), TOF("T_Enfriar", "T#5s"), COIL("%Q0.3"))),
    SEG("CB-002: en automático por la secuencia; en manual se congela", S(P([NO("%I0.5"), NO("%M0.2"), NO("%I0.1"), NC("%I0.2")], [NC("%I0.5"), NO("%Q0.1")]), COIL("%Q0.1"))),
    SEG("CB-001: en automático con retardo; en manual se congela", S(P([NO("%I0.5"), NC("%M0.2"), NO("%I0.0"), NC("%I0.3"), TON("T_Retardo", "T#1s")], [NC("%I0.5"), NO("%Q0.0")]), COIL("%Q0.0"))),
    SEG("CB-003: salida al MCC", S(COIL("%Q0.2")))];
}

var AVISO_TABLERO = '<p class="sub" style="font-size:.82rem">Modelo didáctico hecho a partir de la foto del frente de un tablero real. No reproduce su esquema ni su lógica: para replicar un tablero concreto hace falta su plano unifilar y su lógica de control.</p>';

LECCIONES.push(
/* ==================================================================== */
{ id: "tta3_leds", nivel: "tablero", titulo: "Tablero TTA (básico): las luces de estado", min: 20,
  teoria: `
<p>El frente de un tablero de transferencia dice de un vistazo <b>cómo está la planta</b>. Este tiene un relé con display
y una columna de LED:</p>
<table class="t">
<tr><th>LED</th><th>Se enciende con</th></tr>
<tr><td>CB‑001 / CB‑002 / CB‑003 <b>Abierto</b></td><td>El contacto auxiliar del interruptor dice <b>abierto</b></td></tr>
<tr><td>CB‑001 / CB‑002 / CB‑003 <b>Cerrado</b></td><td>El contacto auxiliar dice <b>cerrado</b></td></tr>
<tr><td><b>En Manual</b> / <b>En Automático</b></td><td>El modo de la transferencia</td></tr>
<tr><td><b>Presencia de tensión en red normal</b></td><td>El relé de tensión de la red (funciones 27/59/81) da «red OK»</td></tr>
<tr><td><b>Presencia de tensión en red de emergencia</b></td><td>El grupo da tensión</td></tr>
</table>
<p>Los interruptores: <b>CB‑001</b> conecta la <b>red</b>, <b>CB‑002</b> el <b>grupo</b> y <b>CB‑003</b> la <b>salida al MCC</b> (centro de control de motores MC‑011) que alimenta la carga.</p>
<div class="tip"><b>Abierto y cerrado son dos LED, no uno.</b> Con una sola señal (el contacto 52a) basta un contacto NA para «cerrado» y
uno NC para «abierto». Los relés de protección usan además el contacto 52b: si <b>los dos</b> dicen lo mismo, el interruptor está a medio
camino o su cableado falló, y se alarma como <b>posición indeterminada</b>.</div>
<p>En el ejemplo las señales las mueves tú con los selectores: cierra y abre los interruptores y mira cómo responden los LED.</p>` + AVISO_TABLERO,
  mina: "Este tipo de tablero, con un relé de protección que también resuelve la transferencia, es habitual en salas eléctricas de mina: alimenta un MCC de planta y lo respalda con un grupo. Lo primero que hace un electricista al llegar es <b>leer el frente</b>: qué está cerrado, qué tensión hay y en qué modo está.",
  ejemplo: { planta: "tta3vista", tags: [TAG("%I0.0", "Red_Presente", "switch", "", { def: 1 }), TAG("%I0.1", "Gen_Presente", "switch"), TAG("%I0.2", "CB001_Cerrado", "switch"), TAG("%I0.3", "CB002_Cerrado", "switch"), TAG("%I0.4", "CB003_Cerrado", "switch"), TAG("%I0.5", "Modo_Auto", "switch")].concat(LEDS3), prog: SEGS_LEDS() },
  reto: { planta: "tta3vista",
    enunciado: "Programa los <b>10 LED</b> del frente del tablero a partir de las señales: abierto y cerrado de CB‑001, CB‑002 y CB‑003 (<code>%I0.2</code>…<code>%I0.4</code>), En Manual / En Automático (<code>Modo_Auto</code> <code>%I0.5</code>) y presencia de tensión en red normal y de emergencia (<code>%I0.0</code>, <code>%I0.1</code>). Los LED van de <code>%Q1.0</code> a <code>%Q1.7</code> y <code>%Q2.0</code>, <code>%Q2.1</code>, en el orden de la tabla.",
    tags: [TAG("%I0.0", "Red_Presente", "switch", "", { def: 1 }), TAG("%I0.1", "Gen_Presente", "switch"), TAG("%I0.2", "CB001_Cerrado", "switch"), TAG("%I0.3", "CB002_Cerrado", "switch"), TAG("%I0.4", "CB003_Cerrado", "switch"), TAG("%I0.5", "Modo_Auto", "switch")].concat(LEDS3),
    inicio: SEGS_LEDS().map(function (s, i) { return i < 2 ? s : SEG(s.title, S()); }),
    solucion: SEGS_LEDS(),
    pasos: [
      { in: {}, t: 100, ex: { "%Q1.0": 1, "%Q1.1": 0, "%Q1.2": 1, "%Q1.3": 0, "%Q1.4": 1, "%Q1.5": 0, "%Q1.6": 1, "%Q1.7": 0, "%Q2.0": 1, "%Q2.1": 0 }, d: "Todo abierto, en manual, con red: abiertos, En Manual y tensión de red." },
      { in: { "%I0.2": 1, "%I0.4": 1, "%I0.5": 1 }, t: 100, ex: { "%Q1.0": 0, "%Q1.1": 1, "%Q1.4": 0, "%Q1.5": 1, "%Q1.6": 0, "%Q1.7": 1 }, d: "CB‑001 y CB‑003 cerrados, en automático: operación normal por la red." },
      { in: { "%I0.0": 0, "%I0.2": 0 }, t: 100, ex: { "%Q2.0": 0, "%Q1.0": 1, "%Q1.1": 0 }, d: "Falla la red y CB‑001 abre." },
      { in: { "%I0.1": 1, "%I0.3": 1 }, t: 100, ex: { "%Q2.1": 1, "%Q1.2": 0, "%Q1.3": 1 }, d: "El grupo da tensión y CB‑002 cierra: carga por el grupo." },
      { in: { "%I0.5": 0 }, t: 100, ex: { "%Q1.6": 1, "%Q1.7": 0 }, d: "Se pasa a manual." }
    ] },
  quiz: [
    { q: "Con un solo contacto auxiliar (52a), ¿cómo se enciende el LED «Abierto»?", o: ["Con un contacto NA de 52a", "Con un contacto NC de 52a", "No se puede"], a: 1, e: "NC: conduce cuando el contacto dice 0 (abierto)." },
    { q: "Los contactos 52a y 52b dicen los dos «cerrado». ¿Qué indica?", o: ["Todo normal", "Posición indeterminada o cableado en falla", "Que el interruptor está en prueba"], a: 1, e: "Siempre deben ser opuestos." },
    { q: "¿Qué alimenta CB‑003 en este tablero?", o: ["La red", "El grupo", "La salida al MCC (la carga)"], a: 2, e: "CB‑001 red, CB‑002 grupo, CB‑003 la carga." }
  ] },
/* ==================================================================== */
{ id: "tta3_manual", nivel: "tablero", titulo: "Tablero TTA (intermedio): mando manual y llave Local/Remoto", min: 30,
  teoria: `
<p>En <b>modo Manual</b> la transferencia no decide nada: el electricista cierra y abre los interruptores y arranca el grupo desde el
frente del tablero. Pero solo si la <b>llave</b> está en <b>Local</b>: en <b>Remoto</b> manda la sala de control y la botonera del frente
no debe hacer nada.</p>
<h3>Reglas del mando manual</h3>
<ul>
  <li><b>Mando habilitado</b> = modo Manual <b>y</b> llave en Local. Una marca lo resume y se usa en cada orden de cierre.</li>
  <li><b>Cerrar</b> solo con el mando habilitado; la orden se mantiene (autorretención) hasta abrir.</li>
  <li><b>Abrir</b> se permite siempre.</li>
  <li><b>Enclavamiento:</b> CB‑001 no cierra si CB‑002 está cerrado, y al revés. Se usa el <b>contacto auxiliar</b> del otro, no su orden.</li>
  <li>CB‑001 solo cierra con tensión de red; CB‑002 solo con tensión de grupo.</li>
</ul>
<div class="tip"><b>Espera antes de cerrar la otra fuente.</b> Al abrir CB‑001, los motores del MCC siguen girando y generan
<b>tensión residual</b> en la barra durante un momento. Cerrar CB‑002 enseguida es cerrar contra esa tensión, fuera de fase: el modelo
de planta lo detecta. En automático lo resuelve la transición con retardo; en manual, el electricista espera unos segundos.</div>
<div class="tip">El enclavamiento por programa no reemplaza al mecánico ni al eléctrico: en el tablero real los dos interruptores de
fuente se enclavan también con un mecanismo y con contactos auxiliares en sus bobinas de cierre.</div>` + AVISO_TABLERO,
  mina: "En mantenimiento se trabaja en <b>Manual + Local</b>, con el equipo intervenido bloqueado y señalizado. La llave Local/Remoto existe para que, mientras alguien opera en el frente, la sala de control no pueda dar una orden sobre el mismo tablero.",
  ejemplo: { planta: "tta3", tags: [T3.red, T3.gen, T3.c1, T3.c2, T3.c3, T3.auto, T3.rem, T3.q1, T3.q2, T3.q3, T3.qg].concat(MANUAL3), prog: SEGS_MANUAL() },
  reto: { planta: "tta3",
    enunciado: "Programa el mando manual. <code>Mando_Local</code> <code>%M0.0</code> = modo Manual y llave en Local. <b>CB‑001</b> (<code>Cmd_CB001</code> <code>%Q0.0</code>): <code>Cerrar_CB001</code> con el mando habilitado y autorretención, <code>Abrir_CB001</code> siempre, nunca con <code>CB002_Cerrado</code>, solo con <code>Red_Presente</code>. <b>CB‑002</b> igual, con sus botones, el enclavamiento con <code>CB001_Cerrado</code> y <code>Gen_Presente</code>. <b>Grupo</b> (<code>Arranque_Gen</code> <code>%Q0.3</code>): arrancar con el mando habilitado y autorretención, parar siempre. <b>CB‑003</b> (<code>%Q0.2</code>) siempre cerrado.",
    tags: [T3.red, T3.gen, T3.c1, T3.c2, T3.c3, T3.auto, T3.rem, T3.q1, T3.q2, T3.q3, T3.qg].concat(MANUAL3),
    inicio: SEGS_MANUAL().map(function (s, i) { return i === 4 ? s : SEG(s.title, S()); }),
    solucion: SEGS_MANUAL(),
    nunca: [["%Q0.0", "%Q0.1"]],
    pasos: [
      { in: {}, t: 500, ex: { "%Q0.0": 0, "%Q0.1": 0, "%I0.4": 1 }, d: "Manual y local, todo abierto; la salida al MCC cerrada." },
      { in: { "%I1.0": 1 }, t: 200, ex: { "%Q0.0": 1 }, d: "Cerrar CB‑001." },
      { in: { "%I1.0": 0 }, t: 300, ex: { "%Q0.0": 1, "%I0.2": 1 }, d: "Se mantiene cerrado: la carga va por la red." },
      { in: { "%I1.2": 1 }, t: 200, ex: { "%Q0.1": 0 }, d: "Cerrar CB‑002 sin grupo y con CB‑001 cerrado: no cierra." },
      { in: { "%I1.2": 0, "%I1.4": 1 }, t: 200, ex: { "%Q0.3": 1 }, d: "Arrancar el grupo." },
      { in: { "%I1.4": 0 }, t: 3500, ex: { "%Q0.3": 1, "%I0.1": 1 }, d: "El grupo da tensión." },
      { in: { "%I1.2": 1 }, t: 300, ex: { "%Q0.1": 0 }, d: "Con CB‑001 cerrado, CB‑002 sigue sin cerrar: enclavamiento." },
      { in: { "%I1.2": 0, "%I1.1": 1 }, t: 200, ex: { "%Q0.0": 0 }, d: "Abrir CB‑001." },
      { in: { "%I1.1": 0 }, t: 1200, ex: { "%I0.2": 0 }, d: "CB‑001 confirmado abierto; el electricista espera 1 s a que caiga la tensión residual de los motores del MCC." },
      { in: { "%I1.2": 1 }, t: 200, ex: { "%Q0.1": 1 }, d: "Ahora sí cierra CB‑002." },
      { in: { "%I1.2": 0 }, t: 300, ex: { "%I0.3": 1, "%Q0.1": 1 }, d: "La carga va por el grupo." },
      { in: { "%I1.0": 1 }, t: 300, ex: { "%Q0.0": 0 }, d: "Cerrar CB‑001 con CB‑002 cerrado: no cierra." },
      { in: { "%I1.0": 0, "%I1.3": 1 }, t: 300, ex: { "%Q0.1": 0 }, d: "Abrir CB‑002." },
      { in: { "%I1.3": 0, "%I0.6": 1, "%I1.0": 1 }, t: 300, ex: { "%Q0.0": 0 }, d: "Llave en Remoto: la botonera del frente no cierra." },
      { in: { "%I1.0": 0, "%I0.6": 0, "%I0.5": 1 }, t: 100, ex: {}, d: "Llave en Local, pero modo Automático…" },
      { in: { "%I1.0": 1 }, t: 300, ex: { "%Q0.0": 0 }, d: "…en Automático la botonera tampoco cierra." },
      { in: { "%I1.0": 0, "%I0.5": 0 }, t: 100, ex: {}, d: "De vuelta a Manual." },
      { in: { "%I1.0": 1 }, t: 300, ex: { "%Q0.0": 1 }, d: "Manual y Local: CB‑001 cierra." }
    ] },
  quiz: [
    { q: "¿Cuándo debe aceptar órdenes la botonera del frente?", o: ["Siempre", "En modo Manual y con la llave en Local", "Solo en Remoto"], a: 1, e: "Las dos condiciones: lo resume la marca Mando_Local." },
    { q: "El enclavamiento entre CB‑001 y CB‑002 usa…", o: ["La orden del otro interruptor", "El contacto auxiliar del otro interruptor", "Un temporizador"], a: 1, e: "Lo que importa es el estado real, no la orden." },
    { q: "¿Por qué abrir se permite siempre?", o: ["Por comodidad", "Porque abrir lleva a un estado seguro y no debe depender del modo", "Para ahorrar contactos"], a: 1, e: "Quitar energía nunca debe quedar bloqueado." }
  ] },
/* ==================================================================== */
{ id: "tta3_auto", nivel: "tablero", titulo: "Tablero TTA (avanzado): transferencia automática con 3 interruptores", min: 40,
  teoria: `
<p>En <b>modo Automático</b> el tablero hace solo la transferencia y la retransferencia, como en la lección TTA pero con este tablero:</p>
<ol>
  <li>La red falla y la falla se <b>confirma</b> 3 s → se pide el grupo.</li>
  <li>CB‑001 abre (sin red no puede seguir cerrado) y, con <b>tensión de grupo</b> y <b>CB‑001 confirmado abierto</b>, cierra CB‑002.</li>
  <li>La red vuelve y se mantiene <b>estable</b> 10 s → se libera el grupo: abre CB‑002 y, 1 s después (transición con retardo), cierra CB‑001.</li>
  <li>El grupo sigue 5 s en vacío para <b>enfriarse</b> y para.</li>
</ol>
<h3>Y el modo Manual</h3>
<p>Al pasar a <b>Manual</b> el automático <b>no toca nada</b>: los interruptores se quedan como están (se «congelan») y el grupo sigue si
estaba en marcha. Por eso cada orden de cierre tiene <b>dos ramas</b>: la del automático (solo con Modo_Auto) y la que <b>mantiene</b> el
estado en manual (NC Modo_Auto + contacto de la propia orden). Y las decisiones de pedir o liberar el grupo solo se toman en automático.</p>
<div class="tip">El LED «En Manual» encendido en un tablero de respaldo es una señal de alerta: si la red falla así, nadie hará la
transferencia. En planta conviene llevar ese estado a la sala de control como alarma.</div>` + AVISO_TABLERO,
  mina: "En una sala eléctrica de mina, la transferencia en automático protege el MCC de bombas y servicios críticos de noche y en fin de semana. El paso a manual es parte de los procedimientos de mantenimiento, y volver a dejar el tablero en <b>Automático</b> es un ítem del checklist de cierre del trabajo.",
  ejemplo: { planta: "tta3", tags: [T3.red, T3.gen, T3.c1, T3.c2, T3.c3, TAG("%I0.5", "Modo_Auto", "switch", "1 = automático", { def: 1 }), T3.q1, T3.q2, T3.q3, T3.qg, LEDS3[6], LEDS3[7], TAG("%M0.0", "Falla_Red"), TAG("%M0.1", "Red_Estable"), TAG("%M0.2", "Pedir_Grupo")], prog: SEGS_AUTO() },
  reto: { planta: "tta3",
    enunciado: "Programa la transferencia automática del tablero. Modo <code>Modo_Auto</code> <code>%I0.5</code> = 1. Falla de red confirmada <b>3 s</b> → Set de <code>Pedir_Grupo</code> <code>%M0.2</code>; red estable <b>10 s</b> → Reset (las dos decisiones, solo en automático). <code>Arranque_Gen</code> con la petición y <b>5 s</b> de enfriamiento. <b>CB‑002</b>: en automático con la petición, tensión de grupo y CB‑001 abierto. <b>CB‑001</b>: en automático sin petición, con red, con CB‑002 abierto y <b>1 s</b> de retardo. En <b>Manual</b> los dos interruptores mantienen su estado. CB‑003 siempre cerrado y los LED En Manual / En Automático (<code>%Q1.6</code>, <code>%Q1.7</code>).",
    tags: [T3.red, T3.gen, T3.c1, T3.c2, T3.c3, TAG("%I0.5", "Modo_Auto", "switch", "1 = automático", { def: 1 }), T3.q1, T3.q2, T3.q3, T3.qg, LEDS3[6], LEDS3[7], TAG("%M0.0", "Falla_Red"), TAG("%M0.1", "Red_Estable"), TAG("%M0.2", "Pedir_Grupo")],
    inicio: SEGS_AUTO().map(function (s, i) { return i < 2 || i === 9 ? s : SEG(s.title, S()); }),
    solucion: SEGS_AUTO(),
    nunca: [["%Q0.0", "%Q0.1"]],
    pasos: [
      { in: {}, t: 1500, ex: { "%Q0.0": 1, "%I0.2": 1, "%Q1.7": 1, "%Q0.3": 0 }, d: "Automático con red: CB‑001 cerrado, la carga va por la red." },
      { in: { "%I0.0": 0 }, t: 1000, ex: { "%Q0.3": 0 }, d: "Microcorte de 1 s: el grupo no arranca." },
      { in: { "%I0.0": 1 }, t: 1500, ex: { "%Q0.0": 1 }, d: "Vuelve la red: CB‑001 cerrado otra vez." },
      { in: { "%I0.0": 0 }, t: 2800, ex: { "%Q0.3": 0 }, d: "Falla de red: a los 2,8 s todavía se confirma." },
      { in: {}, t: 400, ex: { "%Q0.3": 1 }, d: "3,2 s: arranca el grupo." },
      { in: {}, t: 3500, ex: { "%Q0.1": 1, "%I0.3": 1, "%Q0.0": 0 }, d: "Grupo en tensión: CB‑002 cerrado, la carga va por el grupo." },
      { in: { "%I0.5": 0 }, t: 1000, ex: { "%Q1.6": 1, "%Q0.1": 1, "%Q0.3": 1 }, d: "Se pasa a Manual: todo queda como estaba." },
      { in: { "%I0.0": 1 }, t: 16000, ex: { "%Q0.1": 1, "%I0.3": 1, "%Q0.0": 0, "%Q0.3": 1 }, d: "Vuelve la red estable, pero en Manual no hay retransferencia y el grupo sigue alimentando la carga." },
      { in: { "%I0.5": 1 }, t: 1500, ex: { "%Q0.1": 0, "%Q0.0": 1, "%I0.2": 1 }, d: "Vuelta a Automático: retransfiere a la red con retardo." },
      { in: {}, t: 5000, ex: { "%Q0.3": 0, "%Q0.0": 1 }, d: "Enfriamiento terminado: el grupo para." }
    ] },
  quiz: [
    { q: "En modo Manual, si la red falla…", o: ["Transfiere igual", "No pasa nada automático: los interruptores quedan como están", "Abre todo"], a: 1, e: "Por eso «En Manual» en un tablero de respaldo es una alerta." },
    { q: "¿Para qué sirve la rama con NC Modo_Auto y el contacto de la propia orden?", o: ["Para cerrar en manual", "Para mantener el estado del interruptor en Manual", "Para la transición con retardo"], a: 1, e: "Congela la orden al salir del automático." },
    { q: "¿Por qué Pedir/Liberar el grupo solo se decide en automático?", o: ["Para que en Manual el grupo no se pare con un interruptor cerrado sobre él", "Por costumbre", "Para ahorrar combustible"], a: 0, e: "Si en manual se liberara el grupo, quedaría CB‑002 cerrado sobre un grupo parado." }
  ] }
);

/* guías «¿Cómo se resuelve?» */
var GUIAS3 = {
  tta3_leds: { estrategia: "<p>Cada LED es un segmento de un solo contacto: <b>NA</b> para el LED que se enciende con la señal en 1 y <b>NC</b> para el que se enciende con la señal en 0. Abierto y cerrado de un mismo interruptor salen de la misma señal, con contactos opuestos.</p>" },
  tta3_manual: { estrategia: "<p>Primero una marca <b>Mando_Local</b> (Manual y Local). Después cada orden con el patrón marcha‑paro: <b>(Mando_Local y Cerrar) o la propia orden</b>, en serie con Abrir (NC), el enclavamiento con el otro interruptor (NC del auxiliar) y la tensión de su fuente.</p>",
    notas: { 0: "Dos NC en serie: modo no automático y llave no remota.", 1: "El Mando_Local va dentro de la rama de cerrar, no fuera: así abrir funciona en cualquier modo.", 2: "Es CB‑001 en espejo: con sus botones, Gen_Presente y el auxiliar de CB‑001." } },
  tta3_auto: { estrategia: "<p>Como la TTA de la ruta minera, pero con <b>modo</b>: las decisiones (Set/Reset de Pedir_Grupo) llevan Modo_Auto, y cada orden de interruptor tiene una rama automática y otra que la <b>congela</b> en manual.</p>",
    notas: { 4: "Solo en automático se pide el grupo.", 5: "Solo en automático se libera: en manual el grupo no se para con CB‑002 cerrado sobre él.",
      7: "Rama 1 (automático): petición, tensión de grupo y CB‑001 abierto. Rama 2 (manual): NC Modo_Auto + la propia orden, que mantiene lo que había.",
      8: "Rama automática con el TON de 1 s al final: transición con retardo para la tensión residual de los motores del MCC." } }
};
LECCIONES.forEach(function (L) { if (L.reto && GUIAS3[L.id]) L.reto.guia = GUIAS3[L.id]; });

/* orden: el tablero va antes de la ruta de la mina */
(function () {
  var energia = LECCIONES.filter(function (l) { return l.nivel === "energia"; });
  var resto = LECCIONES.filter(function (l) { return l.nivel !== "energia"; });
  LECCIONES.length = 0; resto.concat(energia).forEach(function (l) { LECCIONES.push(l); });
})();
