<script>
/* armar:reglas:inicio — ESPEJO de los cargadores de Python.
 *
 * Las reglas de lo que se puede escribir, copiadas de Python.
 *
 * Esta pantalla existe porque faltaba la mitad del producto. FixMate sabia
 * leer una pauta y un analisis, validarlos, sacar la matriz y el plan; lo que
 * no sabia era CREARLOS. Las dos pantallas de campo abren un `.json` que
 * hasta hoy solo podia escribir a mano alguien que conociera el esquema, y
 * eso no es un producto: es un demo con un formulario escondido en un editor
 * de texto.
 *
 * De aqui sale el archivo que abren las otras dos pantallas, asi que la regla
 * es una sola y no puede negociarse: ESTA PANTALLA NO PUEDE PRODUCIR UN
 * ARCHIVO QUE EL RESTO DE FIXMATE RECHACE. Si lo produjera, el planificador
 * armaria la pauta, la bajaria, el operador la abriria en el socavon y la
 * ronda no arrancaria —y el error aparecería a 4.200 m, no en la oficina.
 *
 * Por eso `erroresDeCarga()` es un espejo exacto de los cargadores de Python
 * —`cargador.checklist_de_dict` y `cargador.analisis_de_dict`, con los
 * `__post_init__` que hay debajo— y no una validacion «parecida». Lo que
 * Python rechaza, esto rechaza; lo que Python acepta, esto acepta. De que
 * sigan diciendo lo mismo responde `tests/test_fixmate_cruce_armar.py`, que
 * corre este javascript con node y compara verdicto por verdicto.
 *
 * Y una segunda lista, aparte: `avisosDeCalidad()`. Esos NO bloquean. Un
 * analisis sin revision ni aprobacion carga perfecto y es un borrador que
 * alguien va a usar como si fuera definitivo; un punto sin presupuesto de
 * segundos carga perfecto y hace que no se pueda detectar una ronda firmada.
 * Son dos cosas distintas y mezclarlas tiene las dos consecuencias malas: o
 * se bloquea al que tiene prisa por un campo opcional, o se deja pasar lo que
 * de verdad rompe. Lo que falta se dice; lo que no carga, se detiene.
 */
/* armar:datos:inicio */
var CLASES = {}, FRECUENCIAS = [], CLASES_CONSECUENCIA = [],
    CONSECUENCIAS_GRAVES = [], TIPOS_FUNCION = [], ESTADOS_VALIDACION = [],
    FUENTES = [], CATALOGO = {}, FORMATO_FECHA = "AAAA-MM-DD";
/* armar:datos:fin */

/* ------------------------------------------------------------- utilidades */

function txt(v) {
  return (v === undefined || v === null) ? "" : String(v);
}
function vacio(v) {
  return txt(v).trim() === "";
}

/* La fecha, con la misma regla que `nefer/fixmate/registro.py`: ISO 8601 o
 * nada. «03/04/2026» en Lima es el 3 de abril y en Houston el 4 de marzo, y
 * dos años despues nadie puede decir cual era. Vacia se admite: es «no se
 * declaro», que es informacion honesta. Lo que no se admite es lo ambiguo. */
function fechaMal(valor, donde) {
  var v = txt(valor).trim();
  if (!v) return "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    return donde + ": la fecha «" + v + "» no esta en formato ISO 8601 (" +
      FORMATO_FECHA + ").";
  }
  var p = v.split("-"), a = +p[0], m = +p[1], d = +p[2];
  var f = new Date(Date.UTC(a, m - 1, d));
  if (f.getUTCFullYear() !== a || f.getUTCMonth() + 1 !== m ||
      f.getUTCDate() !== d) {
    return donde + ": la fecha «" + v + "» no existe.";
  }
  return "";
}

/* `int(p.get("segundos") or 0)` de Python: lo que no sea entero revienta el
 * cargador, asi que aqui tambien. Un «30 s» escrito con la unidad pegada es
 * el error tipico de pegar desde el Excel. */
function segundosMal(valor) {
  var v = txt(valor).trim();
  if (!v) return false;
  return !/^-?\d+$/.test(v);
}

/* ------------------------------------------- espejo: pauta de ronda (TPM) */

/* Espejo de `cargador.checklist_de_dict` + `tpm.Checklist.__post_init__` +
 * `tpm.PuntoChecklist.__post_init__`. El orden de las comprobaciones importa
 * menos que el verdicto, pero se mantiene para que el mensaje que lee el
 * planificador sea el mismo que leeria en la consola. */
