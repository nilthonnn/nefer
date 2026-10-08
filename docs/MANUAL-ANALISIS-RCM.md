# Manual del análisis RCM

**Para quién es esto:** el facilitador y el equipo que hace el análisis —
mantenimiento, operaciones, y quien conozca la máquina en su contexto real.
Es trabajo de oficina o de sala de reuniones, no de patio. Para el patio está
[la ronda CIL](MANUAL-RONDA-CIL.md), que es otra app y otra cosa.

**Dónde está:** <https://nilthonnn.github.io/nefer/fixmate/rcm/>

Arriba de todo está la barra de FixMate: el nombre del producto, la pantalla
en la que está parado, y el paso a las otras dos —el diagnóstico del técnico y
la ronda del operador—. Es la misma barra, el mismo color y la misma
tipografía en las cuatro superficies: las tres personas hablan de la misma
máquina, y una pantalla que parece de otro programa abre la pregunta de cuál
de las tres tiene el dato bueno.

Sigue el tema del aparato, claro u oscuro, como la app de diagnóstico.

También se instala: en Chrome aparece **INSTALAR** en la barra, y queda como
aplicación propia —con su icono, la bifurcación del árbol de decisión— que
abre a pantalla completa y funciona sin red. En una tableta, en la sala de
reuniones donde el wifi va y viene, eso es la diferencia entre seguir el
taller y esperar.

Se abre en el navegador, no se instala y no sube nada: el archivo del análisis
se lee en su computadora y lo que se guarda, se guarda en su computadora.
Funciona igual sin red una vez abierta la página.

---

## Qué hace y qué no

**Hace tres cosas**, y las tres son las que un análisis RCM necesita que
alguien haga bien:

1. **Muestra la cadena completa.** Función → falla funcional → modo de falla →
   efecto → consecuencia. Cuatro cosas distintas que en los planes de
   mantenimiento reales aparecen revueltas en una sola columna llamada
   «falla». Separarlas es la mitad del valor del método.
2. **Recorre el árbol de decisión** de SAE JA1011 con las respuestas del
   equipo, y escribe en pantalla el camino que llevó a cada estrategia. La
   estrategia sin el camino no se puede discutir, y lo que no se puede
   discutir no se puede mejorar.
3. **Informa el estado frente a las siete preguntas** de la norma: cuáles
   están contestadas, cuáles no, y **en qué modos** falta cada cosa.

**No hace tres cosas, y es a propósito:**

| No hace | Por qué, y dónde se hace |
|---|---|
| No evalúa criticidad | El método es configurable y cada planta tiene el suyo, con sus matrices. La pantalla muestra los valores tal como los declara el archivo y el nombre del método; la evaluación la hace el lado de la oficina (`nefer/fixmate/criticidad.py`) |
| No arma la matriz FMECA | Son treinta columnas definidas en un solo sitio. Salen de `fixmate rcm matriz`. Lo que hay en pantalla es un resumen para mirar, no el archivo que se entrega |
| No codifica contra el catálogo ISO 14224 ni mira el historial | Eso lo hace la oficina al recibir el archivo, que es donde está el catálogo y donde está el historial |

Si el método declarado en el archivo es un RPN, la pantalla lo advierte: el
RPN multiplica escalas ordinales, que es estadísticamente indefendible, y
AIAG-VDA lo reemplazó en 2019 por una tabla de prioridad.

---

## Abrir un análisis

Dos botones:

- **Abrir archivo de análisis (.json)** — el mismo formato que lee
  `fixmate rcm analizar`. Hay un ejemplo completo en
  `ejemplos/rcm-tpm/analisis-ex220.json`.
- **Abrir el análisis de ejemplo** — una excavadora EX-220 **que no existe**,
  con los nombres en blanco. Sirve para ver cómo funciona el árbol. El aviso
  está dentro del botón a propósito: un análisis que se ve completo sobre una
  máquina inventada es exactamente la clase de documento que alguien firma.

La pantalla exige lo mismo que el cargador, y por el mismo motivo: **una
función sin estándar de desempeño no se abre**. «El motor debe funcionar» no
se puede fallar de ninguna manera verificable, y de una función así no sale
ningún modo de falla útil. Si el archivo trae una función sin estándar, la
pantalla dice cuál y no abre nada.

