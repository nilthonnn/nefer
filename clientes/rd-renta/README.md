# rdrenta — actas de despacho y recepción de RD RENTA

Automatiza el **reporte fotográfico de despacho y recepción** de equipos:
grupos electrógenos, torres de iluminación, plataformas de elevación y
maquinaria de construcción y minería.

Es una copia del proyecto `nefer` preparada para **RD RENTA**: el catálogo
(`catalogo.json`) ya declara la razón social, el bloque de control documental
del formato en uso —`FO-DR-001`, versión `00`— y la ruta del logo; la
aplicación de campo emite a nombre de RD RENTA. El motor sigue siendo
independiente de cualquier organización: todo lo que identifica a la empresa
son datos, no código, y se cambia en `catalogo.json` sin tocar el paquete.

**Falta un archivo para que el acta salga completa:** `marca/logo.png`. Ver
[`marca/LEEME.md`](marca/LEEME.md) para el formato y el tamaño del hueco.

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
python -m rdrenta construir acta.json -o salidas/acta.xlsx --pdf
```

`--pdf` acepta una ruta opcional. `--sin-guias` omite las dos hojas de guía.

### Validar antes de generar

```bash
python -m rdrenta validar acta.json
```

Devuelve la lista completa de errores en un solo pase: campos faltantes, fechas
mal formadas, estados `OBS`/`D` sin observación, `foto_id` duplicados, resúmenes
de más de 20 palabras y rutas de imagen inexistentes. Comprueba el disco por
defecto, igual que `construir`; `--sin-verificar-fotos` lo omite cuando aún no
se han descargado las fotos de la cámara.

### Digitalizar un acta antigua

```bash
python -m rdrenta extraer acta-2025.xlsx -o acta-2025.json --fotos fotos-acta-2025
```

Lee un reporte llenado a mano y devuelve el manifiesto equivalente, con las
fotos volcadas a disco y ya asociadas a su rótulo. Recupera también las
fotografías pegadas desde Word, que quedan incrustadas como metarchivos EMF y
que ninguna librería de Python lee directamente (ver `rdrenta/emf.py`).

### Otros comandos

```bash
python -m rdrenta plantilla -o acta-nueva.json    # manifiesto en blanco
python -m rdrenta guias -o docs/                  # guías en Markdown
python -m rdrenta pdf acta.xlsx                   # convertir un Excel ya generado
```

## Documentación

| | |
|---|---|
| **[docs/MANUAL-OPERACION.md](docs/MANUAL-OPERACION.md)** | Cómo levantar un acta, de la primera prueba en patio al uso diario |
| **[docs/MANUAL-APP.md](docs/MANUAL-APP.md)** | La aplicación de campo pantalla por pantalla y botón por botón |
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

En esta copia no hay que escribirlos a mano en cada acta: `catalogo.json` los
lleva y `rdrenta acta` los copia al encabezado.

| Campo | Valor de RD RENTA |
|---|---|
| `empresa` | `RD RENTA` |
| `logo` | `marca/logo.png` — el archivo lo aporta el cliente |
| `codigo_formato` | `FO-DR-001` |
| `version_formato` | `00` |
| `fecha_formato` | vacío, como en las actas en uso |

La razón social exacta (`S.A.C.`, `E.I.R.L.`, …) se corrige en
`catalogo.json`; aquí figura sólo el nombre comercial, que es como llegó.

Tres reglas que el validador hace cumplir porque de ellas depende una firma:

- Un horómetro ilegible se declara `"REVISIÓN MANUAL REQUERIDA"`. Nunca se
  estima un valor aproximado.
- Un componente `OBS` o `D` sin observación escrita es un error, no una
  advertencia.
- Un acta de `DESPACHO` no puede declarar datos de recepción: el equipo todavía
  no ha vuelto, y el acta no debe afirmar un retorno que no ocurrió.

En `ejemplos/` hay dos manifiestos de referencia con datos ficticios. No
incluyen fotografías; para probar el flujo completo, extráigalas de un acta
propia con `rdrenta extraer`.

## Estructura

| Módulo | Responsabilidad |
|---|---|
| `rdrenta/layout.py` | Geometría del formato: filas, columnas, bloques, anchos |
| `rdrenta/schema.py` | Esquema del manifiesto y validación |
| `rdrenta/build.py` | Manifiesto → Excel (rejilla, anclaje de fotos, saltos de página) |
| `rdrenta/extract.py` | Excel llenado → manifiesto |
| `rdrenta/emf.py` | Recupera fotos incrustadas como metarchivo EMF |
| `rdrenta/textos.py` | Redacción automática de rótulos, recuperaciones y guías |
| `rdrenta/pdf.py` | Excel → PDF vía LibreOffice headless |
| `rdrenta/cli.py` | Línea de comandos |

## Pruebas

```bash
python -m pytest
```

Cubren la geometría contra las actas reales, el validador, la redacción
automática y la ida y vuelta completa manifiesto → Excel → manifiesto.

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

Esta copia vive hoy dentro del repositorio `nefer`, en
`clientes/rd-renta/`. **Desde ahí GitHub Pages no la publica**: Pages sirve la
carpeta `docs/` de la raíz del repositorio, no la de una subcarpeta. La app y
el QR ya apuntan a `https://nilthonnn.github.io/rd-renta/app/`, que es la
dirección que tendrá cuando este árbol se mueva a su propio repositorio
`rd-renta` —un `git init` en esta carpeta y Pages apuntando a `/docs`—.

Si el destino termina siendo otro, se cambia en dos sitios y se rehace el QR:
`DIRECCION` en `herramientas/generar-qr.py` y `DIRECCION_PUBLICADA` en
`docs/app/index.html`. Una prueba falla si quedan distintos.

### Cómo llega al teléfono

`docs/index.html` es la página de descarga: lleva el **código QR** que se
imprime y se pega en el taller —cada operario lo escanea y la instala—, los
pasos de instalación de Android y iPhone, y la **descarga del archivo único**
`docs/rdrenta-app.html`, la app entera en un solo fichero para probarla en una
computadora o mandarla por WhatsApp.

Ese archivo se rehace con `python herramientas/empaquetar-demo.py
docs/rdrenta-app.html` y una prueba falla si se queda atrás respecto de la app.
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
python3 herramientas/empaquetar-demo.py rdrenta-app.html
```

Deja la app entera en un `.html` que se puede pasar por WhatsApp o correo, con
la tipografía incrustada para que se vea igual que la publicada. Trae un demo
de diez fotos y genera el PDF y el Excel sin conexión.

Lo único que **no** funciona desde un archivo suelto es la cámara integrada: el
navegador deniega ese permiso a los orígenes `file://` y no hay forma de
concederlo. La app lo avisa en pantalla; la galería y la cámara del sistema sí
funcionan.
