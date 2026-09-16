# FixMate AI — asistente de diagnóstico para el técnico en campo

> Pon la experiencia del mejor ingeniero de fábrica en el bolsillo de cada
> mecánico de campo.

El técnico llega a la máquina, la máquina tira humo negro y pierde fuerza, y
la respuesta existe: está en una orden de trabajo que alguien cerró hace tres
meses en otra faena, y en la página 214 del manual del fabricante. Lo que no
existe es la forma de encontrarla desde el patio.

FixMate indexa el **historial de fallas propio**, los **manuales OEM** y las
**actas que nefer ya genera**, y responde a una falla descrita como la
describe un mecánico —no como la titula un capítulo— con la causa raíz que se
confirmó, el procedimiento que funcionó, las herramientas y los repuestos.

Todo lo esencial corre **sin red**: el índice es un archivo que se copia al
teléfono, el buscador y el redactor son de biblioteca estándar. Donde hay
señal y clave, un modelo de lenguaje redacta mejor sobre exactamente la misma
evidencia; donde no la hay —que es donde está la máquina— la respuesta sale
igual.

## En tres órdenes

```bash
# 1. Indexar lo que ya existe en la oficina, en el formato en que está
nefer fixmate -i indice.json indexar historial.xlsx manuales/ actas/

# 2. Preguntar como se pregunta en el patio (o dictarlo)
nefer fixmate -i indice.json consultar "humo negro y pierde fuerza en la subida" --dtc P0300
nefer fixmate -i indice.json consultar --audio nota-de-voz.m4a

# 3. Registrar lo que se resolvió, para que mañana lo encuentre otro
nefer fixmate -i indice.json cerrar --falla "..." --causa "..." --solucion "..."

# 4. O servirlo para la app de campo
FIXMATE_INDICE=indice.json nefer fixmate servir --puerto 8000
```

| Orden | Para qué |
|---|---|
| `indexar` | Historial, manuales y actas → índice. Incremental salvo `--completo` |
| `consultar` | Preguntar por una falla, escrita o dictada (`--audio`) |
| `predecir` | Qué le va a pasar a un equipo, o qué falla más en la flota |
| `cerrar` | Registrar la falla resuelta en el historial y en el índice |
| `estado` | Qué hay indexado y qué tan bien acierta el clasificador |
| `servir` | Levantar la API HTTP |
| `recibir` | Meter en el historial lo que el teléfono cerró en faena |
| `subir` | Subir el índice a PostgreSQL con pgvector |
| `sql` | Imprimir el esquema de PostgreSQL con pgvector |

## Verlo funcionando en un minuto

```bash
python3 herramientas/demo-fixmate.py
```

Arma en una carpeta temporal lo que hay en la oficina de un taller —el
historial en Excel con su membrete, un manual en Word con sus títulos, otro
en PDF y un acta de nefer— y corre encima **los mismos comandos** que correría
usted. Lo que sale en pantalla no es una imitación de la salida: es la salida.

| Demo | Qué enseña |
|---|---|
| `formatos` | PDF, Word y Excel leídos sin instalar nada |
| `indexar` | La primera pasada y la segunda, que no relee lo que no cambió |
| `consultar` | Una falla preguntada como la describe el mecánico |
| `aprendizaje` | Cuando el historial entero corrige a la búsqueda por palabras |
| `prediccion` | Ritmo de uso, próximo servicio y lo que le vuelve a pasar |
| `cierre` | Registrar la falla resuelta y encontrarla en el acto |
| `api` | Las respuestas HTTP que consume la app de campo |

```bash
python3 herramientas/demo-fixmate.py prediccion cierre   # solo esas dos
python3 herramientas/demo-fixmate.py --dir /tmp/taller   # deja el taller en pie
python3 herramientas/demo-fixmate.py servir              # levanta la API con ese corpus
```

La misma corrida, publicada para enseñarla desde el teléfono:
**<https://nilthonnn.github.io/nefer/fixmate/>**. La página vive en
`docs/fixmate/`, lleva su código QR y `tests/test_publicacion_fixmate.py`
comprueba que cada cifra que afirma la siga produciendo la demo.

Con `--dir` la carpeta queda para seguir probando con sus propias consultas.
No hace falta red ni clave de ningún servicio: es el camino local completo,
el mismo que corre en el patio. `tests/test_demo_fixmate.py` corre la demo
entera en cada cambio, porque una demo rota se descubre delante del cliente.

