# Pruebas manuales de operación · RCM + TPM

Guía para probar a mano lo que hace FixMate en confiabilidad y mantenimiento
autónomo. **Treinta minutos**, sin red, sin base de datos, sin configurar
nada.

Los casos con su razón de ser están en
[CASOS-RCM-TPM-FIXMATE.md](CASOS-RCM-TPM-FIXMATE.md). Esto es la versión
corta: qué teclear y qué tiene que salir.

---

## 0. Preparar (una vez, 2 min)

```bash
cd nefer
python3 -m pip install -e .          # o: pip install -r requirements.txt
python3 -m nefer fixmate --help
```

Si `nefer` quedó en el PATH, puede escribir `nefer` en lugar de
`python3 -m nefer`. Todo lo de abajo funciona igual con las dos formas.

**Camino rápido.** Si sólo quiere ver todo funcionando de corrido, sin
teclear caso por caso:

```bash
python3 herramientas/demo-fixmate.py rcm
python3 herramientas/demo-fixmate.py tpm
```

Eso corre **los mismos comandos** de esta guía sobre los mismos archivos. Lo
que sale en pantalla no es una imitación de la salida: es la salida.

---

## 1. El análisis RCM · 5 min

```bash
python3 -m nefer fixmate rcm analizar ejemplos/rcm-tpm/analisis-ex220.json
```

**Tiene que salir:**

```
Funciones 2 · fallas funcionales 2 · modos de falla 4
  2 con consecuencia de seguridad o ambiental
  1 ocultos: su tratamiento por defecto es busqueda de fallas

SAE JA1011: Las siete preguntas de JA1011 estan contestadas.

Estrategias: 1 cbm, 1 descarte, 1 busqueda_fallas, 1 rediseno
  1 con rediseño OBLIGATORIO: ...
```

```bash
echo "código de salida: $?"      # tiene que ser 0
```

**Qué mirar.** Los cuatro modos salen por cuatro caminos distintos del
árbol, a propósito. El rediseño obligatorio es la manguera de freno: ninguna
tarea proactiva sirve y la falla puede herir a alguien.

### 1b. Que el criterio sea binario de verdad

Quite una decisión y compruebe que el análisis **deja** de estar completo:

```bash
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path("/tmp/analisis-cojo.json")
d = json.loads(pathlib.Path("ejemplos/rcm-tpm/analisis-ex220.json").read_text())
del d["funciones"][0]["fallas"][0]["modos"][0]["decision"]
p.write_text(json.dumps(d, ensure_ascii=False))
EOF
python3 -m nefer fixmate rcm analizar /tmp/analisis-cojo.json
echo "código de salida: $?"      # tiene que ser 2
```

**Tiene que decir** `Q6 · ...` y nombrar el modo `F1.1.1`. No hay
«prácticamente completo»: o están las siete o no.

### 1c. Que los errores se entiendan

```bash
python3 - <<'EOF'
import json, pathlib
d = json.loads(pathlib.Path("ejemplos/rcm-tpm/analisis-ex220.json").read_text())
d["funciones"][0]["estandar"] = ""
pathlib.Path("/tmp/analisis-malo.json").write_text(json.dumps(d, ensure_ascii=False))
EOF
python3 -m nefer fixmate rcm analizar /tmp/analisis-malo.json
```

**Tiene que decir** qué función y qué le falta, con la ruta del archivo. No
una traza de Python.

---

## 2. El plan de tareas · 3 min

```bash
python3 -m nefer fixmate rcm tareas ejemplos/rcm-tpm/analisis-ex220.json
```

**Tiene que salir** `4 tareas · 0 listas · 4 en borrador`, y debajo, por
cada una, lo que le falta:

```
falta: cada cuanto: el analisis dice que existe un intervalo, no cual es. Hay que medirlo
falta: el limite y su fuente: tiene que venir del OEM o de un estandar, no de esta herramienta
```

**Qué mirar.** Que **no** invente un intervalo ni un límite. Es la prueba
más importante de esta sección: una tarea con un número inventado se ve
terminada, y en campo se ejecuta.