---

## La pantalla, de arriba abajo

### 1. El activo y su contexto operacional

El análisis está amarrado al **contexto**, no al equipo solo. La misma bomba
en dos contextos son dos análisis: copiar uno sobre el otro sin reconfirmarlo
es el atajo que llena los planes de tareas que no aplican. Si el archivo no
declara contexto, la pantalla lo avisa.

### 2. Las siete preguntas de SAE JA1011

Un panel con las siete, una por una, con ✓ o ○ y **la lista de lo que falta,
con los ids de los modos**.

No dice «78 % completo». El criterio de la norma es **binario a propósito**:
la norma nació porque en los años noventa se vendían metodologías incompletas
con ese nombre. Un porcentaje invita a redondear hacia arriba; una lista de
ids invita a arreglarla.

Cuatro de las siete están marcadas **«sostiene la cadena»**: funciones, fallas
funcionales, modos y consecuencias. Si falta alguna de esas cuatro, lo que hay
no es un análisis RCM incompleto: **es otra cosa**, y la pantalla lo dice con
esas palabras.

### 3. El árbol del análisis (columna izquierda)

Funciones, con su estándar debajo; las fallas funcionales de cada una; y los
modos de falla de cada falla. Cada modo muestra su estado de un vistazo:

- **OCULTA** — la pérdida de función no es evidente para quien opera.
- **GRAVE** — tiene consecuencia de seguridad o ambiental.
- la **estrategia** decidida, o **SIN DECIDIR**.

Se hace clic en un modo para trabajarlo.

### 4. La ficha del modo de falla

Todo lo que el análisis declara de ese modo: ubicación, código de catálogo,
causa, mecanismo, el efecto completo (lo que pasa, lo que observa el operador,
qué parámetro cambia, qué alarma aparece, cómo confirmarlo), las
consecuencias, la criticidad declarada y la **evidencia**.

Lo que no está declarado se ve como *sin declarar*, en gris. No se rellena con
nada — salvo una distinción que importa: si el modo declara un **código de
catálogo**, causa y mecanismo en blanco no son un hueco, porque la oficina los
hereda del catálogo ISO 14224 al cargar el archivo. La pantalla lo dice así en
vez de mandar a alguien a rellenar algo que ya está. Un modo sin evidencia no puede marcarse validado: queda como
**propuesto**, que es un estado legítimo y visible.

Si el modo es **oculto**, la ficha explica por qué eso va primero: una falla
oculta —una válvula de alivio pegada, un detector que no detecta, un freno de
emergencia que no frena— por sí sola no produce ningún efecto. La máquina
sigue trabajando igual. Lo que produce es que, cuando ocurra la segunda falla,
no haya nada que la detenga. **El riesgo no es de la falla: es de la falla
múltiple.**

### 5. El árbol de decisión

Seis preguntas, cada una con **tres botones del mismo tamaño**: **Sí**, **No**
y **Sin evaluar**.

«Sin evaluar» es un botón y no un vacío por un motivo concreto: si la única
forma de dejar una pregunta sin contestar fuera no tocarla, no se podría
distinguir **«decidimos que no»** de **«no lo miramos»**, y esa diferencia es
la que dice cuánto trabajo falta. Una decisión con preguntas sin evaluar sale
marcada **DECISIÓN INCOMPLETA**: salió del lado conservador, pero no está
terminada.

Las preguntas, en el orden del árbol — que no es el orden de los datos:

| Pregunta | Qué se está preguntando de verdad |
|---|---|
| ¿Se puede probar periódicamente que la protección responde? | Sólo para modos **ocultos**. Probarla sin dañarla y sin dejarla fuera de servicio |
| ¿La degradación se detecta con aviso suficiente para actuar? | La ventana P-F tiene que dar tiempo de **programar** la intervención. Detectarla el día que falla no cuenta |
| ¿Hay una edad a la que la probabilidad de falla sube? | No «cada cuánto suele fallar», sino una **zona de desgaste identificable** |
| ¿Restaurar devuelve la resistencia original del ítem? | Si no la devuelve, lo que corresponde es descartar, no restaurar |
| ¿Existe una tarea técnicamente viable? | Herramienta, acceso, repuesto y gente |
| ¿Alguna tarea cuesta menos que la consecuencia de la falla? | Sin datos económicos: **déjela sin evaluar**. La tarea se conserva y no se declara ahorro |

