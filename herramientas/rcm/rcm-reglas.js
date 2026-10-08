<script>
/* rcm:reglas:inicio — ESPEJO de nefer/fixmate/decision.py y rcm.py.
 *
 * Las constantes de abajo las escribe `herramientas/espejo-rcm.py`; el arbol
 * de decision y el informe de completitud estan escritos a mano en los dos
 * lenguajes, igual que el motor de busqueda y las reglas de la ronda. Que
 * hagan lo mismo lo responde `tests/test_fixmate_cruce_rcm.py`, que corre
 * ESTE javascript sobre las 729 combinaciones de respuestas por cada clase
 * de consecuencia, evidente y oculta, y compara dictamen por dictamen —
 * estrategia, motivo, camino, avisos y banderas— con lo que dice Python.
 *
 * Importa mas aqui que en ninguna otra parte de FixMate. Un arbol que se
 * separa no da error en ningun lado: la pantalla del taller dice «operar
 * hasta la falla» y la oficina dice «rediseño obligatorio» sobre el mismo
 * modo de falla de seguridad, las dos se ven razonables, y la que queda
 * firmada es la que alguien imprimio primero.
 *
 * LO QUE ESTA PANTALLA NO HACE, A PROPOSITO:
 *
 *   - No evalua criticidad. El metodo es configurable y vive en
 *     `criticidad.py` con sus matrices; traerlo aqui seria una segunda copia
 *     de una tabla que cada planta cambia. Se muestran los valores tal como
 *     los declara el archivo, con el nombre del metodo, y la evaluacion la
 *     hace la oficina.
 *   - No arma la matriz FMECA. Sus treinta columnas las define `fmeca.py` y
 *     salen del comando `fixmate rcm matriz`. Lo que hay en pantalla es un
 *     resumen para mirar, no el archivo que se entrega.
 *   - No clasifica contra el catalogo de fallas ni toca el historial.
 *
 * Las tres son decisiones de donde vive cada cosa, no funciones a medio
 * hacer, y cada una esta dicha tambien en la pantalla.
 */
/* rcm:datos:inicio */
var ESTRATEGIAS = {};
var POR_DEFECTO = [];
var PROACTIVAS = [];
var CLASES_CONSECUENCIA = [];
var CONSECUENCIAS_GRAVES = [];
var PREGUNTAS = [];
var CRITICAS = [];
var SIN_DATOS_ECONOMICOS = "";
var AVISO_SIN_EVALUAR = "";
var AVISO_89 = "";
var ADVERTENCIA_RPN = "";
var CONSECUENCIAS_JA1011 = {};
/* rcm:datos:fin */

/* Los campos del arbol, en el orden en que los nombra `Respuestas`. El orden
 * importa: es el que decide si una decision quedo «incompleta». */
var CAMPOS_DECISION = ["detectable", "intervalo_edad", "restaurable", "viable",
                       "costo_efectiva", "probable"];

/* Las preguntas del arbol, tal como las registra cada paso en Python. */
var P_EVIDENTE = "¿La perdida de funcion es evidente para quien opera?";
var P_GRAVE = "¿Tiene consecuencia de seguridad o ambiental?";
var P_DETECTABLE = "¿La degradacion se detecta con aviso suficiente para actuar?";
var P_EDAD = "¿Hay una edad a la que la probabilidad de falla sube?";
var P_RESTAURABLE = "¿Restaurar devuelve la resistencia original?";
var P_PROBABLE = "¿Se puede probar periodicamente que la proteccion responde?";
var P_VIABLE_CBM = "¿La tarea a condicion es tecnicamente viable?";
var P_VIABLE_EDAD = "¿La tarea por intervalo es tecnicamente viable?";
var P_COSTO = "¿Alguna tarea cuesta menos que la consecuencia de la falla?";
var P_GUARDA = "Sin tarea proactiva y con consecuencia de seguridad: " +
               "¿operar hasta la falla?";

