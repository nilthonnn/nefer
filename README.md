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

### Otros comandos

```bash
python -m nefer plantilla -o acta-nueva.json    # manifiesto en blanco
python -m nefer guias -o docs/                  # guías en Markdown
python -m nefer pdf acta.xlsx                   # convertir un Excel ya generado
```

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
propia con `nefer extraer`.

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

## Pruebas

```bash
python -m pytest
```

Cubren la geometría contra las actas reales, el validador, la redacción
automática y la ida y vuelta completa manifiesto → Excel → manifiesto.