---

## 3. La matriz FMECA · 2 min

```bash
python3 -m nefer fixmate rcm matriz ejemplos/rcm-tpm/analisis-ex220.json -o /tmp/fmeca.csv
head -1 /tmp/fmeca.csv
wc -l /tmp/fmeca.csv              # 5 = cabecera + 4 modos
```

Ábralo en Excel. **Tiene que abrirse en columnas**, no todo en la primera:
el separador es `;`, que es lo que Excel en es-PE espera.

**Qué mirar.** La columna `evidente` dice `no (oculta)` en la válvula de
alivio. Y `frecuencia_historica` sale **vacía**, no cero: nadie ha contado
todavía.

---

## 4. La pauta de mantenimiento autónomo · 3 min

```bash
python3 -m nefer fixmate tpm checklist ejemplos/rcm-tpm/pauta-ex220.json
```

**Tiene que salir** `5 puntos · por_turno · presupuesto 31 s`, y dos puntos
marcados `[TECNICO]`: el freno y las mangueras.

**Qué mirar.** Quién puede hacer cada punto se decidió al escribir la pauta,
en frío. No se le pregunta al operador en campo con la máquina parada.

---

## 5. La ronda, y el enganche con RCM · 5 min

```bash
python3 -m nefer fixmate tpm ejecutar ejemplos/rcm-tpm/ronda-ex220-hallazgo.json \
  -p ejemplos/rcm-tpm/pauta-ex220.json \
  --rcm ejemplos/rcm-tpm/analisis-ex220.json
```

**Tiene que salir:**

```
5/5 puntos · 3 OK · 1 NOK · 1 sin ver · 33 s de 31
Ronda INCOMPLETA
  Un punto que no se pudo ver no cuenta como visto: ...

cil-ex220-2026-03-16-A.cil-ex220.1 · programable · El panal esta tapado con tierra...
   modo F1.1.1
```

**Las dos cosas que mirar:**

1. **La ronda es INCOMPLETA** aunque los cinco puntos estén respondidos. La
   alternativa real a «no pude ver» es un OK falso.
2. **`modo F1.1.1`**: el texto libre del operador —«el panal está tapado con
   tierra»— pasó por el catálogo y llegó al modo de falla del análisis.
   Nadie escribió ese enlace.

### 5b. Que NO enganche cuando no alcanza

```bash
python3 -m nefer fixmate tpm ejecutar ejemplos/rcm-tpm/ronda-ex220-sin-enganche.json \
  -p ejemplos/rcm-tpm/pauta-ex220.json \
  --rcm ejemplos/rcm-tpm/analisis-ex220.json
```

**Tiene que salir:**

```
cil-ex220-2026-03-18-A.cil-ex220.5 · programable · Se escucha un chirrido raro...
   sin enlazar a RCM
```

Es el mismo análisis y el mismo activo que en la prueba 5. Lo que cambia es
que el punto 5 de la pauta **no declara** qué modo vigila, y «se escucha un
chirrido raro al girar la pluma» el catálogo no lo puede codificar. Entonces
la anomalía queda **sin enlazar, y eso se ve**.

Nunca se elige «el modo más parecido». Un enlace que falta se ve; uno
equivocado se suma con los demás y contamina el MTBF por modo.

**Nota sobre la prueba 5.** Ahí el enganche sale aunque quite `--rcm`, y no
es un error: el punto 1 de la pauta **declara** `modo_falla_id: F1.1.1`.
Quien escribió la pauta ya dijo qué modo vigila ese punto, y eso es mejor
dato que adivinarlo del texto del operador.

---

## 6. La ronda que se firmó en vez de hacerse · 2 min

```bash
python3 -m nefer fixmate tpm ejecutar ejemplos/rcm-tpm/ronda-ex220-firmada.json \
  -p ejemplos/rcm-tpm/pauta-ex220.json
```

**Tiene que salir** `5 s de 31` y:

```
AVISO: demasiado rapida para haber sido ejecutada. Criterio configurable de
la planta, no una norma.
```

