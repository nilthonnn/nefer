<script>
/* ronda:reglas:inicio — ESPEJO de nefer/fixmate/tpm.py y anomalia.py.
 *
 * Las constantes de abajo las escribe `herramientas/espejo-ronda.py`; el
 * algoritmo esta escrito a mano en los dos lenguajes, igual que el motor de
 * busqueda. Que hagan lo mismo lo responde `tests/test_fixmate_cruce_ronda.py`,
 * que corre ESTE javascript y compara sus respuestas con las de Python.
 *
 * Dos copias que se separan no dan error en ninguna parte: el telefono dice
 * que la ronda esta completa y la oficina dice que no, los dos se ven
 * razonables, y nadie se entera. Por eso se genera y se cruza.
 *
 * LA UNICA DIFERENCIA DELIBERADA, Y ESTA PROBADA. El telefono NO codifica la
 * anomalia contra el catalogo ISO 14224; la oficina si, al recibir el
 * archivo. El catalogo son 41 entradas con sus pistas y su ponderacion, y
 * meterlo aqui seria una tercera copia que mantener — la app de diagnostico
 * ya lleva la suya. El telefono hereda el codigo SOLO cuando la pauta lo
 * declara, que es un dato que ya viene escrito.
 *
 * El cruce compara todo lo demas campo por campo, y una prueba aparte fija
 * esta diferencia: si el telefono empezara a codificar, o la oficina dejara
 * de hacerlo, se pone roja.
 */
/* ronda:datos:inicio */
var CLASES = {};
var RESULTADOS = {};
var SEVERIDADES = {};
var FRACCION_SOSPECHOSA = 0.4;
/* ronda:datos:fin */

/** Pone a cada punto el id que le pondria Python.
 *
 * No es cosmetica ni cosa de la pantalla: `Checklist.agregar()` numera
 * «{id de la pauta}.{n}», 1-based, y si el telefono numerara distinto la
 * oficina no podria casar cada anomalia con su punto al recibir el archivo.
 * Por eso vive aqui dentro, con el resto de lo que se cruza, y no en la
 * interfaz.
 */
function normalizarPauta(pauta) {
  var base = pauta.id || "pauta";
  pauta.puntos.forEach(function (p, i) {
    if (!p.id) p.id = base + "." + (i + 1);
    if (p.alcance_operador === undefined) p.alcance_operador = true;
    if (p.segundos === undefined) p.segundos = 0;
  });
  return pauta;
}

/** Como quedo una ronda. Mismo contrato que `tpm.estado()`. */
function estadoRonda(ejecucion, pauta) {
  normalizarPauta(pauta);
  var porId = {};
  pauta.puntos.forEach(function (p) { porId[p.id] = p; });

  var cuenta = { ok: 0, nok: 0, sin_acceso: 0 };
  var segundos = 0;
  var respondidos = {};
  ejecucion.items.forEach(function (i) {
    if (cuenta[i.resultado] === undefined) cuenta[i.resultado] = 0;
    cuenta[i.resultado] += 1;
    segundos += Math.max(0, Math.round(i.segundos || 0));
    respondidos[i.punto_id] = true;
  });

  var presupuesto = 0;
  pauta.puntos.forEach(function (p) { presupuesto += Math.max(0, p.segundos || 0); });
  var todos = ejecucion.items.length === pauta.puntos.length;

  return {
    total: pauta.puntos.length,
    respondidos: ejecucion.items.length,
    ok: cuenta.ok, nok: cuenta.nok, sin_acceso: cuenta.sin_acceso,
    pendientes: pauta.puntos.filter(function (p) { return !respondidos[p.id]; })
                            .map(function (p) { return p.id; }),
    segundos: segundos,
    presupuesto_seg: presupuesto,
    // Un punto sin ver no es una ronda completa con una nota: es una ronda
    // incompleta. La alternativa real a «no pude ver» es un OK falso.
    completa: todos && cuenta.sin_acceso === 0,
    // Solo se juzga la velocidad de una ronda terminada, y solo si la pauta
    // declaro presupuesto.
    sospechosa_de_firma: todos && presupuesto > 0 &&
                         segundos < presupuesto * FRACCION_SOSPECHOSA
  };
}

/** La anomalia que sale de un punto NOK. `null` para cualquier otro caso.
 *  Mismo contrato que `anomalia.desde_item()`. */
function anomaliaDe(ejecucion, item, pauta) {
  if (item.resultado !== "nok") return null;
  var punto = null;
  pauta.puntos.forEach(function (p) { if (p.id === item.punto_id) punto = p; });
  if (punto === null) return null;

  var texto = (item.observacion || "").trim();
  return {
    id: ejecucion.id + "." + punto.id,
    activo_codigo: ejecucion.activo_codigo,
    descripcion: texto || punto.punto,
    // Fuera del alcance del operador significa que hace falta el tecnico: se
    // decidio en frio al escribir la pauta, no en campo.
    severidad: punto.alcance_operador ? "programable" : "detiene",
    ejecucion_id: ejecucion.id,
    punto_id: punto.id,
    componente: punto.punto,
    condicion_observada: punto.criterio,
    detectada_por: ejecucion.operador,
    fecha: ejecucion.fecha,
    // El telefono NO clasifica contra el catalogo ni enlaza con RCM: eso lo
    // hace la oficina al recibir el archivo, que es donde esta el analisis.
    // Lo unico que se hereda es lo que la pauta ya declara.
    codigo_catalogo: punto.codigo_catalogo || "",
    modo_falla_id: punto.modo_falla_id || "",
    evidencia: [],
    estado: "abierta",
    responsable: "", accion: "", fecha_cierre: "", codigo_ot: ""
  };
}

function anomaliasDe(ejecucion, pauta) {
  normalizarPauta(pauta);
  var salida = [];
  ejecucion.items.forEach(function (i) {
    var a = anomaliaDe(ejecucion, i, pauta);
    if (a) salida.push(a);
  });
  return salida;
}
/* ronda:reglas:fin */

if (typeof module !== "undefined" && module.exports) {
  module.exports = { estadoRonda: estadoRonda, anomaliaDe: anomaliaDe,
                     anomaliasDe: anomaliasDe, normalizarPauta: normalizarPauta,
                     CLASES: CLASES,
                     RESULTADOS: RESULTADOS, SEVERIDADES: SEVERIDADES,
                     FRACCION_SOSPECHOSA: FRACCION_SOSPECHOSA };
}
</script>
