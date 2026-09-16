# nefer — actas de despacho y recepción de maquinaria

Automatiza el **reporte fotográfico de despacho y recepción** de equipos:
grupos electrógenos, torres de iluminación, plataformas de elevación y
maquinaria de construcción y minería.

La herramienta es independiente de cualquier organización. El nombre de la
empresa, el logo y el bloque de control documental (código, versión, fecha del
formato) se declaran en el manifiesto; el paquete no trae ninguno por defecto.

De un manifiesto JSON y una carpeta de fotos salen, en un solo paso, el Excel
del acta, el PDF firmable, la hoja de consumibles y las dos guías (operador y
cliente).

```
manifiesto.json  +  fotos/  ──►  acta.xlsx  ──►  acta.pdf
                                   │
                                   ├─ REPORTE         rejilla fotográfica + observaciones
                                   ├─ INSPECCIÓN      estado por componente (OK / OBS / D)
                                   ├─ CONSUMIBLES     niveles de despacho y recepción
                                   ├─ GUÍA OPERADOR   procedimiento interno
                                   └─ GUÍA CLIENTE    condiciones de uso y devolución
```

La geometría se derivó de actas reales llenadas a mano: el Excel generado es
indistinguible del que hoy se llena a mano, misma rejilla, mismos rótulos y
misma franja amarilla de recuperación.

## Instalación

```bash
pip install -e .
```

Para exportar a PDF se necesita LibreOffice Calc:

```bash
sudo apt-get install libreoffice-calc     # Debian / Ubuntu
brew install --cask libreoffice           # macOS
```

## Uso

### Generar un acta completa

```bash
python -m nefer construir acta.json -o salidas/acta.xlsx --pdf
```

`--pdf` acepta una ruta opcional. `--sin-guias` omite las dos hojas de guía.

### Validar antes de generar

```bash
python -m nefer validar acta.json
```

Devuelve la lista completa de errores en un solo pase: campos faltantes, fechas
mal formadas, estados `OBS`/`D` sin observación, `foto_id` duplicados, resúmenes
de más de 20 palabras y rutas de imagen inexistentes. Comprueba el disco por
defecto, igual que `construir`; `--sin-verificar-fotos` lo omite cuando aún no
se han descargado las fotos de la cámara.

### Digitalizar un acta antigua

```bash
python -m nefer extraer acta-2025.xlsx -o acta-2025.json --fotos fotos-acta-2025
```

Lee un reporte llenado a mano y devuelve el manifiesto equivalente, con las
fotos volcadas a disco y ya asociadas a su rótulo. Recupera también las
fotografías pegadas desde Word, que quedan incrustadas como metarchivos EMF y
que ninguna librería de Python lee directamente (ver `nefer/emf.py`).

### Diagnosticar una falla en campo

```bash
python -m nefer fixmate -i indice.json indexar historial.xlsx manuales/ actas/
python -m nefer fixmate -i indice.json consultar "humo negro y pierde fuerza en la subida" --dtc P0300
```

**FixMate AI** indexa el historial de fallas propio, los manuales del
fabricante —en PDF, Word o Excel, como estén— y las actas que este mismo
paquete genera, y responde a una falla descrita como la describe un mecánico
—no como la titula un capítulo— con la causa raíz que se confirmó, el
procedimiento que funcionó y las herramientas y repuestos que hicieron falta.

Funciona sin red: el índice es un archivo que se copia al teléfono y el
buscador no llama a ningún servicio. Con `OPENAI_API_KEY` en el entorno, un
modelo de lenguaje redacta mejor sobre la misma evidencia y se puede dictar
la consulta por audio; si el servicio no contesta, la respuesta sale igual
por el camino local.

Además de buscar, **aprende del historial entero**: un clasificador
bayesiano entrenado con las causas raíz confirmadas dice a qué termina
pareciéndose una descripción así, publica su acierto medido al lado del
porcentaje y corrige a la búsqueda cuando esta se fue por un parecido de
palabras. Y **predice con lo que hay**: del horómetro anotado a mano y de las
fechas de las órdenes salen el ritmo de uso, el próximo servicio en fecha y
las causas que reinciden y ya están vencidas.

