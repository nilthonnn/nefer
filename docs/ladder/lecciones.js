/* Contenido del curso: lecciones, programas de ejemplo, retos autocorregidos y
   cuestionarios. Cada programa es una lista de segmentos; cada segmento es una
   red serie/paralelo de instrucciones LAD. */

/* ---------- constructores de red ---------- */
function S() { return { t: "S", items: Array.prototype.slice.call(arguments) }; }
function P() { return { t: "P", br: Array.prototype.slice.call(arguments).map(function (b) { return Array.isArray(b) ? S.apply(null, b) : (b.t === "S" ? b : S(b)); }) }; }
function E(k, o) { var e = { t: "E", k: k }; for (var p in o) e[p] = o[p]; return e; }
var NO = function (op) { return E("NO", { op: op }); };
var NC = function (op) { return E("NC", { op: op }); };
var PC = function (op, mem) { return E("P", { op: op, mem: mem }); };
var NE = function (op, mem) { return E("N", { op: op, mem: mem }); };
var COIL = function (op) { return E("COIL", { op: op }); };
var SET = function (op) { return E("SET", { op: op }); };
var RST = function (op) { return E("RESET", { op: op }); };
var TON = function (n, pt) { return E("TON", { name: n, pt: pt }); };
var TOF = function (n, pt) { return E("TOF", { name: n, pt: pt }); };
var TP = function (n, pt) { return E("TP", { name: n, pt: pt }); };
var CTU = function (n, r, pv) { return E("CTU", { name: n, r: r, pv: String(pv) }); };
var CTD = function (n, ld, pv) { return E("CTD", { name: n, ld: ld, pv: String(pv) }); };
var CMP = function (c, a, b) { return E("CMP", { cmp: c, a: a, b: String(b) }); };
var MOVE = function (i, o) { return E("MOVE", { in: String(i), out: o }); };
var MATH = function (k, a, b, o) { return E(k, { in1: String(a), in2: String(b), out: o }); };
function SEG(title, net) { return { title: title, net: net }; }

/* tipos de entrada: push (pulsador NA), pushNC (pulsador cableado NC),
   switch (selector), analog (palabra que mueve el alumno), plant / plantw (bit o
   palabra que mueve el modelo de planta). Opciones: def (valor inicial),
   min/max/unit/div (escala de una palabra), falla (botón para simular falla). */
function TAG(addr, name, type, note, o) {
  var t = { addr: addr, name: name, type: type || "", note: note || "" };
  for (var k in (o || {})) t[k] = o[k];
  return t;
}

var NIVELES = [
  { id: "basico", nombre: "Básico", desc: "El PLC, TIA Portal y la lógica de contactos." },
  { id: "intermedio", nombre: "Intermedio", desc: "Flancos, temporizadores, contadores y datos." },
  { id: "avanzado", nombre: "Avanzado", desc: "Bloques, secuencias, analógicas y oficio." }
];