/* ----------------------------------------------------------- utilidades */

/** Tri-estado. `null` es «no se evaluo», y no es lo mismo que «no». */
function tri(v) { return v === true ? true : v === false ? false : null; }

function siNo(v) { return v === true ? "si" : v === false ? "no" : "sin evaluar"; }

function esGrave(modo) {
  var c = modo.consecuencias || [];
  for (var i = 0; i < c.length; i++) {
    var clase = typeof c[i] === "string" ? c[i] : c[i].clase;
    if (CONSECUENCIAS_GRAVES.indexOf(clase) >= 0) return true;
  }
  return false;
}

function respuestas(d) {
  d = d || {};
  var r = {};
  CAMPOS_DECISION.forEach(function (k) { r[k] = tri(d[k]); });
  return r;
}

function _paso(camino, pregunta, respuesta, consecuencia) {
  camino.push({ pregunta: pregunta, respuesta: respuesta,
                consecuencia: consecuencia });
}

function _dictamen(estrategia, motivo, camino, opc) {
  opc = opc || {};
  return {
    estrategia: estrategia,
    rotulo: ESTRATEGIAS[estrategia],
    motivo: motivo,
    camino: camino,
    por_defecto: !!opc.por_defecto,
    bloqueado_por_seguridad: !!opc.bloqueado_por_seguridad,
    incompleta: !!opc.incompleta,
    avisos: opc.avisos || []
  };
}

/* ------------------------------------------------- el arbol de decision */

/** La estrategia de un modo de falla. Mismo contrato que `decision.decidir()`.
 *
 * El orden de las preguntas no es cosmetico: evidente u oculta va primero
 * porque una falla oculta no se trata por su propio riesgo sino por el de la
 * falla multiple; y la guarda del final no se negocia — con consecuencia de
 * seguridad o ambiental, «operar hasta la falla» no es una salida legal.
 */