function erroresPauta(datos) {
  var errores = [];
  var frecuencia = txt(datos.frecuencia) || "diaria";
  if (FRECUENCIAS.indexOf(frecuencia) < 0) {
    errores.push("frecuencia «" + frecuencia + "» desconocida: use " +
                 FRECUENCIAS.join(", ") + ".");
  }
  if (vacio(datos.id) || vacio(datos.activo_codigo)) {
    errores.push("la pauta necesita «id» y «activo_codigo».");
  }
  var puntos = datos.puntos || [];
  if (!(puntos instanceof Array)) {
    errores.push("«puntos» tiene que ser una lista.");
    return errores;
  }
  for (var i = 0; i < puntos.length; i++) {
    var p = puntos[i] || {}, donde = "punto " + (i + 1) + ": ";
    var clase = txt(p.clase);
    if (!Object.prototype.hasOwnProperty.call(CLASES, clase)) {
      errores.push(donde + "clase «" + clase + "» desconocida: use " +
        Object.keys(CLASES).join(", ") + ". «Detectar anomalias» no es una " +
        "clase de punto: es lo que pasa cuando un punto sale NOK.");
      continue;
    }
    if (vacio(p.punto)) {
      errores.push(donde + "el punto necesita un sitio fisico donde pararse.");
      continue;
    }
    if (vacio(p.criterio)) {
      errores.push(donde + "«" + txt(p.punto) + "»: falta el criterio de " +
        "aceptacion. Sin criterio, cada operador juzga otra cosa y la pauta " +
        "no mide nada.");
      continue;
    }
    var cod = txt(p.codigo_catalogo);
    if (cod && !Object.prototype.hasOwnProperty.call(CATALOGO, cod)) {
      errores.push(donde + "el codigo «" + cod + "» no esta en el catalogo.");
      continue;
    }
    if (segundosMal(p.segundos)) {
      errores.push(donde + "«segundos» tiene que ser un numero entero.");
    }
  }
  return errores;
}

/* ------------------------------------------- espejo: analisis RCM (JA1011) */

/* Espejo de `cargador.analisis_de_dict`, con `activos.Activo`, `rcm.Funcion`,
 * `rcm.FallaFuncional`, `rcm.ModoFalla`, `rcm.Consecuencia` y
 * `rcm.Referencia` debajo. */
function erroresAnalisis(datos) {
  var errores = [];
  var activo = datos.activo;
  if (!activo || typeof activo !== "object" || activo instanceof Array) {
    errores.push("falta el objeto «activo».");
    return errores;
  }
  if (vacio(activo.codigo)) {
    errores.push("el activo necesita codigo: es como lo llama el taller.");
  } else if (vacio(activo.nombre)) {
    errores.push(txt(activo.codigo) + ": falta el nombre del activo.");
  }
  var mal = fechaMal(datos.fecha, "el analisis");
  if (mal) errores.push(mal);
  mal = fechaMal(datos.proxima_revision, "la proxima revision del analisis");
  if (mal) errores.push(mal);

  var funciones = datos.funciones || [];
  if (!(funciones instanceof Array)) {
    errores.push("«funciones» tiene que ser una lista.");
    return errores;
  }
  for (var i = 0; i < funciones.length; i++) {
    var f = funciones[i] || {}, dondeF = "funcion " + (i + 1) + ": ";
    if (vacio(f.descripcion)) {
      errores.push(dondeF + "la funcion necesita descripcion.");
    } else if (vacio(f.estandar)) {
      errores.push(dondeF + "«" + txt(f.descripcion) + "»: falta el estandar " +
        "de desempeño. Una funcion sin estandar no se puede fallar de forma " +
        "verificable, y de ella no sale ningun modo de falla util.");
    } else if (TIPOS_FUNCION.indexOf(txt(f.tipo) || "principal") < 0) {
      errores.push(dondeF + "tipo de funcion «" + txt(f.tipo) +
                   "» desconocido.");
    }
    var fallas = f.fallas || [];
    if (!(fallas instanceof Array)) {
      errores.push(dondeF + "«fallas» tiene que ser una lista.");
      continue;
    }
    for (var j = 0; j < fallas.length; j++) {
      var ff = fallas[j] || {};
      var dondeFF = dondeF.slice(0, -2) + ", falla funcional " + (j + 1) + ": ";
      if (vacio(ff.descripcion)) {
        errores.push(dondeFF + "la falla funcional necesita descripcion.");
      }
      var modos = ff.modos || [];
      if (!(modos instanceof Array)) {
        errores.push(dondeFF + "«modos» tiene que ser una lista.");
        continue;
      }
      for (var k = 0; k < modos.length; k++) {
        var donde = dondeFF.slice(0, -2) + ", modo " + (k + 1) + ": ";
        errores = errores.concat(erroresModo(modos[k] || {}, donde));
      }
    }
  }
  return errores;
}

