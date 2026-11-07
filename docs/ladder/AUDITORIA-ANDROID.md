# Auditoría de funcionalidad, operatividad, descargas e instalación en Android

Revisión de LadderLab a raíz de un reporte de uso: **«no lo puedo abrir en
Android»**. Se revisaron todas las formas de llevar la app a un teléfono y se
corrigió lo que fallaba.

Es una revisión interna, no una certificación. Todo lo que dice «medido» o
«probado» se obtuvo con las pruebas de `tests/test_ladder_android.py`, que
emulan un Android 14 (Pixel 7, pantalla táctil, Chrome móvil) y se pueden
volver a correr.

- [1. Resumen](#1-resumen)
- [2. Causa del reporte](#2-causa-del-reporte)
- [3. Matriz por canal de distribución](#3-matriz-por-canal-de-distribución)
- [4. Hallazgos y correcciones](#4-hallazgos-y-correcciones)
- [5. Evidencia](#5-evidencia)
- [6. Lo que queda abierto](#6-lo-que-queda-abierto)

---

## 1. Resumen

| Canal | Antes | Después |
|---|---|---|
| `.zip` → `LadderLab/index.html` en Android | **No abre** (página en blanco) | Sigue sin abrir: es una limitación de Android. El LEEME y el manual lo advierten y ofrecen las alternativas |
| Archivo único `LadderLab.html` en Android | No existía | **Abre**: los 20 retos se corrigen bien, funciona al tacto y no pide ningún archivo vecino |
| APK instalable | No existía | **Compilado y publicado**: `ladderlab-v1`, 2,1 MB, compilación en verde (sección 5) |
| Instalar desde Chrome (PWA) | Solo en `https:`; la dirección aún no está publicada | Funciona en cualquier contexto seguro y **abre sin señal**; hay botón «Instalar» |
| Enlace web `nilthonnn.github.io/nefer/ladder/` | 404 hasta fusionar el PR | Igual: depende de la fusión (sección 6.2) |
| Pruebas automáticas de Android | 0 | **15**, todas aprobadas |

---

## 2. Causa del reporte

El `.zip` traía la app como una carpeta: `index.html` más `lecciones.js` y
`energia.js` al lado.

En una computadora eso funciona. En Android, al abrir `index.html` desde
*Archivos* o *Descargas*, el sistema se lo entrega a Chrome como
`content://…`. Desde ese origen Chrome **no carga los archivos vecinos**, así
que sin las lecciones la app no arranca y la página queda en blanco.

La prueba `test_la_carpeta_abierta_como_en_android_no_sirve` reproduce la
falla: bloquea los archivos vecinos, como lo hace Android, y confirma que la
página no arranca.

A eso se sumaban dos cosas:
- La dirección web no existe hasta que el PR se fusione y GitHub Pages lo
  publique.
- No había APK.

En Android no quedaba ningún camino que funcionara.

---

## 3. Matriz por canal de distribución

| Criterio | APK | Chrome (PWA) | `LadderLab.html` | `.zip` en PC |
|---|---|---|---|---|
| Abre sin conexión | Sí: todo va dentro y no pide permiso de INTERNET | Sí, desde la segunda visita (probado) | Sí (probado) | Sí |
| Funciona al tacto: pulsadores, editor, hoja de propiedades | Sí | Sí | Sí (probado con eventos *touch*) | — |
| Guarda el progreso | Sí: origen https interno estable | Sí | Puede perderse: `content://` no garantiza almacenamiento | Sí, en ese navegador |
| Exportar programa `.json` | **Por el puente nativo, a Descargas** (probado) | Descarga normal | Descarga normal | Descarga normal |
| Importar programa `.json` | Selector del sistema (`onShowFileChooser`) | Sí | Sí | Sí |
| Botón *atrás* del teléfono | Cierra el editor y el menú, vuelve al inicio; dos toques para salir (probado) | Navegación del navegador | Navegación del navegador | — |
| Manual | Va dentro (`manual/index.html`) | Sí | Enlace en línea | En la carpeta y en PDF |
| Actualización | Instalar el APK nuevo encima (con llave propia) | Automática | Volver a descargar | Volver a descargar |

---

## 4. Hallazgos y correcciones

### N1 · Crítico · La versión en carpeta no abre en Android — **corregido con alternativas**

La causa está en la sección 2. Cambiar la forma en que Android abre archivos
locales no está en manos de la app, así que se ofrecen caminos que sí
funcionan:

- **`descargas/LadderLab.html`:** la app entera en un archivo de 218 KB, con
  las lecciones, el simulador, los estilos y el icono dentro. Lo genera
  `herramientas/empaquetar-ladder.py` a partir de `docs/ladder`, así que no
  hay una segunda copia que mantener a mano.
- **El `.zip`** lo trae en la raiz. El `LEEME.txt` dice primero qué hacer en
  Android y avisa explícitamente: «NO abras `LadderLab/index.html` en el
  celular».
- **El manual** (sección 2) tiene ahora una tabla con las cuatro formas de
  abrir la app y una advertencia sobre `content://`. Antes indicaba abrir
  `index.html` en cualquier equipo.

### N2 · Crítico · No había forma de instalar la app en Android — **corregido**

**Corrección:** se creó el proyecto `movil/ladderlab/android`, con la misma
envoltura probada de la ronda CIL y del camal:
- un WebView que sirve `docs/ladder` desde `https://ladderlab.localhost/`;
- sin permiso de INTERNET;
- un puente nativo para guardar en Descargas;
- el selector de archivos del sistema para importar;
- los enlaces externos se entregan al navegador del teléfono;
- iconos adaptables en las cinco densidades.

El flujo `.github/workflows/apk-ladderlab.yml` hace, en orden:
1. comprueba que las descargas están al día;
2. corre las pruebas de Android;
3. compila;
4. verifica que el APK lleva exactamente la app publicada y no pide INTERNET;
5. lo publica.

A diferencia de la ronda, publica también desde las ramas, como
*prepublicación*, para poder instalarlo antes de fusionar.

### N3 · Mayor · El trabajador de servicio solo se registraba en `https:` — **corregido**

La condición `location.protocol === "https:"` dejaba fuera a
`http://localhost`, que también es un contexto seguro. Esto lo detectó la
prueba de instalación sin señal. Ahora la condición es
`window.isSecureContext`, excluye `file:` y excluye el APK, porque dentro del
APK no hay red que cachear y su `sw.js` no viaja.

### N4 · Mayor · Exportar no funcionaría dentro de un WebView — **corregido**

En un WebView, una descarga `blob:` no llega a ningún lado: ni siquiera
dispara el escuchador de descargas de Android. Dentro del APK, *Exportar
.json* entrega ahora los bytes a `PuenteLadder.guardar()`, que los escribe en
Descargas, y la app avisa con el nombre del archivo o con el motivo si falló.

### N5 · Mayor · Enlaces a carpetas (`manual/`) — **corregido**

El cargador de assets del APK sirve archivos, no carpetas, así que `manual/`
habría dado 404 dentro de la app. Todos los enlaces internos apuntan ahora a
`manual/index.html` y `../index.html`. Una prueba lo vigila.

### N6 · Menor · Pulsación larga en los pulsadores — **corregido**

Mantener pulsado un botón en Chrome Android puede abrir el menú contextual o
seleccionar texto, y eso corta la pulsación. Los pulsadores anulan ahora el
menú contextual y el *callout* táctil.

### N7 · Menor · Botón *atrás* del teléfono — **corregido**

`atras()` cierra primero el editor, luego el menú lateral, luego vuelve al
inicio. Desde el inicio, el APK pide dos toques para salir.

### N8 · Menor · Instalación desde Chrome sin aviso — **corregido**

Cuando Chrome ofrece instalar la app, en el inicio aparece **⤓ Instalar en
este equipo**. En Android, si la app no corre dentro del APK, aparece también
**Descargar APK para Android**.

### N9 · Observación · El manual en PDF no se había publicado — **corregido antes**

El `.gitignore` excluye todos los `*.pdf`. Se agregó una excepción para
`docs/ladder/descargas/` (commit `c5d0360`).

---

## 5. Evidencia

`tests/test_ladder_android.py`: **15 pruebas, 15 aprobadas**.

| Prueba | Qué demuestra |
|---|---|
| `test_archivo_unico_en_android_sin_nada_al_lado` | En un Pixel 7 emulado, el archivo único abre solo en una carpeta vacía, sin pedir ningún archivo vecino. Un toque arranca el motor, los 20 retos se corrigen bien y no hay desplazamiento horizontal |
| `test_la_carpeta_abierta_como_en_android_no_sirve` | Reproduce la causa del reporte |
| `test_dentro_del_apk` | Con un puente falso: no hay enlaces de descarga, no se registra el trabajador de servicio y no se pide `sw.js` ni `descargas/`. Exportar sale por el puente con un JSON válido. *Atrás* cierra el editor, vuelve al inicio y luego deja salir. El manual se sirve |
| `test_instalada_desde_chrome_abre_sin_senal` | El manifiesto declara `standalone` e iconos de 192 y 512. El trabajador de servicio toma el control y, sin red, la app y el HMI de sincronismo abren |
| `test_el_archivo_unico_esta_al_dia`, `..._no_depende_de_nada_al_lado` | La descarga coincide con lo que genera `docs/ladder` y no referencia archivos externos |
| `test_el_zip_trae_el_archivo_unico_y_lo_explica` | Contenido del zip, LEEME con instrucciones de Android y PDF válido |
| Proyecto Android (7 pruebas) | Toma `docs/ladder`, identidad propia, sin INTERNET, puente con el mismo nombre en los dos lados, `atras()`, enlaces a archivos, iconos en todas las densidades, flujo completo y ninguna llave en el repositorio |

Además se repitieron las pruebas anteriores, con el mismo resultado:
- 20 de 20 retos pasan con su solución;
- 11 de 11 errores típicos son rechazados;
- el editor funciona con teclado;
- las 41 pruebas existentes de los otros APK del repositorio siguen pasando.

**Compilación del APK** (ejecución 42387039829 de `apk-ladderlab.yml`, en verde): las
pruebas pasaron antes de envolver la app, el APK se compiló y no pide INTERNET. Su
contenido coincide archivo por archivo con `docs/ladder`, sin `sw.js` ni `descargas/`,
y se verificó también después de descargarlo. Se publicó como
[`ladderlab-v1`](https://github.com/nilthonnn/nefer/releases/tag/ladderlab-v1): 2 113 601 bytes,
SHA-256 `40deba451533a54d9ea6083cfcd1c333b42aef7843652f0a40f6411bf06e58ff`.

Las descargas son **reproducibles**: dos ejecuciones de `empaquetar-ladder.py`
dan el mismo `.zip` byte a byte. Por eso la integración puede exigir que estén
al día.

---

## 6. Lo que queda abierto

1. **Compilación del APK — cerrado.** `apk-ladderlab.yml` salió en verde y
   publicó `ladderlab-v1` con `ladderlab.apk` (sección 5).
2. **La dirección web** depende de fusionar el PR #47 y de que GitHub Pages
   publique `main`.
3. **Prueba en un teléfono físico.** Todo lo de arriba se probó en emulación
   de Chrome móvil. Falta instalar el APK en un equipo real y recorrer una
   lección, un reto y exportar e importar un programa.
4. **Firma provisional (confirmado).** El repositorio no tiene los secretos
   `ANDROID_*`, así que `ladderlab-v1` salió con firma provisional. Cada
   versión nueva exige desinstalar la anterior, y con ella se pierde el
   progreso; exporta antes tus programas. Para producción hay que cargar una
   llave propia en los secretos del repositorio:
   `herramientas/crear-llave-android.sh` la genera.