function decidir(modo, entrada) {
  var r = respuestas(entrada);
  var camino = [];
  var avisos = [];
  var grave = esGrave(modo);
  var sinEvaluar = CAMPOS_DECISION.filter(function (k) {
    return r[k] === null && k !== "costo_efectiva";
  });
  var cierre = function (estrategia, motivo, cam, opc) {
    opc = opc || {};
    opc.incompleta = sinEvaluar.length > 0;
    opc.avisos = avisos.concat(sinEvaluar.length ? [AVISO_SIN_EVALUAR] : []);
    return _dictamen(estrategia, motivo, cam, opc);
  };

  // ---- 1. ¿Es evidente? Primera bifurcacion, antes que nada.
  if (!modo.evidente) {
    _paso(camino, P_EVIDENTE, "no",
          "falla oculta: el riesgo es la falla multiple, no esta falla sola");
    if (r.probable === true) {
      _paso(camino, P_PROBABLE, "si", "busqueda de fallas");
      return cierre("busqueda_fallas",
        "La falla es oculta: por si sola no produce efecto, pero deja " +
        "sin proteccion a la siguiente. El riesgo que se trata aqui no " +
        "es esta falla sino la falla multiple, asi que la tarea no " +
        "previene nada: comprueba periodicamente que la funcion oculta " +
        "todavia responde.",
        camino, { por_defecto: true });
    }
    _paso(camino, P_PROBABLE, siNo(r.probable),
          "no hay forma de verificar la funcion oculta");
    return cierre("rediseno",
      "Falla oculta que no se puede verificar: no hay tarea que confirme " +
      "que la proteccion sigue ahi, y entonces nada acota el riesgo de la " +
      "falla multiple. Lo que corresponde es cambiar el diseño para " +
      "hacerla evidente o verificable.",
      camino, { por_defecto: true, bloqueado_por_seguridad: grave });
  }

  _paso(camino, P_EVIDENTE, "si", "sigue por la rama de fallas evidentes");

  // ---- 2. ¿Consecuencia grave? Cambia el criterio de aceptacion.
  _paso(camino, P_GRAVE, grave ? "si" : "no",
        grave ? "la tarea debe reducir el riesgo a un nivel tolerable"
              : "basta con que la tarea cueste menos que la falla");

  // ---- 3. CBM primero: aprovecha la vida util y no abre una maquina sana.
  if (r.detectable === true) {
    _paso(camino, P_DETECTABLE, "si", "mantenimiento segun condicion");
    if (r.viable === false) {
      _paso(camino, P_VIABLE_CBM, "no", "se descarta CBM y se sigue buscando");
    } else {
      if (!grave && r.costo_efectiva === null) avisos.push(SIN_DATOS_ECONOMICOS);
      return cierre("cbm",
        "La degradacion se puede detectar con aviso suficiente: se " +
        "vigila la condicion y se interviene cuando el parametro lo " +
        "pide, no cuando lo diga el calendario.",
        camino, {});
    }
  } else {
    _paso(camino, P_DETECTABLE, siNo(r.detectable),
          "no hay tarea a condicion aplicable");
  }

  // ---- 4. Edad: sin zona de desgaste, un limite por horas no previene nada.
  if (r.intervalo_edad === true) {
    _paso(camino, P_EDAD, "si", "una tarea por intervalo puede servir");
    if (r.restaurable === true && r.viable !== false) {
      return cierre("restauracion",
        "Hay una edad identificable a la que la falla se vuelve probable, " +
        "y restaurar devuelve la resistencia original: se restaura antes " +
        "de ese punto.",
        camino.concat([{ pregunta: P_RESTAURABLE, respuesta: "si",
                         consecuencia: "restauracion programada" }]), {});
    }
    if (r.viable !== false) {
      return cierre("descarte",
        "Hay una edad identificable y el item no se restaura: se descarta " +
        "y se reemplaza antes de ese punto.",
        camino.concat([{ pregunta: P_RESTAURABLE, respuesta: siNo(r.restaurable),
                         consecuencia: "descarte programado" }]), {});
    }
    _paso(camino, P_VIABLE_EDAD, "no", "no hay tarea proactiva aplicable");
  } else {
    _paso(camino, P_EDAD, siNo(r.intervalo_edad),
          "restauracion y descarte no previenen nada aqui");
    if (r.intervalo_edad === false) avisos.push(AVISO_89);
  }

  // ---- 5. No hay tarea proactiva. Aqui manda la guarda.
  if (grave) {
    _paso(camino, P_GUARDA, "no",
          "la guarda lo impide: el rediseño es obligatorio");
    return cierre("rediseno",
      "Ninguna tarea proactiva reduce el riesgo a un nivel tolerable y la " +
      "falla tiene consecuencia de seguridad o ambiental: operar hasta la " +
      "falla no es una salida legal. Corresponde cambiar el diseño, el " +
      "contexto operacional o el procedimiento.",
      camino, { por_defecto: true, bloqueado_por_seguridad: true });
  }

  if (r.costo_efectiva === false) {
    _paso(camino, P_COSTO, "no", "operar hasta la falla");
    return cierre("operar_hasta_falla",
      "Sin consecuencia grave, sin degradacion detectable y sin edad " +
      "identificable: ninguna tarea programada se paga. Se repara cuando " +
      "falle, a conciencia y no por omision.",
      camino, { por_defecto: true });
  }

  if (r.costo_efectiva === null) avisos.push(SIN_DATOS_ECONOMICOS);
  _paso(camino, P_COSTO, siNo(r.costo_efectiva),
        "operar hasta la falla, sin declarar ahorro");
  return cierre("operar_hasta_falla",
    "No hay tarea proactiva aplicable y la consecuencia no es de seguridad. " +
    "Se opera hasta la falla; si aparece un dato economico que lo cambie, se " +
    "revisa.",
    camino, { por_defecto: true });
}

/* ------------------------------------------- el analisis y su completitud */