function erroresModo(m, donde) {
  var errores = [];
  var cs = m.consecuencias || [];
  for (var i = 0; i < cs.length; i++) {
    var clase = typeof cs[i] === "string" ? cs[i] : txt((cs[i] || {}).clase);
    if (CLASES_CONSECUENCIA.indexOf(clase) < 0) {
      errores.push(donde + "clase de consecuencia «" + clase + "» " +
        "desconocida. Si queria decir que la falla es oculta, eso va en " +
        "«evidente», no aqui: es la primera bifurcacion del analisis, no una " +
        "categoria mas.");
    }
  }
  var ev = m.evidencia || [];
  for (i = 0; i < ev.length; i++) {
    var r = ev[i] || {};
    if (FUENTES.indexOf(txt(r.fuente)) < 0) {
      errores.push(donde + "fuente «" + txt(r.fuente) + "» desconocida: use " +
                   FUENTES.join(", ") + ".");
    }
    // La referencia vacia NO es un error de carga: Python la admite. Es un
    // hueco, y como hueco se dice en los avisos. Poner aqui una regla que
    // Python no tiene seria exactamente el espejo roto al reves: la pantalla
    // frenando un archivo que el resto del producto acepta.
  }
  if (vacio(m.descripcion)) {
    errores.push(donde + "el modo de falla necesita descripcion.");
    return errores;
  }
  var estado = txt(m.estado) || "propuesto";
  if (ESTADOS_VALIDACION.indexOf(estado) < 0) {
    errores.push(donde + "estado «" + estado + "» desconocido.");
    return errores;
  }
  if (estado === "validado" && !ev.length) {
    errores.push(donde + "«" + txt(m.descripcion) + "»: no se puede marcar " +
      "validado sin evidencia. Un modo de falla validado de memoria es una " +
      "opinion con sello.");
    return errores;
  }
  var cod = txt(m.codigo_catalogo);
  if (cod && !Object.prototype.hasOwnProperty.call(CATALOGO, cod)) {
    errores.push(donde + "el codigo «" + cod + "» no esta en el catalogo.");
  }
  return errores;
}

/* El unico punto de entrada que usa la pantalla: el verdicto de carga del
 * archivo que se va a bajar, sea del tipo que sea. */
function erroresDeCarga(tipo, datos) {
  return tipo === "pauta" ? erroresPauta(datos) : erroresAnalisis(datos);
}

/* --------------------------------------------------------------- calidad */

/* Lo que carga pero deja un hueco. No bloquea: se dice. Sigue a
 * `rcm.calidad()` y al encabezado de `tpm.py` en lo que cada hueco cuesta.
 *
 * Se lee sobre el ARCHIVO ya armado, igual que `erroresDeCarga`, y no sobre
 * el borrador: asi los dos juicios hablan del mismo objeto —el que se va a
 * bajar— y no hay una segunda forma del dato que mantener al dia. */
function avisosPauta(datos) {
  var avisos = [], puntos = datos.puntos || [];
  if (!puntos.length) {
    avisos.push("La pauta no tiene ningun punto todavia: asi no arranca en el " +
      "telefono del operador.");
  }
  var sinSegundos = 0, conCatalogo = 0, clases = {};
  for (var i = 0; i < puntos.length; i++) {
    var p = puntos[i] || {};
    if (!(+txt(p.segundos))) sinSegundos++;
    if (txt(p.codigo_catalogo)) conCatalogo++;
    clases[txt(p.clase)] = true;
  }
  if (sinSegundos) {
    avisos.push(sinSegundos + " punto(s) sin presupuesto de segundos. Sin el " +
      "no se puede detectar una ronda firmada en lugar de ejecutada, que es " +
      "la forma en que esta herramienta se degrada siempre.");
  }
  if (puntos.length && !clases.limpiar) {
    avisos.push("Ningun punto de clase «limpiar». La mugre esconde la fuga y " +
      "la grieta: una ronda que solo mira encuentra menos.");
  }
  if (puntos.length && !conCatalogo) {
    avisos.push("Ningun punto apunta al catalogo de fallas. Sin esa llave, " +
      "lo que el operador encuentre no se cose con el analisis RCM ni con el " +
      "historial: queda como texto suelto.");
  }
  if (vacio(datos.origen)) {
    avisos.push("Sin «origen»: no queda dicho si la pauta sale del manual " +
      "del fabricante, del analisis RCM o de la experiencia del taller.");
  }
  return avisos;
}