**Qué mirar.** Que diga que el criterio es de la planta y no de una norma.
Si su faena quiere otro umbral, se cambia `FRACCION_SOSPECHOSA` en
`nefer/fixmate/tpm.py`.

---

## 7. La integración: el motor recupera el análisis · 5 min

```bash
python3 -m nefer fixmate -i /tmp/i.json indexar ejemplos/rcm-tpm/historial-ex220.json
python3 -m nefer fixmate -i /tmp/i.json rcm analizar ejemplos/rcm-tpm/analisis-ex220.json --indexar
python3 -m nefer fixmate -i /tmp/i.json consultar "radiador tapado con tierra"
```

**Tiene que aparecer**, dentro de `EVIDENCIA`, una línea de tipo `rcm`:

```
rcm:EX-220:F1.1.1 (rcm, 30%) — RCM EX-220
```

**Qué mirar.** El motor de diagnóstico no se tocó para esto. El análisis RCM
es evidencia buscable como cualquier otra, y por eso aparece sin que nadie
escriba integración.

```bash
python3 -m nefer fixmate -i /tmp/i.json rcm listar
python3 -m nefer fixmate -i /tmp/i.json tablero
```

En el tablero, **MTTR y disponibilidad salen sin dato, y dice por qué.**
FixMate registra cuándo ocurrió una falla, no cuánto duró la reparación.

---

## 8. Que la frecuencia se cuenta y no se declara · 3 min

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, ".")
from nefer.fixmate import cargador, embeddings, fmeca, ingesta
from nefer.fixmate.indice import Indice
import json, pathlib

datos = json.loads(pathlib.Path("ejemplos/rcm-tpm/historial-ex220.json").read_text())
indice = Indice(embeddings.EmbebedorLocal())
indice.agregar(ingesta.de_historial(datos, "historial-ex220.json"))

a, _ = cargador.analisis_y_decisiones("ejemplos/rcm-tpm/analisis-ex220.json")
c = fmeca.contrastar(a, indice)
print("frecuencias:      ", c.frecuencias)
print("nunca ocurrieron: ", c.nunca_ocurrieron)
print("sin cubrir:       ", c.sin_cubrir)
print("sin codificar:    ", c.sin_codificar)
print("cobertura:        ", c.cobertura)
EOF
```

**Tiene que salir** `F1.1.1: 3`.

**Qué mirar.** En el historial esa causa está escrita de **tres formas
distintas**: «Radiador obstruido por tierra», «radiador tapado con tierra y
polvo» y «RADIADOR OBSTRUIDO POR INCRUSTACION». Cuentan como una porque el
cruce va por código de catálogo, no por texto.

Y los dos números que nadie mira y son los que valen:

- `sin_cubrir`: el filtro de aire ocurrió y **ningún modo del análisis lo
  cubre**. Es la lista de trabajo de la próxima revisión.
- `sin_codificar`: «se escuchó algo suelto adentro» el catálogo no lo pudo
  codificar. Es la medida honesta de cuánto alcanza.

---

## 9. La API · 3 min

**Esta prueba necesita una dependencia más.** El servidor HTTP es opcional y
no viene en la instalación base:

```bash
python3 -m pip install 'nefer[fixmate-api]'
```

Sin ella, `servir` lo dice y sale con código 1 en vez de fallar raro.

```bash
python3 -m nefer fixmate -i /tmp/i.json servir &
sleep 2
curl -s localhost:8000/rcm | python3 -m json.tool | head -20
curl -s localhost:8000/tablero | python3 -m json.tool
curl -s -X POST localhost:8000/search-report-rag \
  -H 'content-type: application/json' \
  -d '{"consulta_texto":"radiador tapado con tierra"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["contexto_rcm"])'