```bash
python -m nefer fixmate -i indice.json predecir GE074-01
python -m nefer fixmate -i indice.json cerrar --falla "..." --causa "..." --solucion "..."
```

`cerrar` cierra el círculo: la falla resuelta hoy entra al historial y al
índice en el acto, y la encuentra el compañero que pregunte mañana.

Y **el mismo motor va en la app de campo**, en la pestaña *Diagnóstico*: se le
carga el índice una vez y responde en el teléfono sin señal, que es donde está
la máquina. Está escrito dos veces —Python en la oficina, JavaScript en el
teléfono— y `tests/test_fixmate_cruce.py` corre las mismas consultas en los
dos motores y falla si un ranking se separa.

Tres reglas, las mismas de un acta y por el mismo motivo —lo que imprime una
herramienta se lee como un dato—:

- Sin antecedente en el índice no hay diagnóstico. Se dice que no lo hay.
- Ningún par de apriete se estima: se copia literal de la fuente o no se da.
- Cada respuesta cita la orden de trabajo o la sección de manual de la que
  salió, y una evidencia floja se rotula como pista, no como diagnóstico.
  Con menos de doce casos confirmados, el clasificador no opina.

Para verlo funcionando sin preparar nada:

```bash
python3 herramientas/demo-fixmate.py
```

Arma un taller de mentira —historial en Excel, manuales en Word y PDF, un
acta— y corre encima los comandos de verdad, uno por uno, explicando qué
enseña cada paso. Esa misma corrida, para enseñarla desde el teléfono, está
publicada en **<https://nilthonnn.github.io/nefer/fixmate/>** (la página vive
en `docs/fixmate/` y `tests/test_publicacion_fixmate.py` falla si se queda
atrás de la demo).

Todo el detalle —los formatos que lee, la API HTTP, la consulta dictada,
PostgreSQL con pgvector y lo que falta— está en
**[docs/FIXMATE.md](docs/FIXMATE.md)**.

### Otros comandos

```bash
python -m nefer plantilla -o acta-nueva.json    # manifiesto en blanco
python -m nefer guias -o docs/                  # guías en Markdown
python -m nefer pdf acta.xlsx                   # convertir un Excel ya generado
```

## Documentación

| | |
|---|---|
| **[docs/MANUAL-OPERACION.md](docs/MANUAL-OPERACION.md)** | Cómo levantar un acta, de la primera prueba en patio al uso diario |
| **[docs/MANUAL-APP.md](docs/MANUAL-APP.md)** | La aplicación de campo pantalla por pantalla y botón por botón |
| **[docs/FIXMATE.md](docs/FIXMATE.md)** | FixMate AI: el asistente de diagnóstico sobre el historial de fallas y los manuales OEM |
| **[docs/app/](docs/app/)** | Aplicación de campo: despacho y recepción desde el celular, sin conexión. Cámara, galería, carpeta, arrastre y pegado; genera el PDF y el Excel en el propio teléfono |
| **[docs/AUDITORIA-FORMATO.md](docs/AUDITORIA-FORMATO.md)** | Qué se midió del formato real, qué no cuadraba en el entregable y cómo se corrigió |
| **[docs/AUDITORIA-CALIDAD.md](docs/AUDITORIA-CALIDAD.md)** | Revisión de la app guiada por ISO/IEC 25010: arranque, seguridad, código muerto y espacio |
| **[docs/ESQUEMA-JSON.md](docs/ESQUEMA-JSON.md)** | Todos los campos del manifiesto |
| **[docs/evaluacion-madurez.html](docs/evaluacion-madurez.html)** | Dónde está este proceso frente al estado del arte, y qué falta |
| **[docs/GUIA-OPERADOR.md](docs/GUIA-OPERADOR.md)** | Procedimiento interno, también incluido en cada acta |
| **[docs/GUIA-CLIENTE.md](docs/GUIA-CLIENTE.md)** | Condiciones de uso y devolución para el cliente |

## El manifiesto

Documentado en **[docs/ESQUEMA-JSON.md](docs/ESQUEMA-JSON.md)**. En resumen:

```json
{
  "encabezado":            { "tipo_documento": "DESPACHO", "horometro": 1548.7, ... },
  "inspeccion_componentes": [ { "item": "...", "estado": "OK|OBS|D", "observacion": "..." } ],
  "registro_fotografico":   [ { "foto_id": 1, "descripcion": "VISTA FRONTAL", "archivo": "fotos/1.jpg" } ],
  "consumibles":            [ { "descripcion": "EXTINTOR DE 6 KG", "estado_recepcion": "NO_RETORNA" } ],
  "control_consumibles":    [ { "consumible": "Combustible diésel", "despacho": 100, "recepcion": 35 } ],
  "resumen_ejecutivo":      "Máximo 20 palabras."
}
```

El orden de `registro_fotografico` es el orden de la rejilla: foto 1 arriba a la
izquierda, foto 2 arriba a la derecha, y así. No hace falta calcular celdas.

### Identidad de la organización

Todo lo que identifica a la empresa vive en `encabezado` y es opcional:

| Campo | Efecto |
|---|---|
| `empresa` | Aparece en las hojas auxiliares, en las firmas y en el texto de las guías |
| `logo` | Ruta a la imagen que va en la esquina superior izquierda del acta |
| `codigo_formato`, `version_formato`, `fecha_formato` | Bloque de control documental |

Si se omiten, el acta sale sin logo, sin razón social y con un código de
formato genérico.

Tres reglas que el validador hace cumplir porque de ellas depende una firma:

- Un horómetro ilegible se declara `"REVISIÓN MANUAL REQUERIDA"`. Nunca se
  estima un valor aproximado.
- Un componente `OBS` o `D` sin observación escrita es un error, no una
  advertencia.
- Un acta de `DESPACHO` no puede declarar datos de recepción: el equipo todavía
  no ha vuelto, y el acta no debe afirmar un retorno que no ocurrió.

En `ejemplos/` hay dos manifiestos de referencia con datos ficticios. No
incluyen fotografías; para probar el flujo completo, extráigalas de un acta
propia con `nefer extraer`. En `ejemplos/fixmate/` hay un historial de fallas
y un extracto de manual, también ficticios, con los que probar el asistente de
diagnóstico.

## Estructura

| Módulo | Responsabilidad |
|---|---|
| `nefer/layout.py` | Geometría del formato: filas, columnas, bloques, anchos |
| `nefer/schema.py` | Esquema del manifiesto y validación |
| `nefer/build.py` | Manifiesto → Excel (rejilla, anclaje de fotos, saltos de página) |
| `nefer/extract.py` | Excel llenado → manifiesto |
| `nefer/emf.py` | Recupera fotos incrustadas como metarchivo EMF |
| `nefer/textos.py` | Redacción automática de rótulos, recuperaciones y guías |
| `nefer/pdf.py` | Excel → PDF vía LibreOffice headless |
| `nefer/cli.py` | Línea de comandos |
| `nefer/fixmate/` | FixMate AI: lectura de documentos, búsqueda híbrida, diagnóstico, predicción y API |

## Copias por cliente

`clientes/rd-renta/` es una copia completa del proyecto —motor, app de campo,
pruebas y documentación— preparada para **RD RENTAL**: paquete `rdrenta`,
catálogo con su razón social y su bloque de control (`FO-DR-001`, versión
`00`) y el hueco del logo en `marca/`. Es un árbol independiente, pensado para
mudarse a su propio repositorio, y sus pruebas de núcleo corren en su propio
trabajo de CI.

Su aplicación de campo **sí se publica desde aquí**: Pages sirve `docs/` y nada
más, así que una copia vive en `docs/rd-rental/` y queda servida en
`https://nilthonnn.github.io/nefer/rd-rental/app/`, con su página de descarga y
su QR en `https://nilthonnn.github.io/nefer/rd-rental/`. La copia se rehace con
`python3 herramientas/publicar-clon.py` y `tests/test_publicacion_clon.py`
falla si se queda atrás.

## Pruebas

```bash
python -m pytest
```