var LECCIONES = [
/* ==================================================================== */
{ id: "plc", nivel: "basico", titulo: "El PLC y el ciclo de scan", min: 10,
  teoria: `
<p>Un <b>PLC</b> (controlador lógico programable) es una computadora industrial que lee
sensores, ejecuta un programa y gobierna actuadores. Siemens fabrica las familias
<b>S7‑1200</b> (máquinas pequeñas y medianas) y <b>S7‑1500</b> (procesos grandes);
las dos se programan con <b>TIA Portal</b> (Totally Integrated Automation).</p>
<h3>El ciclo de scan</h3>
<p>El PLC no ejecuta el programa “una vez”: lo repite sin parar, en milisegundos,
siempre en el mismo orden:</p>
<ol>
  <li><b>Lee las entradas</b> físicas y copia su estado a la <i>imagen de proceso de entradas</i> (PII, área <code>%I</code>).</li>
  <li><b>Ejecuta el programa</b> (el bloque <code>OB1 "Main"</code>), segmento por segmento, de arriba hacia abajo y de izquierda a derecha.</li>
  <li><b>Escribe las salidas</b>: copia la <i>imagen de proceso de salidas</i> (PIQ, área <code>%Q</code>) a los bornes físicos.</li>
  <li>Comunicaciones y autodiagnóstico, y vuelta a empezar.</li>
</ol>
<div class="tip"><b>Consecuencia práctica:</b> si un pulsador cambia en mitad del programa, el
PLC no lo “ve” hasta el siguiente ciclo. Y si escribes la misma bobina en dos
segmentos, <b>gana el último</b>: solo ese valor llega a la salida física.</div>
<h3>¿Por qué Ladder?</h3>
<p>El lenguaje <b>Ladder</b> o <b>LAD</b> (diagrama de contactos, norma IEC 61131‑3) dibuja el
programa como un esquema eléctrico de relés: una barra de alimentación a la izquierda, contactos
que dejan o no pasar la “corriente” y bobinas que se energizan. Lo lee cualquier
electricista, y por eso es el lenguaje más usado en planta. TIA Portal también ofrece
FUP (bloques), SCL (texto estructurado) y GRAPH (secuencias).</p>
<p>En el simulador de la derecha, el PLC está en <b>RUN</b>: pulsa la entrada y mira cómo
la corriente (línea verde continua) llega a la bobina. Las líneas azules punteadas no conducen,
igual que en la vista <i>online</i> de TIA Portal.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Pulsador", "push"), TAG("%Q0.0", "Lampara")],
    prog: [SEG("Encender la lámpara mientras se pulsa", S(NO("%I0.0"), COIL("%Q0.0")))] },
  quiz: [
    { q: "¿En qué orden trabaja el ciclo de scan?", o: ["Ejecuta programa → lee entradas → escribe salidas", "Lee entradas → ejecuta programa → escribe salidas", "Escribe salidas → lee entradas → ejecuta programa"], a: 1, e: "Primero congela las entradas en la PII, luego ejecuta OB1 y al final copia la PIQ a las salidas." },
    { q: "Si la bobina %Q0.0 aparece en el segmento 2 y en el 5, ¿qué valor sale por el borne?", o: ["El del segmento 2", "El del segmento 5", "Un OR de los dos"], a: 1, e: "El último en escribir gana. Por eso una bobina debe escribirse en un solo lugar del programa." },
    { q: "¿Qué bloque ejecuta el ciclo principal en un S7‑1200/1500?", o: ["OB100", "FB1", "OB1 \"Main\""], a: 2, e: "OB1 es el bloque de organización del ciclo. OB100 se ejecuta una sola vez en el arranque." }
  ] },
/* ==================================================================== */
{ id: "tia", nivel: "basico", titulo: "TIA Portal, direcciones y tipos de datos", min: 15,
  teoria: `
<h3>Del proyecto al PLC en 6 pasos</h3>
<ol>
  <li><b>Crear proyecto</b> → <i>Agregar dispositivo</i> → elegir la CPU exacta (p. ej. CPU 1214C DC/DC/DC) y su versión de firmware.</li>
  <li>En la <b>configuración de dispositivos</b> revisar las direcciones de E/S, la IP (p. ej. 192.168.0.1) y activar la marca de ciclo si se necesita.</li>
  <li>En <b>Variables PLC</b> declarar la <b>tabla de variables</b>: nombre simbólico, tipo y dirección.</li>
  <li>Abrir <code>Bloques de programa → Main [OB1]</code> y programar en LAD.</li>
  <li><b>Compilar</b> (hardware y software) y corregir los errores de la ventana <i>Información</i>.</li>
  <li><b>Cargar en dispositivo</b> o, sin PLC, <b>Iniciar simulación</b> con S7‑PLCSIM. Luego <i>Activar observación</i> (icono de gafas) para ver el programa online.</li>
</ol>
<h3>Áreas de memoria y direcciones</h3>
<table class="t">
<tr><th>Área</th><th>Ejemplo</th><th>Qué es</th></tr>
<tr><td>Entradas</td><td><code>%I0.0</code></td><td>Bit 0 del byte 0 de entradas (un pulsador, un sensor)</td></tr>
<tr><td>Salidas</td><td><code>%Q0.0</code></td><td>Bit 0 del byte 0 de salidas (contactor, lámpara, válvula)</td></tr>
<tr><td>Marcas</td><td><code>%M10.0</code>, <code>%MW20</code></td><td>Memoria interna: bits auxiliares y palabras</td></tr>
<tr><td>Entrada analógica</td><td><code>%IW64</code></td><td>Palabra de 16 bits de un canal analógico</td></tr>
<tr><td>Bloques de datos</td><td><code>"Datos".Velocidad</code></td><td>Variables en un DB (lo veremos en avanzado)</td></tr>
</table>
<p>Un byte tiene 8 bits (<code>.0</code> a <code>.7</code>): después de <code>%I0.7</code> viene
<code>%I1.0</code>. Una CPU 1214C trae 14 entradas (<code>%I0.0…%I1.5</code>) y 10 salidas
(<code>%Q0.0…%Q1.1</code>).</p>
<h3>Tipos de datos más usados</h3>
<table class="t">
<tr><th>Tipo</th><th>Tamaño</th><th>Rango / uso</th></tr>
<tr><td>Bool</td><td>1 bit</td><td>TRUE / FALSE</td></tr>
<tr><td>Byte, Word, DWord</td><td>8, 16, 32 bits</td><td>Patrones de bits</td></tr>
<tr><td>Int</td><td>16 bits</td><td>−32 768 … 32 767</td></tr>
<tr><td>DInt</td><td>32 bits</td><td>±2 147 483 647</td></tr>
<tr><td>Real</td><td>32 bits</td><td>Coma flotante (3.1416)</td></tr>
<tr><td>Time</td><td>32 bits</td><td>Duraciones: <code>T#5s</code>, <code>T#1m30s</code>, <code>T#250ms</code></td></tr>
</table>
<div class="tip"><b>Buena práctica:</b> programa siempre con <b>nombres simbólicos</b>
(<code>"Marcha_Bomba"</code>) y no con direcciones sueltas. TIA los muestra entre comillas.
Si cambia el cableado, solo editas la tabla de variables.</div>`,
  ejemplo: { tags: [TAG("%I0.0", "Sensor_Puerta", "switch"), TAG("%Q0.0", "Luz_Cabina"), TAG("%I1.0", "Sensor_Tapa", "switch"), TAG("%Q1.0", "Aviso")],
    prog: [SEG("Byte 0", S(NO("%I0.0"), COIL("%Q0.0"))), SEG("Byte 1: después de %I0.7 viene %I1.0", S(NO("%I1.0"), COIL("%Q1.0")))] },
  quiz: [
    { q: "¿Qué dirección sigue a %I0.7?", o: ["%I0.8", "%I1.0", "%I0.10"], a: 1, e: "Los bits van de .0 a .7; luego empieza el byte 1." },
    { q: "¿Qué tipo usarías para guardar una velocidad de 1500 rpm?", o: ["Bool", "Int", "Time"], a: 1, e: "Int (16 bits con signo) alcanza hasta 32 767." },
    { q: "Sin PLC físico, ¿cómo pruebas el programa en TIA Portal?", o: ["No se puede", "Con S7‑PLCSIM (Iniciar simulación)", "Exportando a Excel"], a: 1, e: "PLCSIM emula la CPU en el PC; se carga igual que en una real." },
    { q: "¿Cómo escribe TIA Portal un tiempo de 2 minutos y medio?", o: ["T#2m30s", "2.5min", "TIME(150)"], a: 0, e: "Los literales de tiempo empiezan por T# (o TIME#)." }
  ] },
/* ==================================================================== */
{ id: "contactos", nivel: "basico", titulo: "Contactos NA, NC y bobinas", min: 15,
  teoria: `
<p>Las tres instrucciones con las que se escribe casi todo:</p>
<table class="t">
<tr><th>Símbolo</th><th>Nombre</th><th>Conduce cuando…</th></tr>
<tr><td><code>--| |--</code></td><td>Contacto normalmente abierto (NA)</td><td>el operando vale <b>1</b></td></tr>
<tr><td><code>--|/|--</code></td><td>Contacto normalmente cerrado (NC)</td><td>el operando vale <b>0</b></td></tr>
<tr><td><code>--( )--</code></td><td>Bobina (asignación)</td><td>escribe en el operando el estado de la corriente que le llega</td></tr>
<tr><td><code>--(/)--</code></td><td>Bobina negada</td><td>escribe lo contrario</td></tr>
</table>
<div class="tip"><b>La confusión nº 1:</b> el contacto del programa <b>no</b> es el contacto físico.
El contacto NC del programa pregunta “¿la señal vale 0?”. Si el pulsador físico es NC, cuando
nadie lo toca la entrada vale 1.</div>
<p>En TIA Portal las instrucciones están en la pestaña <i>Instrucciones → Operaciones lógicas
con bits</i>, y las más usadas también en la barra de <b>favoritos</b> sobre el editor.
Se arrastran al segmento y se escribe el operando encima, en el campo <code>&lt;??.?&gt;</code>.</p>
<p>En el ejemplo, la lámpara verde enciende con el pulsador y la roja está encendida
<i>mientras no</i> se pulse.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Pulsador", "push"), TAG("%Q0.0", "Luz_Verde"), TAG("%Q0.1", "Luz_Roja")],
    prog: [SEG("Contacto NA", S(NO("%I0.0"), COIL("%Q0.0"))), SEG("Contacto NC", S(NC("%I0.0"), COIL("%Q0.1")))] },
  reto: {
    enunciado: "Una cinta tiene un sensor de presencia <code>%I0.2 \"Sensor\"</code>. Programa la luz <code>%Q0.0 \"Hay_Pieza\"</code> que enciende cuando hay pieza y la luz <code>%Q0.1 \"Libre\"</code> que enciende cuando no la hay.",
    tags: [TAG("%I0.2", "Sensor", "switch"), TAG("%Q0.0", "Hay_Pieza"), TAG("%Q0.1", "Libre")],
    inicio: [SEG("Hay pieza", S()), SEG("Libre", S())],
    solucion: [SEG("Hay pieza", S(NO("%I0.2"), COIL("%Q0.0"))), SEG("Libre", S(NC("%I0.2"), COIL("%Q0.1")))],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Sin pieza: solo «Libre»." },
      { in: { "%I0.2": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "Con pieza: solo «Hay_Pieza»." },
      { in: { "%I0.2": 0 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "La pieza se va: vuelve «Libre»." }
    ] },
  quiz: [
    { q: "Un contacto NC del programa con operando %I0.0 conduce cuando…", o: ["%I0.0 = 1", "%I0.0 = 0", "Siempre"], a: 1, e: "NC = conduce mientras el operando valga 0." },
    { q: "Un pulsador de paro cableado NC, sin pulsar, da en %I0.1 la señal…", o: ["0", "1"], a: 1, e: "El contacto físico está cerrado: llega tensión a la entrada → 1." },
    { q: "¿Qué hace una bobina --( )-- cuando deja de llegarle corriente?", o: ["Mantiene el 1", "Escribe 0", "Da error"], a: 1, e: "La asignación copia el estado en cada ciclo; si no llega corriente, escribe 0." }
  ] },
/* ==================================================================== */
{ id: "logica", nivel: "basico", titulo: "Serie y paralelo: AND, OR", min: 15,
  teoria: `
<p>Los contactos se combinan como en un tablero eléctrico:</p>
<ul>
  <li><b>En serie = Y (AND):</b> la corriente pasa solo si <i>todos</i> los contactos conducen.</li>
  <li><b>En paralelo = O (OR):</b> pasa si conduce <i>al menos una</i> rama.</li>
</ul>
<table class="t">
<tr><th>A</th><th>B</th><th>A AND B</th><th>A OR B</th></tr>
<tr><td>0</td><td>0</td><td>0</td><td>0</td></tr>
<tr><td>0</td><td>1</td><td>0</td><td>1</td></tr>
<tr><td>1</td><td>0</td><td>0</td><td>1</td></tr>
<tr><td>1</td><td>1</td><td>1</td><td>1</td></tr>
</table>
<p>En TIA Portal una rama paralela se abre con <i>Abrir rama</i> (la flecha ↓ de favoritos) y se
cierra con <i>Cerrar rama</i> (↑) en el punto donde se une a la línea principal.</p>
<p>Con esto aparece la <b>lógica combinada</b>: <code>(A AND B) OR C</code> se dibuja con A y B en
serie en una rama, y C en una rama paralela a las dos.</p>
<div class="tip">En el editor de esta app: activa <b>Editar</b>, toca un contacto y elige
<i>Rama paralela</i>. Para que la rama abarque también el contacto siguiente usa
<i>Extender rama →</i>.</div>`,
  ejemplo: { tags: [TAG("%I0.0", "A", "switch"), TAG("%I0.1", "B", "switch"), TAG("%Q0.0", "A_y_B"), TAG("%Q0.1", "A_o_B")],
    prog: [SEG("Serie = AND", S(NO("%I0.0"), NO("%I0.1"), COIL("%Q0.0"))), SEG("Paralelo = OR", S(P([NO("%I0.0")], [NO("%I0.1")]), COIL("%Q0.1")))] },
  reto: {
    enunciado: "Prensa: el cilindro <code>%Q0.0 \"Bajar\"</code> baja solo si el operario mantiene <b>los dos</b> pulsadores <code>%I0.0 \"Mano_Izq\"</code> y <code>%I0.1 \"Mano_Der\"</code>, <b>o</b> si el técnico activa la llave de mantenimiento <code>%I0.2 \"Llave_Mant\"</code>.",
    tags: [TAG("%I0.0", "Mano_Izq", "push"), TAG("%I0.1", "Mano_Der", "push"), TAG("%I0.2", "Llave_Mant", "switch"), TAG("%Q0.0", "Bajar")],
    inicio: [SEG("Bajar prensa", S(NO("%I0.0"), COIL("%Q0.0")))],
    solucion: [SEG("Bajar prensa", S(P([NO("%I0.0"), NO("%I0.1")], [NO("%I0.2")]), COIL("%Q0.0")))],
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.0": 0 }, d: "Nadie pulsa: no baja." },
      { in: { "%I0.0": 1 }, t: 60, ex: { "%Q0.0": 0 }, d: "Solo mano izquierda: no baja." },
      { in: { "%I0.0": 0, "%I0.1": 1 }, t: 60, ex: { "%Q0.0": 0 }, d: "Solo mano derecha: no baja." },
      { in: { "%I0.0": 1, "%I0.1": 1 }, t: 60, ex: { "%Q0.0": 1 }, d: "Las dos manos: baja." },
      { in: { "%I0.0": 0, "%I0.1": 0, "%I0.2": 1 }, t: 60, ex: { "%Q0.0": 1 }, d: "Llave de mantenimiento: baja." },
      { in: { "%I0.2": 0 }, t: 60, ex: { "%Q0.0": 0 }, d: "Se quita la llave: se detiene." }
    ] },
  quiz: [
    { q: "Dos contactos NA en serie equivalen a…", o: ["OR", "AND", "NOT"], a: 1, e: "Ambos tienen que conducir." },
    { q: "En paralelo con A=0 y B=1, ¿llega corriente?", o: ["Sí", "No"], a: 0, e: "OR: basta una rama." },
    { q: "¿Cómo se dibuja (A AND B) OR C?", o: ["A, B y C en serie", "A y B en serie, con C en paralelo a ambos", "A en paralelo con B, y C en serie"], a: 1, e: "La rama de C debe saltar sobre A y B juntos." }
  ] },