function avisosAnalisis(datos) {
  var avisos = [], funciones = datos.funciones || [];
  if (!funciones.length) {
    avisos.push("El analisis no tiene ninguna funcion todavia: sin funciones " +
      "no hay fallas funcionales, y sin ellas no hay nada que analizar.");
  }
  var fallas = 0, modos = 0, sinEfecto = 0, sinConsecuencia = 0, ocultos = 0,
      sinReferencia = 0;
  for (var i = 0; i < funciones.length; i++) {
    var fs = (funciones[i] || {}).fallas || [];
    if (!fs.length) {
      avisos.push("La funcion " + (i + 1) + " no tiene ninguna falla " +
        "funcional: una funcion declarada y nunca fallada no aporta al plan.");
    }
    fallas += fs.length;
    for (var j = 0; j < fs.length; j++) {
      var ms = (fs[j] || {}).modos || [];
      if (!ms.length) {
        avisos.push("La falla funcional " + (i + 1) + "." + (j + 1) + " no " +
          "tiene modos de falla: la tarea se decide en el modo, no en la falla.");
      }
      modos += ms.length;
      for (var k = 0; k < ms.length; k++) {
        var m = ms[k] || {};
        if (vacio((m.efecto || {}).local)) sinEfecto++;
        if (!((m.consecuencias || []).length)) sinConsecuencia++;
        if (m.evidente === false) ocultos++;
        var refs = m.evidencia || [];
        for (var r = 0; r < refs.length; r++) {
          if (vacio((refs[r] || {}).referencia)) sinReferencia++;
        }
      }
    }
  }
  if (sinEfecto) {
    avisos.push(sinEfecto + " modo(s) sin efecto local descrito. La Q4 de " +
      "JA1011 no se puede contestar sin saber que pasa cuando ocurre.");
  }
  if (sinConsecuencia) {
    avisos.push(sinConsecuencia + " modo(s) sin ninguna consecuencia " +
      "declarada. El arbol de decision empieza por la consecuencia: sin ella " +
      "no sale tarea.");
  }
  if (sinReferencia) {
    avisos.push(sinReferencia + " referencia(s) de evidencia sin apuntar a " +
      "nada. «Historial» sin el numero del informe no se puede ir a mirar: " +
      "es una opinion con etiqueta de fuente.");
  }
  if (modos && !ocultos) {
    avisos.push("Ningun modo marcado como oculto. Es posible, pero conviene " +
      "mirarlo dos veces: las fallas ocultas son la mitad de los modos en " +
      "equipos con protecciones, y no declararlas borra la tarea de busqueda " +
      "de fallas del plan.");
  }
  if (vacio(datos.contexto)) {
    avisos.push("Sin contexto operacional. El mismo equipo en dos contextos " +
      "son dos analisis: sin el declarado, copiar este sobre otra maquina " +
      "parece legitimo.");
  }
  if (vacio(datos.revision) || vacio(datos.aprobado_por)) {
    avisos.push("Sin revision o sin aprobacion: queda como borrador que " +
      "alguien va a usar como definitivo.");
  }
  if (vacio(datos.proxima_revision)) {
    avisos.push("Sin proxima revision. El contexto operacional cambia, y con " +
      "el cambian las consecuencias.");
  }
  if (!(datos.participantes || []).length) {
    avisos.push("Sin participantes. RCM lo hace el equipo que opera y " +
      "mantiene el activo; un analisis de una sola persona es una opinion.");
  }
  return avisos;
}

function avisosDeCalidad(tipo, datos) {
  return tipo === "pauta" ? avisosPauta(datos) : avisosAnalisis(datos);
}