/** Pone a funciones, fallas y modos el id que les pondria Python.
 *
 * No es cosmetica: `Analisis.agregar_*()` numera F1, F1.1, F1.1.1 —1-based,
 * por posicion— y el archivo que exporta esta pantalla se carga despues con
 * `cargador.analisis()`. Si los ids se numeraran distinto, las decisiones no
 * casarian con sus modos al volver a la oficina.
 *
 * Devuelve la misma forma plana que tiene `Analisis`: funciones, fallas y
 * modos en tres listas, con las llaves cosidas.
 */
function normalizarAnalisis(datos) {
  var a = {
    activo: datos.activo || {}, contexto: datos.contexto || "",
    facilitador: datos.facilitador || "",
    participantes: datos.participantes || [],
    fecha: datos.fecha || "",
    metodo_criticidad: datos.metodo_criticidad || "",
    // La identificacion del documento: que version es, quien la aprobo y
    // cuando toca volver a mirarla.
    revision: datos.revision || "",
    aprobado_por: datos.aprobado_por || "",
    proxima_revision: datos.proxima_revision || "",
    funciones: [], fallas: [], modos: []
  };
  if (!a.contexto) a.contexto = a.activo.contexto || "";

  (datos.funciones || []).forEach(function (fd, i) {
    var funcion = {
      id: "F" + (i + 1), descripcion: fd.descripcion || "",
      estandar: fd.estandar || "", tipo: fd.tipo || "principal",
      condicion: fd.condicion || ""
    };
    a.funciones.push(funcion);
    (fd.fallas || []).forEach(function (ffd, j) {
      var falla = { id: funcion.id + "." + (j + 1), funcion_id: funcion.id,
                    descripcion: ffd.descripcion || "" };
      a.fallas.push(falla);
      (ffd.modos || []).forEach(function (md, k) {
        var modo = {
          id: falla.id + "." + (k + 1), falla_funcional_id: falla.id,
          descripcion: md.descripcion || "",
          ubicacion: md.ubicacion || {},
          codigo_catalogo: md.codigo_catalogo || "",
          causa: md.causa || "", mecanismo: md.mecanismo || "",
          evidente: md.evidente === undefined ? true : !!md.evidente,
          efecto: md.efecto || {},
          consecuencias: md.consecuencias || [],
          criticidad: md.criticidad || null,
          evidencia: md.evidencia || [],
          estado: md.estado || "propuesto",
          decision: md.decision || null
        };
        a.modos.push(modo);
      });
    });
  });
  return a;
}

function fallasDe(a, funcionId) {
  return a.fallas.filter(function (f) { return f.funcion_id === funcionId; });
}

function modosDe(a, fallaId) {
  return a.modos.filter(function (m) { return m.falla_funcional_id === fallaId; });
}

function efectoDescrito(modo) {
  return !!String((modo.efecto || {}).local || "").trim();
}

function _respuesta(pregunta, contestada, faltantes) {
  return { numero: pregunta.numero, clave: pregunta.clave, texto: pregunta.texto,
           contestada: !!contestada, faltantes: faltantes || [] };
}

/** Que preguntas de JA1011 quedaron contestadas. Mismo contrato que
 *  `rcm.completitud()`.
 *
 * `completo` es True solo con las siete. No hay porcentaje que redondee
 * hacia arriba: el criterio de la norma es binario a proposito, porque la
 * norma nacio porque se vendian metodologias incompletas con ese nombre.
 */