## Los tres insumos

| Insumo | Formato | Qué aporta |
|---|---|---|
| **Historial de fallas** | `.xlsx`, `.json` | La causa raíz *confirmada* y la solución que funcionó. Es lo que ningún manual trae |
| **Manuales de taller** | `.pdf`, `.docx`, `.xlsx`, `.md`, `.txt` | El procedimiento del fabricante, los pares de apriete y los códigos de falla |
| **Actas de nefer** | `.json` o `.xlsx` | Los componentes `OBS` y `D` y los consumibles que no retornaron, con la observación escrita a mano en el patio |

Los formatos de hace veinte años —`.doc`, `.xls`, `.odt`, `.rtf`— se convierten
al vuelo si hay LibreOffice instalado.

Una carpeta se recorre entera; los archivos que no se saben leer se avisan y
detienen la indexación, en vez de dejar un índice al que le falta la mitad del
historial sin que nadie lo note. Al indexar una carpeta que ya contiene el
propio archivo de índice, ese se salta solo.

### Qué se hace con cada formato

| Formato | Cómo se lee |
|---|---|
| **PDF** | `pdftotext` de poppler si está; si no, `pypdf`; si no, un lector de biblioteca estándar que descomprime los flujos y resuelve las tablas `ToUnicode` de las fuentes incrustadas. Un PDF **escaneado** no tiene capa de texto y ninguno de los tres saca nada: se dice, y se pide pasarlo por OCR, en vez de indexar un manual vacío |
| **Word** | Se abre el `.docx` como el zip que es y se lee su XML, sin dependencias. Los **títulos de Word salen como títulos Markdown**, así que el troceado por secciones funciona igual que con un `.md` |
| **Excel** | Una sección por hoja y una línea por fila. Si el libro resulta ser un acta de nefer o un historial de fallas, se trata como tal |

### El historial de fallas, como está en el taller

Está en un Excel con una fila por orden de trabajo, y sus columnas no se
llaman como el esquema: se llaman `N° OT`, `Falla reportada`, `Causa raíz`,
`Trabajo realizado`. Eso es lo que se reconoce, sin renombrar nada y sin que
el encabezado tenga que estar en la primera fila —arriba casi siempre hay un
membrete y dos filas en blanco—.

| Campo | Columnas que se reconocen |
|---|---|
| `codigo_ot` | OT, N° OT, Orden, Orden de trabajo, OS |
| `fecha` | Fecha, Fecha de atención, Fecha de cierre |
| `codigo_equipo` | Equipo, Código de equipo, Unidad, Máquina, Flota, Placa |
| `codigos_dtc` | DTC, Código de falla, SPN, FMI, Código de error |
| `resumen_falla` | Falla, Síntoma, Problema, Falla reportada, Descripción |
| `causa_raiz` | Causa, Causa raíz, Diagnóstico, Origen |
| `solucion_aplicada` | Solución, Trabajo realizado, Acción correctiva, Reparación |
| `pasos`, `herramientas`, `repuestos` | Procedimiento, Herramientas, Repuestos, Materiales |
| `horometro`, `horas_hombre` | Horómetro, Km, HH, Horas |

Las celdas con varias cosas dentro (`Filtro P533781; Filtro P533782`) se
separan solas. Las columnas que no se reconocen **no se tiran**: el técnico
que atendió, el sistema afectado o el costo se indexan igual, porque por ahí
también se busca. Si ninguna columna se parece a una falla o a una causa, se
dice cuáles había en vez de indexar filas vacías.

En JSON, el mismo historial se ve así:

```json
{
  "informes": [
    {
      "codigo_ot": "OT-2026-0412",
      "fecha": "2026-03-14",
      "codigo_equipo": "GE074-01",
      "categoria": "grupo_electrogeno",
      "codigos_dtc": ["P0300"],
      "resumen_falla": "Humo negro y pérdida de potencia sobre el 60% de carga a 4100 msnm.",
      "causa_raiz": "Filtro de aire colmatado por polvo de mina.",
      "solucion_aplicada": "Se reemplazó el elemento primario y secundario.",
      "pasos": ["Bloquear el arranque.", "Revisar el indicador de restricción."],
      "herramientas": ["Llave de 13 mm"],
      "repuestos": ["Filtro de aire primario P533781"],
      "horas_hombre": 1.5
    }
  ]
}
```

