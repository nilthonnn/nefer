<script>
/* La pantalla donde se escribe. Tres decisiones, y las tres vienen de que
 * esto NO es una pantalla de campo:
 *
 * ESCRIBIR NO PUEDE REDIBUJAR. Un formulario que se vuelve a pintar en cada
 * tecla pierde el cursor a media palabra, y entonces nadie escribe un
 * criterio de aceptacion de dos lineas: lo deja en tres palabras. Aqui el
 * tecleo solo toca el borrador y el panel de abajo; la pantalla se vuelve a
 * armar unicamente cuando cambia la ESTRUCTURA —se agrega un punto, se quita
 * un modo—.
 *
 * EL PANEL VA FIJO ABAJO. Es lo unico que se mira sin parar: que falta,
 * cuanto falta, y si ya se puede bajar el archivo. Suelto arriba, se escribe
 * media pauta sin ver que esta trabada.
 *
 * SE PEGA DESDE EL EXCEL. El planificador ya tiene la pauta en una planilla.
 * Pedirle que la vuelva a escribir punto por punto es la forma mas segura de
 * que no la escriba, y de que el producto se quede en demo.
 */

var app = document.getElementById("app");
var panel = document.getElementById("panel");
var tipo = null;      // "pauta" | "analisis"
var b = null;         // el borrador que se esta escribiendo
var abierto = {};     // que bloques quedan desplegados entre redibujos
var mensaje = "";     // lo ultimo que paso, para decirlo una vez

