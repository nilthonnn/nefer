<script>
/* La pantalla. Es trabajo de oficina, no de campo: aqui no hay guante ni
 * socavon, hay una mesa, un proyector y cuatro personas discutiendo un modo
 * de falla. De ahi vienen las decisiones de diseño:
 *
 * EL ARBOL SE VE MIENTRAS SE CONTESTA. El valor de RCM no es la estrategia
 * que sale: es poder discutir por que salio esa. Cada respuesta reescribe el
 * camino en pantalla, y el camino es lo que queda firmado.
 *
 * «SIN EVALUAR» ES UN BOTON, NO UN VACIO. Si la unica forma de dejar una
 * pregunta sin contestar fuera no tocarla, no se podria distinguir «decidimos
 * que no» de «no lo miramos», y esa diferencia es la que dice cuanto trabajo
 * falta. Por eso son tres botones del mismo tamaño.
 *
 * LO QUE FALTA SE MUESTRA CON NOMBRE Y APELLIDO. El informe de JA1011 no dice
 * «78 % completo»: dice que falta Q4 y en que modos. Un porcentaje invita a
 * redondear hacia arriba; una lista de ids invita a arreglarla.
 *
 * NADA SE SUBE. El archivo se abre y se guarda en este navegador.
 */
/* rcm:demo:inicio */
var ANALISIS_DEMO = null;
/* rcm:demo:fin */

var app = document.getElementById("app");
var crudo = null;        // el JSON tal como lo abrio el usuario
var analisis = null;     // normalizado, con los ids de Python
var respuestasPorModo = {};  // modo_id -> {campo: true|false|null}
var decisiones = {};     // modo_id -> dictamen
var seleccion = null;    // modo_id abierto en la ficha
var ronda = null;        // la ronda CIL que se haya abierto encima
var porModo = {};        // modo_id -> anomalias de campo enganchadas
var sueltas = [];        // las que no engancharon, con el motivo

