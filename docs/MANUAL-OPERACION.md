# Manual de operación

Cómo levantar un acta de despacho o recepción con `nefer`, desde la primera
prueba en patio hasta el uso diario.

- [1. Preparación](#1-preparación-una-sola-vez)
- [2. Prueba piloto](#2-prueba-piloto-la-primera-acta-real)
- [3. Operación normal](#3-operación-normal)
- [4. Digitalizar actas antiguas](#4-digitalizar-actas-antiguas)
- [5. Referencia](#5-referencia)
- [6. Si algo falla](#6-si-algo-falla)

---

## 1. Preparación (una sola vez)

### Requisitos

| | |
|---|---|
| Python | 3.10 o superior |
| LibreOffice Calc | Solo para exportar a PDF |

```bash
sudo apt-get install libreoffice-calc     # Debian / Ubuntu
brew install --cask libreoffice           # macOS
```

### Instalación

```bash
git clone https://github.com/nilthonnn/nefer.git
cd nefer
pip install -e .
```

### Si algo no carga

La pestaña **Guía** de la aplicación termina con una **comprobación del
dispositivo**: dice si la página va dentro de otra aplicación, si hay acceso a
la cámara, si el selector de archivos devuelve algo y si la foto que devolvió se
pudo abrir. El botón *copiar informe* deja ese texto listo para pegarlo en un
mensaje. Es lo primero que hay que mirar antes de suponer nada.

Dos causas cubren casi todo:

- **La app se abrió como archivo local.** Medido: desde `file://` el permiso de
  cámara sale `denied` y no se puede conceder, aunque el teléfono tenga cámara.
  Abra **https://nilthonnn.github.io/nefer/app/**.
- **La app se abrió dentro del visor interno de una aplicación de mensajería.**
  Ahí no se conceden ni el selector ni la cámara. Abra el enlace con **Chrome**
  o **Safari**.

La propia aplicación lo detecta y lo dice en un aviso, con la dirección
correcta, antes de que lo descubra en el patio.

### En el celular

La computadora genera el Excel y el PDF; el celular es donde se levanta el acta,
con el equipo delante. Para tenerlo ahí:

1. Abra **https://nilthonnn.github.io/nefer/app/** en el navegador del celular.
2. **Android:** menú ⋮ del navegador → *Instalar aplicación*.
   **iPhone:** botón Compartir → *Añadir a inicio*.
3. Queda un icono en la pantalla de inicio. Desde ahí abre a pantalla completa
   y **sin conexión**: un trabajador de servicio guarda la aplicación en el
   teléfono la primera vez.

**Tiene que ser esa dirección, no un archivo descargado.** A una página abierta
como archivo local (`file://`) el navegador le deniega la cámara siempre —el
permiso sale `denied` y no hay forma de concederlo— y algunos visores tampoco
le abren el selector de fotos. Servida por `https` funcionan las dos cosas.

Para publicar esa dirección en el repositorio: **Settings → Pages → Source:
Deploy from a branch → Branch: `main`, carpeta `/docs` → Save**. En un par de
minutos la aplicación queda en `/app/`.

En el patio no hace falta señal. El acta sale del teléfono como un paquete
`.zip` que se envía o se pasa por cable cuando haya cobertura.

### Verificación

```bash
pip install -e ".[dev]"
python -m pytest
```

Debe terminar con **64 passed**. Si falla, no siga: el problema es del entorno,
no de sus datos.

Para comprobar además la aplicación de campo —la carga por galería y la
cámara— contra un navegador de verdad:

```bash
pip install -e ".[navegador]"
python -m playwright install chromium
python -m pytest                       # ahora son 91
```

Las **27 pruebas** de `tests/test_app_navegador.py` abren el selector de
archivos real, disparan una cámara simulada y comprueban que cada foto cae en
su casilla, que lo que no se puede abrir se nombra con su motivo y que el
paquete resultante genera el acta. Seis de ellas sirven la app por HTTP para
fijar lo que sólo ahí funciona: que la cámara se conceda, que el manifiesto y
el trabajador de servicio se registren, y que abra sin conexión. Sin Playwright
instalado se saltan solas y la suite sigue en 64.

```bash
nefer --version        # nefer 1.0.0
```

---

## 2. Prueba piloto: la primera acta real

### Elija bien el primer equipo

- **Uno solo**, en patio, sin prisa. No estrene el sistema con un despacho
  urgente a obra.
- **Empiece por un DESPACHO.** Es el flujo con menos kilometraje: todo lo
  verificado hasta ahora se hizo contra actas de recepción.
- Elija un equipo del que **ya exista un acta hecha a mano**. Al final va a
  comparar las dos, y esa comparación es la prueba de verdad.

### Paso 1 — Tome las fotos

Con el equipo apagado y a plena luz. Una toma por vista, en horizontal, con el
equipo completo dentro del encuadre.

Las mínimas son seis: frontal, posterior, lateral izquierda, lateral derecha,
horómetro y panel de control. Según la familia se agregan motor, baterías,
mástil y focos, cucharón o piso de plataforma.

Además, **una foto por cada accesorio** que salga con el equipo: extintor,
conos, barra de puesta a tierra, bandejas, tacos.

> **El horómetro decide.** Fotografíelo de frente, sin reflejos. El valor de esa
> foto es el que se transcribe. Si no se lee con certeza, no lo estime: se
> declara `REVISIÓN MANUAL REQUERIDA` y se levanta en patio.

### Paso 2 — Pase las fotos del teléfono al computador

Cualquiera de estas vías sirve; use la que ya use su gente:

| Vía | Cómo |
|---|---|
| **Cable USB** | Conecte el teléfono, acepte «Transferir archivos» y copie desde `DCIM/Camera` |
| **WhatsApp o Telegram** | Envíese las fotos a usted mismo y descárguelas desde el escritorio |
| **Google Drive o Dropbox** | Si el teléfono sincroniza solo, las fotos ya están |
| **Correo** | Adjúntelas y descárguelas. Cuide que no las comprima |

> **iPhone: revise el formato antes de salir a patio.** Por defecto toma en
> HEIC, que Excel no sabe incrustar. En **Ajustes → Cámara → Formatos**
> elija **«Más compatible»** y desde ahí grabará en JPG. Es un cambio de una
> sola vez que ahorra convertir fotos cada acta.

### Paso 3 — Ordene las fotos en la carpeta

```bash
mkdir -p ~/actas/TI009-04-despacho/fotos
cd ~/actas/TI009-04-despacho
```

Copie las fotos a `fotos/` y **numérelas en el orden de la rejilla del
formato**: primero la frontal, luego la posterior, después las laterales, y así.

```
fotos/
  01-frontal.jpg      05-horometro.jpg     09-baterias.jpg
  02-posterior.jpg    06-panel.jpg         10-tanque.jpg
  03-lat-izq.jpg      07-motor-frente.jpg  extintor.jpg
  04-lat-der.jpg      08-motor-atras.jpg   barra-tierra.jpg
```

El prefijo numérico es lo único que importa: fija el orden. El resto del
nombre es para que usted se entienda.

### Paso 3b — Cree el acta desde el catálogo

Si tiene el catálogo de clientes y equipos configurado, el encabezado se llena
solo:

```bash
nefer acta -e GE110-02 -c andina --acta 004-001120 --guia T001-00019876
```

```
Acta creada: acta.json
  empresa          Maquinarias del Sur S.A.C.
  tipo_documento   DESPACHO
  cliente          CONSTRUCTORA ANDINA S.A.C.
  obra             PLANTA CONCENTRADORA — FASE II
  fecha            2026-09-08
  codigo_equipo    GE110-02
  modelo_equipo    GRUPO ELECTRÓGENO INSONORIZADO DE 110 KW (POT. CONTINUA)
  categoria        grupo_electrogeno

Falta por llenar a mano:
  horometro        léalo de la foto; si no se lee con certeza, escriba
                   REVISIÓN MANUAL REQUERIDA
  resumen_ejecutivo  máximo 20 palabras
```

El catálogo se crea una sola vez con `nefer catalogo --crear` y se completa con
sus clientes y su parque. Se busca junto al acta, en el directorio actual y en
`~/.nefer/catalogo.json`, en ese orden: el último sirve como maestro compartido
de toda la flota.

`nefer catalogo` lo lista, y busca por fragmento: `-e ge110`, `-e torre`,
`-c PACIFICO`. Si el fragmento coincide con varios, avisa en vez de adivinar.

### Paso 4 — Cargue las fotos

Hay dos caminos. Use el que le acomode; el resultado es el mismo.

#### Con la aplicación de campo (recomendado la primera vez)

Abra la aplicación —en el celular desde **https://nilthonnn.github.io/nefer/app/**, en la computadora también
sirve abrir `docs/app/index.html` con doble clic— y entre en **Despacho**.

**Las cinco vías por las que entra una foto.** La aplicación ofrece las que este
aparato tiene, y sólo esas:

| Vía | Dónde | Para qué |
|---|---|---|
| **Cámara** | donde haya una | Abre la cámara **dentro de la app** y recorre las casillas vacías en orden: se dispara diez veces y cada foto cae en la suya, con el rótulo en pantalla mientras apunta. La de menos errores, porque no hay paso de asignación donde equivocarse. |
| Tocar una casilla vacía | donde haya cámara | Lo mismo, para esa casilla sola |
| **Galería / Cargar fotos** | ambos | Las que ya tomó, de una vez |
| **Cámara del sistema** | celular | La cámara normal del teléfono; la foto cae en la bandeja |
| **Carpeta** o arrastrarla | computadora | La carpeta entera de un tirón, subcarpetas incluidas |
| Pegar con `Ctrl+V` | computadora | Cuando la foto ya está en el portapapeles |

La cámara de la app no usa el selector de archivos: pide la cámara directamente.
Es la ruta que queda cuando el navegador o el visor donde se abrió la página no
dejan abrir el selector. Si tampoco se concede, la app lo dice, ofrece la galería
en el momento y deja de interponerse.

Ninguna de las vías filtra por extensión: los selectores de Android y de iOS
entregan a menudo nombres y tipos vacíos, y filtrar por ellos escondía la
fototeca o hacía desaparecer fotos. Vale lo que el navegador sepa abrir.

Vale cualquier archivo que **el navegador sepa abrir**, se llame como se llame:
los selectores de Android entregan a menudo nombres sin extensión y sin tipo, y
esos también entran. Lo que no se puede abrir se nombra con su motivo — HEIC del
iPhone, RAW, vídeo — para que nunca desaparezca nada en silencio.

Al entrar, cada foto se reduce a **1600 px** por su lado mayor. Una foto de
celular baja de unos 4 MB a menos de 1: el paquete cabe en un mensaje y el Excel
la imprime igual, porque en el formato ocupa un tercio de esa resolución.
Desmarque **Reducir** antes de cargar si necesita los originales.

Luego:

1. Elija la familia del equipo.
2. Cargue las fotos por cualquiera de las vías de arriba.
3. La aplicación **propone** una asignación leyendo el nombre del archivo y la
   fecha de captura EXIF. Las casillas propuestas quedan marcadas.
4. Corrija lo que haga falta: arrastre una foto a otra casilla, o tóquela y
   luego toque su destino. Cargar más fotos **no deshace** lo que ya colocó.
5. Rellene **Datos del acta** (va plegado, con el contador de lo que falta).
6. Pulse **Guardar paquete .zip**: sale un archivo con `acta.json` y la carpeta
   `fotos/` ya nombrada como el acta espera. Descomprímalo y siga en el paso 5.

También puede pulsar **Copiar JSON** y pegarlo en un `acta.json` propio.

Las fotos no salen de su equipo: todo ocurre en el navegador.

#### Desde la terminal

```bash
nefer plantilla -o acta.json
```

Abra `acta.json`, escriba la `categoria` del equipo y luego deje que el
programa arme el bloque de fotografías:

```bash
nefer fotos fotos/ -m acta.json
```

Usa las mismas reglas que la herramienta visual: primero coloca las fotos cuyo
nombre delata la vista (`frontal`, `horometro`, `lat-izq`, `baterias`…), y las
que no dicen nada rellenan los huecos en orden alfabético. Avisa si encuentra
formatos que Excel no puede incrustar:

```
10 fotos escritas en acta.json
   1. VISTA FRONTAL              fotos/01-frontal.jpg
   2. VISTA POSTERIOR            fotos/02-posterior.jpg
   3. VISTA LATERAL IZQUIERDA    fotos/03-lat-izq.jpg
   ...
Revise que cada rotulo corresponda a su foto antes de construir.
```

**Revise esa lista.** Si una foto quedó bajo el rótulo equivocado, corrija el
nombre del archivo y vuelva a ejecutar el comando, o cambie la `descripcion` a
mano en el JSON.

Las fotos de accesorios (extintor, conos, barra) **no** van en este bloque:
van en `consumibles`, como `foto_despacho`.

### Paso 5 — Complete el resto del manifiesto

**El orden de `registro_fotografico` es el orden de la rejilla del formato:**
la foto 1 va arriba a la izquierda, la 2 arriba a la derecha, la 3 debajo a la
izquierda, y así. No hay que calcular celdas.

```json
{
  "encabezado": {
    "empresa": "Su Razón Social S.A.C.",
    "tipo_documento": "DESPACHO",
    "n_acta": "003-000789",
    "n_guia": "T001-00012345",
    "cliente": "INGENIERÍA Y MONTAJES DEL NORTE S.A.C.",
    "obra": "SUBESTACIÓN ELÉCTRICA — TRUJILLO",
    "fecha": "2026-09-08",
    "horometro": 412.5,
    "codigo_equipo": "TI009-04",
    "modelo_equipo": "TORRE DE ILUMINACIÓN 4x1000 W CON MÁSTIL DE 9 M",
    "categoria": "torre_iluminacion"
  },
  "registro_fotografico": [
    { "foto_id": 1, "descripcion": "VISTA FRONTAL",  "archivo": "fotos/frontal.jpg" },
    { "foto_id": 2, "descripcion": "VISTA POSTERIOR", "archivo": "fotos/posterior.jpg" }
  ],
  "inspeccion_componentes": [
    { "item": "Mástil y winche", "estado": "OK", "observacion": "" },
    { "item": "Estabilizadores", "estado": "OBS",
      "observacion": "Gato posterior derecho con juego; revisar al retorno." }
  ],
  "consumibles": [
    { "descripcion": "EXTINTOR DE 6 KG", "cantidad": 1,
      "foto_despacho": "fotos/extintor.jpg" }
  ],
  "control_consumibles": [
    { "consumible": "Combustible diésel", "unidad": "%", "despacho": 100 }
  ],
  "resumen_ejecutivo": "Torre operativa y completa; estabilizador posterior derecho observado."
}
```

Detalle completo de cada campo en [ESQUEMA-JSON.md](ESQUEMA-JSON.md).

### Paso 6 — Valide

```bash
nefer validar acta.json
```

Devuelve **todos** los errores de una vez, no el primero. Corrija y repita
hasta leer `manifiesto valido.`

### Paso 7 — Genere el acta

```bash
nefer construir acta.json -o salidas/TI009-04-DESPACHO.xlsx --pdf
```

Un acta de diez fotos y dos consumibles tarda unos cinco segundos y sale en
siete páginas A4.

### Paso 8 — Revise el PDF

No firme nada sin pasar esta lista:

- [ ] La cabecera lleva el logo, el código de formato y la razón social correctos
- [ ] La **X** está en la casilla `DESPACHO`, no en `RECEPCIÓN`
- [ ] El horómetro impreso coincide con la foto del horómetro
- [ ] Cada foto está bajo el rótulo que le corresponde
- [ ] Ninguna foto sale cortada, girada o demasiado oscura para ver un rayón
- [ ] En un despacho, la columna `RECEPCIÓN` está **vacía** y no hay franja amarilla
- [ ] La hoja `INSPECCIÓN` lista los componentes con su estado
- [ ] La hoja `CONSUMIBLES` tiene los niveles de despacho y espacio para dos firmas
- [ ] Ningún bloque fotográfico queda partido entre dos páginas

### Paso 9 — Compare con el acta manual

Ponga lado a lado el PDF generado y el acta del mismo equipo hecha a mano.

**Lo que debe coincidir:** la rejilla, los rótulos, la posición de la franja
amarilla, el bloque de control documental.

**Lo que puede diferir y está bien:** las hojas `INSPECCIÓN` y `CONSUMIBLES`,
que el formato en papel no tenía.

> **Antes de extenderlo, confirme con operaciones** los ítems de inspección y la
> tabla de fluidos por familia de equipo. Son secciones nuevas y sus contenidos
> por defecto son una propuesta, no una lista oficial.

### Paso 10 — Cierre el ciclo

Cuando el equipo regrese, levante la recepción del mismo equipo. Solo entonces
habrá probado el sistema completo: es en la recepción donde aparecen las
recuperaciones y el consumo calculado.

### Criterios para dar el piloto por bueno

1. El acta de despacho pasa la lista del paso 8 sin retoques a mano.
2. El acta de recepción refleja correctamente lo que faltó o volvió dañado.
3. El cliente firma sin pedir aclaraciones sobre el documento.
4. El operador levanta el acta sin consultar este manual más de una vez.

---

## 3. Operación normal

### El ciclo

```
DESPACHO                              RECEPCIÓN
├─ fotos + niveles de salida          ├─ mismas tomas
├─ accesorios que salen               ├─ qué volvió y en qué estado
├─ acta firmada en patio              ├─ recuperaciones (franja amarilla)
└─ PDF al cliente                     └─ horas facturables por diferencia
```

En la recepción **repita exactamente las mismas tomas** del despacho. Si no son
comparables, la recepción no sustenta ningún cobro.

### Nomenclatura

```
CODIGO_TIPO_FECHA.pdf        →  TI009-04_DESPACHO_2026-09-08.pdf
```

Una carpeta por acta, con su `acta.json` y sus fotos dentro. El JSON es el
respaldo: con él se regenera el Excel y el PDF cuando haga falta.

### Levantar la recepción con el asistente

Abra la aplicación en **Recepción** y cargue tres cosas: el `acta.json` del
despacho, su carpeta `fotos/`, y las fotos del retorno que acaba de tomar. Si
el despacho se levantó en ese mismo teléfono, basta pulsar *usar el acta de la
pestaña Despacho*.

El paquete `.zip` de recepción incluye las dos tandas de fotos —las del retorno
en `fotos/`, las del despacho en `fotos/despacho/`— porque el acta cita ambas.

Para cada vista muestra **la foto de salida al lado**, y le pide la del retorno.
Para cada accesorio le pide el estado. Para cada componente marcado observado o
dañado le pide la foto de retorno y la observación escrita.

Abajo indica en todo momento qué falta, y al final copia el acta de recepción
completa. El acta resultante lleva `archivo_despacho` en cada vista, que es lo
que hace aparecer en el PDF las secciones **COMPARATIVO DESPACHO / RECEPCIÓN**
y **DAÑOS Y OBSERVACIONES**.

> **El horómetro se teclea mirando la foto.** El asistente no lo adivina, y si
> no se lee con certeza hay que escribir `REVISIÓN MANUAL REQUERIDA`.

### Reutilizar el despacho para la recepción, a mano

```bash
cp -r TI009-04-despacho TI009-04-recepcion
cd TI009-04-recepcion
```

Luego, en `acta.json`:

1. `tipo_documento` a `"RECEPCION"`
2. `fecha` y `horometro` nuevos, y un `n_acta` nuevo
3. Reemplace las fotos por las del retorno
4. Añada `estado_recepcion` a cada consumible
5. Complete `recepcion` en `control_consumibles`

El consumo se calcula solo cuando despacho y recepción son ambos numéricos.

---

## 4. Digitalizar actas antiguas

```bash
nefer extraer acta-2025.xlsx -o acta-2025.json --fotos fotos-2025
```

Lee un acta llenada a mano y devuelve el manifiesto equivalente, con las fotos
volcadas a disco y ya asociadas a su rótulo.

Recupera también las fotografías pegadas desde Word, que quedan incrustadas como
metarchivos EMF y que ninguna librería de Python lee directamente.

**Revise siempre el resultado.** La extracción es fiel en cabecera, rótulos y
consumibles, pero `obra`, `inspeccion_componentes` y `control_consumibles` salen
vacíos: el formato en papel no los tenía.

---

## 4b. Qué se llena solo y qué no

| Campo | Cómo | Fiabilidad |
|---|---|---|
| `empresa`, `logo`, código de formato | Catálogo | Determinista |
| `cliente`, `obra` | Catálogo | Determinista |
| `codigo_equipo`, `modelo_equipo`, `categoria` | Catálogo | Determinista |
| `fecha` | EXIF de las fotos | Determinista |
| `descripcion` de cada foto | Nombre de archivo + orden EXIF | Alta, se revisa |
| `n_acta`, `n_guia` | A mano, de la guía de remisión | — |
| `horometro` | **A mano, leyendo la foto** | — |
| `resumen_ejecutivo` | A mano | — |

### Por qué el horómetro no se lee automáticamente

Se probó. Sobre la foto real de un panel InteliLite4 con reflejos —el caso
normal en patio— se ejecutó Tesseract 5.3 con **48 combinaciones** de recorte,
escalado, umbral y modo de segmentación. El valor real era **1548.7**:

```
4543.3   ← 6 combinaciones (la lectura más frecuente, y es falsa)
1543.7   ← 4
1542.7   ← 3
1548.7   ← 2   ✓ la correcta
```

Un sistema por votación habría elegido `4543.3`: tres mil horas de error. Y el
segundo candidato, `1543.7`, **parece una lectura perfectamente razonable**: no
hay forma de que el operador note el fallo sin volver a mirar la foto, que es
exactamente el trabajo que el OCR pretendía ahorrar.

Las horas facturables salen de la diferencia de horómetro entre el despacho y
la recepción. Un dígito mal es una factura mal. Por eso el horómetro se teclea
mirando la foto, y si no se lee con certeza se declara
`REVISIÓN MANUAL REQUERIDA`.

Un modelo de visión con conexión leería ese panel mejor que Tesseract, pero
sigue sin resolver lo esencial: en un documento que se firma, la lectura hay
que confirmarla igual, y en patio muchas veces no hay señal.

## 5. Referencia

### Comandos

| Comando | Qué hace |
|---|---|
| `nefer catalogo --crear` | Crea el maestro de clientes y equipos |
| `nefer catalogo` | Lista lo que hay en el catálogo |
| `nefer acta -e GE110-02 -c andina` | Acta con el encabezado ya lleno |
| `nefer plantilla -o acta.json` | Manifiesto en blanco, sin catálogo |
| `nefer fotos fotos/ -m acta.json` | Carga la carpeta de fotos en el manifiesto |
| `docs/app/` | Aplicación de campo: despacho y recepción, sin conexión |
| `nefer validar acta.json` | Verifica el manifiesto y que las fotos existan |
| `nefer validar acta.json --sin-verificar-fotos` | Solo el manifiesto, sin mirar el disco |
| `nefer construir acta.json -o salida.xlsx` | Genera el Excel |
| `nefer construir acta.json -o salida.xlsx --pdf` | Excel y PDF |
| `nefer construir ... --sin-guias` | Sin las hojas de guía |
| `nefer extraer acta.xlsx -o acta.json --fotos fotos/` | Excel llenado → manifiesto |
| `nefer pdf salida.xlsx` | Convierte un Excel ya generado |
| `nefer guias -o docs/` | Exporta las guías en Markdown |

### Campos obligatorios

`cliente`, `codigo_equipo`, `modelo_equipo`, `fecha`, `horometro`,
`tipo_documento`, al menos una fotografía y `resumen_ejecutivo`.

### Reglas que rechazan el acta

Estas tres son errores, no advertencias, porque de ellas depende una firma:

| Regla | Motivo |
|---|---|
| Horómetro ilegible se declara `REVISIÓN MANUAL REQUERIDA` | Nadie debe firmar una lectura estimada |
| Un componente `OBS` o `D` exige observación escrita | Un daño sin describir no es reclamable |
| Un `DESPACHO` no admite datos de recepción | El equipo no ha vuelto: no se puede afirmar que volvió |

Además: `fecha` en formato `YYYY-MM-DD`, `foto_id` sin duplicados,
`resumen_ejecutivo` de 20 palabras como máximo, y todo archivo declarado —
fotos y logo — debe existir.

### Estados

| | |
|---|---|
| `OK` | Funcional |
| `OBS` | Observado |
| `D` | Dañado |
| `NO_RETORNA` | Solo consumibles: no volvió con el equipo |

### Categorías

`grupo_electrogeno` · `torre_iluminacion` · `plataforma_elevacion` ·
`maquinaria_amarilla` · `generico`

Determinan los rótulos sugeridos y la tabla de fluidos de la hoja
`CONSUMIBLES`. Una plataforma eléctrica no lleva diésel; una maquinaria amarilla
sí, y además filtros y tren de rodaje.

### Identidad de la organización

Todo opcional, en `encabezado`:

| Campo | Si se omite |
|---|---|
| `empresa` | El acta sale sin razón social |
| `logo` | La esquina superior izquierda queda vacía |
| `codigo_formato` | `FO-DR-001` |
| `version_formato` | `00` |
| `fecha_formato` | Vacío |

---

## 6. Si algo falla

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `no existe fotos/x.jpg` | La ruta del JSON no coincide con el disco | Revise el nombre; las rutas son relativas al `acta.json` |
| `un acta de DESPACHO no puede declarar datos de recepcion` | Hay `estado_recepcion`, `texto_recepcion` o `foto_recepcion` en un despacho | Bórrelos, o cambie `tipo_documento` a `RECEPCION` |
| `el archivo no es JSON valido` | Falta una coma o una comilla | El mensaje da línea y columna |
| `resumen_ejecutivo: maximo 20 palabras` | El resumen es muy largo | Es lo que lee el cliente antes de firmar; recórtelo |
| `observacion: obligatoria cuando el estado es OBS o D` | Marcó un daño sin describirlo | Escriba qué tiene |
| `No se encontro LibreOffice` | Falta Calc | Instálelo, o genere solo el Excel sin `--pdf` |
| `LibreOffice no respondio en 300 s` | Acta muy pesada | Reduzca el tamaño de las fotos |
| `no se pudo incrustar X (formato no soportado)` | Es un aviso, no un error | Convierta la imagen a JPG o PNG y regenere |

### El PDF sale bien pero una foto no aparece

Excel solo incrusta PNG, JPG, GIF y BMP. Un HEIC de iPhone o un TIFF no entran.
Tanto `nefer fotos` como el generador avisan y dejan el bloque vacío en vez de
fallar en silencio.

Para convertir lo que ya tomó:

```bash
sudo apt-get install libheif-examples imagemagick
for f in fotos/*.HEIC; do heif-convert "$f" "${f%.HEIC}.jpg"; done
mogrify -format jpg fotos/*.tif        # para TIFF
```

Mejor todavía, evítelo de raíz: en el iPhone, **Ajustes → Cámara → Formatos →
«Más compatible»**.

### El acta sale sin logo y sin decir por qué

No debería: si `logo` está declarado y el archivo no existe, la validación lo
rechaza. Si aun así ocurre, revise que la ruta sea relativa al `acta.json`.

### Volver a empezar

El `acta.json` y la carpeta de fotos son todo lo que necesita. Borre el Excel y
el PDF y vuelva a generar: el resultado es idéntico.