/* ---------------------------------------------- pegar desde una planilla */

/* El planificador ya tiene la pauta en un Excel. Pedirle que la vuelva a
 * escribir punto por punto en un formulario es la forma mas segura de que no
 * la escriba. Se pega el rango y se separa por tabulaciones —que es lo que
 * pone el Excel en el portapapeles—, por punto y coma o por coma.
 *
 * Las filas que no se entienden NO se descartan en silencio: vuelven con su
 * numero de linea y su motivo. Un importador que se come filas calladas es
 * peor que no tener importador. */
function separar(linea) {
  if (linea.indexOf("\t") >= 0) return linea.split("\t");
  if (linea.indexOf(";") >= 0) return linea.split(";");
  return linea.split(",");
}

function filasPegadas(texto) {
  var lineas = txt(texto).split(/\r?\n/);
  var puntos = [], rechazos = [];
  for (var i = 0; i < lineas.length; i++) {
    var linea = lineas[i];
    if (!linea.trim()) continue;
    var c = separar(linea).map(function (x) { return x.trim(); });
    // Un encabezado pegado junto con el rango: se saltea, no se rechaza.
    if (i === 0 && /^clase$/i.test(c[0] || "")) continue;
    var clase = (c[0] || "").toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(CLASES, clase)) {
      rechazos.push("linea " + (i + 1) + ": «" + (c[0] || "") + "» no es una " +
        "de las cinco clases (" + Object.keys(CLASES).join(", ") + ").");
      continue;
    }
    if (!(c[1] || "").trim()) {
      rechazos.push("linea " + (i + 1) + ": falta el punto, la segunda columna.");
      continue;
    }
    if (!(c[2] || "").trim()) {
      rechazos.push("linea " + (i + 1) + ": «" + c[1] + "» sin criterio de " +
        "aceptacion, la tercera columna.");
      continue;
    }
    var seg = (c[3] || "").replace(/[^\d-]/g, "");
    puntos.push({
      clase: clase, punto: c[1], criterio: c[2],
      segundos: seg ? +seg : 0, alcance_operador: true,
      codigo_catalogo: "", modo_falla_id: ""
    });
  }
  return { puntos: puntos, rechazos: rechazos };
}

/* ------------------------------------------------- armar el archivo final */

/* LO QUE ESTA PANTALLA NO EDITA, NO LO BORRA.
 *
 * Un analisis que ya existe trae cosas que aqui no se tocan: el metodo de
 * criticidad, los valores de severidad/frecuencia/deteccion de cada modo y
 * —la peor de perder— la `decision`, que son las respuestas del equipo al
 * arbol de JA1011. Si el editor reescribiera el archivo solo con los campos
 * que conoce, abrir un analisis para corregir una coma borraria la reunion
 * entera, y lo haria en silencio: el archivo nuevo se veria perfecto.
 *
 * Asi que todo lo que se abre y no se edita viaja en `_resto` y se vuelve a
 * escribir tal cual. Lo conocido gana sobre `_resto`, no al reves: lo que el
 * planificador acaba de escribir no lo puede pisar una copia vieja. */
function conResto(origen, salida) {
  var resto = origen && origen._resto;
  if (!resto) return salida;
  var final = {};
  for (var k in resto) {
    if (Object.prototype.hasOwnProperty.call(resto, k)) final[k] = resto[k];
  }
  for (k in salida) {
    if (Object.prototype.hasOwnProperty.call(salida, k)) final[k] = salida[k];
  }
  return final;
}


/* El `id` de la pauta no se le pide al planificador: se deriva del codigo del
 * activo y de la frecuencia, que es lo que lo hace unico de verdad. Si lo
 * escribe, gana el suyo —una pauta que ya existe tiene su id y hay que poder
 * conservarlo—. */
function idDerivado(borrador) {
  var codigo = txt(borrador.activo_codigo).trim().toUpperCase()
    .replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "");
  if (!codigo) return "";
  return "pauta-" + codigo.toLowerCase() + "-" + (txt(borrador.frecuencia) || "diaria");
}