kill %1
```

**Tiene que salir** `4` modos en `/rcm`, `"mttr_horas": null` en `/tablero`
y `[{'origen': 'analisis RCM', ..., 'estrategia': 'cbm', ...}]` en el
diagnóstico.

**Qué mirar.** `contexto_rcm` trae el modo de falla con su estrategia, y
cada entrada declara su origen. Los endpoints de RCM y TPM son **sólo de
lectura**: crear un análisis por HTTP exigiría autenticación, que FixMate no
tiene.

---

## 10. La pantalla del análisis RCM · 6 min

Es la única prueba de esta guía que no usa la terminal. Se abre el archivo en
el navegador —doble clic, o `file://`— y no hace falta servidor:

```bash
python3 -c "import pathlib,webbrowser; webbrowser.open(
  pathlib.Path('docs/fixmate/rcm/index.html').resolve().as_uri())"
```

También está publicada en <https://nilthonnn.github.io/nefer/fixmate/rcm/>.

**10a. El ejemplo, y que avise que es inventado.** Pulse **Abrir el análisis
de ejemplo**. El propio botón tiene que decir que la EX-220 **no existe**.
Arriba sale el contexto operacional (4.200 m, polvo de sílice) y el panel de
JA1011 con **«Las siete están contestadas»** — el ejemplo trae los cuatro
modos decididos.

**10b. Las cuatro que sostienen la cadena.** En el panel de las siete, cuatro
preguntas están marcadas *sostiene la cadena*: funciones, fallas funcionales,
modos y consecuencias. No hay porcentaje en ninguna parte.

**10c. La falla oculta.** Haga clic en el modo **F1.1.3** (válvula de alivio
pegada). Tiene que decir **OCULTA**, explicar que el riesgo que se trata es la
**falla múltiple**, y marcar las cinco preguntas de la rama evidente como *no
aplica a este modo*.

**10d. La guarda, que es la prueba importante.** Haga clic en **F2.1.1** (la
manguera de freno: consecuencia de seguridad). Contéstele al árbol:
degradación detectable **No**, intervalo de edad **No**, restaurar **No**,
tarea viable **Sí**, costo-efectiva **No**.

**Tiene que salir** «Rediseño o cambio de ingenieria», con el chip **REDISEÑO
OBLIGATORIO**, y el último paso del camino tiene que ser la guarda cerrándose:
*«¿operar hasta la falla?» → no → la guarda lo impide*. Si en algún momento la
pantalla ofreciera «operar hasta la falla» como estrategia de ese modo, deje
de probar y avise: es el único error de este proyecto que no tiene atenuante.

**10e. El 89 %.** Al contestar **No** al intervalo de edad, tiene que aparecer
el aviso de Nowlan y Heap (1978) y el 89 % de ítems sin zona de desgaste.

**10f. Sin dato económico, sin ahorro.** Vaya a **F1.1.1** (el radiador) y
ponga la pregunta del costo en **Sin evaluar**. Sale «Mantenimiento segun
condicion» con el aviso *«Información económica insuficiente…»*. No hay ningún
número de ahorro en pantalla.

**10g. «Sin evaluar» no es «No».** Los tres botones de cada pregunta tienen
que ser del mismo tamaño y estar en la misma fila. Una decisión con preguntas
sin evaluar sale marcada **DECISIÓN INCOMPLETA**.

**10h. Quitar una decisión.** En cualquier modo, **Quitar la decisión de este
modo**. El panel de las siete baja a **5/7** —la Q6 queda abierta y con ella
la Q7, que depende de que todas estén decididas—, nombra el modo en la Q6, y
en el árbol ese modo queda **SIN DECIDIR**.

**10i. Que lo exportado vuelva a entrar.** Pulse **Guardar el análisis con sus
decisiones** y pase el archivo por la terminal:

```bash
python3 -m nefer fixmate rcm analizar ~/Descargas/analisis-EX-220.json
```

Tiene que leerlo sin convertir nada y dar el mismo informe. Con la decisión de
10d puesta, `rcm tareas` sobre ese archivo saca la tarea de rediseño del freno
como **proyecto**, no como tarea programada.

**10j. La ronda del operador, encima del análisis.** Baje a **Evidencia de
campo · ronda CIL**, pulse **Abrir una ronda del operador** y elija
`ejemplos/rcm-tpm/ronda-ex220-telefono.json`.