Solo `resumen_falla` hace falta para que el informe entre; todo lo demás
mejora lo que se puede responder. Los códigos de falla se guardan en forma
canónica —`SPN 157`, `spn-157` y `SPN157` son el mismo código— y los que
aparezcan escritos dentro del relato se detectan solos.

Hay un corpus de ejemplo, con datos ficticios, en
[`ejemplos/fixmate/`](../ejemplos/fixmate/).

## Cómo busca

Dos búsquedas sumadas, porque por separado cada una falla donde la otra
acierta:

- **BM25** encuentra lo que se llama igual: un código de falla, un número de
  parte, el nombre de un componente. `P533781` no se parece a nada.
- **Coseno de vectores** encuentra lo que se dice distinto: «fugas
  hidráulicas» contra «fuga de aceite hidráulico», «inyectores» contra
  «inyector». Casi ningún informe está escrito con las palabras con que se
  dicta la consulta.

El vector por defecto no llama a ningún servicio: es un hash de las palabras y
de sus trozos de cuatro caracteres, que es lo que le da la tolerancia a
plurales y variantes. Con `--embebedor openai` se usan embeddings del
servicio, mejores y con dependencia de red. **Los dos no se mezclan**: el
índice recuerda con cuál se construyó y se niega a buscar con otro, porque
hacerlo no da error, da resultados sin sentido.

### Filtrar y preferir no es lo mismo

| | Efecto |
|---|---|
| `--dtc P0300` | **Filtra**: un código está o no está. Si nada lo cita, se responde por la descripción avisando de que el filtro no se pudo aplicar |
| `--equipo`, `--categoria` | **Prefieren**: suben lo que coincide, sin descartar lo demás. Un manual no dice de qué equipo de la flota habla, y descartarlo por eso deja al técnico sin el procedimiento |

## Reindexar solo lo que cambió

```bash
nefer fixmate -i indice.json indexar manuales/ historial.xlsx     # incremental
nefer fixmate -i indice.json indexar manuales/ --completo         # desde cero
```

Un manual de cuatrocientas páginas no cambia porque se haya añadido una orden
de trabajo al historial. Cada archivo queda anotado en el índice con la huella
de su contenido, y en la siguiente pasada solo se vuelve a leer lo que
cambió. Por contenido y no por fecha: copiar la carpeta compartida a otra
máquina cambia todas las fechas y ninguna coma.

Lo que se borró del disco se quita del índice —un manual retirado no debe
seguir respondiendo—, y solo dentro de las rutas que se acaban de recorrer:
indexar la carpeta de manuales nunca borra el historial.

```
  nuevo: manuales/hidraulica.pdf
  actualizado: historial.xlsx
  sin cambios: 23 archivos

Indice escrito: indice.json (1841 fragmentos de 25 archivos, embebedor local-fnv-256)
```

## La consulta dictada

En campo nadie escribe: el técnico tiene guantes, las manos sucias y la
máquina al lado haciendo ruido. Hay dos caminos, y fallan en sitios distintos.

**El dictado del propio teléfono** no necesita nada de aquí: el teclado de
Android y de iPhone transcribe al campo de texto, y la app de campo usa el
reconocimiento del navegador. Funciona sin cuenta de nadie y, en los teléfonos
recientes, también sin señal.

**La nota de voz que ya quedó grabada** —la que el técnico mandó por WhatsApp
desde el socavón, donde no había señal para nada más— se transcribe con el
servicio, cuando hay red:

```bash
nefer fixmate -i indice.json consultar --audio nota-de-voz.m4a
```

```http
POST /search-report-rag-audio     (multipart: audio=@nota.m4a)
```

Dos detalles que cambian el resultado. Al servicio se le pasan **los códigos
de la propia flota** sacados del índice: sin eso, «ge cero setenta y cuatro
guion cero uno» se transcribe como suene; con la lista delante, sale
`GE074-01`. Y **lo transcrito se devuelve siempre**, en la respuesta y en la
pantalla, antes del diagnóstico: una transcripción equivocada que nadie ve es
el diagnóstico de otra falla.

## Lo que aprende del historial completo