function esc(s) {
  return String(s === undefined || s === null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function campo(etiqueta, valor, vacio) {
  var hay = String(valor === undefined || valor === null ? "" : valor).trim();
  return '<div class="campo"><span>' + esc(etiqueta) + '</span><span' +
    (hay ? '>' + esc(hay) : ' class="vacio">' + esc(vacio || "sin declarar")) +
    '</span></div>';
}

function modo(id) {
  return analisis.modos.filter(function (m) { return m.id === id; })[0] || null;
}

function fallaDe(m) {
  return analisis.fallas.filter(function (f) {
    return f.id === m.falla_funcional_id; })[0] || null;
}

function funcionDe(m) {
  var ff = fallaDe(m);
  return ff ? analisis.funciones.filter(function (f) {
    return f.id === ff.funcion_id; })[0] || null : null;
}

// ------------------------------------------------------------- pantallas

function verInicio(error) {
  crudo = null; analisis = null; decisiones = {}; respuestasPorModo = {};
  seleccion = null;
  app.innerHTML =
    '<h1>Análisis RCM</h1>' +
    '<p class="tenue">Función → falla funcional → modo de falla → efecto → ' +
    'consecuencia, y de ahí al árbol de decisión de SAE JA1011. La pantalla ' +
    'no decide por usted: registra lo que el equipo contesta y muestra a ' +
    'dónde lleva cada respuesta.</p>' +
    (error ? '<div class="aviso peligro">' + esc(error) + '</div>' : '') +
    '<h2>Abrir el análisis</h2>' +
    '<div class="tarjeta">' +
    '<button id="archivo" class="primary">Abrir archivo de análisis (.json)</button>' +
    '<p class="tenue" style="margin:10px 0 0">El mismo formato que lee ' +
    '<code>fixmate rcm analizar</code>. Se abre en este navegador: no se ' +
    'sube a ninguna parte.</p></div>' +
    (ANALISIS_DEMO ? '<div class="tarjeta"><button id="demo">' +
      'Abrir el análisis de ejemplo' +
      '<span class="tenue" style="display:block;font-weight:400;margin-top:4px">' +
      'La excavadora EX-220 es un equipo inventado y los nombres están en ' +
      'blanco. Sirve para ver cómo funciona el árbol, no para firmar nada.' +
      '</span></button></div>' : '') +
    '<h2>Lo que esta pantalla no hace</h2>' +
    '<div class="aviso nota"><ul class="lista">' +
    '<li><b>No evalúa criticidad.</b> El método es configurable y vive en el ' +
    'lado de la oficina; aquí se muestran los valores tal como los declara el ' +
    'archivo, con el nombre del método.</li>' +
    '<li><b>No arma la matriz FMECA.</b> Sus treinta columnas salen de ' +
    '<code>fixmate rcm matriz</code>. Lo de aquí es un resumen para mirar.</li>' +
    '<li><b>No inventa respuestas.</b> Una pregunta sin evaluar se queda sin ' +
    'evaluar, y la decisión sale marcada como incompleta.</li>' +
    '</ul></div>';

  var inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json"; inp.className = "oculto";
  document.body.appendChild(inp);
  document.getElementById("archivo").onclick = function () { inp.click(); };
  inp.onchange = function () {
    var f = inp.files && inp.files[0];
    if (!f) return;
    var lector = new FileReader();
    lector.onload = function () {
      try { abrir(JSON.parse(lector.result)); }
      catch (e) { verInicio("Ese archivo no es un análisis legible: " + e.message); }
    };
    lector.readAsText(f);
  };
  if (ANALISIS_DEMO) {
    document.getElementById("demo").onclick = function () {
      abrir(JSON.parse(JSON.stringify(ANALISIS_DEMO)));
    };
  }
}

/** Las mismas exigencias que `cargador.analisis_de_dict()`, con los mismos
 *  motivos: una función sin estándar no se puede fallar de forma
 *  verificable, y de ella no sale ningún modo de falla útil. */
function revisar(a) {
  if (!a.funciones.length) return "El análisis no declara ninguna función.";
  for (var i = 0; i < a.funciones.length; i++) {
    var f = a.funciones[i];
    if (!String(f.descripcion).trim()) {
      return "La función " + f.id + " no tiene descripción.";
    }
    if (!String(f.estandar).trim()) {
      return "La función " + f.id + " («" + f.descripcion + "») no declara " +
        "estándar de desempeño. Una función sin estándar no se puede fallar " +
        "de forma verificable, y de ella no sale ningún modo de falla útil.";
    }
  }
  for (var j = 0; j < a.fallas.length; j++) {
    if (!String(a.fallas[j].descripcion).trim()) {
      return "La falla funcional " + a.fallas[j].id + " no tiene descripción.";
    }
  }
  for (var k = 0; k < a.modos.length; k++) {
    if (!String(a.modos[k].descripcion).trim()) {
      return "El modo de falla " + a.modos[k].id + " no tiene descripción.";
    }
    var cs = a.modos[k].consecuencias || [];
    for (var n = 0; n < cs.length; n++) {
      var clase = typeof cs[n] === "string" ? cs[n] : cs[n].clase;
      if (CLASES_CONSECUENCIA.indexOf(clase) < 0) {
        return "El modo " + a.modos[k].id + " declara la consecuencia «" +
          clase + "», que no existe. Si quería decir que la falla es oculta, " +
          "eso va en «evidente»: false, no en las consecuencias — es la " +
          "primera bifurcación del análisis, no una categoría más.";
      }
    }
  }
  return "";
}

function abrir(datos) {
  var a;
  try { a = normalizarAnalisis(datos || {}); }
  catch (e) { return verInicio("No se pudo leer el análisis: " + e.message); }
  var problema = revisar(a);
  if (problema) return verInicio(problema);

  crudo = datos; analisis = a;
  respuestasPorModo = {}; decisiones = {};
  ronda = null; porModo = {}; sueltas = [];
  // Las decisiones que ya vienen en el archivo se cargan tal como están. Un
  // modo sin «decision» no se decide: no se le inventa una respuesta
  // conservadora para que el análisis parezca completo.
  a.modos.forEach(function (m) {
    if (m.decision) {
      respuestasPorModo[m.id] = respuestas(m.decision);
      decisiones[m.id] = decidir(m, respuestasPorModo[m.id]);
    } else {
      respuestasPorModo[m.id] = respuestas(null);
    }
  });
  seleccion = a.modos.length ? a.modos[0].id : null;
  render();
}

// ------------------------------------------------------------ el taller

function render() {
  var c = completitud(analisis, decisiones);
  var r = resumenRCM(analisis, decisiones);
  app.innerHTML =
    encabezado(r) +
    panelJA1011(c) +
    panelRegistro(calidadRCM(analisis, hoyISO())) +
    '<div class="rejilla"><div>' + arbol() + '</div><div id="ficha">' +
    ficha() + '</div></div>' +
    evidencia_campo() +
    tablero(r) +
    resumenEnPantalla() +
    salida();
  conectar();
}

function encabezado(r) {
  var a = analisis.activo;
  return '<h1>' + esc(a.codigo || "(sin código)") + ' · ' +
    esc(a.nombre || "") + '</h1>' +
    '<p class="tenue">' +
    [a.marca, a.modelo].filter(Boolean).map(esc).join(" ") +
    (analisis.fecha ? ' · ' + esc(analisis.fecha) : '') +
    (analisis.facilitador ? ' · facilita ' + esc(analisis.facilitador) : '') +
    '</p>' +
    (analisis.contexto
      ? '<div class="tarjeta"><span class="lb">Contexto operacional</span>' +
        '<p style="margin:4px 0 0">' + esc(analisis.contexto) + '</p>' +
        '<p class="tenue" style="margin:8px 0 0">El análisis está amarrado a ' +
        'este contexto, no al equipo solo. La misma máquina en otro contexto ' +
        'es otro análisis: copiar uno sobre el otro sin reconfirmarlo es el ' +
        'atajo que llena los planes de tareas que no aplican.</p></div>'
      : '<div class="aviso">El análisis no declara contexto operacional. Sin ' +
        'contexto, las consecuencias y los estándares no se pueden juzgar.</div>');
}

function panelJA1011(c) {
  var html = '<h2>Las siete preguntas de SAE JA1011</h2><div class="tarjeta">' +
    '<div class="estrategia">' +
    (c.completo ? 'Las siete están contestadas.'
                : c.contestadas + ' de 7 contestadas') + '</div>' +
    '<div class="progreso"><i style="width:' + (c.contestadas / 7 * 100) + '%"></i></div>';
  if (!c.completo) {
    html += '<p class="tenue" style="margin-top:10px">' +
      (c.rompe_cadena
        ? 'Falta alguna de las cuatro que sostienen la cadena función → falla ' +
          '→ modo → consecuencia: <b>esto todavía no es un análisis RCM</b>. El ' +
          'criterio de la norma es binario a propósito — nació porque se ' +
          'vendían metodologías incompletas con ese nombre.'
        : 'El esqueleto está; falta decidir tareas.') + '</p>';
  }
  c.respuestas.forEach(function (q) {
    html += '<div class="q ' + (q.contestada ? 'si' : 'no') + '">' +
      '<span class="marca">' + (q.contestada ? '✓' : '○') + '</span><div>' +
      '<b>Q' + q.numero + '.</b> ' + esc(q.texto) +
      (CRITICAS.indexOf(q.clave) >= 0
        ? ' <span class="chip">sostiene la cadena</span>' : '') +
      (q.faltantes.length
        ? '<ul class="lista">' + q.faltantes.map(function (f) {
            return '<li>' + esc(f) + '</li>'; }).join("") + '</ul>'
        : '') +
      '</div></div>';
  });
  return html + '</div>';
}

/** El análisis como REGISTRO, que no es lo mismo que su completitud.
 *
 * Las siete preguntas dicen si está terminado. Esto dice si se puede
 * auditar dentro de dos años: quién lo aprobó, qué versión es, cuándo toca
 * revisarlo, y si los códigos de adentro son inequívocos. Un análisis puede
 * tener las siete contestadas y no ser un registro válido, y esa diferencia
 * es justo la que nadie ve hasta que llega la auditoría.
 */
function hoyISO() { return new Date().toISOString().slice(0, 10); }

function panelRegistro(q) {
  var nc = q.hallazgos.filter(function (h) {
    return h.gravedad === "no conformidad"; });
  var html = '<h2>El análisis como registro</h2><div class="tarjeta">' +
    '<div class="estrategia">' +
    (q.conforme ? 'Identificado y auditable'
                : nc.length + ' no conformidad(es) de registro') + '</div>' +
    '<p class="tenue" style="margin:6px 0 0">' +
    esc(analisis.revision ? 'Revisión ' + analisis.revision : 'Sin revisión') +
    ' · ' + esc(analisis.aprobado_por || 'sin aprobar') +
    ' · ' + esc(analisis.fecha || 'sin fecha') +
    (analisis.proxima_revision
      ? ' · se revisa el ' + esc(analisis.proxima_revision) : '') + '</p>';
  if (!q.hallazgos.length) {
    html += '<p class="tenue" style="margin:8px 0 0">Nada que anotar.</p>';
  }
  q.hallazgos.forEach(function (h) {
    html += '<div class="aviso' +
      (h.gravedad === "no conformidad" ? ' peligro' : ' nota') + '">' +
      '<b>' + esc(h.gravedad) + '</b> · ' + esc(h.detalle) + '</div>';
  });
  return html + '</div>';
}

function arbol() {
  var html = '<div class="arbol"><div class="lb" style="padding:4px 6px">' +
    analisis.funciones.length + ' funciones · ' + analisis.fallas.length +
    ' fallas funcionales · ' + analisis.modos.length + ' modos</div>';
  analisis.funciones.forEach(function (f) {
    html += '<div class="fn">' + esc(f.id) + ' · ' + esc(f.descripcion) + '</div>' +
      '<div class="est">' +
      esc(f.estandar) + '</div>';
    fallasDe(analisis, f.id).forEach(function (ff) {
      html += '<div class="ff">' + esc(ff.id) + ' · ' + esc(ff.descripcion) + '</div>';
      modosDe(analisis, ff.id).forEach(function (m) {
        var d = decisiones[m.id];
        html += '<button data-modo="' + esc(m.id) + '"' +
          (m.id === seleccion ? ' class="activo"' : '') + '>' +
          '<b>' + esc(m.id) + '</b> ' + esc(m.descripcion) +
          '<span style="display:block;margin-top:4px">' +
          (m.evidente ? '' : '<span class="chip obs">oculta</span>') +
          (esGrave(m) ? '<span class="chip grave">grave</span>' : '') +
          (d ? '<span class="chip acento">' + esc(d.rotulo) + '</span>'
             : '<span class="chip">sin decidir</span>') +
          (porModo[m.id] ? '<span class="chip obs">' + porModo[m.id].length +
             ' en campo</span>' : '') +
          '</span></button>';
      });
    });
  });
  return html + '</div>';
}

// --------------------------------------------- la ficha del modo de falla

var ETIQUETAS = {
  probable: ["¿Se puede probar periódicamente que la protección responde?",
             "Probarla sin dañarla y sin dejarla fuera de servicio."],
  detectable: ["¿La degradación se detecta con aviso suficiente para actuar?",
               "La ventana P-F tiene que dar tiempo de programar la " +
               "intervención. Detectarla el día que falla no cuenta."],
  intervalo_edad: ["¿Hay una edad a la que la probabilidad de falla sube?",
                   "No «cada cuánto suele fallar», sino una zona de desgaste " +
                   "identificable. Es la pregunta que más planes OEM no pasan."],
  restaurable: ["¿Restaurar devuelve la resistencia original del ítem?",
                "Si no la devuelve, lo que corresponde es descartar, no " +
                "restaurar."],
  viable: ["¿Existe una tarea técnicamente viable?",
           "Herramienta, acceso, repuesto y gente. Una tarea que no se puede " +
           "ejecutar no protege nada."],
  costo_efectiva: ["¿Alguna tarea cuesta menos que la consecuencia de la falla?",
                   "Sin datos económicos, déjela sin evaluar: la tarea se " +
                   "conserva y no se declara ahorro."]
};

// El orden del árbol, que no es el orden de los datos: oculta primero.
var ORDEN = ["probable", "detectable", "intervalo_edad", "restaurable",
             "viable", "costo_efectiva"];

var PREGUNTAS_DE = {
  probable: [P_PROBABLE], detectable: [P_DETECTABLE],
  intervalo_edad: [P_EDAD], restaurable: [P_RESTAURABLE],
  viable: [P_VIABLE_CBM, P_VIABLE_EDAD], costo_efectiva: [P_COSTO]
};

function usada(campo, d) {
  if (!d) return false;
  var textos = PREGUNTAS_DE[campo] || [];
  return d.camino.some(function (p) { return textos.indexOf(p.pregunta) >= 0; });
}

function ficha() {
  if (!seleccion) {
    return '<div class="tarjeta">El análisis no tiene modos de falla. Sin ' +
      'modos no hay nada que decidir: la Q3 está sin contestar y la cadena ' +
      'está rota.</div>';
  }
  var m = modo(seleccion);
  var ff = fallaDe(m), f = funcionDe(m);
  var u = m.efecto || {};
  var html = '<div class="tarjeta">' +
    '<h3>' + esc(m.id) + ' · ' + esc(m.descripcion) + '</h3>' +
    '<p class="tenue">' + esc(f ? f.descripcion : "") + ' → ' +
    esc(ff ? ff.descripcion : "") + '</p>' +
    (m.evidente
      ? '<span class="chip">pérdida evidente</span>'
      : '<span class="chip obs">falla oculta</span>') +
    (m.estado === "validado" ? '<span class="chip ok">validado</span>'
                             : '<span class="chip">' + esc(m.estado) + '</span>') +
    (m.consecuencias || []).map(function (c) {
      var clase = typeof c === "string" ? c : c.clase;
      return '<span class="chip ' +
        (CONSECUENCIAS_GRAVES.indexOf(clase) >= 0 ? 'grave' : '') + '">' +
        esc(clase) + '</span>';
    }).join("") +
    (!m.evidente
      ? '<div class="aviso nota" style="margin-top:10px">Una falla oculta por ' +
        'sí sola no produce efecto: la máquina sigue trabajando igual. Lo que ' +
        'produce es que, cuando ocurra la segunda falla, no haya nada que la ' +
        'detenga. El riesgo que se trata aquí es la <b>falla múltiple</b>, y ' +
        'por eso esta pregunta va antes que todas las demás.</div>'
      : '') +
    campo("Ubicación", [(m.ubicacion || {}).sistema, (m.ubicacion || {}).subsistema,
                        (m.ubicacion || {}).componente].filter(Boolean).join(" · ")) +
    campo("Código de catálogo", m.codigo_catalogo, "sin codificar") +
    campo("Causa", m.causa, heredado(m)) +
    campo("Mecanismo", m.mecanismo, heredado(m)) +
    campo("Efecto local", u.local,
          "sin describir — es la Q4, y sin ella no se puede juzgar la consecuencia") +
    campo("Lo que observa el operador", u.observa_operador) +
    campo("Parámetro", u.parametro) +
    campo("Alarma o código", u.alarma) +
    campo("Componente afectado", u.componente_afectado) +
    campo("Cómo confirmarlo", u.como_detectarlo) +
    criticidad(m) + evidencia(m) + anomaliasDelModo(m) +
    '</div>';
  return html + decisionPanel(m);
}

/** Causa y mecanismo en blanco no significan lo mismo con código que sin él.
 *
 * Cuando el modo declara un código de catálogo, la oficina los hereda de ahí
 * —lo hace `ModoFalla.desde_catalogo()`—, así que decir aquí «sin declarar»
 * haría ver como un hueco algo que el archivo sí tiene. El catálogo no está
 * en esta pantalla a propósito: son 41 entradas con sus pistas, y ya hay una
 * copia en la app de diagnóstico.
 */
function heredado(m) {
  return m.codigo_catalogo
    ? "lo hereda del catálogo de fallas en la oficina"
    : "sin declarar";
}

function criticidad(m) {
  if (!m.criticidad) {
    return campo("Criticidad", "", "no evaluada — que no es lo mismo que cero");
  }
  var pares = Object.keys(m.criticidad).map(function (k) {
    return k + " " + m.criticidad[k]; }).join(" · ");
  var metodo = analisis.metodo_criticidad || "";
  var html = campo("Criticidad declarada", pares) +
    campo("Método", metodo, "sin método declarado: la criticidad queda sin evaluar") +
    '<p class="tenue" style="margin:6px 0 0">Los valores se muestran tal como ' +
    'los declara el archivo. La evaluación la hace el lado de la oficina, con ' +
    'el método configurado de la planta.</p>';
  if (/RPN/i.test(metodo)) {
    html += '<div class="aviso">' + esc(ADVERTENCIA_RPN) + '</div>';
  }
  return html;
}

function evidencia(m) {
  if (!(m.evidencia || []).length) {
    return campo("Evidencia", "",
      "sin evidencia: el modo no puede marcarse validado, y queda como propuesto");
  }
  return '<div class="campo"><span>Evidencia</span><span><ul class="lista">' +
    m.evidencia.map(function (r) {
      return '<li><b>' + esc(r.fuente) + '</b>' +
        (r.referencia ? ' · ' + esc(r.referencia) : '') +
        (r.nota ? ' — ' + esc(r.nota) : '') + '</li>';
    }).join("") + '</ul></span></div>';
}

function decisionPanel(m) {
  var d = decisiones[m.id];
  var r = respuestasPorModo[m.id] || respuestas(null);
  var html = '<h2>Árbol de decisión</h2>';

  if (d) {
    var clase = d.bloqueado_por_seguridad ? 'bloqueada'
              : PROACTIVAS.indexOf(d.estrategia) >= 0 ? 'proactiva'
              : d.por_defecto ? 'defecto' : '';
    html += '<div class="dictamen ' + clase + '">' +
      '<div class="estrategia">' + esc(d.rotulo) + '</div>' +
      '<div style="margin:6px 0 0">' +
      (PROACTIVAS.indexOf(d.estrategia) >= 0
        ? '<span class="chip ok">tarea proactiva</span>' : '') +
      (d.por_defecto ? '<span class="chip obs">acción por defecto (Q7)</span>' : '') +
      (d.bloqueado_por_seguridad
        ? '<span class="chip grave">rediseño obligatorio</span>' : '') +
      (d.incompleta ? '<span class="chip obs">decisión incompleta</span>' : '') +
      '</div>' +
      (d.incompleta
        ? '<p class="tenue" style="margin:8px 0 0">Queda incompleta mientras ' +
          'alguna pregunta esté sin evaluar, incluso una que este modo no use: ' +
          'el criterio es conservador a propósito. «No lo miramos» no se ' +
          'cuenta como mirado.</p>'
        : '') +
      '<p style="margin:10px 0 0">' + esc(d.motivo) + '</p>' +
      '<ol class="camino">' + d.camino.map(function (p) {
        return '<li><b>' + esc(p.pregunta) + '</b> → <span class="resp">' +
          esc(p.respuesta) + '</span><br><span class="tenue">' +
          esc(p.consecuencia) + '</span></li>';
      }).join("") + '</ol>' +
      d.avisos.map(function (a) {
        return '<div class="aviso">' + esc(a) + '</div>'; }).join("") +
      '</div>';
  } else {
    html += '<div class="aviso">Este modo de falla no tiene decisión ' +
      'registrada. La Q6 lo cuenta como pendiente, y eso es lo correcto: una ' +
      'decisión que nadie tomó no se rellena con la opción conservadora para ' +
      'que el análisis parezca completo.</div>';
  }

  html += '<div class="tarjeta">';
  ORDEN.forEach(function (k) {
    var et = ETIQUETAS[k];
    var pertinente = k !== "probable" ? m.evidente : !m.evidente;
    html += '<div class="pregunta"' +
      (pertinente ? '' : ' style="opacity:.55"') + '>' +
      '<div><b>' + esc(et[0]) + '</b>' +
      (usada(k, d) ? ' <span class="chip acento">la usó el árbol</span>' : '') +
      (pertinente ? '' : ' <span class="chip">no aplica a este modo</span>') +
      '<span class="tenue" style="display:block">' + esc(et[1]) + '</span></div>' +
      '<div class="opciones">' +
      ['si', 'no', 'nd'].map(function (op) {
        var val = op === 'si' ? true : op === 'no' ? false : null;
        var puesto = r[k] === val;
        return '<button class="op-' + op + '" data-campo="' + k +
          '" data-valor="' + op + '" aria-pressed="' + (puesto ? 'true' : 'false') +
          '">' + (op === 'si' ? 'Sí' : op === 'no' ? 'No' : 'Sin evaluar') +
          '</button>';
      }).join("") + '</div>' +
      (k === "intervalo_edad" && r[k] === false
        ? '<div class="aviso" style="margin-top:8px">' + esc(AVISO_89) + '</div>'
        : '') +
      '</div>';
  });
  html += '<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">' +
    '<button id="quitar">Quitar la decisión de este modo</button></div>' +
    '<p class="tenue" style="margin:8px 0 0">Quitarla no es lo mismo que ' +
    'dejar todo «sin evaluar»: deja el modo sin decisión, y la Q6 vuelve a ' +
    'contarlo como pendiente.</p></div>';
  return html;
}

// ------------------------------------------------ la evidencia de campo

var _entradaRonda = null;

/** La entrada de archivo de la ronda, una sola para toda la sesión.
 *  La pantalla se repinta entera a cada respuesta del árbol; crearla en cada
 *  repintado dejaba una colgando del documento por cada clic. */
function entradaRonda() {
  if (_entradaRonda) return _entradaRonda;
  var inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json";
  inp.className = "oculto"; inp.id = "entrada-ronda";
  document.body.appendChild(inp);
  inp.onchange = function () {
    var f = inp.files && inp.files[0];
    if (!f) return;
    var lector = new FileReader();
    lector.onload = function () {
      var r;
      try { r = abrirRonda(JSON.parse(lector.result)); }
      catch (e) { r = { error: "Ese archivo no es una ronda legible: " + e.message }; }
      inp.value = "";          // el mismo archivo se puede volver a abrir
      render();
      if (r.error) {
        var caja = document.getElementById("abrir-ronda");
        if (caja) caja.insertAdjacentHTML("afterend",
          '<div class="aviso peligro">' + esc(r.error) + '</div>');
      }
    };
    lector.readAsText(f);
  };
  _entradaRonda = inp;
  return inp;
}

/** La ronda que hizo el operador, puesta encima del análisis.
 *
 * Es el circuito que justifica todo lo demás: el operador ve algo en el
 * turno, la oficina abre el análisis y ve **en qué modo de falla** cayó eso
 * que vio. Sin esto, la ronda es una lista de hallazgos y el análisis es un
 * documento, y nadie los cruza nunca.
 *
 * El enganche es el mismo que hace la oficina —código exacto y mismo
 * activo—, y lo que no engancha se muestra con el motivo, no se esconde.
 */
function abrirRonda(datos) {
  var lista = (datos && datos.anomalias) || [];
  if (!lista.length) {
    return { error: "Ese archivo no trae anomalías. Una ronda sin hallazgos " +
                    "no tiene nada que cruzar con el análisis — lo cual, " +
                    "dicho sea de paso, es una buena noticia." };
  }
  ronda = datos;
  porModo = {}; sueltas = [];
  lista.forEach(function (a) {
    var enlace = enlazarAnomalia(a, analisis);
    if (enlace.modo_falla_id && modo(enlace.modo_falla_id)) {
      if (!porModo[enlace.modo_falla_id]) porModo[enlace.modo_falla_id] = [];
      porModo[enlace.modo_falla_id].push({ a: a, motivo: enlace.motivo });
    } else {
      sueltas.push({ a: a, motivo: enlace.modo_falla_id
        ? "declara el modo " + enlace.modo_falla_id + ", que no está en este análisis"
        : enlace.motivo });
    }
  });
  return { error: "" };
}

function anomaliasDelModo(m) {
  var lista = porModo[m.id];
  if (!lista) return "";
  return '<div class="campo"><span>Visto en campo</span><span>' +
    lista.map(function (x) {
      return '<div class="hallazgo"><b>' + esc(x.a.descripcion) + '</b>' +
        '<span class="tenue"> · ' + esc(x.a.detectada_por || "sin firmar") +
        ' · ' + esc(x.a.fecha || "sin fecha") + '</span>' +
        (x.a.condicion_observada
          ? '<div class="tenue">criterio: ' + esc(x.a.condicion_observada) + '</div>'
          : '') +
        '<div class="tenue">enganchado ' + esc(x.motivo) + '</div></div>';
    }).join("") + '</span></div>';
}

function evidencia_campo() {
  var html = '<h2>Evidencia de campo · ronda CIL</h2><div class="tarjeta">';
  if (!ronda) {
    html += '<button id="abrir-ronda">Abrir una ronda del operador (.json)</button>' +
      '<p class="tenue" style="margin:10px 0 0">El archivo que sale del ' +
      'teléfono al terminar la ronda. Se cruza con este análisis y se ve en ' +
      'qué modo de falla cayó lo que el operador encontró. No se sube a ' +
      'ninguna parte y no se guarda dentro del análisis: la ronda sigue ' +
      'siendo la ronda.</p></div>';
    return html;
  }
  var e = ronda.ejecucion || {};
  var mismoActivo = !e.activo_codigo ||
                    e.activo_codigo === analisis.activo.codigo;
  var enganchadas = 0;
  Object.keys(porModo).forEach(function (k) { enganchadas += porModo[k].length; });

  html += '<div class="lb">' + esc(e.activo_codigo || "activo sin declarar") +
    ' · ' + esc(e.operador || "sin firmar") + ' · ' + esc(e.fecha || "sin fecha") +
    '</div>' +
    '<div class="numeros" style="margin-top:10px">' +
    '<div><span class="lb">Hallazgos</span><b>' +
    (enganchadas + sueltas.length) + '</b></div>' +
    '<div><span class="lb">En un modo</span><b>' + enganchadas + '</b></div>' +
    '<div><span class="lb">Sin enganchar</span><b>' + sueltas.length + '</b></div>' +
    '</div>';

  if (!mismoActivo) {
    html += '<div class="aviso peligro">La ronda es de <b>' +
      esc(e.activo_codigo) + '</b> y este análisis es de <b>' +
      esc(analisis.activo.codigo) + '</b>. No se engancha nada: una anomalía ' +
      'puesta en el modo de otra máquina ensucia las dos.</div>';
  }
  if (ronda.estado && ronda.estado.completa === false) {
    html += '<div class="aviso">La ronda llegó <b>incompleta</b>: ' +
      (ronda.estado.sin_acceso || 0) + ' punto(s) no se pudieron ver. Lo que ' +
      'no se vio no dice nada del modo de falla, ni a favor ni en contra.</div>';
  }
  if (ronda.estado && ronda.estado.sospechosa_de_firma) {
    html += '<div class="aviso peligro">La ronda se marcó <b>demasiado ' +
      'rápida</b> para haber sido ejecutada. Antes de usarla como evidencia, ' +
      'conviene mirarla.</div>';
  }

  if (sueltas.length) {
    html += '<h3 style="margin-top:14px">No engancharon, y por qué</h3>' +
      '<table><tr><th>Hallazgo</th><th>Motivo</th></tr>' +
      sueltas.map(function (x) {
        return '<tr><td><b>' + esc(x.a.componente || "") + '</b><br>' +
          esc(x.a.descripcion) + '</td><td>' + esc(x.motivo) + '</td></tr>';
      }).join("") + '</table>' +
      '<p class="tenue" style="margin:10px 0 0">Deducir el código desde el ' +
      'texto libre es trabajo del catálogo de fallas, y lo hace ' +
      '<code>fixmate tpm anomalias</code>. Esta pantalla no lo trae: ' +
      'enganchar al modo «más parecido» es como se contamina la frecuencia ' +
      'por modo.</p>';
  } else {
    html += '<p class="tenue" style="margin:10px 0 0">Todos los hallazgos ' +
      'cayeron en un modo de falla del análisis.</p>';
  }

  html += '<div style="margin-top:12px"><button id="quitar-ronda">' +
    'Quitar esta ronda</button></div>';
  return html + '</div>';
}

// ------------------------------------------------------------- el tablero

function tablero(r) {
  var html = '<h2>Tablero del análisis</h2><div class="tarjeta">' +
    '<div class="numeros">' +
    '<div><span class="lb">Modos</span><b>' + r.modos + '</b></div>' +
    '<div><span class="lb">Decididos</span><b>' + r.decididos + '</b></div>' +
    '<div><span class="lb">Graves</span><b>' + r.graves + '</b></div>' +
    '<div><span class="lb">Ocultos</span><b>' + r.ocultos + '</b></div>' +
    '<div><span class="lb">Rediseños obligatorios</span><b>' +
    r["rediseños_obligatorios"] + '</b></div>' +
    '<div><span class="lb">Decisiones incompletas</span><b>' +
    r["decisiones_incompletas"] + '</b></div>' +
    '</div><table style="margin-top:14px"><tr><th>Estrategia</th>' +
    '<th>Modos</th><th></th></tr>';
  Object.keys(ESTRATEGIAS).forEach(function (k) {
    html += '<tr><td>' + esc(ESTRATEGIAS[k]) + '</td><td><b>' + r.reparto[k] +
      '</b></td><td>' +
      (PROACTIVAS.indexOf(k) >= 0 ? '<span class="chip ok">proactiva</span>' : '') +
      (POR_DEFECTO.indexOf(k) >= 0
        ? '<span class="chip obs">acción por defecto</span>' : '') +
      '</td></tr>';
  });
  html += '</table>';
  if (r["decisiones_incompletas"]) {
    html += '<div class="aviso">' + r["decisiones_incompletas"] + ' decisión(es) ' +
      'salieron con preguntas sin evaluar. Están del lado conservador, pero no ' +
      'están terminadas.</div>';
  }
  if (r["rediseños_obligatorios"]) {
    html += '<div class="aviso peligro">' + r["rediseños_obligatorios"] +
      ' modo(s) de falla quedaron en rediseño obligatorio: ninguna tarea ' +
      'proactiva reduce el riesgo y la consecuencia es de seguridad o ' +
      'ambiental. «Operar hasta la falla» no es una salida legal ahí.</div>';
  }
  return html + '</div>';
}

function resumenEnPantalla() {
  var html = '<h2>Resumen por modo</h2><div class="tarjeta"><table>' +
    '<tr><th>Modo</th><th>Falla funcional</th><th>Evidente</th>' +
    '<th>Consecuencia</th><th>Criticidad</th><th>Estrategia</th></tr>';
  analisis.modos.forEach(function (m) {
    var d = decisiones[m.id];
    var ff = fallaDe(m);
    var crit = m.criticidad
      ? Object.keys(m.criticidad).map(function (k) {
          return k[0].toUpperCase() + m.criticidad[k]; }).join(" ")
      : "";
    html += '<tr' + (esGrave(m) ? ' class="grave"' : '') + '>' +
      '<td><b>' + esc(m.id) + '</b><br>' + esc(m.descripcion) + '</td>' +
      '<td>' + esc(ff ? ff.descripcion : "") + '</td>' +
      '<td>' + (m.evidente ? 'sí' : '<b>oculta</b>') + '</td>' +
      '<td>' + (m.consecuencias || []).map(function (c) {
        return esc(typeof c === "string" ? c : c.clase); }).join(", ") + '</td>' +
      '<td>' + (crit ? esc(crit) : '<span class="vacio">no evaluada</span>') + '</td>' +
      '<td>' + (d ? esc(d.rotulo) +
        (d.bloqueado_por_seguridad ? ' <span class="chip grave">obligatorio</span>' : '')
        : '<span class="vacio">sin decidir</span>') + '</td></tr>';
  });
  return html + '</table>' +
    '<p class="tenue" style="margin:10px 0 0">Esto es un resumen para mirar. ' +
    'La matriz FMECA que se entrega tiene treinta columnas y sale de ' +
    '<code>fixmate rcm matriz</code> sobre el archivo exportado.</p></div>';
}

// -------------------------------------------------------------- la salida

/** El archivo exportado es el MISMO que se abrió, con las decisiones puestas
 *  dentro de cada modo. Así vuelve a entrar por `cargador.analisis()` y por
 *  `fixmate rcm analizar` sin convertir nada, y los ids se reconstruyen por
 *  posición igual que aquí. */
function exportar() {
  var copia = JSON.parse(JSON.stringify(crudo));
  var i = 0;
  (copia.funciones || []).forEach(function (fd) {
    (fd.fallas || []).forEach(function (ffd) {
      (ffd.modos || []).forEach(function (md) {
        var m = analisis.modos[i]; i += 1;
        if (!m) return;
        if (decisiones[m.id]) {
          var r = respuestasPorModo[m.id];
          var fuera = {};
          CAMPOS_DECISION.forEach(function (k) { fuera[k] = r[k]; });
          md.decision = fuera;
        } else if (md.decision) {
          delete md.decision;
        }
      });
    });
  });
  return copia;
}

function salida() {
  return '<h2>Guardar</h2><div class="tarjeta">' +
    '<button id="bajar" class="primary">Guardar el análisis con sus decisiones</button>' +
    '<p class="tenue" style="margin:10px 0 0">Un <code>.json</code> con las ' +
    'respuestas del árbol dentro de cada modo. Vuelve a entrar por ' +
    '<code>fixmate rcm analizar</code>, <code>fixmate rcm tareas</code> y ' +
    '<code>fixmate rcm matriz</code> sin convertir nada.</p>' +
    '<div style="margin-top:12px"><button id="otro">Abrir otro análisis</button></div>' +
    '</div>';
}

// ------------------------------------------------------------- conexiones

function conectar() {
  Array.prototype.forEach.call(app.querySelectorAll("button[data-modo]"), function (b) {
    b.onclick = function () { seleccion = b.getAttribute("data-modo"); render(); };
  });
  Array.prototype.forEach.call(app.querySelectorAll("button[data-campo]"), function (b) {
    b.onclick = function () {
      var k = b.getAttribute("data-campo"), v = b.getAttribute("data-valor");
      var m = modo(seleccion);
      respuestasPorModo[m.id][k] = v === "si" ? true : v === "no" ? false : null;
      decisiones[m.id] = decidir(m, respuestasPorModo[m.id]);
      render();
    };
  });
  var quitar = document.getElementById("quitar");
  if (quitar) {
    quitar.onclick = function () {
      delete decisiones[seleccion];
      respuestasPorModo[seleccion] = respuestas(null);
      render();
    };
  }
  var abrirR = document.getElementById("abrir-ronda");
  if (abrirR) abrirR.onclick = function () { entradaRonda().click(); };
  var quitarR = document.getElementById("quitar-ronda");
  if (quitarR) {
    quitarR.onclick = function () {
      ronda = null; porModo = {}; sueltas = []; render();
    };
  }
  var otro = document.getElementById("otro");
  if (otro) otro.onclick = function () { verInicio(); };
  var bajar = document.getElementById("bajar");
  if (bajar) {
    bajar.onclick = function () {
      var blob = new Blob([JSON.stringify(exportar(), null, 2)],
                          { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "analisis-" + (analisis.activo.codigo || "rcm") + ".json";
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    };
  }
}

verInicio();
</script>
</body>
</html>