/* ==================================================================== */
{ id: "enclavamiento", nivel: "basico", titulo: "Marcha‑paro con autorretención", min: 20,
  teoria: `
<p>El circuito más famoso de la automatización. Un motor arranca con un pulsador de
<b>marcha</b> y debe <b>seguir</b> funcionando al soltarlo, hasta que se pulse <b>paro</b>.</p>
<p>El truco es el <b>contacto de autorretención</b> (o enclavamiento): un contacto NA de la propia
salida en paralelo con la marcha. Cuando la bobina se energiza, su contacto “se puentea” a sí mismo.</p>
<h3>El paro va cableado NC (seguridad positiva)</h3>
<p>Los pulsadores de paro y las setas de emergencia se cablean <b>normalmente cerrados</b>: si se corta
un cable, la entrada cae a 0 y la máquina se detiene sola. Por eso, sin pulsar, <code>%I0.1 "Paro" = 1</code>,
y en el programa se usa un <b>contacto NA</b> de Paro: conduce mientras nadie lo pulse.</p>
<div class="tip"><b>Ojo:</b> en el simulador, el pulsador de paro está marcado como <i>NC cableado</i>:
fíjate que la señal vale 1 en reposo y 0 al pulsarlo.</div>
<p>Como el paro está en serie <b>después</b> del paralelo, también manda cuando se pulsan los dos a la vez:
es un circuito <b>con prioridad al paro</b>, que es lo que pide la seguridad.</p>
<p><i>Nota:</i> la parada de emergencia real no se resuelve solo con el programa: va por un relé o PLC de
seguridad (F‑CPU) que corta la potencia.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Paro", "pushNC", "NC cableado"), TAG("%Q0.0", "Motor")],
    prog: [SEG("Motor con autorretención", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0")))] },
  reto: {
    enunciado: "Una bomba <code>%Q0.4 \"Bomba\"</code> arranca con <code>%I0.3 \"Marcha_B\"</code> (NA) y se detiene con <code>%I0.4 \"Paro_B\"</code> (cableado <b>NC</b>) <b>o</b> si salta el relé térmico <code>%I0.5 \"Termico\"</code> (cableado NC: vale 1 si todo está bien). El paro debe tener prioridad.",
    tags: [TAG("%I0.3", "Marcha_B", "push"), TAG("%I0.4", "Paro_B", "pushNC", "NC cableado"), TAG("%I0.5", "Termico", "pushNC", "NC: pulsa = disparo"), TAG("%Q0.4", "Bomba")],
    inicio: [SEG("Bomba", S(NO("%I0.3"), COIL("%Q0.4")))],
    solucion: [SEG("Bomba", S(P([NO("%I0.3")], [NO("%Q0.4")]), NO("%I0.4"), NO("%I0.5"), COIL("%Q0.4")))],
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.4": 0 }, d: "Reposo: bomba parada." },
      { in: { "%I0.3": 1 }, t: 60, ex: { "%Q0.4": 1 }, d: "Pulsar marcha: arranca." },
      { in: { "%I0.3": 0 }, t: 200, ex: { "%Q0.4": 1 }, d: "Soltar marcha: sigue en marcha (autorretención)." },
      { in: { "%I0.4": 1 }, t: 60, ex: { "%Q0.4": 0 }, d: "Pulsar paro: se detiene." },
      { in: { "%I0.4": 0 }, t: 60, ex: { "%Q0.4": 0 }, d: "Soltar paro: sigue parada." },
      { in: { "%I0.3": 1, "%I0.4": 1 }, t: 60, ex: { "%Q0.4": 0 }, d: "Marcha y paro a la vez: gana el paro." },
      { in: { "%I0.4": 0 }, t: 60, ex: { "%Q0.4": 1 }, d: "Se suelta el paro con marcha pulsada: arranca." },
      { in: { "%I0.3": 0, "%I0.5": 1 }, t: 60, ex: { "%Q0.4": 0 }, d: "Dispara el térmico: se detiene." },
      { in: { "%I0.5": 0 }, t: 60, ex: { "%Q0.4": 0 }, d: "Rearmado el térmico: no rearranca sola." }
    ] },
  quiz: [
    { q: "¿Dónde se coloca el contacto de autorretención?", o: ["En serie con el paro", "En paralelo con la marcha", "En paralelo con la bobina"], a: 1, e: "Puentea a la marcha para que la bobina se mantenga." },
    { q: "Con el paro cableado NC, ¿qué contacto se usa en el programa?", o: ["NA (--| |--)", "NC (--|/|--)"], a: 0, e: "En reposo la entrada vale 1; el contacto NA conduce hasta que se pulsa." },
    { q: "Si se corta el cable del paro NC…", o: ["La máquina no se puede detener", "La máquina se detiene (falla segura)", "No pasa nada"], a: 1, e: "La entrada cae a 0 como si se pulsara: seguridad positiva." }
  ] },
/* ==================================================================== */
{ id: "setreset", nivel: "basico", titulo: "Set, Reset y biestables SR/RS", min: 15,
  teoria: `
<p>Otra forma de memorizar un estado son las bobinas <b>Set</b> y <b>Reset</b>:</p>
<ul>
  <li><code>--(S)--</code> pone el operando a 1 cuando le llega corriente, y lo deja así.</li>
  <li><code>--(R)--</code> pone el operando a 0 cuando le llega corriente.</li>
  <li>Si no les llega corriente, <b>no hacen nada</b> (el valor se conserva).</li>
</ul>
<p>Si en el mismo ciclo se ejecutan las dos, gana la que está <b>más abajo</b> en el programa
(la última que escribe). TIA también tiene las cajas <b>SR</b> (prioridad al Reset) y
<b>RS</b> (prioridad al Set) que resumen eso en una instrucción.</p>
<div class="tip"><b>¿Autorretención o Set/Reset?</b> Las dos sirven. La autorretención se ve entera en un
segmento; con Set/Reset el arranque y la parada pueden estar lejos, así que conviene agruparlos.
Muchas empresas prohíben hacer Set de una misma salida en varios lugares: complica el diagnóstico.</div>
<p>Uso típico: <b>alarmas</b> que quedan memorizadas hasta que el operador las reconoce.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Paro", "pushNC", "NC cableado"), TAG("%Q0.0", "Motor")],
    prog: [SEG("Arranque", S(NO("%I0.0"), SET("%Q0.0"))), SEG("Parada (abajo: tiene prioridad)", S(NC("%I0.1"), RST("%Q0.0")))] },
  reto: {
    enunciado: "Alarma de nivel alto: cuando el sensor <code>%I0.2 \"Nivel_Alto\"</code> se activa, la baliza <code>%Q0.1 \"Alarma\"</code> se enciende y <b>queda memorizada</b> aunque el nivel baje. El pulsador <code>%I0.3 \"Reconocer\"</code> la apaga, pero <b>solo</b> si el nivel ya no está alto.",
    tags: [TAG("%I0.2", "Nivel_Alto", "switch"), TAG("%I0.3", "Reconocer", "push"), TAG("%Q0.1", "Alarma")],
    inicio: [SEG("Activar alarma", S()), SEG("Reconocer alarma", S())],
    solucion: [SEG("Activar alarma", S(NO("%I0.2"), SET("%Q0.1"))), SEG("Reconocer alarma", S(NO("%I0.3"), NC("%I0.2"), RST("%Q0.1")))],
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.1": 0 }, d: "Todo normal: sin alarma." },
      { in: { "%I0.2": 1 }, t: 60, ex: { "%Q0.1": 1 }, d: "Nivel alto: alarma." },
      { in: { "%I0.2": 0 }, t: 200, ex: { "%Q0.1": 1 }, d: "El nivel baja: la alarma queda memorizada." },
      { in: { "%I0.2": 1, "%I0.3": 1 }, t: 60, ex: { "%Q0.1": 1 }, d: "Reconocer con el nivel aún alto: no se apaga." },
      { in: { "%I0.3": 0, "%I0.2": 0 }, t: 60, ex: { "%Q0.1": 1 }, d: "Baja el nivel: sigue memorizada." },
      { in: { "%I0.3": 1 }, t: 60, ex: { "%Q0.1": 0 }, d: "Reconocer con nivel normal: se apaga." }
    ] },
  quiz: [
    { q: "Una bobina (S) deja de recibir corriente. El operando…", o: ["Pasa a 0", "Conserva su valor", "Cambia de estado"], a: 1, e: "Set solo actúa cuando le llega corriente." },
    { q: "Set en el segmento 3 y Reset en el 4, ambos activos en el mismo ciclo. Resultado:", o: ["1", "0"], a: 1, e: "Gana el último en ejecutarse." },
    { q: "La caja SR de TIA Portal tiene prioridad al…", o: ["Set", "Reset"], a: 1, e: "SR = Reset dominante; RS = Set dominante (la última letra manda)." }
  ] },