function pautaJSON(b) {
  var puntos = (b.puntos || []).map(function (p, i) {
    return conResto(p, {
      id: (txt(b.id).trim() || idDerivado(b)) + "." + (i + 1),
      clase: txt(p.clase), punto: txt(p.punto).trim(),
      criterio: txt(p.criterio).trim(),
      alcance_operador: p.alcance_operador !== false,
      segundos: segundosMal(p.segundos) ? txt(p.segundos) : (+txt(p.segundos) || 0),
      codigo_catalogo: txt(p.codigo_catalogo).trim(),
      modo_falla_id: txt(p.modo_falla_id).trim()
    });
  });
  var total = 0;
  for (var i = 0; i < puntos.length; i++) {
    total += Math.max(0, +puntos[i].segundos || 0);
  }
  return conResto(b, {
    id: txt(b.id).trim() || idDerivado(b),
    activo_codigo: txt(b.activo_codigo).trim(),
    nombre: txt(b.nombre).trim(),
    frecuencia: txt(b.frecuencia) || "diaria",
    origen: txt(b.origen).trim(),
    presupuesto_seg: total,
    puntos: puntos
  });
}

/* Los participantes se escriben en una sola linea separados por coma, porque
 * es como los dicta alguien al final de la reunion. */
function listaDeTexto(valor) {
  return txt(valor).split(/[,;\n]/).map(function (x) { return x.trim(); })
    .filter(function (x) { return x; });
}

function analisisJSON(b) {
  var a = b.activo || {};
  var funciones = (b.funciones || []).map(function (f) {
    return conResto(f, {
      descripcion: txt(f.descripcion).trim(),
      estandar: txt(f.estandar).trim(),
      tipo: txt(f.tipo) || "principal",
      condicion: txt(f.condicion).trim(),
      fallas: (f.fallas || []).map(function (ff) {
        return conResto(ff, {
          descripcion: txt(ff.descripcion).trim(),
          modos: (ff.modos || []).map(modoJSON)
        });
      })
    });
  });
  return conResto(b, {
    activo: {
      codigo: txt(a.codigo).trim(), nombre: txt(a.nombre).trim(),
      marca: txt(a.marca).trim(), modelo: txt(a.modelo).trim(),
      serie: txt(a.serie).trim(), categoria: txt(a.categoria).trim(),
      instalacion: txt(a.instalacion).trim(),
      contexto: txt(a.contexto).trim()
    },
    contexto: txt(b.contexto).trim(),
    facilitador: txt(b.facilitador).trim(),
    participantes: listaDeTexto(b.participantes),
    fecha: txt(b.fecha).trim(),
    revision: txt(b.revision).trim(),
    aprobado_por: txt(b.aprobado_por).trim(),
    proxima_revision: txt(b.proxima_revision).trim(),
    funciones: funciones
  });
}

function modoJSON(m) {
  var u = m.ubicacion || {}, e = m.efecto || {};
  return conResto(m, {
    descripcion: txt(m.descripcion).trim(),
    ubicacion: {
      sistema: txt(u.sistema).trim(), subsistema: txt(u.subsistema).trim(),
      componente: txt(u.componente).trim()
    },
    codigo_catalogo: txt(m.codigo_catalogo).trim(),
    causa: txt(m.causa).trim(),
    mecanismo: txt(m.mecanismo).trim(),
    // El desplegable de la pantalla da «si»/«no»; el archivo lleva un
    // booleano, porque eso es lo que es. La traduccion vive aqui, en el unico
    // sitio que arma el archivo: hecha en la pantalla, el cruce con Python
    // comparaba un borrador que nadie va a bajar.
    evidente: m.evidente !== false && m.evidente !== "no",
    efecto: {
      local: txt(e.local).trim(),
      observa_operador: txt(e.observa_operador).trim(),
      parametro: txt(e.parametro).trim(),
      alarma: txt(e.alarma).trim(),
      componente_afectado: txt(e.componente_afectado).trim(),
      como_detectarlo: txt(e.como_detectarlo).trim()
    },
    consecuencias: (m.consecuencias || []).map(function (c) {
      return typeof c === "string"
        ? { clase: c, descripcion: "" }
        : { clase: txt(c.clase), descripcion: txt(c.descripcion).trim() };
    }),
    evidencia: (m.evidencia || []).map(function (r) {
      return { fuente: txt(r.fuente), referencia: txt(r.referencia).trim(),
               nota: txt(r.nota).trim() };
    }),
    estado: txt(m.estado) || "propuesto"
  });
}

function armarJSON(tipo, borrador) {
  return tipo === "pauta" ? pautaJSON(borrador) : analisisJSON(borrador);
}

/* armar:reglas:fin */
</script>