La búsqueda contesta «esta orden de trabajo se parece a lo que me cuentas».
Eso no es lo mismo que «de las veces que alguien escribió algo parecido, el
54% terminó en el filtro de aire». Son dos preguntas y las dos hacen falta: la
primera trae el procedimiento, la segunda dice por dónde empezar.

Lo segundo lo contesta un clasificador bayesiano ingenuo entrenado sobre las
causas raíz confirmadas de la propia flota. Es de biblioteca estándar, se
entrena en milisegundos cada vez que se carga el índice y no hay nada que
descargar ni que servir.

**Agrupa la misma causa escrita de tres formas.** «Filtro de aire colmatado» y
«filtro de aire colmatado por polvo de mina» son una causa, no dos; separarlas
parte en dos la evidencia de las dos. Se agrupa por cómo empieza la frase
—que en español es donde va el sujeto de la avería— y por las palabras que
comparten.

**Publica lo que midió.** Cada respuesta trae el acierto del clasificador,
medido dejando uno fuera, junto a la línea base de acertar siempre la causa
más común:

```
LO QUE DICE EL HISTORIAL COMPLETO
     54%  Filtro de aire colmatado por polvo de mina. (3 casos)
     37%  Inyector con retorno excesivo por aguja desgastada. (3 casos)
      6%  Sello del vástago cortado por rebaba en el cromado. (3 casos)
         (el clasificador acierta el 100% sobre 14 casos; la causa más común sola daría 21%)
```

Un 62% suena bien hasta que se ve que contestar siempre «filtro de aire»
acierta el 58%. Por eso los dos números van juntos, siempre.

**Y corrige a la búsqueda cuando hace falta.** «Humo negro y pierde fuerza» se
parece, palabra por palabra, al informe de un sello de vástago que también
hacía perder fuerza. Si el historial entero apunta a otra causa y ninguno de
los antecedentes recuperados es de esa causa, el motor **vuelve al índice** a
buscar el que falta, lo añade a la evidencia y lo dice. No se inventa nada: se
elige mejor entre lo que ya hay.

**Pero la evidencia fuerte le gana a la estadística.** Cuando la búsqueda ya
trajo un antecedente que encaja de sobra, ese manda aunque el historial viejo
apunte a otro lado. Es el caso de la falla nueva: el informe que se registró
ayer describe exactamente esto, y un clasificador entrenado con las averías
de siempre no puede saberlo todavía. Si la estadística pudiera sobreescribir
eso, el asistente no aprendería nunca nada nuevo.

**Y se calla cuando no hay de dónde.** Con menos de doce casos con causa
confirmada, o con una sola causa en todo el historial, se declara sin entrenar
y no devuelve ningún porcentaje. Un porcentaje sobre cuatro informes es peor
que ninguno, porque parece medido.

## Diagnóstico predictivo

No hay sensores en estas máquinas. Hay dos cosas: la fecha de cada falla y el
horómetro que el técnico anota en cada acta. Con eso se contestan tres
preguntas, y ninguna más:

```bash
nefer fixmate -i indice.json predecir GE074-01
nefer fixmate -i indice.json predecir --flota
```

```
EQUIPO GE074-01 · 7 registros fechados

USO
  8.4 h/día (3 lecturas en 150 días); horómetro 2460.0 al 2026-06-09

PRÓXIMO SERVICIO
  3500 h: faltan 216.8 h (~26 días, 2026-10-11)

MTBF
  44 días entre fallas, en promedio

LO QUE LE VUELVE A PASAR
  VENCIDA · Filtro de aire colmatado por polvo de mina.
      3 casos · cada ~66 días · última 2026-06-02 (hace 105 días)

REPUESTOS QUE CONVIENE TENER
  · Filtro de aire primario P533781
```

- **A qué ritmo se usa.** Horas por día, de la pendiente entre dos lecturas de
  horómetro con fecha. De ahí sale el próximo intervalo de mantenimiento **en
  fecha**: «faltan 118 horas» no se puede poner en un calendario; «llega el 11
  de octubre» sí.
- **Qué le vuelve a pasar.** Cada causa que apareció dos veces o más tiene un
  intervalo medio entre apariciones. Si desde la última pasó más tiempo que
  ese intervalo, la falla está **vencida** y se dice primero.
- **Qué repuestos tener.** Los que consumieron las causas que reinciden.