**Tiene que salir** 1 hallazgo, 1 en un modo, 0 sin enganchar; el modo
**F1.1.1** marcado en el árbol con *1 en campo*; y en su ficha, lo que el
operador escribió («el panal esta tapado con tierra…»), quién lo vio, cuándo y
por qué enganchó. Además avisa de que la ronda llegó **incompleta**: un punto
no se pudo ver.

Pruebe también a exportar el análisis con la ronda abierta: el archivo que
baja **no** lleva la ronda dentro. La ronda sigue siendo la ronda, y el
análisis sigue entrando por `rcm analizar` sin convertir nada.

**10k. La misma pantalla, en claro y en oscuro.** Cambie el tema del sistema
operativo. Las cuatro superficies de FixMate —la página, la app, la ronda y
esta— siguen al aparato y comparten la misma paleta. A 4.200 m al sol, una
pantalla oscura no se lee; en interior mina a las tres de la mañana, una
blanca encandila.

**Qué mirar.** La pantalla no evalúa criticidad, no arma la matriz FMECA y no
codifica contra el catálogo: lo dice ella misma en el inicio, y cada una se
hace en el lado de la oficina. Lo que sí hace, lo hace **igual que Python**:
hay 10.206 dictámenes comparados uno por uno en
`tests/test_fixmate_cruce_rcm.py`.

---

## Hoja de resultados

| # | Prueba | Esperado | ¿Pasó? |
|---|---|---|---|
| 1 | `rcm analizar` | 7/7, código 0, 4 estrategias distintas | |
| 1b | Análisis cojo | Código 2, nombra Q6 y el modo | |
| 1c | Análisis malo | Error legible con función y archivo | |
| 2 | `rcm tareas` | 4 en borrador; no inventa intervalo ni límite | |
| 3 | `rcm matriz` | Abre en columnas; `no (oculta)`; frecuencia vacía | |
| 4 | `tpm checklist` | 31 s; dos puntos `[TECNICO]` | |
| 5 | Ronda con hallazgo | INCOMPLETA; llega a `modo F1.1.1` | |
| 5b | Ronda sin enganche | `sin enlazar a RCM`, y se ve | |
| 6 | Ronda firmada | Avisa, y dice que el criterio es de planta | |
| 7 | Consulta | Aparece evidencia de tipo `rcm` | |
| 7 | `tablero` | MTTR sin dato, y dice por qué | |
| 8 | `contrastar` | `F1.1.1: 3` pese a tres escrituras | |
| 9 | API | 4 modos; MTTR `null`; `contexto_rcm` con origen declarado | |
| 10d | Pantalla RCM · guarda | Rediseño obligatorio; la guarda en el camino | |
| 10e | Pantalla RCM · 89 % | Aparece Nowlan y Heap al contestar «no» a la edad | |
| 10i | Pantalla RCM · ida y vuelta | Lo exportado lo lee `rcm analizar` sin convertir | |
| 10j | Pantalla RCM · ronda encima | 1 hallazgo en F1.1.1, con quién y cuándo | |
| 10k | Claro y oscuro | Las cuatro pantallas siguen al aparato | |

---

## Lo que NO va a encontrar, y es a propósito

- **No hay pantalla para *crear* el análisis.** La hay para recorrerlo y
  decidirlo (prueba 10), y para la ronda del operador (pruebas 5 y 6). Escribir
  las funciones, las fallas y los modos sigue siendo editar el JSON; evaluar
  criticidad, armar la matriz y cerrar anomalías siguen siendo comandos.
- **No hay MTTR ni disponibilidad.** Ver prueba 7.
- **No hay costo-efectividad.** No existe un dato económico en el sistema.
- **No puede crear un análisis por HTTP.** Ver prueba 9.
- **TPM es sólo el pilar 1**, mantenimiento autónomo. Los otros siete no
  están.

Si algo de esto le hace falta para el piloto, dígalo antes de empezar: son
fases, no olvidos.