Cubren la geometría contra las actas reales, el validador, la redacción
automática, la ida y vuelta completa manifiesto → Excel → manifiesto y todo
FixMate: los lectores de PDF, Word y Excel, la búsqueda, el clasificador de
causas, la predicción, el cierre del círculo y la API.

La aplicación de campo tiene su propia suite, que conduce un navegador de
verdad: abre el selector de archivos real y dispara una cámara simulada, para
comprobar que cada foto entra y cae donde debe.

```bash
pip install -e ".[navegador]"
python -m playwright install chromium
python -m pytest tests/test_app_navegador.py
```

Sin Playwright instalado se saltan solas. Para validar además los entregables
hacen falta `poppler-utils` (el `pdftotext` que lee el PDF) y LibreOffice (que
abre el Excel como lo abriría la oficina).

### En cada cambio

`.github/workflows/pruebas.yml` corre la suite en GitHub con cada push a `main`
y en cada pull request, en dos trabajos:

| Trabajo | Qué corre | Cuánto tarda |
|---|---|---|
| **núcleo** | generador, esquema, geometría y redacción | segundos |
| **entregables** | navegador de verdad, Excel y PDF abiertos por sus lectores | unos minutos |

El primero da la señal enseguida, y así un error de lógica no se descubre un
cuarto de hora después. El segundo comprueba antes de empezar que están
Chromium, `pdftotext` y LibreOffice —y que el navegador da la cámara, porque el
binario que Playwright usa por omisión no la trae—, y **falla si alguna prueba
se salta**: una herramienta que falte deja verde una comprobación que no ha
validado nada, y eso es peor que un rojo.

### Publicación

### Cómo llega al teléfono

`docs/index.html` es la página de descarga: lleva el **código QR** que se
imprime y se pega en el taller —cada operario lo escanea y la instala—, los
pasos de instalación de Android y iPhone, y la **descarga del archivo único**
`docs/nefer-app.html`, la app entera en un solo fichero para probarla en una
computadora o mandarla por WhatsApp.

Ese archivo se rehace con `python herramientas/empaquetar-demo.py
docs/nefer-app.html` y una prueba falla si se queda atrás respecto de la app.
El QR se rehace con `python herramientas/generar-qr.py` (necesita `segno`,
sólo para regenerarlo) y otra prueba comprueba que apunta a la dirección que
la propia app declara.

La app se publica **directamente desde la rama**, sin workflow: en *Ajustes →
Pages → Build and deployment* se elige **Deploy from a branch**, rama `main`,
carpeta **`/docs`**. Con eso GitHub publica `docs/` en cada cambio de `main` y
la app queda en `https://<usuario>.github.io/<repo>/app/`. El archivo
`docs/.nojekyll` hace que los archivos se sirvan tal cual, sin procesarlos.

Hubo antes un `.github/workflows/publicar.yml` que hacía lo mismo desde
Actions. Se quitó: para funcionar, el sitio de Pages tiene que existir de
antemano, y crearlo pide permiso de administración que el token de Actions no
tiene —`Create Pages site failed. Error: Resource not accessible by
integration`, medido cinco veces seguidas en este repositorio—. Publicar desde
la rama no necesita permiso ninguno y crea el sitio al guardarlo.

Esto no es un lujo: desde un archivo descargado el navegador **deniega** el
permiso de cámara y no hay forma de concederlo. La app tiene que servirse.

La tipografía va alojada en `docs/app/tipografia/` (Barlow, SIL OFL 1.1) en vez
de pedirse a un tercero: pedirla fuera bloqueaba el arranque casi trece
segundos donde no hay señal. Ver [docs/app/tipografia/LEEME.md](docs/app/tipografia/LEEME.md).

### Un demo en un solo archivo

```bash
python3 herramientas/empaquetar-demo.py nefer-app.html
```

Deja la app entera en un `.html` que se puede pasar por WhatsApp o correo, con
la tipografía incrustada para que se vea igual que la publicada. Trae un demo
de diez fotos y genera el PDF y el Excel sin conexión.

Lo único que **no** funciona desde un archivo suelto es la cámara integrada: el
navegador deniega ese permiso a los orígenes `file://` y no hay forma de
concederlo. La app lo avisa en pantalla; la galería y la cámara del sistema sí
funcionan.