function esc(s) {
  return String(s === undefined || s === null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function hoyISO() { return new Date().toISOString().slice(0, 10); }

/* ---------------------------------------------- el borrador por su camino
 * Cada campo lleva su ruta escrita —`funciones.0.fallas.1.modos.0.causa`— y
 * un solo oyente la usa para escribir en el borrador. La alternativa es
 * enganchar cada campo uno por uno, y con tres niveles de anidamiento eso es
 * donde se cuelan los campos que se ven pero no guardan nada. */
function leer(ruta) {
  var partes = ruta.split("."), o = b;
  for (var i = 0; i < partes.length; i++) {
    if (o === null || o === undefined) return "";
    o = o[partes[i]];
  }
  return o === undefined || o === null ? "" : o;
}
function fijar(ruta, valor) {
  var partes = ruta.split("."), o = b;
  for (var i = 0; i < partes.length - 1; i++) o = o[partes[i]];
  o[partes[partes.length - 1]] = valor;
}
function enRuta(ruta) {
  var partes = ruta.split("."), o = b;
  for (var i = 0; i < partes.length; i++) o = o[partes[i]];
  return o;
}

/* ------------------------------------------------------------ los campos */

function fTexto(ruta, etiqueta, ayuda, opts) {
  opts = opts || {};
  var v = esc(leer(ruta));
  var falta = opts.falta && !String(leer(ruta)).trim() ? " falta" : "";
  // `data-obliga` es lo que deja que el aviso se apague MIENTRAS se escribe.
  // Sin eso, el campo se quedaba en rojo hasta el próximo redibujo —que al
  // teclear no ocurre— y el aviso pasaba de ayudar a estorbar.
  var obliga = opts.falta ? ' data-obliga="1"' : '';
  var cuerpo = opts.area
    ? '<textarea data-ruta="' + ruta + '"' + obliga + ' rows="' + (opts.filas || 2) + '"' +
      (opts.pista ? ' placeholder="' + esc(opts.pista) + '"' : '') + '>' + v + '</textarea>'
    : '<input type="text" data-ruta="' + ruta + '"' + obliga + ' value="' + v + '"' +
      (opts.pista ? ' placeholder="' + esc(opts.pista) + '"' : '') + '>';
  return '<label class="campo' + falta + '"><span>' + esc(etiqueta) +
    (opts.falta ? '<i class="pide"> ·&nbsp;hace falta</i>' : '') + '</span>' + cuerpo +
    (ayuda ? '<em>' + esc(ayuda) + '</em>' : '') + '</label>';
}

function fNumero(ruta, etiqueta, ayuda) {
  return '<label class="campo"><span>' + esc(etiqueta) + '</span>' +
    '<input type="number" min="0" step="5" data-ruta="' + ruta + '" value="' +
    esc(leer(ruta) || 0) + '"></label>' +
    (ayuda ? '<em class="tenue">' + esc(ayuda) + '</em>' : '');
}

function fSelect(ruta, etiqueta, opciones, ayuda) {
  var v = String(leer(ruta));
  var o = opciones.map(function (par) {
    var val = par instanceof Array ? par[0] : par;
    var txt = par instanceof Array ? par[1] : par;
    return '<option value="' + esc(val) + '"' + (val === v ? ' selected' : '') +
      '>' + esc(txt) + '</option>';
  }).join("");
  return '<label class="campo"><span>' + esc(etiqueta) + '</span>' +
    '<select data-ruta="' + ruta + '" data-recarga="' + (ruta.indexOf("codigo_catalogo") >= 0 ? "1" : "0") +
    '">' + o + '</select>' + (ayuda ? '<em>' + esc(ayuda) + '</em>' : '') + '</label>';
}

function fMarca(ruta, etiqueta, ayuda) {
  return '<label class="marca"><input type="checkbox" data-ruta="' + ruta +
    '" data-bool="1"' + (leer(ruta) !== false ? ' checked' : '') + '>' +
    '<span>' + esc(etiqueta) + (ayuda ? ' <em class="tenue">' + esc(ayuda) +
    '</em>' : '') + '</span></label>';
}

function botones(ruta, i, n, que) {
  return '<div class="acciones">' +
    (i > 0 ? '<button data-accion="subir" data-ruta="' + ruta + '" data-i="' + i + '">↑ subir</button>' : '') +
    (i < n - 1 ? '<button data-accion="bajar" data-ruta="' + ruta + '" data-i="' + i + '">↓ bajar</button>' : '') +
    '<button class="borrar" data-accion="quitar" data-ruta="' + ruta +
    '" data-i="' + i + '">quitar ' + esc(que) + '</button></div>';
}

/* El catalogo como lista para elegir, nunca como campo libre. Un codigo
 * escrito a mano que no existe revienta en el cargador de Python, y lo haria
 * despues de bajar el archivo. Aqui no se puede escribir uno que no exista. */
function opcionesCatalogo() {
  var codigos = Object.keys(CATALOGO).sort();
  var o = [["", "— ninguno —"]];
  for (var i = 0; i < codigos.length; i++) {
    o.push([codigos[i], codigos[i] + " · " + CATALOGO[codigos[i]].causa]);
  }
  return o;
}

/* ---------------------------------------------------------- las pantallas */

function verInicio(error) {
  tipo = null; b = null; mensaje = "";
  panel.hidden = true;
  app.innerHTML =
    '<h1>Armar</h1>' +
    '<p class="tenue">Las dos pantallas de campo de FixMate abren un archivo ' +
    '<code>.json</code>: la ronda abre la pauta del equipo, la mesa de ' +
    'trabajo abre el análisis RCM. Aquí se escriben esos dos archivos, con ' +
    'las mismas reglas que usa el resto de FixMate para leerlos.</p>' +
    (error ? '<div class="aviso peligro">' + esc(error) + '</div>' : '') +
    '<div class="inicio">' +
    '<h2>Empezar</h2>' +
    '<button id="n-pauta" class="primary">Nueva pauta de ronda' +
    '<span class="tenue">Para el operador: los puntos de limpieza, ' +
    'inspección y lubricación del arranque de turno. Se pega desde el Excel ' +
    'si ya la tiene en una planilla.</span></button>' +
    '<button id="n-analisis">Nuevo análisis RCM' +
    '<span class="tenue">Para la oficina: funciones, fallas funcionales y ' +
    'modos de falla, con sus consecuencias. De aquí sale lo que la mesa de ' +
    'trabajo lleva por el árbol de SAE JA1011.</span></button>' +
    '<h2>Seguir uno que ya existe</h2>' +
    '<button id="abrir">Abrir un archivo' +
    '<span class="tenue">Una pauta o un análisis que ya tenga. Se reconoce ' +
    'cuál es por lo que lleva dentro.</span></button>' +
    '</div>' +
    '<p class="tenue">Nada de esto sale de este equipo: no hay servidor ' +
    'detrás. El archivo se guarda donde usted lo baje.</p>';

  document.getElementById("n-pauta").onclick = nuevaPauta;
  document.getElementById("n-analisis").onclick = nuevoAnalisis;
  document.getElementById("abrir").onclick = function () { entrada().click(); };
}

/* El input de archivo se crea UNA vez y se reusa. Creándolo en cada dibujo
   quedaban inputs huérfanos pegados al body, y el de un dibujo viejo seguía
   respondiendo. */
var _entrada = null;
function entrada() {
  if (_entrada) return _entrada;
  var inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json"; inp.className = "oculto";
  inp.onchange = function () {
    var f = inp.files && inp.files[0];
    if (!f) return;
    var lector = new FileReader();
    lector.onload = function () {
      try { abrirArchivo(JSON.parse(lector.result)); }
      catch (e) { verInicio("Ese archivo no se puede leer: " + e.message); }
      inp.value = "";
    };
    lector.readAsText(f);
  };
  document.body.appendChild(inp);
  _entrada = inp;
  return inp;
}

function abrirArchivo(d) {
  if (d && d.puntos instanceof Array && !d.funciones) {
    tipo = "pauta"; b = borradorDePauta(d);
  } else if (d && d.activo) {
    tipo = "analisis"; b = borradorDeAnalisis(d);
  } else {
    verInicio("Ese archivo no es una pauta ni un análisis: no tiene «puntos» " +
              "ni «activo».");
    return;
  }
  abierto = {}; mensaje = "Abierto. Lo que cambie aquí no toca el archivo " +
    "original: se baja uno nuevo.";
  render();
}

/* --------------------------------------------------------- los borradores */

/* Lo que trae el archivo y esta pantalla no edita. Viaja aparte y se vuelve a
   escribir tal cual: ver `conResto()` en las reglas. Los `id` NO viajan —se
   regeneran por posicion en Python, y un id viejo sobre un modo que se movio
   de sitio es peor que ninguno: apuntaria a la decision de otro modo. */
function resto(origen, conocidas) {
  var o = {}, hay = false;
  for (var k in origen) {
    if (!Object.prototype.hasOwnProperty.call(origen, k)) continue;
    if (conocidas.indexOf(k) >= 0) continue;
    o[k] = origen[k];
    hay = true;
  }
  return hay ? o : null;
}

var CONOCIDAS_PAUTA = ["id", "activo_codigo", "codigo_equipo", "nombre",
                       "frecuencia", "origen", "presupuesto_seg", "puntos"];
var CONOCIDAS_PUNTO = ["id", "clase", "punto", "criterio", "alcance_operador",
                       "segundos", "codigo_catalogo", "modo_falla_id"];
var CONOCIDAS_ANALISIS = ["activo", "contexto", "facilitador", "participantes",
                          "fecha", "revision", "aprobado_por",
                          "proxima_revision", "funciones", "fallas", "modos"];
var CONOCIDAS_FUNCION = ["id", "descripcion", "estandar", "tipo", "condicion",
                         "fallas"];
var CONOCIDAS_FALLA = ["id", "funcion_id", "descripcion", "modos"];
var CONOCIDAS_MODO = ["id", "falla_funcional_id", "descripcion", "ubicacion",
                      "codigo_catalogo", "causa", "mecanismo", "evidente",
                      "efecto", "consecuencias", "evidencia", "estado"];


function puntoVacio() {
  return { clase: "inspeccionar", punto: "", criterio: "", segundos: 30,
           alcance_operador: true, codigo_catalogo: "", modo_falla_id: "" };
}

function nuevaPauta() {
  tipo = "pauta";
  b = { id: "", activo_codigo: "", nombre: "", frecuencia: "por_turno",
        origen: "", puntos: [puntoVacio()] };
  abierto = { "puntos.0": true }; mensaje = "";
  render();
}

function borradorDePauta(d) {
  return {
    _resto: resto(d, CONOCIDAS_PAUTA),
    id: String(d.id || ""), activo_codigo: String(d.activo_codigo || d.codigo_equipo || ""),
    nombre: String(d.nombre || ""), frecuencia: String(d.frecuencia || "diaria"),
    origen: String(d.origen || ""),
    puntos: (d.puntos || []).map(function (p) {
      return {
        _resto: resto(p, CONOCIDAS_PUNTO),
        clase: String(p.clase || "inspeccionar"), punto: String(p.punto || ""),
        criterio: String(p.criterio || ""), segundos: +p.segundos || 0,
        alcance_operador: p.alcance_operador !== false,
        codigo_catalogo: String(p.codigo_catalogo || ""),
        modo_falla_id: String(p.modo_falla_id || "")
      };
    })
  };
}

function modoVacio() {
  return { descripcion: "", ubicacion: { sistema: "", subsistema: "", componente: "" },
           codigo_catalogo: "", causa: "", mecanismo: "", evidente: "si",
           efecto: { local: "", observa_operador: "", parametro: "", alarma: "",
                     componente_afectado: "", como_detectarlo: "" },
           consecuencias: [], evidencia: [], estado: "propuesto" };
}
function fallaVacia() { return { descripcion: "", modos: [modoVacio()] }; }
function funcionVacia() {
  return { descripcion: "", estandar: "", tipo: "principal", condicion: "",
           fallas: [fallaVacia()] };
}

function nuevoAnalisis() {
  tipo = "analisis";
  b = { activo: { codigo: "", nombre: "", marca: "", modelo: "", serie: "",
                  categoria: "", instalacion: "", contexto: "" },
        contexto: "", facilitador: "", participantes: "", fecha: hoyISO(),
        revision: "", aprobado_por: "", proxima_revision: "",
        funciones: [funcionVacia()] };
  abierto = { "funciones.0": true }; mensaje = "";
  render();
}

function borradorDeAnalisis(d) {
  var a = d.activo || {};
  // Un análisis guardado trae funciones, fallas y modos en tres listas planas
  // cosidas por id —así lo escribe `Analisis.a_dict()`— o ya anidados, como
  // lo escribe esta pantalla. Las dos formas se leen: si solo se leyera la
  // anidada, un análisis exportado por el CLI no se podría volver a editar.
  var funciones = (d.funciones || []).map(function (f) {
    return { _resto: resto(f, CONOCIDAS_FUNCION),
             descripcion: String(f.descripcion || ""), estandar: String(f.estandar || ""),
             tipo: String(f.tipo || "principal"), condicion: String(f.condicion || ""),
             id: String(f.id || ""), fallas: (f.fallas || []).map(fallaDe) };
  });
  if (d.fallas instanceof Array && d.fallas.length) {
    var porFuncion = {};
    for (var i = 0; i < funciones.length; i++) {
      porFuncion[funciones[i].id || ("F" + (i + 1))] = funciones[i];
      funciones[i].fallas = [];
    }
    var porId = {};
    for (i = 0; i < d.fallas.length; i++) {
      var ff = d.fallas[i], destino = porFuncion[String(ff.funcion_id || "")];
      if (!destino) continue;
      var nueva = { _resto: resto(ff, CONOCIDAS_FALLA),
                    descripcion: String(ff.descripcion || ""), modos: [] };
      porId[String(ff.id || "")] = nueva;
      destino.fallas.push(nueva);
    }
    for (i = 0; i < (d.modos || []).length; i++) {
      var m = d.modos[i], padre = porId[String(m.falla_funcional_id || "")];
      if (padre) padre.modos.push(modoDe(m));
    }
  }
  for (i = 0; i < funciones.length; i++) delete funciones[i].id;
  return {
    _resto: resto(d, CONOCIDAS_ANALISIS),
    activo: { codigo: String(a.codigo || ""), nombre: String(a.nombre || ""),
              marca: String(a.marca || ""), modelo: String(a.modelo || ""),
              serie: String(a.serie || ""), categoria: String(a.categoria || ""),
              instalacion: String(a.instalacion || ""),
              contexto: String(a.contexto || "") },
    contexto: String(d.contexto || ""), facilitador: String(d.facilitador || ""),
    participantes: (d.participantes || []).join(", "),
    fecha: String(d.fecha || ""), revision: String(d.revision || ""),
    aprobado_por: String(d.aprobado_por || ""),
    proxima_revision: String(d.proxima_revision || ""),
    funciones: funciones
  };
}

function fallaDe(ff) {
  return { _resto: resto(ff, CONOCIDAS_FALLA),
           descripcion: String(ff.descripcion || ""),
           modos: (ff.modos || []).map(modoDe) };
}

function modoDe(m) {
  var u = m.ubicacion || {}, e = m.efecto || {};
  return {
    // Aqui viajan la criticidad y la `decision` —las respuestas del equipo al
    // arbol de JA1011—. Reescribir el archivo sin ellas borraria la reunion.
    _resto: resto(m, CONOCIDAS_MODO),
    descripcion: String(m.descripcion || ""),
    ubicacion: { sistema: String(u.sistema || ""), subsistema: String(u.subsistema || ""),
                 componente: String(u.componente || "") },
    codigo_catalogo: String(m.codigo_catalogo || ""),
    causa: String(m.causa || ""), mecanismo: String(m.mecanismo || ""),
    // En el borrador es «si»/«no» porque sale de un desplegable; en el
    // archivo es un booleano, porque eso es lo que es. Guardar el booleano y
    // pintarlo con `String()` dejaba el desplegable diciendo «sí» sobre un
    // modo oculto: la pantalla y el dato, distintos, sin avisar.
    evidente: m.evidente === false ? "no" : "si",
    efecto: { local: String(e.local || ""), observa_operador: String(e.observa_operador || ""),
              parametro: String(e.parametro || ""), alarma: String(e.alarma || ""),
              componente_afectado: String(e.componente_afectado || ""),
              como_detectarlo: String(e.como_detectarlo || "") },
    consecuencias: (m.consecuencias || []).map(function (c) {
      return typeof c === "string" ? { clase: c, descripcion: "" }
        : { clase: String(c.clase || ""), descripcion: String(c.descripcion || "") };
    }),
    evidencia: (m.evidencia || []).map(function (r) {
      return { fuente: String(r.fuente || "historial"),
               referencia: String(r.referencia || ""), nota: String(r.nota || "") };
    }),
    estado: String(m.estado || "propuesto")
  };
}

/* ------------------------------------------------------------- el dibujo */

function render() {
  var y = window.scrollY;
  app.innerHTML = tipo === "pauta" ? hojaPauta() : hojaAnalisis();
  for (var llave in abierto) {
    var d = app.querySelector('[data-llave="' + llave + '"]');
    if (d && abierto[llave]) d.open = true;
  }
  pintarPanel();
  // Volver a armar la hoja entera manda la página arriba. En un análisis de
  // treinta modos eso significa buscar otra vez dónde se estaba cada vez que
  // se agrega algo.
  window.scrollTo(0, y);
}

function cabecera(titulo, bajada) {
  return '<h1>' + esc(titulo) + '</h1>' +
    '<p class="tenue">' + bajada + '</p>' +
    (mensaje ? '<div class="aviso nota">' + esc(mensaje) + '</div>' : '') +
    '<div class="acciones"><button data-accion="volver">← empezar otro</button></div>';
}

function hojaPauta() {
  var h = cabecera("Armar la pauta",
    'Lo que el operador va a tocar en el teléfono, punto por punto. Lo que ' +
    'se escriba aquí es lo que él va a leer parado frente a la máquina, con ' +
    'guantes: un sitio donde pararse y un criterio que se decide mirando.');

  h += '<h2>El equipo</h2>' +
    '<div class="rejilla">' +
    fTexto("activo_codigo", "Código del activo",
           "El que está pintado en la máquina y ya viaja en los informes. No se inventa aquí.",
           { falta: true, pista: "EX-220-03" }) +
    fTexto("nombre", "Nombre de la pauta", "Cómo la va a pedir el operador.",
           { falta: true, pista: "Ronda de arranque · excavadora" }) +
    fSelect("frecuencia", "Cada cuándo", [
      ["por_turno", "por turno"], ["diaria", "diaria"], ["semanal", "semanal"],
      ["quincenal", "quincenal"], ["mensual", "mensual"], ["por_horas", "por horas"]
    ], "Una pauta de arranque de turno es la que de verdad se ejecuta.") +
    fTexto("origen", "De dónde sale",
           "Manual del fabricante, análisis RCM, experiencia del taller. Sin esto, " +
           "dentro de un año nadie sabe por qué está este punto.",
           { pista: "manual OEM, sección 4.2" }) +
    '</div>';

  h += '<h2>Los puntos <span class="lb">' + b.puntos.length + '</span></h2>';
  if (!b.puntos.length) {
    h += '<p class="vacio">Ninguno todavía. Sin puntos, la pauta no arranca en ' +
      'el teléfono.</p>';
  }
  for (var i = 0; i < b.puntos.length; i++) h += bloquePunto(i);
  h += '<div class="acciones">' +
    '<button class="primary" data-accion="agregar-punto">+ agregar punto</button>' +
    '</div>' + cajaPegar();
  return h;
}

function bloquePunto(i) {
  var p = b.puntos[i], llave = "puntos." + i;
  var titulo = p.punto ? esc(p.punto) : '<span class="vacio">sin sitio todavía</span>';
  return '<details class="bloque" data-llave="' + llave + '">' +
    '<summary><span class="chip">' + (i + 1) + '</span>' +
    '<span class="chip acento">' + esc(p.clase) + '</span>' + titulo + '</summary>' +
    '<div class="cuerpo">' +
    fSelect(llave + ".clase", "Qué se hace",
      Object.keys(CLASES).map(function (c) { return [c, c + " — " + CLASES[c]]; }),
      "Cinco, no siete: «detectar anomalías» y «registrar anomalía» no son " +
      "clases de punto, son lo que pasa cuando un punto sale NOK.") +
    fTexto(llave + ".punto", "El sitio",
      "Un sitio físico donde pararse, no un sistema. «Revisar lubricación» no " +
      "es un punto; «visor de nivel del reductor» sí.",
      { falta: true, pista: "visor de nivel del reductor de giro" }) +
    fTexto(llave + ".criterio", "Criterio de aceptación",
      "Tiene que decidirse sin instrumento. Si hace falta un medidor, el punto " +
      "es de la ruta predictiva, no de la ronda del operador.",
      { falta: true, area: true, pista: "el nivel queda entre las dos marcas del visor" }) +
    '<div class="rejilla">' +
    fNumero(llave + ".segundos", "Segundos que debería llevar") +
    fSelect(llave + ".codigo_catalogo", "Falla del catálogo que vigila",
      opcionesCatalogo(),
      "Es la llave hacia el análisis RCM y el historial: con ella, lo que el " +
      "operador encuentre se cose solo.") +
    '</div>' +
    fMarca(llave + ".alcance_operador", "Está al alcance del operador",
      "Se decide aquí, en frío, por quien conoce el bloqueo y la herramienta. " +
      "Preguntárselo en campo garantiza la respuesta cómoda.") +
    botones("puntos", i, b.puntos.length, "punto") +
    '</div></details>';
}

function cajaPegar() {
  return '<details class="bloque" data-llave="pegar">' +
    '<summary><span class="chip acento">excel</span>Pegar los puntos desde una planilla</summary>' +
    '<div class="cuerpo">' +
    '<p class="tenue">Copie el rango en Excel y péguelo aquí. Cuatro columnas, ' +
    'en este orden: <code>clase</code>, <code>punto</code>, ' +
    '<code>criterio</code>, <code>segundos</code>. Las filas que no se ' +
    'entiendan se devuelven con su número de línea y el motivo: no se ' +
    'descarta ninguna en silencio.</p>' +
    '<textarea id="pegado" rows="6" placeholder="limpiar&#9;radiador, cara de ' +
    'entrada&#9;sin tierra pegada entre aletas&#9;40"></textarea>' +
    '<div class="acciones"><button data-accion="pegar">agregar esas filas</button>' +
    '</div></div></details>';
}

function hojaAnalisis() {
  var h = cabecera("Armar el análisis RCM",
    'Función, falla funcional, modo de falla: en ese orden y sin saltarse ' +
    'ninguno. Un modo de falla que no cuelga de una función declarada no se ' +
    'puede leer, porque dice cómo falla algo que nadie dijo que la máquina ' +
    'deba hacer.');

  h += '<h2>El activo</h2><div class="rejilla">' +
    fTexto("activo.codigo", "Código", "Como lo llama el taller.",
           { falta: true, pista: "EX-220-03" }) +
    fTexto("activo.nombre", "Nombre", "", { falta: true, pista: "Excavadora hidráulica" }) +
    fTexto("activo.marca", "Marca") +
    fTexto("activo.modelo", "Modelo") +
    fTexto("activo.serie", "Serie") +
    fTexto("activo.categoria", "Familia",
           "Sirve para preferir antecedentes de máquinas parecidas.") +
    fTexto("activo.instalacion", "Obra o unidad",
           "Nivel 3 de la taxonomía de ISO 14224. Es el único de los de " +
           "localización que cambia por activo en una flota que se mueve.") +
    '</div>';

  h += '<h2>El análisis</h2>' +
    fTexto("contexto", "Contexto operacional",
      "El análisis está amarrado al contexto, no al activo solo: la misma " +
      "bomba en dos contextos son dos análisis. Sin esto declarado, copiar " +
      "este análisis sobre otra máquina parece legítimo.",
      { area: true, filas: 3,
        pista: "turno continuo en interior mina, 4.200 m, polvo de sílice" }) +
    '<div class="rejilla">' +
    fTexto("facilitador", "Facilitador") +
    fTexto("participantes", "Participantes",
      "Separados por coma. RCM lo hace el equipo que opera y mantiene el " +
      "activo; de una sola persona es una opinión.") +
    fTexto("fecha", "Fecha", "ISO 8601: " + FORMATO_FECHA + ".", { pista: hoyISO() }) +
    fTexto("revision", "Revisión", "Qué versión es esto.", { pista: "rev. 1" }) +
    fTexto("aprobado_por", "Aprobado por") +
    fTexto("proxima_revision", "Próxima revisión",
      "El contexto cambia, y con él las consecuencias.", { pista: "2027-10-08" }) +
    '</div>';

  h += '<h2>Funciones <span class="lb">' + b.funciones.length + '</span></h2>';
  if (!b.funciones.length) {
    h += '<p class="vacio">Ninguna todavía.</p>';
  }
  for (var i = 0; i < b.funciones.length; i++) h += bloqueFuncion(i);
  h += '<div class="acciones">' +
    '<button class="primary" data-accion="agregar-funcion">+ agregar función</button>' +
    '</div>';
  return h;
}

function bloqueFuncion(i) {
  var f = b.funciones[i], llave = "funciones." + i;
  var titulo = f.descripcion ? esc(f.descripcion)
    : '<span class="vacio">sin descripción todavía</span>';
  var h = '<details class="bloque" data-llave="' + llave + '">' +
    '<summary><span class="chip acento">F' + (i + 1) + '</span>' + titulo +
    '<span class="chip">' + f.fallas.length + ' falla(s)</span></summary>' +
    '<div class="cuerpo">' +
    fTexto(llave + ".descripcion", "La función",
      "Lo que el activo debe hacer. En verbo y con el objeto.",
      { falta: true, pista: "Girar la superestructura 360°" }) +
    fTexto(llave + ".estandar", "Estándar de desempeño",
      "Lo que la vuelve verificable, con número. Una función sin estándar no " +
      "se puede fallar de forma verificable, y de ella no sale ningún modo " +
      "de falla útil.",
      { falta: true, area: true, pista: "a 9 rpm con carga nominal de 2,1 m³" }) +
    '<div class="rejilla">' +
    fSelect(llave + ".tipo", "Tipo", [["principal", "principal"], ["secundaria", "secundaria"]]) +
    fTexto(llave + ".condicion", "En qué condición aplica",
      "", { pista: "solo en pendiente > 15%" }) +
    '</div>' +
    botones("funciones", i, b.funciones.length, "función");

  h += '<div class="anidado"><h2>Fallas funcionales <span class="lb">' +
    f.fallas.length + '</span></h2>';
  if (!f.fallas.length) {
    h += '<p class="vacio">Ninguna. Una función declarada y nunca fallada no ' +
      'aporta al plan.</p>';
  }
  for (var j = 0; j < f.fallas.length; j++) h += bloqueFalla(i, j);
  h += '<div class="acciones"><button data-accion="agregar-falla" data-ruta="' +
    llave + '.fallas">+ agregar falla funcional</button></div></div>';

  return h + '</div></details>';
}

function bloqueFalla(i, j) {
  var ff = b.funciones[i].fallas[j], llave = "funciones." + i + ".fallas." + j;
  var titulo = ff.descripcion ? esc(ff.descripcion)
    : '<span class="vacio">sin descripción todavía</span>';
  var h = '<details class="bloque" data-llave="' + llave + '">' +
    '<summary><span class="chip">F' + (i + 1) + '.' + (j + 1) + '</span>' + titulo +
    '<span class="chip">' + ff.modos.length + ' modo(s)</span></summary>' +
    '<div class="cuerpo">' +
    fTexto(llave + ".descripcion", "La falla funcional",
      "Cómo deja de cumplir la función. Pérdida total y pérdida parcial son " +
      "dos fallas funcionales distintas, no una.",
      { falta: true, pista: "No gira" }) +
    botones("funciones." + i + ".fallas", j, b.funciones[i].fallas.length,
            "falla funcional");

  h += '<div class="anidado"><h2>Modos de falla <span class="lb">' +
    ff.modos.length + '</span></h2>';
  if (!ff.modos.length) {
    h += '<p class="vacio">Ninguno. La tarea se decide en el modo, no en la ' +
      'falla funcional.</p>';
  }
  for (var k = 0; k < ff.modos.length; k++) h += bloqueModo(i, j, k);
  h += '<div class="acciones"><button data-accion="agregar-modo" data-ruta="' +
    llave + '.modos">+ agregar modo de falla</button></div></div>';

  return h + '</div></details>';
}

function bloqueModo(i, j, k) {
  var m = b.funciones[i].fallas[j].modos[k];
  var llave = "funciones." + i + ".fallas." + j + ".modos." + k;
  var titulo = m.descripcion ? esc(m.descripcion)
    : '<span class="vacio">sin descripción todavía</span>';
  var h = '<details class="bloque" data-llave="' + llave + '">' +
    '<summary><span class="chip">' + (i + 1) + '.' + (j + 1) + '.' + (k + 1) + '</span>' +
    titulo + (m.evidente === "no" ? '<span class="chip grave">oculta</span>' : '') +
    '</summary><div class="cuerpo">' +
    fTexto(llave + ".descripcion", "El modo de falla",
      "Qué produce la falla funcional. Es el nivel donde se decide la tarea.",
      { falta: true, pista: "Corona de giro con desgaste en los dientes" }) +

    fSelect(llave + ".codigo_catalogo", "Falla del catálogo", opcionesCatalogo(),
      "Al elegirla se rellenan causa, mecanismo y sistema si están vacíos: " +
      "lo que usted ya escribió no se pisa.") +

    '<div class="rejilla">' +
    fTexto(llave + ".causa", "Causa") +
    fTexto(llave + ".mecanismo", "Mecanismo", "Desgaste, fatiga, corrosión…") +
    '</div>' +
    '<div class="rejilla">' +
    fTexto(llave + ".ubicacion.sistema", "Sistema") +
    fTexto(llave + ".ubicacion.subsistema", "Subsistema") +
    fTexto(llave + ".ubicacion.componente", "Componente",
      "Nivel 8 de ISO 14224: el ítem mantenible, donde cae el mantenimiento.") +
    '</div>' +

    fSelect(llave + ".evidente", "¿La falla se nota cuando ocurre?", [
      ["si", "Sí — el operador se da cuenta solo"],
      ["no", "No — es una falla oculta"]
    ], "Es la PRIMERA bifurcación de RCM, no una consecuencia más. Si es " +
       "oculta, el riesgo no es esta falla: es la falla múltiple, y de ahí " +
       "sale una tarea de búsqueda de fallas.");

  h += '<label class="campo"><span>Consecuencias</span>' +
    '<em>Qué pasa si ocurre y nadie lo evita. El árbol de decisión empieza ' +
    'aquí: sin consecuencia declarada no sale tarea.</em></label>';
  for (var c = 0; c < CLASES_CONSECUENCIA.length; c++) {
    var clase = CLASES_CONSECUENCIA[c], puesta = claseEn(m, clase);
    h += '<label class="marca"><input type="checkbox" data-accion="consecuencia" ' +
      'data-ruta="' + llave + '" data-clase="' + clase + '"' +
      (puesta ? ' checked' : '') + '><span>' + esc(clase) +
      (CONSECUENCIAS_GRAVES.indexOf(clase) >= 0
        ? ' <span class="chip grave">grave</span>' : '') + '</span></label>';
    if (puesta) {
      h += fTexto(llave + ".consecuencias." + indiceClase(m, clase) + ".descripcion",
                  "cómo, concretamente", "", { pista: "aplasta al que está abajo" });
    }
  }

  h += fTexto(llave + ".efecto.local", "Efecto: qué pasa en el equipo",
    "Responde la Q4 de JA1011. Sin esto, la pregunta no se puede contestar.",
    { area: true, pista: "la superestructura se traba y el giro se detiene" }) +
    '<div class="rejilla">' +
    fTexto(llave + ".efecto.observa_operador", "Qué ve, oye o huele el operador") +
    fTexto(llave + ".efecto.parametro", "Qué lectura cambia") +
    fTexto(llave + ".efecto.alarma", "Qué alarma o luz aparece") +
    fTexto(llave + ".efecto.como_detectarlo", "Cómo se confirma") +
    '</div>' +
    fSelect(llave + ".estado", "Estado", [
      ["propuesto", "propuesto"], ["validado", "validado — necesita evidencia"],
      ["descartado", "descartado"]
    ], "«Validado» sin evidencia no se puede guardar: un modo validado de " +
       "memoria es una opinión con sello.");

  h += '<div class="anidado"><h2>Evidencia <span class="lb">' +
    m.evidencia.length + '</span></h2>';
  if (!m.evidencia.length) {
    h += '<p class="vacio">Ninguna. Sin evidencia, el análisis es una opinión.</p>';
  }
  for (var e = 0; e < m.evidencia.length; e++) {
    h += '<div class="bloque"><div class="rejilla">' +
      fSelect(llave + ".evidencia." + e + ".fuente", "Fuente",
              FUENTES.map(function (f) { return f; })) +
      fTexto(llave + ".evidencia." + e + ".referencia", "Dónde ir a mirarlo",
             "", { pista: "informe 2026-0412, sección 3" }) +
      '</div>' +
      fTexto(llave + ".evidencia." + e + ".nota", "Nota") +
      '<div class="acciones"><button class="borrar" data-accion="quitar" data-ruta="' +
      llave + '.evidencia" data-i="' + e + '">quitar evidencia</button></div></div>';
  }
  h += '<div class="acciones"><button data-accion="agregar-evidencia" data-ruta="' +
    llave + '.evidencia">+ agregar evidencia</button></div></div>';

  h += botones("funciones." + i + ".fallas." + j + ".modos", k,
               b.funciones[i].fallas[j].modos.length, "modo");
  return h + '</div></details>';
}

function claseEn(m, clase) {
  return indiceClase(m, clase) >= 0;
}
function indiceClase(m, clase) {
  for (var i = 0; i < m.consecuencias.length; i++) {
    if (m.consecuencias[i].clase === clase) return i;
  }
  return -1;
}

/* ------------------------------------------------------------- el panel */

function pintarPanel() {
  var datos = armarJSON(tipo, b);
  var errores = erroresDeCarga(tipo, datos);
  var avisos = avisosDeCalidad(tipo, datos);
  var listo = !errores.length && cuantos() > 0;

  // El `id` va a la vista porque es el nombre con el que la pauta se va a
  // pedir por radio, y no hay ningún campo donde se vea: se deriva.
  var cuenta = tipo === "pauta"
    ? (datos.id || "sin id") + " · " + b.puntos.length + " punto(s) · " +
      datos.presupuesto_seg + " s de ronda"
    : contarAnalisis();

  panel.hidden = false;
  panel.innerHTML = '<div>' +
    '<div class="cuenta">' + esc(cuenta) +
    (errores.length ? ' · <b style="color:var(--mal)">' + errores.length +
      ' cosa(s) que hay que arreglar antes de bajarlo</b>' : '') +
    (!errores.length && avisos.length ? ' · <b style="color:var(--obs)">' +
      avisos.length + ' hueco(s)</b>' : '') +
    '</div>' +
    '<button id="ver-detalle">' + (errores.length || avisos.length
      ? 'ver qué falta' : 'sin pendientes') + '</button>' +
    '<button class="primary" id="bajar"' + (listo ? '' : ' disabled') + '>' +
    (tipo === "pauta" ? 'Guardar la pauta (.json)' : 'Guardar el análisis (.json)') +
    '</button></div>' +
    '<div id="detalle" class="detalle" hidden>' + detalleHTML(errores, avisos) + '</div>';

  document.getElementById("ver-detalle").onclick = function () {
    var d = document.getElementById("detalle");
    d.hidden = !d.hidden;
    dejarSitio();
  };
  document.getElementById("bajar").onclick = bajar;
  dejarSitio();
}

/* El panel va fijo abajo, y lo ultimo de la hoja le quedaba DEBAJO: el ultimo
   punto de la pauta y la caja de pegar desde el Excel no se podian tocar. Un
   margen fijo no alcanza —el panel crece cuando el texto de la cuenta se
   parte en dos lineas, y mucho mas cuando se despliega el detalle—, asi que
   se mide lo que ocupa y se le deja ese sitio. */
function dejarSitio() {
  app.style.paddingBottom = (panel.offsetHeight + 24) + "px";
}

function detalleHTML(errores, avisos) {
  var h = "";
  if (errores.length) {
    h += '<p class="lb" style="color:var(--mal)">Esto detiene el archivo: el ' +
      'resto de FixMate lo rechazaría</p><ul class="lista mal">' +
      errores.map(function (e) { return '<li>' + esc(e) + '</li>'; }).join("") +
      '</ul>';
  }
  if (avisos.length) {
    h += '<p class="lb" style="color:var(--obs)">Esto carga igual, pero deja ' +
      'un hueco</p><ul class="lista obs">' +
      avisos.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join("") +
      '</ul>';
  }
  if (!h) {
    h = '<p class="tenue">No queda nada pendiente. El archivo carga en el ' +
      'resto de FixMate y no tiene huecos declarados.</p>';
  }
  return h;
}

function cuantos() {
  if (tipo === "pauta") return b.puntos.length;
  var n = 0;
  for (var i = 0; i < b.funciones.length; i++) {
    for (var j = 0; j < b.funciones[i].fallas.length; j++) {
      n += b.funciones[i].fallas[j].modos.length;
    }
  }
  return n;
}

function contarAnalisis() {
  var fallas = 0;
  for (var i = 0; i < b.funciones.length; i++) {
    fallas += b.funciones[i].fallas.length;
  }
  return b.funciones.length + " función(es) · " + fallas + " falla(s) · " +
    cuantos() + " modo(s)";
}

function nombreArchivo() {
  var codigo = tipo === "pauta" ? b.activo_codigo : b.activo.codigo;
  codigo = String(codigo || "sin-codigo").trim().toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return (tipo === "pauta" ? "pauta-" : "analisis-") + codigo + ".json";
}

function bajar() {
  var datos = armarJSON(tipo, b);
  var texto = JSON.stringify(datos, null, 2) + "\n";
  var blob = new Blob([texto], { type: "application/json" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nombreArchivo();
  document.body.appendChild(a);
  a.click();
  setTimeout(function () {
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 0);
  mensaje = "Guardado como «" + nombreArchivo() + "». " + (tipo === "pauta"
    ? "Ábralo en la Ronda CIL del teléfono del operador."
    : "Ábralo en la mesa de trabajo del análisis RCM.");
  render();
}

/* ------------------------------------------------------------ los oyentes
 * Dos, delegados en la hoja entera: uno para lo que se escribe y otro para
 * lo que se toca. Con tres niveles de anidamiento, enganchar campo por campo
 * es donde se cuelan los que se ven y no guardan nada. */
app.addEventListener("input", function (ev) {
  var t = ev.target, ruta = t.getAttribute("data-ruta");
  if (!ruta || t.getAttribute("data-accion")) return;
  if (t.getAttribute("data-bool")) fijar(ruta, t.checked);
  else fijar(ruta, t.value);
  if (t.getAttribute("data-obliga")) {
    var campo = t.closest(".campo");
    if (campo) campo.classList.toggle("falta", !t.value.trim());
  }
  pintarPanel();
  // El resumen del bloque lleva la descripción: se actualiza al escribir sin
  // volver a armar la hoja, que perdería el cursor.
  refrescarResumen(ruta);
});

app.addEventListener("change", function (ev) {
  var t = ev.target;
  if (!t.getAttribute("data-ruta")) return;
  if (t.getAttribute("data-recarga") === "1") {
    heredarDelCatalogo(t.getAttribute("data-ruta"));
  } else if (t.tagName !== "SELECT") {
    return;
  }
  // Clase de punto, tipo de función, estado, `evidente`: cambian el chip del
  // resumen, así que se vuelve a armar. No hay cursor que perder. Pero sí
  // bloques desplegados: sin recordarlos, elegir un código de catálogo
  // cerraba el modo que se estaba escribiendo y los dos niveles de arriba.
  recordarAbiertos();
  render();
});

app.addEventListener("click", function (ev) {
  var t = ev.target.closest("[data-accion]");
  if (!t) return;
  var accion = t.getAttribute("data-accion"), ruta = t.getAttribute("data-ruta");
  var i = +t.getAttribute("data-i");

  if (accion === "consecuencia") {
    var m = enRuta(ruta), clase = t.getAttribute("data-clase");
    var pos = indiceClase(m, clase);
    if (pos >= 0) m.consecuencias.splice(pos, 1);
    else m.consecuencias.push({ clase: clase, descripcion: "" });
    recordarAbiertos();
    render();
    return;
  }
  if (accion === "volver") { verInicio(""); return; }
  if (accion === "pegar") { pegar(); return; }

  recordarAbiertos();
  if (accion === "agregar-punto") {
    b.puntos.push(puntoVacio());
    abierto["puntos." + (b.puntos.length - 1)] = true;
  } else if (accion === "agregar-funcion") {
    b.funciones.push(funcionVacia());
    abierto["funciones." + (b.funciones.length - 1)] = true;
  } else if (accion === "agregar-falla") {
    var fallas = enRuta(ruta);
    fallas.push(fallaVacia());
    abierto[ruta + "." + (fallas.length - 1)] = true;
  } else if (accion === "agregar-modo") {
    var modos = enRuta(ruta);
    modos.push(modoVacio());
    abierto[ruta + "." + (modos.length - 1)] = true;
  } else if (accion === "agregar-evidencia") {
    enRuta(ruta).push({ fuente: "historial", referencia: "", nota: "" });
  } else if (accion === "quitar") {
    enRuta(ruta).splice(i, 1);
  } else if (accion === "subir" || accion === "bajar") {
    var lista = enRuta(ruta), j = accion === "subir" ? i - 1 : i + 1;
    var tmp = lista[i]; lista[i] = lista[j]; lista[j] = tmp;
  } else {
    return;
  }
  mensaje = "";
  render();
});

/* Cuáles bloques estaban desplegados antes de volver a armar la hoja. Sin
   esto, agregar un punto cerraba los otros doce y había que abrirlos de
   nuevo uno por uno. */
function recordarAbiertos() {
  abierto = {};
  var ds = app.querySelectorAll("details[data-llave]");
  for (var i = 0; i < ds.length; i++) {
    if (ds[i].open) abierto[ds[i].getAttribute("data-llave")] = true;
  }
}

function refrescarResumen(ruta) {
  var partes = ruta.split(".");
  if (partes[partes.length - 1] !== "descripcion" &&
      partes[partes.length - 1] !== "punto") return;
  var llave = partes.slice(0, -1).join(".");
  var d = app.querySelector('details[data-llave="' + llave + '"] > summary');
  if (!d) return;
  var hijos = d.querySelectorAll(".chip");
  var texto = String(leer(ruta)).trim();
  // El resumen se rearma a mano para no tocar el resto del bloque.
  var chips = [];
  for (var i = 0; i < hijos.length; i++) chips.push(hijos[i].outerHTML);
  d.innerHTML = chips.join("") +
    (texto ? esc(texto) : '<span class="vacio">sin descripción todavía</span>');
}

/* Espejo de `ModoFalla.desde_catalogo()`: rellena huecos, no corrige. Lo que
   el analista ya escribió gana. */
function heredarDelCatalogo(ruta) {
  var m = enRuta(ruta.replace(/\.codigo_catalogo$/, ""));
  var e = CATALOGO[m.codigo_catalogo];
  // El punto de una pauta tambien apunta al catalogo, pero ahi el codigo es
  // solo la llave: no tiene causa ni ubicacion que rellenar.
  if (!e || !m.efecto) return;
  if (!String(m.causa || "").trim()) m.causa = e.causa;
  if (!String(m.mecanismo || "").trim()) m.mecanismo = e.mecanismo;
  if (m.ubicacion && !String(m.ubicacion.sistema || "").trim()) {
    m.ubicacion.sistema = e.sistema;
  }
  if (!String(m.descripcion || "").trim()) m.descripcion = e.causa;
}

function pegar() {
  var caja = document.getElementById("pegado");
  if (!caja) return;
  var r = filasPegadas(caja.value);
  for (var i = 0; i < r.puntos.length; i++) b.puntos.push(r.puntos[i]);
  recordarAbiertos();
  abierto["pegar"] = true;
  mensaje = r.puntos.length + " punto(s) agregados." +
    (r.rechazos.length ? " No entraron " + r.rechazos.length + ": " +
      r.rechazos.join(" ") : "");
  if (r.puntos.length) caja.value = "";
  render();
}

/* ---------------------------------------------------------------- arranque */

verInicio("");
</script>