Una decisión queda marcada incompleta mientras **alguna** pregunta esté sin
evaluar, incluso una que ese modo no use. El criterio es conservador a
propósito: «no lo miramos» no se cuenta como mirado. Si el equipo revisó la
pregunta y no aplica, contéstela y queda constancia.

Las preguntas que el árbol **usó** quedan marcadas; las que no aplican a ese
modo quedan atenuadas. La pregunta de la protección no aplica a un modo
evidente, y las otras cinco no aplican a uno oculto: en RCM, oculta o evidente
es la **primera bifurcación**, no una categoría más.

Dos avisos que aparecen solos:

- **Sin intervalo de edad**, la pantalla recuerda que Nowlan y Heap
  encontraron en 1978, para United Airlines, que el **89 %** de los ítems no
  tiene zona de desgaste identificable —patrones D, E y F—, de modo que un
  límite por horas no previene nada en la gran mayoría de los casos. Sólo el
  11 % lo justifica.
- **Sin dato económico**, la pantalla dice «Información económica insuficiente
  para determinar costo-efectividad» y **no declara ahorro**. No inventa un
  número.

### 6. El dictamen

La estrategia, con el **motivo escrito** y el **camino numerado**: cada
pregunta, lo que se contestó y a dónde llevó. Eso es lo que queda firmado y lo
que se puede discutir en la auditoría.

Las seis estrategias posibles son las de RCM, y ninguna de ellas es
«preventivo» a secas:

| Estrategia | |
|---|---|
| Mantenimiento según condición | tarea proactiva |
| Restauración programada | tarea proactiva |
| Descarte programado | tarea proactiva |
| Búsqueda de fallas | acción por defecto (Q7) |
| Operar hasta la falla | acción por defecto (Q7) |
| Rediseño o cambio de ingeniería | acción por defecto (Q7) |

**La guarda que no se negocia:** con consecuencia de **seguridad o
ambiental**, «operar hasta la falla» **no es una salida legal**. Si ninguna
tarea proactiva sirve, la salida es **rediseño**, y en RCM ahí el rediseño es
obligatorio, no una sugerencia. La pantalla lo marca **REDISEÑO OBLIGATORIO**
y el último paso del camino muestra la guarda cerrándose. Un árbol que
permita cerrar un modo de falla de seguridad con «operar hasta la falla» es
peor que no tener árbol, porque firma la omisión.

**Quitar la decisión de este modo** no es lo mismo que dejar todo «sin
evaluar»: deja el modo sin decisión, y la Q6 vuelve a contarlo como
pendiente. Una decisión que nadie tomó no se rellena con la opción
conservadora para que el análisis parezca completo.

### 7. La ronda del operador, encima del análisis

Aquí se cierra el circuito que justifica todo lo demás: el operador ve algo
en el turno, y la oficina abre el análisis y ve **en qué modo de falla** cayó
eso que vio. Sin este cruce, la ronda es una lista de hallazgos, el análisis
es un documento, y nadie los junta nunca.

**Abrir una ronda del operador (.json)** toma el archivo que sale del botón
«Guardar» de la [ronda CIL](MANUAL-RONDA-CIL.md) —el que trae `ejecucion`,
`anomalias` y `estado`— y lo cruza con el análisis abierto. Hay un ejemplo en
`ejemplos/rcm-tpm/ronda-ex220-telefono.json`.

Lo que pasa después:

- Cada hallazgo que engancha con un modo de falla **marca ese modo en el
  árbol** y aparece en su ficha, con lo que el operador escribió, quién lo
  vio, cuándo, y **por qué enganchó**.
- Los que no enganchan se listan aparte **con el motivo**. No se esconden y
  no se aproximan al modo «más parecido»: una anomalía puesta en el modo
  equivocado contamina la frecuencia por modo y la decisión de estrategia que
  sale de ahí.

