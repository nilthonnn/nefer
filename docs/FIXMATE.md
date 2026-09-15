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
# 1. Indexar lo que ya existe en la oficina
nefer fixmate -i indice.json indexar historial.json manuales/ actas/

# 2. Preguntar como se pregunta en el patio
nefer fixmate -i indice.json consultar "humo negro y pierde fuerza en la subida" --dtc P0300

# 3. O servirlo para la app de campo
FIXMATE_INDICE=indice.json nefer fixmate servir --puerto 8000
```

## Los tres insumos

| Insumo | Formato | Qué aporta |
|---|---|---|
| **Historial de fallas** | `.json` | La causa raíz *confirmada* y la solución que funcionó. Es lo que ningún manual trae |
| **Manuales de taller** | `.md`, `.txt` | El procedimiento del fabricante, los pares de apriete y los códigos de falla |
| **Actas de nefer** | `.json` o `.xlsx` | Los componentes `OBS` y `D` con la observación escrita a mano en el patio |

Una carpeta se recorre entera; los archivos que no se saben leer se avisan y
detienen la indexación, en vez de dejar un índice al que le falta la mitad del
historial sin que nadie lo note.

### El historial de fallas

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

## La API

```bash
pip install -e ".[fixmate-api]"
FIXMATE_INDICE=indice.json nefer fixmate servir --host 0.0.0.0 --puerto 8000
```

| Ruta | Qué hace |
|---|---|
| `POST /search-report-rag` | El diagnóstico: consulta → evidencia → procedimiento |
| `GET /salud` | Si hay índice, cuántos fragmentos y con qué redactor |
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

## PostgreSQL con pgvector

Cuando el historial deja de caber en un archivo —una flota entera, varios
talleres escribiendo a la vez— el índice se muda a una base y la búsqueda se
hace en SQL. La interfaz es la misma; el motor no distingue cuál tiene
delante.

```bash
pip install -e ".[fixmate-pg]"
nefer fixmate sql | psql "$FIXMATE_PG_DSN"
```

La conexión se lee de `FIXMATE_PG_DSN`, o de las `PGHOST`/`PGUSER`/`PGPASSWORD`
de cualquier cliente de PostgreSQL. **Nunca del código**: una contraseña
escrita en un `.py` es una contraseña publicada el día que el repositorio se
comparte.

Quien ya tenga sus informes en sus propias tablas no necesita copiarlos: basta
una vista llamada `fixmate_fragmentos` con las columnas del esquema y el
`JOIN` que le corresponda.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `FIXMATE_INDICE` | Ruta del índice que usan `nefer fixmate` y la API |
| `OPENAI_API_KEY` | Habilita el redactor con modelo y el embebedor de OpenAI. Sin ella, todo sigue funcionando en local |
| `FIXMATE_PG_DSN` | Cadena de conexión de PostgreSQL |
| `FIXMATE_PG_TABLA` | Tabla o vista de fragmentos (por defecto, `fixmate_fragmentos`) |

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
```

## Qué falta

Dicho para que nadie lo descubra en campo:

- **La foto todavía no diagnostica.** El técnico puede fotografiar una fuga o
  la pantalla de un código, y la foto entra al acta, pero el motor consulta
  por texto. Lo que hay hoy es dictado: el teclado del teléfono transcribe y
  lo transcrito es la consulta.
- **El índice se rehace entero.** No hay actualización incremental; con el
  corpus de un taller tarda segundos, con el de una corporación habrá que
  mudarse a PostgreSQL.
- **Los manuales entran en texto.** Un PDF escaneado hay que pasarlo antes por
  OCR; los diagramas esquemáticos no se indexan como imagen.
- **El registro automático de la solución aplicada** —cerrar el círculo, que
  lo resuelto hoy sea el antecedente de mañana— es hoy manual: se escribe el
  informe en el historial y se vuelve a indexar.

## Estructura

| Módulo | Responsabilidad |
|---|---|
| `nefer/fixmate/texto.py` | Normalización, códigos de falla, torques y troceado |
| `nefer/fixmate/embeddings.py` | Vectores: el local sin red y el de OpenAI |
| `nefer/fixmate/indice.py` | Búsqueda híbrida, filtros y persistencia |
| `nefer/fixmate/ingesta.py` | Historiales, manuales y actas → fragmentos |
| `nefer/fixmate/motor.py` | Consulta → evidencia → diagnóstico |
| `nefer/fixmate/almacen_pg.py` | El mismo índice sobre PostgreSQL con pgvector |
| `nefer/fixmate/api.py` | La API HTTP |
| `nefer/fixmate/cli.py` | `nefer fixmate …` |