function completitud(a, decisiones) {
  decisiones = decisiones || {};
  var rs = [];

  // Q1 - funciones con estandar. El estandar ya es obligatorio al cargar.
  rs.push(_respuesta(PREGUNTAS[0], a.funciones.length > 0,
    a.funciones.length ? [] : ["no hay ninguna funcion declarada"]));

  // Q2 - cada funcion con al menos una falla funcional.
  var sinFalla = a.funciones.filter(function (f) { return !fallasDe(a, f.id).length; })
                            .map(function (f) { return f.id; });
  rs.push(_respuesta(PREGUNTAS[1], a.fallas.length > 0 && !sinFalla.length,
    sinFalla.length
      ? sinFalla.map(function (i) { return "la funcion " + i + " no tiene fallas funcionales"; })
      : (a.fallas.length ? [] : ["no hay fallas funcionales"])));

  // Q3 - cada falla funcional con al menos un modo.
  var sinModo = a.fallas.filter(function (f) { return !modosDe(a, f.id).length; })
                        .map(function (f) { return f.id; });
  rs.push(_respuesta(PREGUNTAS[2], a.modos.length > 0 && !sinModo.length,
    sinModo.length
      ? sinModo.map(function (i) { return "la falla " + i + " no tiene modos de falla"; })
      : (a.modos.length ? [] : ["no hay modos de falla"])));

  // Q4 - efecto descrito en cada modo.
  var sinEfecto = a.modos.filter(function (m) { return !efectoDescrito(m); })
                         .map(function (m) { return m.id; });
  rs.push(_respuesta(PREGUNTAS[3], a.modos.length > 0 && !sinEfecto.length,
    sinEfecto.length
      ? sinEfecto.map(function (i) { return "el modo " + i + " no tiene efecto descrito"; })
      : (a.modos.length ? [] : ["no hay modos de falla"])));

  // Q5 - consecuencia clasificada en cada modo.
  var sinConsec = a.modos.filter(function (m) { return !(m.consecuencias || []).length; })
                         .map(function (m) { return m.id; });
  rs.push(_respuesta(PREGUNTAS[4], a.modos.length > 0 && !sinConsec.length,
    sinConsec.length
      ? sinConsec.map(function (i) { return "el modo " + i + " no tiene consecuencia clasificada"; })
      : (a.modos.length ? [] : ["no hay modos de falla"])));

  // Q6 - una decision registrada por modo.
  var sinDecision = a.modos.filter(function (m) {
    return !Object.prototype.hasOwnProperty.call(decisiones, m.id);
  }).map(function (m) { return m.id; });
  rs.push(_respuesta(PREGUNTAS[5], a.modos.length > 0 && !sinDecision.length,
    sinDecision.length
      ? sinDecision.map(function (i) { return "el modo " + i + " no tiene decision de estrategia"; })
      : (a.modos.length ? [] : ["no hay modos de falla"])));

  // Q7 - donde la decision fue una accion por defecto, tiene que estar
  // registrada como tal. Un modo con tarea proactiva no debe nada aqui.
  var faltanDefecto = Object.keys(decisiones).filter(function (mid) {
    var d = decisiones[mid];
    return d && d.por_defecto && !d.motivo;
  }).map(function (mid) {
    return "el modo " + mid + ": la decision es una accion por defecto y no quedo justificada";
  });
  var hayDecisiones = Object.keys(decisiones).length > 0;
  var q7 = hayDecisiones && !sinDecision.length && !faltanDefecto.length;
  rs.push(_respuesta(PREGUNTAS[6], q7,
    faltanDefecto.length
      ? faltanDefecto
      : ((hayDecisiones && !sinDecision.length) ? [] : ["faltan decisiones por registrar"])));

  var rompe = rs.some(function (r) {
    return !r.contestada && CRITICAS.indexOf(r.clave) >= 0;
  });
  return {
    respuestas: rs,
    completo: rs.every(function (r) { return r.contestada; }),
    contestadas: rs.filter(function (r) { return r.contestada; }).length,
    rompe_cadena: rompe
  };
}

/* ------------------------------------- la evidencia que llega del campo */

