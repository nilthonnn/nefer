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

### Verificación

```bash
pip install -e ".[dev]"
python -m pytest
```

Debe terminar con **42 passed**. Si falla, no siga: el problema es del entorno,
no de sus datos.

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

### Paso 4 — Cargue las fotos

Hay dos caminos. Use el que le acomode; el resultado es el mismo.

#### Con la herramienta visual (recomendado la primera vez)

Abra **`herramientas/asignador-fotos.html`** en el navegador —basta doble clic,
no necesita conexión ni instalar nada— y:

1. Elija la familia del equipo.
2. Arrastre la carpeta de fotos, o púlselas para cargarlas.
3. La herramienta **propone** una asignación leyendo el nombre del archivo y la
   fecha de captura EXIF. Las casillas propuestas quedan marcadas.
4. Corrija lo que haga falta: arrastre una foto a otra casilla, o tóquela y
   luego toque su destino. Funciona igual en tableta.
5. Pulse **Copiar JSON** y péguelo en `acta.json`.

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

### Reutilizar el despacho para la recepción

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

## 5. Referencia

### Comandos

| Comando | Qué hace |
|---|---|
| `nefer plantilla -o acta.json` | Manifiesto en blanco |
| `nefer fotos fotos/ -m acta.json` | Carga la carpeta de fotos en el manifiesto |
| `herramientas/asignador-fotos.html` | Asignación visual en el navegador, sin conexión |
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