Todo lleva el número de casos en que se apoya, y nada se calcula con uno solo:
con una sola aparición no hay intervalo, hay una fecha. Sin dos lecturas de
horómetro no hay ritmo, y se dice en vez de estimarlo. La diferencia importa
cuando alguien va a comprar un repuesto por lo que diga esto.

## Cerrar el círculo

Un asistente que solo lee envejece. La falla que el técnico acaba de resolver
—sobre todo la que resolvió *sin* que el índice la tuviera— es exactamente el
dato que le faltaba al próximo. Si registrarla cuesta abrir un Excel en la
oficina tres días después, no se registra.

```bash
nefer fixmate -i indice.json cerrar \
  --falla "El mástil no sube y la bomba manual hace vacío" \
  --causa "Nivel de aceite bajo por fuga en el acople rápido" \
  --solucion "Se cambió el acople, se rellenó y se purgó" \
  --equipo TI09-04 --repuesto "Acople rápido 1/4\""
```

```http
POST /informes
```

El informe se añade al historial en disco **y al índice que ya está cargado**:
la siguiente consulta —la del compañero que está a cuarenta kilómetros— ya lo
encuentra, sin reindexar. El código de orden sale correlativo del año si no se
da uno.

Lo que no se acepta: un informe sin causa ni solución, que no es un
antecedente sino una queja; y una orden de trabajo repetida, que haría contar
dos veces lo que pasó una.

## Los dos redactores

**Extractivo** (por defecto, sin red). Recorta y ordena lo recuperado. Es
determinista y no puede inventarse un torque porque solo sabe copiar. Los
pasos salen de **un solo** antecedente —encadenar el procedimiento de dos
causas distintas produce una lista que se lee como un solo trabajo y no lo
es—; los demás quedan citados en la evidencia, con su propia causa.

**Con modelo de lenguaje** (`--llm`, necesita `OPENAI_API_KEY`). Redacta
mejor, junta varios informes en una explicación y ordena los pasos como los
diría un instructor. Trabaja sobre la misma evidencia recuperada y bajo un
prompt que le prohíbe estimar valores. Si el modelo no contesta, devuelve algo
ilegible o se queda sin cuota, **la respuesta sale igual** por el camino
extractivo, con un aviso; no se le devuelve un error al técnico que está
parado al lado de la máquina.

## Las tres reglas que el motor hace cumplir

Son las mismas de un acta firmada, por el mismo motivo: lo que imprime una
herramienta se lee como un dato.

- **Sin antecedente no hay diagnóstico.** Si nada en el índice respalda la
  consulta, se responde que no hay antecedentes —y que registre el caso al
  cerrarlo, para que el próximo técnico sí los tenga—. Un diagnóstico sin
  evidencia es una conjetura con formato de informe.
- **Ningún par de apriete se estima.** Los torques se copian literales de la
  fuente, con su unidad y su rango tal como están escritos; nunca se
  convierten ni se redondean. Un «torquímetro de 5 a 60 N·m» es una
  herramienta, no un apriete, y no se ofrece como tal. Cada respuesta con
  torques lleva el aviso de contrastarlos con el manual OEM.
- **Todo se cita.** Cada respuesta trae la orden de trabajo o la sección de
  manual de donde salió, con su porcentaje de parecido y un extracto. Una
  evidencia floja se declara floja: la confianza baja se rotula como pista, no
  como diagnóstico.

## En el teléfono, sin señal

La oficina indexa; el teléfono busca. Es el reparto natural: leer Excel, Word
y PDF pide una computadora, y buscar es aritmética sobre un archivo.

La app de campo trae una pestaña **Diagnóstico** con el mismo motor escrito en
JavaScript: se le carga el `indice.json` una vez —el que genera
`nefer fixmate indexar`— y queda guardado en el teléfono, así que a partir de
ahí responde sin red, en el patio y en el socavón.

| | |
|---|---|
| **Tamaño** | 4 KB por fragmento, 0,5 KB comprimido. Un taller de 2000 fragmentos son 7,9 MB, 1,0 MB comprimidos |
| **Cómo llega** | Se elige el archivo desde la app, o se sirve un `indice.json` junto a ella y lo toma solo |
| **Dónde queda** | En IndexedDB del propio teléfono. No sale de ahí |
| **Dictado** | Donde el navegador lo trae, el botón dicta y escribe la consulta en el campo, a la vista, antes de buscar |