/** Une una anomalia de la ronda con el modo de falla que declara su mismo
 *  codigo. Mismo contrato que `anomalia.enlazar()`, y el `motivo` de mas,
 *  que es para la pantalla.
 *
 * Exige coincidencia EXACTA de codigo y de activo, y no elige entre dos
 * candidatos: una anomalia enlazada al modo equivocado contamina la
 * frecuencia por modo y la decision de estrategia que sale de ahi.
 *
 * Lo que aqui NO se hace, igual que en el telefono: deducir el codigo de un
 * texto libre. Eso es el catalogo de fallas —41 entradas con sus pistas— y
 * lo hace la oficina con `fixmate tpm anomalias`. Una anomalia sin codigo se
 * queda sin enganchar, y la pantalla dice por que.
 */
function enlazarAnomalia(a, analisis) {
  if (a.modo_falla_id) {
    return { modo_falla_id: a.modo_falla_id, motivo: "la pauta declara el modo" };
  }
  if (!a.codigo_catalogo) {
    return { modo_falla_id: "",
             motivo: "sin codigo de catalogo: el telefono no clasifica texto libre" };
  }
  if (!analisis || analisis.activo.codigo !== a.activo_codigo) {
    return { modo_falla_id: "", motivo: "la anomalia es de otro activo" };
  }
  var candidatos = analisis.modos.filter(function (m) {
    return m.codigo_catalogo === a.codigo_catalogo;
  });
  if (candidatos.length === 1) {
    return { modo_falla_id: candidatos[0].id, motivo: "por codigo de catalogo" };
  }
  if (candidatos.length === 0) {
    return { modo_falla_id: "",
             motivo: "ningun modo del analisis declara ese codigo" };
  }
  return { modo_falla_id: "",
           motivo: "dos modos declaran el mismo codigo: la ambiguedad se " +
                   "resuelve en el analisis, no aqui a la suerte" };
}

/* ------------------------------- el analisis como registro auditable */

/** Audita el analisis como documento, no como metodo. Mismo contrato que
 *  `rcm.calidad()`.
 *
 * Las siete preguntas dicen si el analisis esta terminado. Esto dice si se
 * puede auditar dentro de dos años: quien lo aprobo, que version es, cuando
 * toca revisarlo, y si los codigos de adentro son inequivocos. Un analisis
 * puede tener las siete contestadas y no ser un registro valido.
 *
 * `hoy` en ISO 8601 activa la comprobacion de vigencia; sin el no se mira,
 * porque una funcion que cambia de respuesta segun el dia no se puede
 * probar ni comparar con el otro lado.
 */