/* ==================================================================== */
{ id: "flancos", nivel: "intermedio", titulo: "Flancos: detectar el instante del cambio", min: 20,
  teoria: `
<p>A veces no interesa <i>si</i> un pulsador está pulsado, sino el <b>instante</b> en que se pulsa:
contar piezas, avanzar un paso, invertir un estado. Eso es un <b>flanco</b>:</p>
<ul>
  <li><b>Flanco positivo</b> <code>--|P|--</code>: conduce <b>un solo ciclo</b> cuando el operando pasa de 0 a 1.</li>
  <li><b>Flanco negativo</b> <code>--|N|--</code>: conduce un ciclo cuando pasa de 1 a 0.</li>
</ul>
<p>Para recordar el estado anterior, la instrucción necesita un <b>bit de marca de flanco</b> propio
(se escribe debajo del contacto, p. ej. <code>%M10.0</code>). <b>Cada flanco necesita su propio bit</b>
y no se debe usar ese bit para nada más.</p>
<p>TIA Portal también ofrece <code>P_TRIG</code>/<code>N_TRIG</code> (flanco de la corriente del segmento)
y los bloques <code>R_TRIG</code>/<code>F_TRIG</code> con instancia, muy usados dentro de FB.</p>
<div class="tip">El pulso dura un ciclo de scan (unos milisegundos): en la vista online casi no se ve.
Por eso en el ejemplo se usa para hacer <b>Set</b>; así se nota el efecto.</div>
<h3>Telerruptor (toggle)</h3>
<p>Un mismo pulsador que enciende con una pulsación y apaga con la siguiente. Es un clásico de entrevista:
necesitas un flanco y luego invertir la salida usando su propio estado.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Pulsador", "push"), TAG("%I0.1", "Borrar", "push"), TAG("%Q0.0", "Lampara_Pulsado"), TAG("%Q0.1", "Memo_Flanco_P"), TAG("%Q0.2", "Memo_Flanco_N")],
    prog: [SEG("Nivel: mientras está pulsado", S(NO("%I0.0"), COIL("%Q0.0"))),
      SEG("Flanco positivo → memoriza", S(PC("%I0.0", "%M10.0"), SET("%Q0.1"))),
      SEG("Flanco negativo → memoriza", S(NE("%I0.0", "%M10.1"), SET("%Q0.2"))),
      SEG("Borrar memorias", S(NO("%I0.1"), RST("%Q0.1"))), SEG("", S(NO("%I0.1"), RST("%Q0.2")))] },
  reto: {
    enunciado: "Telerruptor: cada vez que se pulsa <code>%I0.0 \"Pulsador\"</code>, la luz <code>%Q0.0 \"Luz\"</code> cambia de estado (si estaba apagada se enciende y viceversa). Mantener pulsado no debe hacerla parpadear. <i>Pista: un flanco P hacia una marca de pulso y luego dos ramas con la propia salida.</i>",
    tags: [TAG("%I0.0", "Pulsador", "push"), TAG("%M0.1", "Pulso"), TAG("%Q0.0", "Luz")],
    inicio: [SEG("Pulso de un ciclo", S(PC("%I0.0", "%M0.0"), COIL("%M0.1"))), SEG("Invertir la luz", S())],
    solucion: [SEG("Pulso de un ciclo", S(PC("%I0.0", "%M0.0"), COIL("%M0.1"))),
      SEG("Invertir la luz", S(P([NO("%M0.1"), NC("%Q0.0")], [NC("%M0.1"), NO("%Q0.0")]), COIL("%Q0.0")))],
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.0": 0 }, d: "Inicio: apagada." },
      { in: { "%I0.0": 1 }, t: 300, ex: { "%Q0.0": 1 }, d: "1ª pulsación (mantenida 0,3 s): enciende y no parpadea." },
      { in: { "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 1 }, d: "Soltar: sigue encendida." },
      { in: { "%I0.0": 1 }, t: 100, ex: { "%Q0.0": 0 }, d: "2ª pulsación: apaga." },
      { in: { "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 0 }, d: "Soltar: sigue apagada." },
      { in: { "%I0.0": 1 }, t: 100, ex: { "%Q0.0": 1 }, d: "3ª pulsación: enciende otra vez." }
    ] },
  quiz: [
    { q: "¿Cuánto tiempo conduce un contacto de flanco P?", o: ["Mientras el operando vale 1", "Un ciclo de scan", "1 segundo"], a: 1, e: "Solo el ciclo en que detecta el paso 0→1." },
    { q: "¿Para qué sirve el bit de marca de flanco (%M10.0)?", o: ["Guardar el estado del ciclo anterior", "Sacar el pulso a una salida", "Nada, es opcional"], a: 0, e: "Compara el valor actual con el anterior guardado en ese bit." },
    { q: "Dos flancos distintos comparten el mismo bit de marca. ¿Qué pasa?", o: ["Funcionan bien", "Se interfieren y fallan pulsos", "TIA lo corrige solo"], a: 1, e: "Cada flanco debe tener su bit exclusivo." }
  ] },
/* ==================================================================== */
{ id: "temporizadores", nivel: "intermedio", titulo: "Temporizadores IEC: TON, TOF, TP", min: 25,
  teoria: `
<p>En S7‑1200/1500 se usan los temporizadores <b>IEC</b>. Cada uno es una caja con su
<b>bloque de datos de instancia</b> (TIA lo crea al soltar la caja: <code>"IEC_Timer_0_DB"</code>), donde
guarda su estado.</p>
<table class="t">
<tr><th>Pin</th><th>Tipo</th><th>Significado</th></tr>
<tr><td>IN</td><td>Bool</td><td>Entrada de arranque (la corriente del segmento)</td></tr>
<tr><td>PT</td><td>Time</td><td>Tiempo preseleccionado, p. ej. <code>T#5s</code></td></tr>
<tr><td>Q</td><td>Bool</td><td>Salida del temporizador</td></tr>
<tr><td>ET</td><td>Time</td><td>Tiempo transcurrido</td></tr>
</table>
<h3>Los tres tipos</h3>
<ul>
  <li><b>TON — retardo a la conexión:</b> Q se activa cuando IN lleva PT seguido en 1. Si IN cae antes, se reinicia.</li>
  <li><b>TOF — retardo a la desconexión:</b> Q se activa al instante con IN y se desactiva PT después de que IN cae. Ideal para ventiladores que siguen un rato.</li>
  <li><b>TP — impulso:</b> con el flanco de IN, Q da un pulso de duración exacta PT, aunque IN dure más o menos.</li>
</ul>
<div class="tip">Se puede leer el estado desde cualquier parte: <code>"T_Arranque".Q</code> y
<code>"T_Arranque".ET</code>. En esta app el nombre de la instancia es el texto sobre la caja
(<code>T1.Q</code>, <code>T1.ET</code>).</div>
<p>Prueba el ejemplo con el selector y mira cómo avanza ET en cada caja.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Selector", "switch"), TAG("%Q0.0", "Salida_TON"), TAG("%Q0.1", "Salida_TOF"), TAG("%Q0.2", "Salida_TP")],
    prog: [SEG("TON: retardo a la conexión", S(NO("%I0.0"), TON("T_on", "T#3s"), COIL("%Q0.0"))),
      SEG("TOF: retardo a la desconexión", S(NO("%I0.0"), TOF("T_off", "T#3s"), COIL("%Q0.1"))),
      SEG("TP: impulso", S(NO("%I0.0"), TP("T_imp", "T#2s"), COIL("%Q0.2")))] },
  reto: {
    enunciado: "Arranque retardado: cuando el selector <code>%I0.0 \"Selector\"</code> se pone en ON, la bomba <code>%Q0.0 \"Bomba\"</code> arranca <b>3 segundos</b> después. Al apagar el selector, la bomba para al instante. Además, el ventilador <code>%Q0.1 \"Ventilador\"</code> funciona con el selector y sigue <b>2 s</b> después de apagarlo.",
    tags: [TAG("%I0.0", "Selector", "switch"), TAG("%Q0.0", "Bomba"), TAG("%Q0.1", "Ventilador")],
    inicio: [SEG("Bomba con retardo", S(NO("%I0.0"), COIL("%Q0.0"))), SEG("Ventilador con post‑ventilación", S())],
    solucion: [SEG("Bomba con retardo", S(NO("%I0.0"), TON("T1", "T#3s"), COIL("%Q0.0"))),
      SEG("Ventilador con post‑ventilación", S(NO("%I0.0"), TOF("T2", "T#2s"), COIL("%Q0.1")))],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Selector en OFF: todo parado." },
      { in: { "%I0.0": 1 }, t: 2800, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "2,8 s después de ON: la bomba aún no arranca; el ventilador sí." },
      { in: {}, t: 400, ex: { "%Q0.0": 1, "%Q0.1": 1 }, d: "3,2 s: la bomba ya arrancó." },
      { in: { "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Selector OFF: la bomba para; el ventilador sigue." },
      { in: {}, t: 1800, ex: { "%Q0.1": 1 }, d: "1,9 s después: el ventilador sigue." },
      { in: {}, t: 400, ex: { "%Q0.1": 0 }, d: "2,3 s después: el ventilador paró." },
      { in: { "%I0.0": 1 }, t: 1500, ex: { "%Q0.0": 0 }, d: "Nuevo ON corto de 1,5 s…" },
      { in: { "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 0 }, d: "…y OFF: la bomba nunca arrancó." },
      { in: { "%I0.0": 1 }, t: 2000, ex: { "%Q0.0": 0 }, d: "ON otra vez: el TON empieza de cero (2 s → aún no)." }
    ] },
  quiz: [
    { q: "Un ventilador debe seguir girando 60 s después de apagar el horno. ¿Qué temporizador?", o: ["TON", "TOF", "TP"], a: 1, e: "Retardo a la desconexión." },
    { q: "Con un TON de PT = T#5s, IN está 3 s en 1 y luego cae a 0. ¿Qué pasa con ET?", o: ["Se queda en 3 s", "Vuelve a 0", "Llega a 5 s igual"], a: 1, e: "El TON se reinicia cuando IN cae." },
    { q: "¿Dónde guarda su estado un temporizador IEC en TIA Portal?", o: ["En una marca %M", "En su DB de instancia", "En la salida Q"], a: 1, e: "Cada temporizador tiene su DB de instancia (o una multiinstancia dentro de un FB)." },
    { q: "Un TP de 2 s recibe un IN de 0,5 s. ¿Cuánto dura Q?", o: ["0,5 s", "2 s", "2,5 s"], a: 1, e: "El impulso siempre dura PT." }
  ] },
/* ==================================================================== */
{ id: "contadores", nivel: "intermedio", titulo: "Contadores CTU, CTD, CTUD", min: 20,
  teoria: `
<p>Los contadores IEC también usan un DB de instancia y cuentan <b>flancos</b> de su entrada
(no hace falta poner un contacto P delante).</p>
<table class="t">
<tr><th>Caja</th><th>Pines</th><th>Comportamiento</th></tr>
<tr><td><b>CTU</b> (ascendente)</td><td>CU, R, PV → Q, CV</td><td>CV +1 en cada flanco de CU. R pone CV a 0. Q = 1 cuando CV ≥ PV.</td></tr>
<tr><td><b>CTD</b> (descendente)</td><td>CD, LD, PV → Q, CV</td><td>CV −1 en cada flanco de CD. LD carga CV = PV. Q = 1 cuando CV ≤ 0.</td></tr>
<tr><td><b>CTUD</b></td><td>CU, CD, R, LD, PV → QU, QD, CV</td><td>Combina ambos.</td></tr>
</table>
<p>Al soltar la caja TIA pregunta el tipo de dato del contador (Int por defecto, también SInt, DInt, UInt…).</p>
<div class="tip">Para que el contador cuente con el sensor <b>y</b> se reinicie al empezar otro lote,
usa la propia <code>C1.Q</code> o un pulsador en R. Si R está activo, el contador no cuenta.</div>
<p>Si la cuenta va muy rápido (encoder, miles de pulsos por segundo), el ciclo de scan no alcanza: se usan los
<b>contadores rápidos HSC</b> de la CPU.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Sensor_Pieza", "push"), TAG("%I0.1", "Reset", "push"), TAG("%Q0.0", "Lote_Lleno")],
    prog: [SEG("Contar 3 piezas", S(NO("%I0.0"), CTU("C1", "%I0.1", 3), COIL("%Q0.0")))] },
  reto: {
    enunciado: "Empaquetadora: el sensor <code>%I0.0 \"Sensor\"</code> da un pulso por cada botella. Cuando pasan <b>6</b> botellas se enciende <code>%Q0.0 \"Caja_Llena\"</code>. El operario cambia la caja y pulsa <code>%I0.1 \"Nueva_Caja\"</code>, que pone la cuenta a cero.",
    tags: [TAG("%I0.0", "Sensor", "push"), TAG("%I0.1", "Nueva_Caja", "push"), TAG("%Q0.0", "Caja_Llena")],
    inicio: [SEG("Contar botellas", S())],
    solucion: [SEG("Contar botellas", S(NO("%I0.0"), CTU("C1", "%I0.1", 6), COIL("%Q0.0")))],
    pulsos: true,
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.0": 0 }, d: "Inicio: caja vacía." },
      { pulsos: { "%I0.0": 5 }, ex: { "%Q0.0": 0 }, d: "Pasan 5 botellas: aún no está llena." },
      { pulsos: { "%I0.0": 1 }, ex: { "%Q0.0": 1 }, d: "La 6ª botella: caja llena." },
      { in: { "%I0.1": 1 }, t: 60, ex: { "%Q0.0": 0 }, d: "Nueva caja: se borra la cuenta." },
      { in: { "%I0.1": 0 }, t: 60, ex: { "%Q0.0": 0 }, d: "Soltar el pulsador." },
      { pulsos: { "%I0.0": 6 }, ex: { "%Q0.0": 1 }, d: "Otras 6 botellas: llena otra vez." }
    ] },
  quiz: [
    { q: "¿Qué hace el pin R de un CTU?", o: ["Cuenta hacia atrás", "Pone CV a 0", "Carga PV"], a: 1, e: "Reset de la cuenta." },
    { q: "Un CTU con PV = 10 lleva CV = 12. ¿Q?", o: ["0", "1"], a: 1, e: "Q = CV ≥ PV." },
    { q: "Para contar los pulsos de un encoder a 20 kHz se usa…", o: ["CTU en OB1", "Un contador rápido HSC", "Un TON"], a: 1, e: "El ciclo de scan es demasiado lento; el HSC cuenta por hardware." }
  ] },
/* ==================================================================== */
{ id: "datos", nivel: "intermedio", titulo: "Comparar, mover y calcular", min: 25,
  teoria: `
<p>El Ladder no es solo bits. Con cajas se trabaja con números (Int, DInt, Real, Time):</p>
<ul>
  <li><b>Comparadores</b> <code>CMP ==, &lt;&gt;, &gt;, &lt;, &gt;=, &lt;=</code>: se comportan como un contacto que conduce si la comparación es cierta. Hay que elegir el tipo de dato (??? → Int).</li>
  <li><b>MOVE</b>: copia IN en OUT1 mientras le llega corriente por EN. Puedes añadir más salidas con la estrella (OUT2…).</li>
  <li><b>ADD, SUB, MUL, DIV</b>: OUT = IN1 op IN2. También <code>INC</code>/<code>DEC</code>, <code>MOD</code>, <code>ABS</code>, <code>LIMIT</code>, <code>MIN</code>/<code>MAX</code>.</li>
  <li><b>CONVERT</b>: cambia de tipo (Int → Real, Real → DInt con redondeo…).</li>
</ul>
<h3>EN y ENO</h3>
<p>Las cajas tienen una entrada <b>EN</b> (habilitación) y una salida <b>ENO</b>. Si EN = 0, la caja no se
ejecuta y OUT conserva su valor. ENO = 1 cuando se ejecutó sin errores (por ejemplo, un desbordamiento lo pone a 0).</p>
<div class="tip"><b>Cuidado con MOVE y ADD sin flanco:</b> un <code>ADD %MW10 + 1 → %MW10</code> con un pulsador sin flanco suma 1
<b>en cada ciclo</b> mientras esté pulsado: cientos de veces por segundo. Para sumar una vez por pulsación, pon un contacto P delante.</div>`,
  ejemplo: { tags: [TAG("%I0.0", "Sumar", "push"), TAG("%I0.1", "Borrar", "push"), TAG("%MW10", "Cuenta"), TAG("%Q0.0", "Mayor_3")],
    prog: [SEG("Sumar 1 por pulsación", S(PC("%I0.0", "%M10.0"), MATH("ADD", "%MW10", "1", "%MW10"))),
      SEG("Borrar", S(NO("%I0.1"), MOVE("0", "%MW10"))),
      SEG("Comparar", S(CMP(">", "%MW10", "3"), COIL("%Q0.0")))] },
  reto: {
    enunciado: "Selector de velocidad: el pulsador <code>%I0.0 \"Lenta\"</code> carga <b>1500</b> en <code>%MW10 \"Consigna\"</code> y <code>%I0.1 \"Rapida\"</code> carga <b>3000</b>. La luz <code>%Q0.0 \"Alta_Vel\"</code> se enciende cuando la consigna es <b>mayor o igual a 2000</b>.",
    tags: [TAG("%I0.0", "Lenta", "push"), TAG("%I0.1", "Rapida", "push"), TAG("%MW10", "Consigna"), TAG("%Q0.0", "Alta_Vel")],
    inicio: [SEG("Lenta", S(NO("%I0.0"))), SEG("Rápida", S()), SEG("Indicador", S())],
    solucion: [SEG("Lenta", S(NO("%I0.0"), MOVE("1500", "%MW10"))), SEG("Rápida", S(NO("%I0.1"), MOVE("3000", "%MW10"))),
      SEG("Indicador", S(CMP(">=", "%MW10", "2000"), COIL("%Q0.0")))],
    pasos: [
      { in: {}, t: 60, ex: { "%MW10": 0, "%Q0.0": 0 }, d: "Inicio: consigna 0." },
      { in: { "%I0.1": 1 }, t: 60, ex: { "%MW10": 3000, "%Q0.0": 1 }, d: "Rápida: consigna 3000 y luz encendida." },
      { in: { "%I0.1": 0 }, t: 60, ex: { "%MW10": 3000, "%Q0.0": 1 }, d: "Al soltar, la consigna se conserva." },
      { in: { "%I0.0": 1 }, t: 60, ex: { "%MW10": 1500, "%Q0.0": 0 }, d: "Lenta: consigna 1500 y luz apagada." },
      { in: { "%I0.0": 0 }, t: 60, ex: { "%MW10": 1500, "%Q0.0": 0 }, d: "Se conserva 1500." }
    ] },
  quiz: [
    { q: "Si EN de un MOVE vale 0, OUT1…", o: ["Pasa a 0", "Conserva su último valor", "Toma el valor de IN"], a: 1, e: "La caja no se ejecuta." },
    { q: "Un ADD %MW10 + 1 → %MW10 con un pulsador NA sin flanco, pulsado 1 s, suma…", o: ["1", "Una vez por ciclo de scan (cientos)", "1000 exactos"], a: 1, e: "Se ejecuta en cada ciclo mientras llegue corriente." },
    { q: "Un comparador en LAD se comporta como…", o: ["Una bobina", "Un contacto", "Un temporizador"], a: 1, e: "Deja pasar la corriente si la comparación es verdadera." }
  ] },
/* ==================================================================== */
{ id: "estrella", nivel: "intermedio", titulo: "Proyecto: arranque estrella‑triángulo", min: 30,
  teoria: `
<p>Un motor grande arranca en <b>estrella</b> para reducir la corriente de arranque (≈ 1/3) y, pasado un tiempo,
pasa a <b>triángulo</b> para dar su par nominal. Se usan tres contactores:</p>
<ul>
  <li><b>KM1</b> — principal (línea).</li>
  <li><b>KM2</b> — estrella.</li>
  <li><b>KM3</b> — triángulo.</li>
</ul>
<p>Secuencia: Marcha → KM1 + KM2 (estrella). A los <i>t</i> segundos → cae KM2 y entra KM3 (triángulo).
Paro → todo fuera.</p>
<div class="tip"><b>Enclavamiento obligatorio:</b> KM2 y KM3 <b>nunca</b> pueden estar a la vez (sería un
cortocircuito). Se enclavan en el programa (contacto NC de KM3 en la bobina de KM2 y viceversa) <b>y</b> también
con contactos auxiliares cableados, porque el programa solo no es suficiente.</div>
<p>Este reto junta todo lo anterior: autorretención, paro NC, un TON y enclavamientos. El corrector
comprueba en <b>cada ciclo</b> que estrella y triángulo nunca coinciden.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Paro", "pushNC", "NC cableado"), TAG("%Q0.0", "KM1_Linea"), TAG("%Q0.1", "KM2_Estrella"), TAG("%Q0.2", "KM3_Triangulo")],
    prog: [SEG("Solo el contactor de línea (complétalo en el reto)", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0")))] },
  reto: {
    enunciado: "Programa el arranque estrella‑triángulo: <code>%I0.0 \"Marcha\"</code> (NA), <code>%I0.1 \"Paro\"</code> (NC cableado), <code>%Q0.0 \"KM1\"</code> línea, <code>%Q0.1 \"KM2\"</code> estrella, <code>%Q0.2 \"KM3\"</code> triángulo. Tiempo de estrella: <b>5 s</b>. KM2 y KM3 jamás a la vez.",
    tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Paro", "pushNC", "NC cableado"), TAG("%Q0.0", "KM1"), TAG("%Q0.1", "KM2"), TAG("%Q0.2", "KM3")],
    inicio: [SEG("KM1 línea", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0"))), SEG("Tiempo de estrella", S()), SEG("KM2 estrella", S()), SEG("KM3 triángulo", S())],
    solucion: [SEG("KM1 línea", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0"))),
      SEG("Tiempo de estrella", S(NO("%Q0.0"), TON("T_Estrella", "T#5s"))),
      SEG("KM2 estrella", S(NO("%Q0.0"), NC("T_Estrella.Q"), NC("%Q0.2"), COIL("%Q0.1"))),
      SEG("KM3 triángulo", S(NO("%Q0.0"), NO("T_Estrella.Q"), NC("%Q0.1"), COIL("%Q0.2")))],
    nunca: [["%Q0.1", "%Q0.2"]],
    pasos: [
      { in: {}, t: 60, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "Reposo: todo apagado." },
      { in: { "%I0.0": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 1, "%Q0.2": 0 }, d: "Marcha: KM1 + KM2 (estrella)." },
      { in: { "%I0.0": 0 }, t: 4600, ex: { "%Q0.0": 1, "%Q0.1": 1, "%Q0.2": 0 }, d: "4,7 s: sigue en estrella." },
      { in: {}, t: 800, ex: { "%Q0.0": 1, "%Q0.1": 0, "%Q0.2": 1 }, d: "5,5 s: ya en triángulo." },
      { in: {}, t: 2000, ex: { "%Q0.0": 1, "%Q0.1": 0, "%Q0.2": 1 }, d: "Sigue en triángulo." },
      { in: { "%I0.1": 1 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "Paro: todo fuera." },
      { in: { "%I0.1": 0, "%I0.0": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 1, "%Q0.2": 0 }, d: "Nueva marcha: vuelve a empezar en estrella." }
    ] },
  quiz: [
    { q: "¿Por qué se arranca en estrella?", o: ["Para girar más rápido", "Para reducir la corriente de arranque", "Para invertir el giro"], a: 1, e: "En estrella cada bobinado recibe √3 veces menos tensión: la corriente baja a ~1/3." },
    { q: "¿Qué pasa si KM2 y KM3 cierran a la vez?", o: ["Nada", "Cortocircuito entre fases", "El motor gira al revés"], a: 1, e: "Por eso se enclavan por programa y por cableado." },
    { q: "El enclavamiento por programa entre KM2 y KM3 se hace con…", o: ["Contactos NA cruzados", "Contactos NC cruzados", "Un contador"], a: 1, e: "NC de KM3 en la bobina de KM2 y NC de KM2 en la de KM3." }
  ] },
/* ==================================================================== */
{ id: "bloques", nivel: "avanzado", titulo: "Programa estructurado: OB, FC, FB y DB", min: 25,
  teoria: `
<p>Un programa profesional no es un OB1 con 300 segmentos. Se divide en bloques:</p>
<table class="t">
<tr><th>Bloque</th><th>Para qué</th></tr>
<tr><td><b>OB</b> (bloque de organización)</td><td>Los llama el sistema operativo: <code>OB1</code> ciclo, <code>OB100</code> arranque, <code>OB30</code> alarma cíclica (cada X ms, ideal para PID), <code>OB82</code> diagnóstico, <code>OB80</code> error de tiempo.</td></tr>
<tr><td><b>FC</b> (función)</td><td>Código <b>sin memoria</b>: lo que entra, se calcula y sale. Ej.: escalar una señal.</td></tr>
<tr><td><b>FB</b> (bloque de función)</td><td>Código <b>con memoria</b> (variables Static) guardada en un <b>DB de instancia</b>. Ej.: un FB "Motor" que se reutiliza para 20 motores, cada uno con su DB.</td></tr>
<tr><td><b>DB global</b></td><td>Datos compartidos por todo el programa: recetas, consignas, datos para el HMI.</td></tr>
</table>
<h3>La interfaz de un bloque</h3>
<ul>
  <li><b>Input</b>: datos que entran. <b>Output</b>: resultados. <b>InOut</b>: se lee y se escribe.</li>
  <li><b>Static</b> (solo FB): memoria que se conserva entre ciclos (aquí viven los temporizadores como <b>multiinstancia</b>).</li>
  <li><b>Temp</b>: variables de trabajo que <b>no conservan</b> su valor: escríbelas antes de leerlas.</li>
  <li><b>Constant</b>: valores fijos con nombre.</li>
</ul>
<div class="tip"><b>Regla de oro del FB reutilizable:</b> dentro del FB usa solo su interfaz, nunca
<code>%I</code>, <code>%Q</code> o <code>%M</code> directos. Así el mismo bloque sirve para cualquier motor.</div>
<p>Con <b>acceso optimizado</b> (por defecto en S7‑1200/1500) las variables de un DB no tienen dirección
absoluta: se accede solo por nombre (<code>"Motor_1_DB".Marcha</code>), lo que es más rápido y seguro.</p>
<p>Un <b>UDT</b> (tipo de datos PLC) agrupa variables en una estructura propia: por ejemplo
<code>typMotor</code> con Marcha, Paro, Fallo, Horas… y se declara un array de 20 motores.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha_M1", "push"), TAG("%I0.1", "Paro_M1", "pushNC", "NC cableado"), TAG("%Q0.0", "M1"), TAG("%I0.2", "Marcha_M2", "push"), TAG("%I0.3", "Paro_M2", "pushNC", "NC cableado"), TAG("%Q0.1", "M2")],
    prog: [SEG("Esto, repetido para cada motor, es lo que se encapsula en un FB \"Motor\"", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0"))),
      SEG("Mismo código, otro motor: candidato a FB con su DB de instancia", S(P([NO("%I0.2")], [NO("%Q0.1")]), NO("%I0.3"), COIL("%Q0.1")))] },
  quiz: [
    { q: "Necesitas un bloque que guarde las horas de funcionamiento de cada motor. ¿FC o FB?", o: ["FC", "FB con DB de instancia"], a: 1, e: "Necesita memoria propia entre ciclos: Static en un FB." },
    { q: "Una variable Temp…", o: ["Conserva el valor del ciclo anterior", "No conserva su valor: hay que escribirla antes de leerla", "Se guarda en el DB global"], a: 1, e: "Vive en la pila local solo mientras se ejecuta el bloque." },
    { q: "¿Qué OB usarías para un PID que debe ejecutarse cada 100 ms exactos?", o: ["OB1", "OB30 (alarma cíclica)", "OB100"], a: 1, e: "La alarma cíclica da una base de tiempo constante, independiente del ciclo." },
    { q: "Dentro de un FB reutilizable conviene…", o: ["Usar %I y %Q directamente", "Usar solo variables de su interfaz", "Usar marcas %M globales"], a: 1, e: "Así es independiente del cableado y se puede instanciar muchas veces." }
  ] },
/* ==================================================================== */
{ id: "secuencias", nivel: "avanzado", titulo: "Secuencias y máquinas de estado", min: 30,
  teoria: `
<p>Las máquinas trabajan por <b>pasos</b>: llenar → calentar → mezclar → vaciar. Programarlo con
autorretenciones sueltas acaba en un enredo. La forma limpia es una <b>variable de paso</b> (Int):</p>
<ol>
  <li>Cada paso tiene un número: 0 = reposo, 10 = llenar, 20 = calentar…</li>
  <li>Un segmento por transición: <code>paso == 10</code> AND <code>nivel_lleno</code> → <code>MOVE 20 → paso</code>.</li>
  <li>Las salidas se escriben <b>una sola vez</b>, comparando el paso: <code>paso == 10</code> → bobina <code>Valvula_Entrada</code>.</li>
</ol>
<div class="tip">Numera de 10 en 10: así se pueden intercalar pasos nuevos (15) sin renumerar.
Para secuencias grandes, TIA Portal tiene el lenguaje <b>GRAPH</b> (SFC), y en SCL se usa <code>CASE paso OF</code>.</div>
<h3>Secuencias por tiempo</h3>
<p>Si los pasos solo dependen del tiempo (un semáforo), basta un TON que se reinicia solo
(con un NC de su propia <code>.Q</code> en IN) y comparadores sobre su <code>.ET</code>.</p>
<p>El ejemplo es una mezcladora con variable de paso en <code>%MW20</code>. Pulsa Marcha, activa el
sensor de nivel y observa cómo avanza el paso en la tabla de observación.</p>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Nivel_Lleno", "switch"), TAG("%MW20", "Paso"), TAG("%Q0.0", "Valvula_Llenado"), TAG("%Q0.1", "Mezclador"), TAG("%Q0.2", "Valvula_Vaciado"), TAG("%I0.2", "Tanque_Vacio", "switch")],
    prog: [
      SEG("Paso 0 → 10 con Marcha", S(CMP("==", "%MW20", "0"), NO("%I0.0"), MOVE("10", "%MW20"))),
      SEG("Paso 10 → 20 con nivel lleno", S(CMP("==", "%MW20", "10"), NO("%I0.1"), MOVE("20", "%MW20"))),
      SEG("Paso 20: mezclar 4 s", S(CMP("==", "%MW20", "20"), TON("T_Mezcla", "T#4s"), MOVE("30", "%MW20"))),
      SEG("Paso 30 → 0 con tanque vacío", S(CMP("==", "%MW20", "30"), NO("%I0.2"), MOVE("0", "%MW20"))),
      SEG("Salidas", S(CMP("==", "%MW20", "10"), COIL("%Q0.0"))),
      SEG("", S(CMP("==", "%MW20", "20"), COIL("%Q0.1"))),
      SEG("", S(CMP("==", "%MW20", "30"), COIL("%Q0.2")))] },
  reto: {
    enunciado: "Semáforo cíclico con el selector <code>%I0.0 \"Habilitar\"</code>: <b>Verde</b> <code>%Q0.0</code> 4 s → <b>Ámbar</b> <code>%Q0.1</code> 1 s → <b>Rojo</b> <code>%Q0.2</code> 3 s, y se repite. Con el selector en OFF, todo apagado. <i>Pista: un TON de 8 s que se reinicia solo y comparadores sobre su ET (los tiempos se comparan con literales como <code>T#4s</code>).</i>",
    tags: [TAG("%I0.0", "Habilitar", "switch"), TAG("%Q0.0", "Verde"), TAG("%Q0.1", "Ambar"), TAG("%Q0.2", "Rojo")],
    inicio: [SEG("Temporizador de ciclo", S(NO("%I0.0"), NC("T_Ciclo.Q"), TON("T_Ciclo", "T#8s"))), SEG("Verde", S()), SEG("Ámbar", S()), SEG("Rojo", S())],
    solucion: [SEG("Temporizador de ciclo", S(NO("%I0.0"), NC("T_Ciclo.Q"), TON("T_Ciclo", "T#8s"))),
      SEG("Verde", S(NO("%I0.0"), CMP("<", "T_Ciclo.ET", "T#4s"), COIL("%Q0.0"))),
      SEG("Ámbar", S(CMP(">=", "T_Ciclo.ET", "T#4s"), CMP("<", "T_Ciclo.ET", "T#5s"), COIL("%Q0.1"))),
      SEG("Rojo", S(CMP(">=", "T_Ciclo.ET", "T#5s"), COIL("%Q0.2")))],
    nunca: [["%Q0.0", "%Q0.1"], ["%Q0.0", "%Q0.2"], ["%Q0.1", "%Q0.2"]],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "OFF: todo apagado." },
      { in: { "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 1, "%Q0.1": 0, "%Q0.2": 0 }, d: "0,2 s: verde." },
      { in: {}, t: 3600, ex: { "%Q0.0": 1 }, d: "3,8 s: sigue verde." },
      { in: {}, t: 500, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "4,3 s: ámbar." },
      { in: {}, t: 1000, ex: { "%Q0.1": 0, "%Q0.2": 1 }, d: "5,3 s: rojo." },
      { in: {}, t: 2500, ex: { "%Q0.2": 1 }, d: "7,8 s: sigue rojo." },
      { in: {}, t: 500, ex: { "%Q0.0": 1, "%Q0.2": 0 }, d: "8,3 s: vuelve el verde (ciclo nuevo)." },
      { in: { "%I0.0": 0 }, t: 200, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "OFF: todo apagado." }
    ] },
  quiz: [
    { q: "¿Por qué numerar los pasos de 10 en 10?", o: ["Porque el PLC lo exige", "Para poder intercalar pasos sin renumerar", "Para ahorrar memoria"], a: 1, e: "Paso 15 entre el 10 y el 20, sin tocar el resto." },
    { q: "En una máquina de estados, cada salida física se escribe…", o: ["En cada transición", "Una sola vez, según el paso activo", "Con Set en todos los pasos"], a: 1, e: "Una bobina por salida, en un único lugar." },
    { q: "¿Qué lenguaje de TIA Portal está hecho para secuencias?", o: ["GRAPH", "FUP", "STL"], a: 0, e: "GRAPH (SFC) dibuja pasos y transiciones." }
  ] },
/* ==================================================================== */
{ id: "analogicas", nivel: "avanzado", titulo: "Señales analógicas: NORM_X y SCALE_X", min: 25,
  teoria: `
<p>Un transmisor de nivel, presión o temperatura entrega 4‑20 mA o 0‑10 V. El módulo analógico lo
convierte en un <b>Int</b> en una palabra de entrada, por ejemplo <code>%IW64</code>:</p>
<table class="t">
<tr><th>Señal</th><th>Valor en %IW</th></tr>
<tr><td>0 V / 4 mA (0 %)</td><td>0</td></tr>
<tr><td>5 V / 12 mA (50 %)</td><td>13 824</td></tr>
<tr><td>10 V / 20 mA (100 %)</td><td><b>27 648</b></td></tr>
<tr><td>Rebase / rotura de hilo</td><td>&gt; 27 648 (hasta 32 767)</td></tr>
</table>
<h3>Escalar en dos cajas</h3>
<ol>
  <li><code>NORM_X</code> (MIN = 0, VALUE = %IW64, MAX = 27648) → un <b>Real</b> de 0.0 a 1.0.</li>
  <li><code>SCALE_X</code> (MIN = 0.0, VALUE = ese Real, MAX = 5.0) → el nivel en metros.</li>
</ol>
<p>Para una salida analógica (<code>%QW80</code>, un variador) se hace al revés: NORM_X de la consigna y SCALE_X a 0…27648 en Int.</p>
<h3>Histéresis</h3>
<p>Si una bomba arranca a 20 % y para a 20 %, el ruido del sensor la hará arrancar y parar sin fin
(<i>chattering</i>). Se usan dos umbrales: arranca por debajo del 20 % y para por encima del 80 %. Entre medio,
<b>conserva el estado</b>: un trabajo perfecto para Set/Reset con comparadores.</p>
<div class="tip">En el simulador mueve la barra de <code>%IW64</code>: el ejemplo compara directamente en bruto
(13 824 = 50 %). Un programa real escalaría primero a unidades de ingeniería.</div>`,
  ejemplo: { tags: [TAG("%IW64", "Nivel_Bruto", "analog"), TAG("%Q0.0", "Mas_de_50pct"), TAG("%Q0.1", "Rebase")],
    prog: [SEG("Más de la mitad", S(CMP(">=", "%IW64", "13824"), COIL("%Q0.0"))), SEG("Fuera de rango (rotura o rebase)", S(CMP(">", "%IW64", "27648"), COIL("%Q0.1")))] },
  reto: {
    enunciado: "Tanque con histéresis: el nivel llega en bruto en <code>%IW64 \"Nivel\"</code> (0…27648). La bomba de llenado <code>%Q0.0 \"Bomba\"</code> arranca cuando el nivel baja de <b>5530</b> (20 %) y para cuando supera <b>22118</b> (80 %). Entre los dos umbrales mantiene lo que estaba haciendo.",
    tags: [TAG("%IW64", "Nivel", "analog"), TAG("%Q0.0", "Bomba")],
    inicio: [SEG("Arrancar con nivel bajo", S()), SEG("Parar con nivel alto", S())],
    solucion: [SEG("Arrancar con nivel bajo", S(CMP("<", "%IW64", "5530"), SET("%Q0.0"))), SEG("Parar con nivel alto", S(CMP(">", "%IW64", "22118"), RST("%Q0.0")))],
    pasos: [
      { in: { "%IW64": 3000 }, t: 60, ex: { "%Q0.0": 1 }, d: "Nivel 11 %: la bomba llena." },
      { in: { "%IW64": 14000 }, t: 60, ex: { "%Q0.0": 1 }, d: "Nivel 50 % subiendo: sigue llenando." },
      { in: { "%IW64": 23000 }, t: 60, ex: { "%Q0.0": 0 }, d: "Nivel 83 %: para." },
      { in: { "%IW64": 14000 }, t: 60, ex: { "%Q0.0": 0 }, d: "Baja a 50 %: sigue parada." },
      { in: { "%IW64": 6000 }, t: 60, ex: { "%Q0.0": 0 }, d: "Baja a 22 %: aún parada." },
      { in: { "%IW64": 5000 }, t: 60, ex: { "%Q0.0": 1 }, d: "Baja a 18 %: arranca." }
    ] },
  quiz: [
    { q: "En un S7‑1200, una señal de 10 V en el canal analógico se lee como…", o: ["10", "1000", "27648"], a: 2, e: "El rango nominal es 0…27648." },
    { q: "¿Qué devuelve NORM_X?", o: ["Un Real entre 0.0 y 1.0", "Un Int en %", "La señal en mA"], a: 0, e: "Normaliza; SCALE_X lo lleva a unidades de ingeniería." },
    { q: "¿Para qué sirve la histéresis?", o: ["Para que el sensor sea más preciso", "Para evitar arranques y paradas continuas por ruido", "Para escalar la señal"], a: 1, e: "Dos umbrales separados dan estabilidad." }
  ] },
/* ==================================================================== */
{ id: "oficio", nivel: "avanzado", titulo: "Puesta en marcha, diagnóstico y buenas prácticas", min: 20,
  teoria: `
<h3>Herramientas de prueba en TIA Portal</h3>
<ul>
  <li><b>Observación online</b> (gafas): ve el flujo de corriente en LAD, como en este simulador.</li>
  <li><b>Tabla de observación y forzado</b>: lee y <i>modifica</i> variables una vez (útil para probar un paso).</li>
  <li><b>Forzado permanente</b>: impone el valor de una E/S aunque el programa diga otra cosa. La CPU enciende el LED MAINT. <b>Peligroso</b>: quítalo siempre al terminar y avisa.</li>
  <li><b>Referencias cruzadas</b> (F11 en un operando): dónde se lee y dónde se escribe una variable. La herramienta nº 1 para encontrar “¿quién apaga esta salida?”.</li>
  <li><b>Búfer de diagnóstico</b> de la CPU: el historial de errores, paradas y cambios de modo.</li>
  <li><b>Trace</b>: graba señales en el tiempo como un osciloscopio.</li>
</ul>
<h3>Buenas prácticas</h3>
<ol>
  <li>Nombres simbólicos claros y comentarios en <b>cada segmento</b> (título + qué hace).</li>
  <li>Cada bobina se escribe en <b>un solo lugar</b>. Evita Set/Reset dispersos.</li>
  <li>Paros y emergencias cableados <b>NC</b>; la seguridad de personas va por hardware o F‑CPU.</li>
  <li>Estructura: un FB por equipo, DB globales para HMI, OB100 para inicializar.</li>
  <li>Guarda versiones del proyecto (archivo <code>.zap</code>) antes de cada cambio en planta.</li>
  <li>Prueba en PLCSIM antes de cargar en una máquina real.</li>
</ol>
<div class="tip"><b>Diagnóstico en 4 preguntas:</b> ¿llega la señal a la entrada (LED del módulo)? ¿El
programa la ve (observación)? ¿El segmento conduce hasta la bobina? ¿Alguien más escribe esa salida
(referencias cruzadas)?</div>`,
  ejemplo: { tags: [TAG("%I0.0", "Marcha", "push"), TAG("%I0.1", "Paro", "pushNC", "NC cableado"), TAG("%Q0.0", "Motor")],
    prog: [SEG("BUG: la autorretención funciona…", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0"))),
      SEG("…pero esta bobina repetida la apaga. Bórrala en modo Editar.", S(NO("%I0.0"), COIL("%Q0.0")))] },
  quiz: [
    { q: "Una salida se apaga “sola” y no sabes por qué. Primera herramienta:", o: ["Borrar y reescribir el segmento", "Referencias cruzadas de la salida", "Cambiar la CPU"], a: 1, e: "Te muestra todos los lugares donde se escribe." },
    { q: "Terminaste de probar con forzado permanente. Debes…", o: ["Dejarlo por si acaso", "Quitar todos los forzados y comprobar que el LED MAINT se apaga", "Desconectar el PLC"], a: 1, e: "Un forzado olvidado es un riesgo serio." },
    { q: "En el ejemplo de esta lección, ¿por qué el motor no se mantiene al soltar Marcha?", o: ["Falta el paro", "La bobina se escribe dos veces y gana la última", "El contacto de autorretención está mal"], a: 1, e: "El segmento 2 escribe 0 cuando no se pulsa Marcha." }
  ] }
];
