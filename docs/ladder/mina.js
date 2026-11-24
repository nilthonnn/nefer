/* La mina: escenarios de una operación de cobre a tajo abierto en altura,
   como Quellaveco (Moquegua), y la guía «¿Cómo se resuelve?» de los retos.

   IMPORTANTE: los escenarios son DIDÁCTICOS. Describen prácticas comunes de la
   minería del cobre (bloque estándar de motor, permisivos, local/remoto desde
   la sala de control, respaldo de energía, sincronismo, fajas y bombas). Los
   nombres de equipos, TAG, tiempos y valores son de ejemplo: no son datos de
   la planta real de Quellaveco ni de ninguna otra. */

(function () {
  var n = NIVELES.find(function (x) { return x.id === "energia"; });
  if (n) { n.nombre = "Mina: energía y planta"; n.desc = "Lógica de mina: bloque de motor, TTA, sincronismo de grupos, fajas y bombas, en escenarios tipo de una mina de cobre en altura."; }
})();

/* ===================== bloque estándar de motor ===================== */
PLANTAS.motor = {
  /* el contactor confirma 300 ms después de la orden, salvo falla simulada */
  model: function (e) {
    var s = e.ps;
    if (e.v["%Q0.0"] && !e.pressed["%I0.4"]) s.t = (s.t || 0) + e.dt; else s.t = 0;
    e.forced["%I0.4"] = s.t >= 300 ? 1 : 0;
    s.giro = ((s.giro || 0) + (e.forced["%I0.4"] ? e.dt * 0.4 : 0)) % 360;
  },
  hmi: function (e) {
    var s = e.ps, rem = !!e.v["%I0.0"], on = !!e.forced["%I0.4"], g = (s.giro || 0) * Math.PI / 180, aspas = "";
    for (var i = 0; i < 3; i++) { var a = g + i * 2.094; aspas += '<line x1="70" y1="78" x2="' + (70 + 22 * Math.cos(a)) + '" y2="' + (78 + 22 * Math.sin(a)) + '" style="stroke:' + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:4;stroke-linecap:round"/>'; }
    return HM.svg(165, '<circle cx="70" cy="78" r="34" style="fill:' + (on ? "var(--good2)" : "var(--canvas)") + ";stroke:" + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:3"/>' + aspas +
      HM.tx(70, 130, "Bomba de agua de proceso", { w: 700, s: 10.5 }) + HM.tx(70, 143, "(equipo de ejemplo)", { s: 9, c: "var(--ink3)" }) +
      '<rect x="150" y="14" width="100" height="26" rx="13" style="fill:var(--box);stroke:var(--line)"/><circle cx="' + (rem ? 236 : 164) + '" cy="27" r="10" style="fill:var(--acc)"/>' +
      HM.tx(178, 31, "LOCAL", { a: "start", s: 9.5, w: 700, c: rem ? "var(--ink3)" : "var(--ink)" }) + HM.tx(224, 31, "REM", { a: "end", s: 9.5, w: 700, c: rem ? "var(--ink)" : "var(--ink3)" }) +
      HM.tx(258, 31, rem ? "manda la sala de control" : "manda el operador en campo", { a: "start", s: 9.5, c: "var(--ink2)" }) +
      HM.lamp(160, 60, e.v["%I0.7"], "Orden de la sala de control (DCS)", "var(--acc)") +
      HM.lamp(160, 80, e.v["%I0.5"], "Permisivo de proceso (nivel, válvula abierta…)", "var(--on)") +
      HM.lamp(160, 100, !e.v["%I0.3"], "Parada de emergencia pulsada", "var(--bad)") +
      HM.lamp(160, 120, e.v["%Q0.0"], "Contactor: orden de marcha", "var(--on)") +
      HM.lamp(160, 140, e.v["%Q0.1"], "FALLA: el contactor no confirmó", "var(--bad)") + HM.falla(e, 162));
  }
};

function TAGS_MOTOR() {
  return [TAG("%I0.0", "Remoto", "switch", "1 = sala de control"), TAG("%I0.1", "Arranque_Local", "push"), TAG("%I0.2", "Parada_Local", "pushNC", "NC cableado"),
    TAG("%I0.3", "Emergencia", "pushNC", "seta NC"), TAG("%I0.4", "Confirmacion", "plant", "pulsa = el contactor no confirma", { falla: 1 }),
    TAG("%I0.5", "Permisivo", "switch", "", { def: 1 }), TAG("%I0.6", "Reset", "push"), TAG("%I0.7", "Orden_DCS", "switch"),
    TAG("%Q0.0", "Contactor"), TAG("%Q0.1", "Falla_Arranque"), TAG("%Q0.2", "En_Marcha")];
}

LECCIONES.push({
  id: "motor", nivel: "energia", titulo: "Lógica de mina: el bloque estándar de motor", min: 35,
  teoria: `
<p>En una concentradora hay cientos de motores: bombas, fajas, chancadoras, agitadores, ventiladores. No se programa cada
uno «a su manera»: se usa un <b>bloque estándar</b> (en TIA Portal, un FB «Motor» con su DB por equipo) que todos los
técnicos conocen. Su lógica es siempre la misma:</p>
<table class="t">
<tr><th>Pieza</th><th>Qué hace</th></tr>
<tr><td><b>Local / Remoto</b></td><td>Un selector en campo decide quién manda: el operador junto al equipo (<i>Local</i>, con su botonera) o la sala de control (<i>Remoto</i>, la orden llega del DCS o SCADA). Nunca los dos a la vez.</td></tr>
<tr><td><b>Orden remota mantenida</b></td><td>La sala de control envía una orden <b>de nivel</b>: 1 = marcha. No hace falta autorretención.</td></tr>
<tr><td><b>Botonera local</b></td><td>Pulsadores de marcha y parada con autorretención, como en la lección Marcha‑paro.</td></tr>
<tr><td><b>Permisivos</b></td><td>Condiciones de proceso para poder marchar: nivel mínimo en el pozo, válvula de succión abierta, chute libre… Si caen, el equipo para.</td></tr>
<tr><td><b>Parada de emergencia</b></td><td>Manda siempre, en local y en remoto. (La seguridad real va además por hardware: relé o PLC de seguridad.)</td></tr>
<tr><td><b>Confirmación de marcha</b></td><td>El contacto auxiliar del contactor (o el variador) confirma que arrancó. Orden sin confirmación en un tiempo = <b>falla de arranque</b>, memorizada hasta el reset.</td></tr>
<tr><td><b>Estado al DCS</b></td><td>La sala de control ve el estado real (confirmado), no la orden.</td></tr>
</table>
<div class="tip">Este bloque es la base de todo lo demás de la ruta: la bomba de un pozo de relaves, una faja de mineral o
el ventilador de una sala eléctrica son este mismo bloque con permisivos distintos.</div>
<p>Prueba el ejemplo: cambia el selector a remoto y verás que la botonera local ya no manda.</p>`,
  mina: `En una mina de cobre a tajo abierto en altura, como Quellaveco, los equipos de planta se operan casi siempre en
<b>remoto</b> desde la sala de control, y se pasan a <b>local</b> para mantenimiento o pruebas, con el equipo bloqueado y
señalizado según el procedimiento de bloqueo (LOTO). Por eso el bloque debe impedir que la botonera local arranque un
equipo que la sala de control cree detenido, y viceversa.`,
  ejemplo: { planta: "motor", tags: TAGS_MOTOR(),
    prog: [SEG("Marcha solo en local (falta el modo remoto)", S(P([NO("%I0.1")], [NO("%Q0.0")]), NO("%I0.2"), NO("%I0.3"), COIL("%Q0.0"))), SEG("Estado al DCS", S(NO("%I0.4"), COIL("%Q0.2")))] },
  reto: { planta: "motor",
    enunciado: "Programa el bloque de motor. <b>Remoto</b> (<code>%I0.0</code> = 1): el contactor <code>%Q0.0</code> sigue a <code>Orden_DCS</code> <code>%I0.7</code>. <b>Local</b> (<code>%I0.0</code> = 0): <code>Arranque_Local</code> con autorretención y <code>Parada_Local</code> (NC). En los dos modos hacen falta el <code>Permisivo</code> <code>%I0.5</code>, la <code>Emergencia</code> sin pulsar (NC) y no tener <code>Falla_Arranque</code>. Si hay orden y no llega <code>Confirmacion</code> <code>%I0.4</code> en <b>2 s</b>: Set de <code>Falla_Arranque</code> <code>%Q0.1</code>, que se borra con <code>Reset</code> <code>%I0.6</code>. <code>En_Marcha</code> <code>%Q0.2</code> refleja la confirmación.",
    tags: TAGS_MOTOR(),
    inicio: [SEG("Marcha (remoto o local)", S()), SEG("Falla de confirmación", S()), SEG("Reset de falla", S()), SEG("Estado al DCS", S())],
    solucion: [SEG("Marcha (remoto o local)", S(P([NO("%I0.0"), NO("%I0.7")], [NC("%I0.0"), P([NO("%I0.1")], [NO("%Q0.0")]), NO("%I0.2")]), NO("%I0.5"), NO("%I0.3"), NC("%Q0.1"), COIL("%Q0.0"))),
      SEG("Falla de confirmación", S(NO("%Q0.0"), NC("%I0.4"), TON("T_Conf", "T#2s"), SET("%Q0.1"))),
      SEG("Reset de falla", S(NO("%I0.6"), RST("%Q0.1"))),
      SEG("Estado al DCS", S(NO("%I0.4"), COIL("%Q0.2")))],
    pasos: [
      { in: {}, t: 200, ex: { "%Q0.0": 0 }, d: "En local, sin órdenes: parado." },
      { in: { "%I0.1": 1 }, t: 200, ex: { "%Q0.0": 1 }, d: "Arranque local." },
      { in: { "%I0.1": 0 }, t: 600, ex: { "%Q0.0": 1, "%Q0.2": 1 }, d: "Se mantiene y la sala de control ve «en marcha» confirmado." },
      { in: { "%I0.2": 1 }, t: 200, ex: { "%Q0.0": 0 }, d: "Parada local." },
      { in: { "%I0.2": 0, "%I0.0": 1, "%I0.1": 1 }, t: 300, ex: { "%Q0.0": 0 }, d: "En remoto, la botonera local no arranca." },
      { in: { "%I0.1": 0, "%I0.7": 1 }, t: 600, ex: { "%Q0.0": 1, "%Q0.2": 1 }, d: "La sala de control da la orden: arranca." },
      { in: { "%I0.5": 0 }, t: 200, ex: { "%Q0.0": 0 }, d: "Cae el permisivo de proceso: se detiene." },
      { in: { "%I0.5": 1 }, t: 300, ex: { "%Q0.0": 1 }, d: "Vuelve el permisivo con la orden presente: marcha." },
      { in: { "%I0.3": 1 }, t: 200, ex: { "%Q0.0": 0 }, d: "Parada de emergencia: se detiene, también en remoto." },
      { in: { "%I0.3": 0, "%I0.7": 0 }, t: 300, ex: { "%Q0.0": 0 }, d: "Se rearma la seta y la sala quita la orden." },
      { in: { "%I0.4": 1, "%I0.7": 1 }, t: 2500, ex: { "%Q0.1": 1, "%Q0.0": 0 }, d: "Orden sin confirmación del contactor: a los 2 s, falla de arranque." },
      { in: { "%I0.4": 0 }, t: 300, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Bloqueado mientras no se haga reset." },
      { in: { "%I0.6": 1 }, t: 600, ex: { "%Q0.1": 0, "%Q0.0": 1, "%Q0.2": 1 }, d: "Reset: con la orden presente arranca y confirma." }
    ] },
  quiz: [
    { q: "En modo remoto, ¿quién da la orden de marcha?", o: ["La botonera local", "La sala de control (DCS/SCADA)", "Los dos a la vez"], a: 1, e: "El selector define un único dueño del equipo." },
    { q: "¿Qué es un permisivo?", o: ["Una alarma", "Una condición de proceso necesaria para marchar (nivel, válvula, chute libre)", "Un tipo de temporizador"], a: 1, e: "Si cae, el equipo se detiene." },
    { q: "La sala de control debe ver como «en marcha»…", o: ["La orden del PLC", "La confirmación real del contactor", "El selector"], a: 1, e: "Orden ≠ estado: se informa lo confirmado." },
    { q: "¿La parada de emergencia actúa en remoto?", o: ["No, solo en local", "Sí, siempre", "Solo si el DCS lo permite"], a: 1, e: "La emergencia manda en cualquier modo." }
  ]
});

/* ===================== «En la mina»: escenarios tipo ===================== */
var MINA = {
  grupo: "Una mina en altura tiene grupos electrógenos de respaldo para la sala de control, las comunicaciones, el campamento y las bombas de drenaje del tajo. A más de 3 000 m el grupo entrega menos que su placa (derrateo) y el frío hace más difícil el arranque: las protecciones y su inhibición en el arranque se ajustan a eso.",
  arranque: "Tras un apagón de la red, el grupo de emergencia de una sala eléctrica de la concentradora tiene que arrancar sin nadie al lado, de noche y con frío de altura. Los ciclos de arranque y reposo protegen el arrancador y las baterías, y la alarma de falla de arranque llega a la sala de control.",
  tta: "En una operación como Quellaveco, las cargas críticas (sala de control, servidores, comunicaciones, iluminación de emergencia, bombas de drenaje) se respaldan con TTA. La red llega en alta tensión desde el sistema interconectado y se reduce en subestaciones: un hueco de tensión breve es frecuente, por eso la confirmación de falla evita arrancar el grupo sin necesidad.",
  discrepancia: "Los interruptores de media tensión de las subestaciones de planta se operan en remoto desde la sala de control. Si un interruptor no confirma su maniobra (resorte descargado, carro extraído, disparo por protección), el sistema debe alarmar y bloquear la secuencia: nadie está en la subestación para verlo.",
  sincronismo: "Cuando la potencia de respaldo de un área supera lo que da un grupo, se instala una central de grupos en paralelo. El segundo grupo tiene que sincronizarse con la barra antes de cerrar su interruptor: un cierre fuera de fase en una barra que alimenta motores grandes daña el grupo y los equipos.",
  reparto: "Con varios grupos en la misma barra, el reparto de kW entre ellos decide cuánto combustible quema cada uno y cuánto dura el mantenimiento. En altura, la capacidad de cada grupo ya viene recortada por el derrateo: ningún grupo debe quedar sobrecargado mientras otro va en vacío.",
  demanda: "El arranque de un motor grande de la planta (una bomba de relaves, un molino de bolas en arranque asistido) es un escalón de carga que un solo grupo no siempre aguanta. Arrancar el segundo grupo por demanda y deslastrar cargas no esenciales (talleres, iluminación de patios, campamento) evita que caiga toda la barra.",
  faja: "En una mina de cobre el mineral viaja del chancado primario al acopio y a la molienda por fajas de cientos de metros. Arranque contra el flujo, vaciado al parar, sirena de prearranque y pull‑cord a lo largo de toda la faja son obligatorios: hay personal de mantenimiento trabajando en el recorrido.",
  bombas: "Pozos de bombeo de relaves, de agua recuperada desde el espesador y de drenaje del tajo: casi siempre con bomba principal y de reserva que se alternan. Una bomba que no arranca cuando sube el nivel termina en un rebalse ambiental: por eso el nivel muy alto pone las dos en marcha.",
  linea: "La misma lógica de transferencia con cilindro se encuentra en el laboratorio químico de una mina (cajas de muestras de perforación y de control de leyes que pasan de una faja a otra) y en las estaciones de muestreo de la planta.",
  diagnostico: "En una guardia de mantenimiento eléctrico‑instrumentación, la mayor parte del trabajo con el PLC no es programar: es encontrar por qué un equipo no hace lo que debe, con el programa en línea y el equipo detenido esperando.",
  lote: "Contar unidades y cortar por lote es lo de siempre en un despacho: sacos de reactivos, cajas de muestras para el laboratorio externo, bolas de molienda.",
  falla_cilindro: "Los cilindros neumáticos de compuertas, válvulas de dardo y desviadores de chute trabajan con polvo y frío de altura: se traban. Supervisar el fin de carrera por tiempo convierte una máquina que «se quedó pegada» en una alarma clara para la sala de control."
};
LECCIONES.forEach(function (L) {
  if (MINA[L.id]) L.mina = MINA[L.id];
  if (L.mina && !/de ejemplo/.test(L.mina)) L.mina += ' <span style="color:var(--ink3)">Escenario de ejemplo: los equipos, TAG y valores no son de la planta real.</span>';
});

/* ===================== «¿Cómo se resuelve?»: estrategia, teoría y porqué ===================== */
var GUIAS = {
  motor: {
    estrategia: "<p>Divide el problema en <b>quién manda</b> (local o remoto) y <b>qué lo deja marchar</b> (permisivo, emergencia, sin falla). La primera parte es un paralelo de dos ramas, una por modo; la segunda, contactos en serie después del paralelo, para que valgan en los dos modos.</p>",
    teoria: "<p>El selector Remoto aparece dos veces: <b>NA</b> en la rama remota y <b>NC</b> en la local. Así, en cada momento solo una rama puede conducir. La rama local lleva la autorretención (marcha‑paro); la remota no, porque la orden del DCS es de nivel.</p><p>La falla por falta de confirmación es una supervisión por tiempo: orden activa y confirmación ausente durante 2 s → Set de la alarma, que corta la orden en el segmento de marcha (contacto NC de la falla).</p>",
    notas: { 0: "El paralelo exterior separa los modos. Dentro de la rama local hay otro paralelo: Arranque_Local o el propio Contactor (autorretención). Permisivo, Emergencia y Falla van <b>fuera</b> del paralelo, para que manden en local y en remoto.",
      1: "Se mide el tiempo con la orden presente y la confirmación ausente. Si el contactor confirma en 300 ms, el TON se reinicia y nunca llega a 2 s.",
      2: "El reset solo borra la alarma. Si la orden remota sigue presente, el equipo vuelve a arrancar: en planta, la sala de control decide.",
      3: "Se informa lo <b>confirmado</b>, no la orden: así la sala de control ve la verdad del campo." } },
  tta: {
    estrategia: "<p>La TTA es una <b>secuencia con memoria</b>: primero decide <b>si hace falta el grupo</b> (una marca con Set/Reset) y después, por separado, <b>qué interruptor cierra</b>. Separar «decidir» de «actuar» es lo que la hace fácil de leer y de diagnosticar.</p>",
    teoria: "<p><b>Confirmación de falla:</b> un TON sobre «red ausente» filtra los microcortes. <b>Retorno estable:</b> otro TON sobre «red presente», más largo. <b>Pedir grupo:</b> Set con la falla confirmada, Reset con la red estable.</p><p><b>Abrir antes de cerrar:</b> cada interruptor se cierra solo si el <b>contacto auxiliar</b> del otro dice abierto. <b>Transición con retardo:</b> el 52R espera 1 s para que decaiga la tensión residual de los motores. <b>Enfriamiento:</b> un TOF mantiene el grupo girando después de liberarlo.</p>",
    notas: { 0: "Un hueco de tensión de menos de 3 s no llega a la salida del TON: el grupo no arranca por un microcorte.",
      1: "El retorno exige 10 s de red estable (en planta, minutos): una red que va y viene no provoca transferencias en cadena.",
      2: "Set: una vez confirmada la falla, la decisión se mantiene aunque la red vuelva a medias.",
      3: "Reset: solo la red estable libera el grupo. Este segmento va después del Set: si se cumplieran los dos a la vez, ganaría el último.",
      4: "El TOF hace dos cosas con un solo contacto: arrancar el grupo con la decisión y mantenerlo 5 s más para enfriar.",
      5: "52G solo cierra con grupo en tensión y con 52R confirmado abierto (contacto auxiliar, no la orden).",
      6: "52R espera la decisión inversa, la red, el 52G abierto y 1 s más: la transición con retardo para que caiga la tensión residual." } },
  sincronismo: {
    estrategia: "<p>Un sincronizador hace dos trabajos independientes: <b>regular</b> la velocidad del grupo entrante hasta la ventana de deslizamiento, y <b>permitir el cierre</b> solo cuando todo está dentro de ventana. Escribe primero la medida (Δf), después la regulación y al final el permiso de cierre.</p>",
    teoria: "<p>Ventanas de IEEE 1547 para más de 1 500 kVA: <b>Δf ≤ 0,1 Hz</b>, <b>ΔV ≤ 3 %</b>, <b>Δφ ≤ ±10°</b>. Se busca un deslizamiento <b>positivo</b> pequeño (el entrante algo más rápido) para que tome carga al cerrar y no quede motorizado.</p><p>Una ventana «entre A y B» en LAD son <b>dos comparadores en serie</b>: ≥ A y ≤ B.</p>",
    notas: { 0: "Sin condiciones: el SUB se calcula en cada ciclo. Δf en centésimas de Hz evita trabajar con decimales.",
      1: "Subir mientras el entrante va lento (Δf < 0,05 Hz). Con 52G2 cerrado ya no se regula: la frecuencia la manda la barra.",
      2: "Bajar si se pasó (Δf > 0,10 Hz). Entre 5 y 10 no se toca nada: esa banda muerta evita que suba y baje sin parar.",
      3: "Seis condiciones en serie = todas a la vez. El Set da el pulso de cierre; el interruptor tarda 80 ms y el modelo de planta revisa el ángulo en el momento real del cierre.",
      4: "Sin modo sincronizar, se retira la orden de cierre y el 52G2 abre." } },
  grupo: {
    estrategia: "<p>Primero el temporizador de <b>inhibición</b> (el tiempo que la presión tiene para subir), después los <b>disparos</b> que memorizan la alarma, el <b>reset</b> y al final la <b>marcha</b>, que respeta la alarma.</p>",
    notas: { 0: "El TON corre desde que hay combustible: a los 8 s la protección de presión queda habilitada.",
      1: "Tres ramas en paralelo = cualquiera dispara. La de presión necesita las dos cosas: inhibición terminada y presión baja.",
      2: "El reset exige que la causa haya desaparecido: un reset con la temperatura alta no borra nada.",
      3: "La alarma (NC) corta la marcha y además impide volver a arrancar mientras siga." } },
  arranque: {
    estrategia: "<p>El truco es un <b>reloj de ciclo</b>: un TON de 10 s que se reinicia solo. Con un comparador sobre su ET partes cada ciclo en «arrancar» (0–5 s) y «reposar» (5–10 s). Un contador de flancos del arrancador cuenta los intentos.</p>",
    notas: { 3: "El NC de su propia salida Q reinicia el TON al terminar: cada 10 s empieza un ciclo nuevo mientras el motor no gire.",
      4: "Arrancador en la primera mitad del ciclo, y nunca con el motor girando (NC Motor_Girando): así el piñón se suelta al instante.",
      5: "Cada flanco del arrancador es un intento. El contador se pone a cero cuando no hay demanda.",
      6: "Al terminar la parte de arranque del 3.er intento sin que gire: alarma." } },
  discrepancia: {
    estrategia: "<p>«Orden distinta del estado» es un <b>O exclusivo</b>: (orden y no estado) o (no orden y estado). Dos ramas en paralelo. Un TON le da a la maniobra su tiempo normal antes de alarmar.</p>",
    notas: { 0: "Durante una maniobra normal la discrepancia dura 80 ms: el TON de 0,5 s no llega a terminar.",
      2: "La alarma retira la orden: no se insiste sobre un interruptor que no responde." } },
  reparto: {
    estrategia: "<p>Mide la diferencia de carga entre los grupos y corrige el que se ajusta (G2) con <b>subir</b> o <b>bajar</b>, dejando una <b>banda muerta</b> en el medio.</p>",
    notas: { 1: "G1 lleva más: subir G2 para que tome carga.", 2: "G2 lleva más: bajarlo. Entre −50 y +50 kW no se toca: banda muerta." } },
  demanda: {
    estrategia: "<p>Dos umbrales con dos temporizadores, uno para pedir y otro para liberar el segundo grupo (Set/Reset), y el deslastre aparte, <b>sin retardo</b>, porque una sobrecarga no espera.</p>" },
  faja: {
    estrategia: "<p>Una marca de <b>sistema en marcha</b> con todas las paradas, y después cada faja <b>desde aguas abajo</b>: cada una con un TON para arrancar después de la anterior y un TOF para vaciarse al parar.</p>",
    notas: { 1: "La sirena suena mientras el TON de 5 s corre: un paralelo con el TON en una rama y la bobina de la sirena en la otra.",
      2: "CV‑02 arranca cuando terminó la sirena y sigue 10 s después (TOF): se vacía. Su pull‑cord la para al instante." } },
  bombas: {
    estrategia: "<p>La <b>demanda</b> con Set/Reset por niveles (histéresis), un <b>flanco negativo</b> de la demanda para saber que terminó un ciclo, y un <b>telerruptor</b> que cambia el turno. Cada bomba: demanda y su turno, o nivel muy alto.</p>" },
  linea: {
    estrategia: "<p>Escribe primero el <b>sistema</b> (autorretención), después las fajas y el cilindro. Para la faja 1 pregúntate: ¿qué tiene que pasar para que pueda traer otra caja? Cada respuesta es un contacto NC en serie.</p>",
    teoria: "<p>El cilindro necesita <b>autorretención propia</b>: el sensor que lo arranca deja de ver la caja al moverse. El <b>fin de carrera</b> corta esa autorretención (por eso el retorno es un NC en la rama del cilindro).</p>",
    notas: { 2: "Tres permisos en serie: sin caja en el tope, entrada de la faja 2 libre y cilindro recogido.",
      3: "El paralelo Sensor_1 / Cilindro es la autorretención. El NC de Retorno la corta al llegar al fin de carrera.",
      4: "El retorno es solo el fin de carrera; separarlo en una marca hace el programa más legible." } },
  diagnostico: {
    estrategia: "<p>No reescribas todo: <b>compara</b> segmento por segmento con lo que debería hacer la máquina. Mira la faja 1 cuando hay una caja en la entrada de la faja 2, y mira el cilindro justo cuando la caja deja de tapar el sensor 1.</p>",
    notas: { 2: "Error 1: el contacto del Sensor_2 tiene que ser <b>NC</b> (faja 1 solo si la entrada está libre). Con NA, la faja 1 solo correría con la entrada ocupada.",
      3: "Error 2: faltaba la rama de <b>autorretención</b> con el propio Cilindro. Sin ella, el cilindro vuelve en cuanto la caja deja de tapar el sensor 1." } },
  lote: {
    estrategia: "<p>Un CTU sobre el sensor de salida, y su Q usado dos veces: como <b>NC en la faja 1</b> (deja de traer cajas) y como <b>bobina de la luz</b>.</p>",
    notas: { 2: "El NC de C_Lote.Q es un permiso más de la faja 1.", 5: "La luz copia la salida del contador." } },
  falla_cilindro: {
    estrategia: "<p>Supervisión por tiempo: orden del cilindro presente y fin de carrera ausente durante 2 s → Set de la falla. La falla entra como NC en el cilindro (retira la orden) y en la faja 1 (detiene la línea).</p>",
    notas: { 5: "Una salida normal tarda 0,7 s: el TON de 2 s solo termina si el vástago se trabó.", 6: "El reconocimiento borra la alarma; la línea sigue sola si las condiciones lo permiten." } },
  estrella: {
    estrategia: "<p>KM1 con marcha‑paro, un TON que empieza con KM1, y estrella y triángulo como <b>dos ramas que se excluyen</b>: el TON terminado elige triángulo, y cada contactor lleva el NC del otro.</p>" }
};
LECCIONES.forEach(function (L) { if (L.reto && GUIAS[L.id]) L.reto.guia = GUIAS[L.id]; });

/* orden: el bloque de motor abre la ruta de la mina */
(function () {
  var m = LECCIONES.findIndex(function (l) { return l.id === "motor"; }), L = LECCIONES.splice(m, 1)[0];
  var g = LECCIONES.findIndex(function (l) { return l.nivel === "energia"; });
  LECCIONES.splice(g < 0 ? LECCIONES.length : g, 0, L);
})();

/* guías de los niveles básico, intermedio y avanzado */
var GUIAS_BASE = {
  contactos: { estrategia: "<p>Dos salidas, dos segmentos. Para cada una pregúntate: ¿con el sensor en 1 o en 0? En 1 → contacto <b>NA</b>; en 0 → contacto <b>NC</b>. Las dos usan el mismo sensor.</p>",
    teoria: "<p>El contacto del programa no es el contacto físico: un NC del programa pregunta «¿la señal vale 0?». La bobina escribe en cada ciclo lo que le llega: si deja de llegarle corriente, escribe 0.</p>" },
  logica: { estrategia: "<p>Escribe la frase como lógica: «(mano izquierda <b>y</b> mano derecha) <b>o</b> llave». El «y» son dos contactos en serie dentro de una rama; el «o», otra rama en paralelo con la llave.</p>",
    teoria: "<p>Serie = AND: conducen todos. Paralelo = OR: basta una rama. Para que la llave salte sobre <i>los dos</i> pulsadores, su rama tiene que abarcar a ambos (en el editor: <i>Rama paralela</i> y luego <i>Extender rama →</i>).</p>",
    notas: { 0: "La rama de arriba son las dos manos en serie; la de abajo, la llave. Así la llave sola basta, y las manos necesitan estar las dos." } },
  enclavamiento: { estrategia: "<p>Es marcha‑paro: <b>(marcha o la propia bomba)</b> en paralelo, y después, en serie, todo lo que puede pararla. Como el paro y el térmico están cableados NC, en reposo valen 1: se usan con contacto <b>NA</b>.</p>",
    teoria: "<p>La autorretención es el contacto de la propia salida en paralelo con la marcha. Las paradas van <b>después</b> del paralelo para tener prioridad: si se pulsan marcha y paro a la vez, gana el paro.</p>",
    notas: { 0: "Paro y térmico en serie después del paralelo: cualquiera de los dos corta, también la autorretención." } },
  setreset: { estrategia: "<p>Una salida que se «memoriza» pide <b>Set</b> en un segmento y <b>Reset</b> en otro. El Set con el sensor; el Reset con el reconocimiento <b>y</b> el sensor ya en 0.</p>",
    teoria: "<p>Set y Reset solo actúan cuando les llega corriente; si no, la salida conserva su valor. Si los dos actúan en el mismo ciclo gana el que está más abajo.</p>",
    notas: { 1: "El NC del nivel alto en el reset hace que reconocer no sirva mientras la causa siga presente." } },
  flancos: { estrategia: "<p>Dos pasos: un <b>pulso de un ciclo</b> con el flanco del pulsador, y un <b>telerruptor</b>: la luz cambia cuando llega el pulso y se mantiene cuando no.</p>",
    teoria: "<p>Telerruptor en LAD: (pulso <b>y no</b> luz) <b>o</b> (no pulso <b>y</b> luz) → luz. Con el pulso, la luz pasa a lo contrario de lo que era; sin pulso, se mantiene. Funciona porque el pulso dura un solo ciclo.</p>",
    notas: { 1: "Rama de arriba: llega el pulso con la luz apagada → enciende. Rama de abajo: sin pulso, la luz se mantiene a sí misma." } },
  temporizadores: { estrategia: "<p>«Arranca 3 s después de encender» es un <b>TON</b>; «sigue 2 s después de apagar» es un <b>TOF</b>. Cada uno en su segmento, con su instancia, y la bobina después de la caja.</p>",
    teoria: "<p>TON: Q se activa cuando IN lleva PT seguido; si IN cae antes, vuelve a cero. TOF: Q sigue PT después de que IN cae. La caja se pone en serie: deja pasar la corriente según su Q.</p>" },
  contadores: { estrategia: "<p>Un <b>CTU</b> con el sensor en CU (cuenta flancos, no hace falta un contacto P), el pulsador de nueva caja en R y PV = 6. Su salida Q enciende la luz.</p>",
    teoria: "<p>Q = CV ≥ PV. R pone CV a cero y tiene prioridad: mientras está activo no se cuenta.</p>" },
  datos: { estrategia: "<p>Dos MOVE, uno por pulsador, que escriben la consigna, y un comparador ≥ 2000 que enciende la luz. MOVE solo escribe mientras le llega corriente: al soltar, la consigna se conserva.</p>",
    teoria: "<p>EN = 0 → la caja no se ejecuta y OUT conserva su valor. Un comparador en LAD se comporta como un contacto: conduce si la comparación es cierta.</p>" },
  secuencias: { estrategia: "<p>Un solo TON de ciclo que se reinicia solo (NC de su propia Q) y <b>ventanas de tiempo</b> sobre su ET: verde 0–4 s, ámbar 4–5 s, rojo 5–8 s. Cada luz es un segmento con sus comparadores en serie.</p>",
    teoria: "<p>«Entre 4 y 5 s» son dos comparadores en serie: ET ≥ T#4s y ET &lt; T#5s. Las ventanas no se tocan, así que nunca hay dos luces a la vez.</p>" },
  analogicas: { estrategia: "<p>Histéresis con <b>Set/Reset</b>: Set por debajo del umbral bajo, Reset por encima del alto. Entre los dos no se cumple ninguno y la bomba conserva lo que estaba haciendo.</p>",
    teoria: "<p>La señal llega en bruto (0…27648 = 0…100 %). 20 % = 5530 y 80 % = 22118. Con un solo umbral la bomba arrancaría y pararía sin fin por el ruido del sensor.</p><p><b>La revisión de calidad te dejará una observación INFO</b>, y tiene razón: si el transmisor se corta, la entrada lee más de 27648 y el programa creería que el tanque está lleno. En planta se agrega un segmento con <code>CMP &gt; %IW64 27648</code> que da una alarma de «sensor fuera de rango» y lleva la bomba a un estado seguro. El reto no lo exige para mantenerlo simple.</p>" }
};
LECCIONES.forEach(function (L) { if (L.reto && !L.reto.guia && GUIAS_BASE[L.id]) L.reto.guia = GUIAS_BASE[L.id]; });