function calidadRCM(a, hoy) {
  hoy = hoy || "";
  var hallazgos = [];

  var faltan = [];
  if (!String(a.revision || "").trim()) faltan.push("numero de revision");
  if (!String(a.aprobado_por || "").trim()) faltan.push("quien lo aprobo");
  if (!String(a.fecha || "").trim()) faltan.push("fecha");
  if (faltan.length) {
    hallazgos.push({ clave: "identificacion", gravedad: "no conformidad",
      detalle: "el analisis no declara " + faltan.join(", ") + ". Un analisis " +
        "sin version ni aprobacion es un borrador que alguien va a usar " +
        "como si fuera definitivo.", ids: [] });
  }

  if (!(a.participantes || []).length) {
    hallazgos.push({ clave: "participantes", gravedad: "no conformidad",
      detalle: "el analisis no declara participantes. Un analisis RCM hecho por " +
        "una sola persona no tiene el contexto operacional de quien opera.",
      ids: [] });
  }

  if (!a.proxima_revision) {
    hallazgos.push({ clave: "vigencia", gravedad: "observacion",
      detalle: "no se declara cuando toca revisarlo. El contexto operacional " +
        "cambia, y una consecuencia evaluada en otro contexto ya no vale.",
      ids: [] });
  } else if (hoy && a.proxima_revision < hoy) {
    hallazgos.push({ clave: "vigencia", gravedad: "no conformidad",
      detalle: "la revision vencio el " + a.proxima_revision + ".", ids: [] });
  }

  // La ambiguedad que impide enganchar una anomalia de campo. Si nadie la
  // dice al revisar, el analisis se da por bueno y el enganche falla en
  // silencio meses despues.
  var porcodigo = {};
  a.modos.forEach(function (m) {
    if (!m.codigo_catalogo) return;
    if (!porcodigo[m.codigo_catalogo]) porcodigo[m.codigo_catalogo] = [];
    porcodigo[m.codigo_catalogo].push(m.id);
  });
  Object.keys(porcodigo).filter(function (c) { return porcodigo[c].length > 1; })
    .sort().forEach(function (codigo) {
      hallazgos.push({ clave: "codigo_repetido", gravedad: "no conformidad",
        detalle: "los modos " + porcodigo[codigo].join(", ") + " declaran el mismo " +
          "codigo «" + codigo + "». Una anomalia de campo con ese codigo no se " +
          "puede enganchar: la ambiguedad se resuelve aqui, no al recibirla.",
        ids: porcodigo[codigo] });
    });

  var codificados = a.modos.filter(function (m) { return !!m.codigo_catalogo; }).length;
  var sinCodigo = a.modos.filter(function (m) { return !m.codigo_catalogo; })
                         .map(function (m) { return m.id; });
  if (sinCodigo.length) {
    hallazgos.push({ clave: "sin_codificar", gravedad: "observacion",
      detalle: sinCodigo.length + " de " + a.modos.length + " modos no tienen " +
        "codigo de catalogo: no se agregan con los de la flota ni se " +
        "enganchan con la ronda.", ids: sinCodigo });
  }

  var conforme = !hallazgos.some(function (h) {
    return h.gravedad === "no conformidad"; });
  return { hallazgos: hallazgos, modos: a.modos.length,
           codificados: codificados, conforme: conforme };
}

/** Lo que un jefe de mantenimiento mira primero. Mismo contrato que
 *  `decision.resumen()`. */
function resumenRCM(a, decisiones) {
  decisiones = decisiones || {};
  var reparto = {};
  Object.keys(ESTRATEGIAS).forEach(function (k) { reparto[k] = 0; });
  var ids = Object.keys(decisiones);
  ids.forEach(function (mid) { reparto[decisiones[mid].estrategia] += 1; });
  return {
    activo: a.activo.codigo || "",
    modos: a.modos.length,
    decididos: ids.length,
    graves: a.modos.filter(esGrave).length,
    ocultos: a.modos.filter(function (m) { return !m.evidente; }).length,
    reparto: reparto,
    "rediseños_obligatorios": ids.filter(function (mid) {
      return decisiones[mid].bloqueado_por_seguridad; }).length,
    "decisiones_incompletas": ids.filter(function (mid) {
      return decisiones[mid].incompleta; }).length
  };
}
/* rcm:reglas:fin */

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    decidir: decidir, completitud: completitud, resumenRCM: resumenRCM,
    enlazarAnomalia: enlazarAnomalia, calidadRCM: calidadRCM,
    CONSECUENCIAS_JA1011: CONSECUENCIAS_JA1011,
    normalizarAnalisis: normalizarAnalisis, esGrave: esGrave,
    fallasDe: fallasDe, modosDe: modosDe, efectoDescrito: efectoDescrito,
    ESTRATEGIAS: ESTRATEGIAS, POR_DEFECTO: POR_DEFECTO, PROACTIVAS: PROACTIVAS,
    PREGUNTAS: PREGUNTAS, CRITICAS: CRITICAS,
    CLASES_CONSECUENCIA: CLASES_CONSECUENCIA,
    CONSECUENCIAS_GRAVES: CONSECUENCIAS_GRAVES,
    SIN_DATOS_ECONOMICOS: SIN_DATOS_ECONOMICOS,
    AVISO_SIN_EVALUAR: AVISO_SIN_EVALUAR, AVISO_89: AVISO_89,
    ADVERTENCIA_RPN: ADVERTENCIA_RPN
  };
}
</script>