**Los dos motores tienen que dar lo mismo.** Dos implementaciones de la misma
búsqueda se separan solas, y nadie lo nota hasta que el teléfono contesta otra
cosa que la computadora. Por eso el hash es FNV-1a —dos operaciones enteras,
idéntico en los dos lenguajes— y por eso `tests/test_fixmate_cruce.py` corre
ocho consultas en los dos motores y compara el ranking con sus puntajes a
cuatro decimales, la causa, los pasos, los torques y las probabilidades del
clasificador. El JavaScript que prueba lo saca de la app publicada, no de una
copia.

Lo que el teléfono no hace: medir el acierto del clasificador —dejar uno fuera
es cuadrático— así que esa medición viaja dentro del índice, calculada en la
oficina, y se enseña al lado de cada porcentaje.

### Y el círculo se cierra desde el patio

El técnico registra en la app lo que resultó —incluso, y sobre todo, cuando la
consulta no encontró nada—. Ese informe queda buscable **en el acto y sin
señal** en ese teléfono, y se suma a una cuenta de pendientes. Cuando hay
señal, un botón los manda todos en un archivo y la oficina los mete al
historial:

```bash
nefer fixmate recibir informes-de-campo-2026-09-16.json
```

Reenviar el mismo archivo no duplica nada: lo que ya está se cuenta como
repetido. Es lo que va a pasar —el técnico manda, no sabe si llegó, vuelve a
mandar— y tratarlo como error obligaría a alguien a decidir cuál envío valía.
Un archivo por WhatsApp es toda la sincronización que un taller necesita, y no
obliga a montar un servidor que alguien tendría que mantener.

El informe que arma el teléfono es **idéntico** al que armaría la oficina con
los mismos datos —mismo texto, mismos metadatos, mismo vector—, y eso también
lo comprueba la prueba cruzada: si no lo fuera, el índice cambiaría al
sincronizar justo cuando nadie está mirando.

## La API

```bash
pip install -e ".[fixmate-api]"
FIXMATE_INDICE=indice.json nefer fixmate servir --host 0.0.0.0 --puerto 8000
```

| Ruta | Qué hace |
|---|---|
| `POST /search-report-rag` | El diagnóstico: consulta → evidencia → procedimiento |
| `POST /search-report-rag-audio` | Lo mismo, desde una nota de voz (multipart) |
| `POST /informes` | Registrar una falla resuelta; queda buscable en el acto |
| `GET /prediccion/{equipo}` | Ritmo de uso, próximo servicio y lo que le vuelve a pasar |
| `GET /prediccion` | Qué falla más en toda la flota |
| `GET /salud` | Índice, redactor, clasificador y su acierto medido |
| `GET /docs` | La documentación interactiva que genera FastAPI |

```bash
curl -s localhost:8000/search-report-rag -H 'content-type: application/json' -d '{
  "consulta_texto": "humo negro y pérdida de potencia en pendiente a 4000 msnm",
  "codigo_dtc": "P0300",
  "codigo_equipo": "GE074-01",
  "limite_resultados": 3
}'
```

Los códigos de estado dicen cosas distintas y por eso no se confunden:

| Código | Significa |
|---|---|
| `200` | Hay diagnóstico, con su evidencia |
| `404` | No hay antecedentes de esa falla. **No** es un error del servidor: es una respuesta, y le dice al técnico que siga por su cuenta y registre el caso |
| `422` | La consulta no cumple el esquema (vacía, o más de 10 resultados) |
| `500` | Falló el servidor. El detalle se registra completo y **no** viaja al cliente: trae rutas y a veces credenciales |
| `503` | No hay índice cargado. La API arranca igual para poder decirlo |

Y en las rutas nuevas: `201` cuando el informe queda registrado, `400`
cuando el informe no vale como antecedente (sin causa, sin solución, o con
una orden repetida) y `422` cuando el audio llegó pero no se pudo convertir
en consulta.

## PostgreSQL con pgvector

Cuando el historial deja de caber en un archivo —varios talleres escribiendo
a la vez, una flota entera— el índice se muda a una base y la búsqueda se hace
en SQL. **La interfaz es la misma**: el motor, el clasificador, la predicción y
la API no distinguen cuál tienen delante.

```bash
pip install -e ".[fixmate-pg]"
export FIXMATE_PG_DSN="host=servidor user=nefer dbname=taller"

nefer fixmate indexar historial.xlsx manuales/      # la oficina lee documentos
nefer fixmate subir                                  # y sube lo ya leído
nefer fixmate consultar "humo negro y pierde fuerza" --pg
nefer fixmate servir --pg
```