El enganche es el mismo que hace la oficina (`anomalia.enlazar`): código de
catálogo **exacto**, mismo activo, y un solo candidato. Si dos modos del
análisis declaran el mismo código, no se elige: la ambigüedad se resuelve en
el análisis. Y hay una cosa que esta pantalla **no** hace, igual que el
teléfono: deducir el código a partir de un texto libre. Eso es el catálogo
ISO 14224 —41 entradas con sus pistas— y lo hace `fixmate tpm anomalias`.

Tres avisos que aparecen solos: si la ronda es **de otra máquina**, no se
engancha nada; si llegó **incompleta**, se dice, porque lo que no se vio no
dice nada del modo de falla ni a favor ni en contra; y si la app la marcó
**demasiado rápida para haber sido ejecutada**, conviene mirarla antes de
usarla como evidencia.

La ronda **no se guarda dentro del análisis**. Meterla ahí obligaría a
inventar un campo que el cargador no lee, y el primer cliente que abriera el
archivo con el comando perdería la evidencia sin enterarse. La ronda sigue
siendo la ronda.

### 8. El tablero y el resumen

Modos, decididos, graves, ocultos, rediseños obligatorios, decisiones
incompletas, y el reparto por estrategia. Debajo, una fila por modo con su
consecuencia, su criticidad declarada y su estrategia.

Es un resumen **para mirar**. La matriz FMECA que se entrega sale del comando.

### 9. Guardar

**Guardar el análisis con sus decisiones** baja un `.json` que es el mismo
archivo que se abrió, con las respuestas del árbol dentro de cada modo. Vuelve
a entrar sin convertir nada:

```bash
fixmate rcm analizar  analisis-EX-220.json   # el informe JA1011; sale 2 si falta algo
fixmate rcm tareas    analisis-EX-220.json   # el plan que sale de las decisiones
fixmate rcm matriz    analisis-EX-220.json   # la matriz FMECA, treinta columnas
```

Si la pantalla exportara una forma propia, el análisis haría un viaje de ida
sin vuelta: se decidiría en pantalla y se volvería a decidir a mano en el
comando. Hay una prueba de navegador que baja el archivo de verdad y lo vuelve
a cargar con el cargador para comprobar que las decisiones son las mismas.

---

## Por qué se puede confiar en que las dos mitades dicen lo mismo

El árbol se recorre **dos veces**: en el JavaScript de esta pantalla y en
`nefer/fixmate/decision.py`, que es lo que corre cuando el archivo vuelve a la
oficina y de donde sale el plan y la matriz.

Dos copias que se separan **no dan error en ninguna parte**: la pantalla dice
«operar hasta la falla» y la oficina dice «rediseño obligatorio» sobre el
mismo modo de falla de seguridad, las dos se ven razonables, y la que queda
firmada es la que alguien imprimió primero.

Por eso:

- Las constantes —las seis estrategias, las clases de consecuencia, las siete
  preguntas, los tres avisos— **se generan** desde Python con
  `python herramientas/espejo-rcm.py`; nadie las escribe dos veces.
- El árbol está escrito a mano en los dos lenguajes, y
  `tests/test_fixmate_cruce_rcm.py` lo recorre en **las 729 combinaciones** de
  respuestas —tres estados en seis preguntas— por cada clase de consecuencia,
  evidente y oculta: 10.206 dictámenes comparados uno por uno, con estrategia,
  motivo, camino completo, avisos y banderas.
- Otra prueba comprueba que la pantalla publicada es exactamente la que sale
  del generador. Si alguien la edita a mano, o cambia una constante en Python
  y se olvida de regenerar, se pone roja.

---

## Lo que esto no es

FixMate **no declara cumplir RCM completo por tener esta pantalla**. Lo que
hay es el árbol de decisión de JA1011 recorrido con respuestas registradas, el
informe de las siete preguntas y la trazabilidad de cada decisión. Un análisis
RCM de verdad lo hace un equipo que conoce la máquina y su contexto; la
herramienta sirve para que ese trabajo quede escrito, discutible y revisable
—y para que nadie firme un plan donde las preguntas no se contestaron.

De TPM está implementado el primer pilar, Jishu Hozen, con
[la ronda CIL](MANUAL-RONDA-CIL.md). Los otros siete pilares no están.