La base **no lee documentos**: guarda lo que ya se leyó. Indexar sigue siendo
cosa de la máquina que tiene los Excel y los PDF delante, y `subir` es lo que
se corre después de cada indexación.

### La búsqueda sigue siendo híbrida

El vector lo pone pgvector y las palabras exactas las pone la búsqueda de texto
del propio PostgreSQL, con diccionario español, en un solo recorrido:

```sql
ts_rank_cd(to_tsvector('spanish', texto),
           replace(plainto_tsquery('spanish', $1)::text, ' & ', ' | ')::tsquery)
```

Ese `replace` no es un adorno. `plainto_tsquery` une las palabras con **y**, y
el técnico describe la falla con las suyas: «gotea aceite por el cilindro»
contra «fuga de aceite en el cilindro» exige «gotea», que no está, y el ranking
entero da cero. Con **o**, cada palabra que sí coincide suma.

No es el mismo BM25 que el motor local —son dos implementaciones de la misma
idea— así que los puntajes no se comparan entre los dos caminos. Lo que sí
coincide, y está probado consulta por consulta, es **a quién señalan**.

### Por qué el esquema no trae índice vectorial

Se indexan los metadatos y el texto, no el vector, y es a propósito.

La consulta híbrida ordena por una **mezcla** de dos puntajes, y por esa
expresión no hay índice que sirva: PostgreSQL recorre la tabla de todos modos.
El único camino que usaría un índice aproximado es la búsqueda sin la mitad
léxica, y ahí `ivfflat` hace daño: reparte las filas en listas **en el momento
de crearse**, y el esquema se crea antes de la primera carga. Listas vacías,
cero filas devueltas. Cero, no menos: el técnico pregunta y no sale nada, sin
un error que lo delate.

Con el historial de un taller —miles de filas, no millones— el recorrido
completo cuesta milisegundos y acierta siempre. Si algún día la tabla crece
hasta que no alcance, el índice se agrega **sobre la tabla ya cargada**:

```sql
CREATE INDEX ON fixmate_fragmentos USING hnsw (embedding vector_cosine_ops);
```

`hnsw` se construye fila por fila y no depende de que la tabla esté llena, pero
sigue siendo aproximado: antes de dejarlo puesto hay que comparar lo que
devuelve contra el recorrido exacto, porque **lo que se pierde no se ve**.

### Lo que hay que saber antes de mudarse

| | |
|---|---|
| **Cuándo** | Cuando el archivo deje de alcanzar. Con miles de fragmentos, el archivo va sobrado; esto es para decenas de miles o para varias sedes escribiendo |
| **Recorre la tabla entera** | Y está bien: con el historial de un taller cuesta milisegundos. Afinar eso con búsqueda aproximada en dos pasos haría que el resultado dependa de que la fila buena caiga en el primer lote |
| **El teléfono no cambia** | Sigue llevando su archivo. La base es para la oficina y para quien tenga señal |
| **Sus propias tablas** | No hace falta copiar nada: basta una vista llamada `fixmate_fragmentos` con esas columnas y el `JOIN` que corresponda |

```bash
nefer fixmate sql | psql "$FIXMATE_PG_DSN"     # crea tabla e índices
```

La conexión se lee de `FIXMATE_PG_DSN`, o de las `PGHOST`/`PGUSER`/`PGPASSWORD`
de cualquier cliente de PostgreSQL. **Nunca del código**: una contraseña
escrita en un `.py` es una contraseña publicada el día que el repositorio se
comparte.

Y se prueba contra una base de verdad, no contra un simulacro:
`tests/test_fixmate_pg.py` levanta el esquema, sube el corpus de ejemplo y
comprueba que la base y el archivo señalen el mismo antecedente. En CI hay un
PostgreSQL con pgvector y `FIXMATE_PG_EXIGIR` convierte el salto en fallo,
porque una prueba que se salta sola no es una prueba.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `FIXMATE_INDICE` | Ruta del índice que usan `nefer fixmate` y la API |
| `FIXMATE_HISTORIAL` | Historial donde se anotan las fallas resueltas (`cerrar`, `POST /informes`) |
| `OPENAI_API_KEY` | Habilita el redactor con modelo, el embebedor de OpenAI y la transcripción de audio. Sin ella, todo lo demás sigue funcionando en local |
| `FIXMATE_PG_DSN` | Cadena de conexión de PostgreSQL |
| `FIXMATE_PG_TABLA` | Tabla o vista de fragmentos (por defecto, `fixmate_fragmentos`). El esquema se crea con ese nombre, no con el fijo. Sólo letras, números y guión bajo: el nombre se pega al SQL porque PostgreSQL no lo admite como parámetro |
| `FIXMATE_ALMACEN` | `pg` hace que la API busque en PostgreSQL en vez de en el archivo |

## Desde Python

```python
from nefer.fixmate import Consulta, Motor, indexar

indice = indexar(["historial.json", "manuales/", "actas/"])
indice.guardar("indice.json")

motor = Motor(indice)
diagnostico = motor.consultar(Consulta(
    "humo negro y pérdida de potencia en pendiente", codigo_dtc="P0300"))

print(diagnostico.causa_raiz_mas_probable)
for paso in diagnostico.pasos_recomendados:
    print("-", paso)

# Lo que dice el historial entero, con su acierto medido
print(diagnostico.causas_probables, diagnostico.precision_medida)

# Y al terminar el trabajo, cerrar el círculo
from nefer.fixmate import cierre, prediccion

cierre.registrar({"resumen_falla": "...", "causa_raiz": "...",
                  "solucion_aplicada": "..."}, "historial.json", indice)
print(prediccion.pronostico(indice, "GE074-01").a_dict())
```

## Qué falta

Dicho para que nadie lo descubra en campo:

- **La foto todavía no diagnostica.** El técnico puede fotografiar una fuga o
  la pantalla de un código, y la foto entra al acta, pero el motor consulta
  por texto y por voz. Reconocer la avería *en la imagen* pide un modelo
  multimodal, y eso pide red: no puede ser el camino por defecto de una
  herramienta que tiene que responder en el socavón.
- **Un PDF escaneado sigue necesitando OCR.** Se detecta y se dice —no se
  indexa vacío—, pero el OCR hay que correrlo aparte (`ocrmypdf entrada.pdf
  salida.pdf`). Los diagramas esquemáticos no se indexan como imagen.
- **Los `.doc` y `.xls` de hace veinte años necesitan LibreOffice** instalado
  para convertirse al vuelo. Sin él se dice cuál es la alternativa, no se
  falla en silencio.
- **El clasificador es de palabras, no de física.** Con menos de doce casos
  con causa confirmada no opina. No entiende el motor: cuenta lo que el
  taller escribió, y por eso publica su acierto medido al lado de cada
  porcentaje.
- **La predicción no tiene telemetría.** Sale del horómetro anotado a mano y
  de las fechas de las órdenes. Con un equipo que envía datos de verdad
  —presiones, temperaturas, horas por régimen— se podría anticipar mucho
  antes; hoy se anticipa con lo que hay.

## Estructura

| Módulo | Responsabilidad |
|---|---|
| `nefer/fixmate/texto.py` | Normalización, códigos de falla, torques y troceado |
| `nefer/fixmate/documentos.py` | PDF, Word, Excel y texto plano → texto con secciones |
| `nefer/fixmate/pdf_texto.py` | El lector de PDF: poppler, pypdf y uno propio de biblioteca estándar |
| `nefer/fixmate/embeddings.py` | Vectores: el local sin red y el de OpenAI |
| `nefer/fixmate/indice.py` | Búsqueda híbrida, filtros, firmas de archivo y persistencia |
| `nefer/fixmate/ingesta.py` | Historiales, manuales y actas → fragmentos |
| `nefer/fixmate/aprendizaje.py` | Clasificador de causas y su medición |
| `nefer/fixmate/prediccion.py` | Ritmo de uso, próximo servicio y reincidencias |
| `nefer/fixmate/transcripcion.py` | La nota de voz → consulta |
| `nefer/fixmate/cierre.py` | La falla resuelta → antecedente |
| `nefer/fixmate/motor.py` | Consulta → evidencia → diagnóstico |
| `nefer/fixmate/almacen_pg.py` | El mismo índice sobre PostgreSQL con pgvector |
| `nefer/fixmate/api.py` | La API HTTP |
| `nefer/fixmate/cli.py` | `nefer fixmate …` |
