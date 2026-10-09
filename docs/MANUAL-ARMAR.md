# Manual de «Armar»

Para una sola persona: **quien escribe la pauta y el análisis**
—planificador, confiabilidad, jefe de taller—. El operador no entra aquí: él
abre la Ronda CIL.

---

## 1. Qué es esto, y por qué existe

Las otras dos pantallas de FixMate abren un archivo `.json`: la **Ronda CIL**
abre la pauta del equipo, la **mesa de trabajo de RCM** abre el análisis.
Hasta que existió esta pantalla, esos dos archivos sólo podía escribirlos
alguien que conociera el esquema y lo tecleara a mano en un editor de texto.

Eso quiere decir que, en la práctica, un usuario real sólo podía ver el
ejemplo: la excavadora EX-220, que no existe. Aquí se escriben los dos
archivos de verdad.

La regla de esta pantalla es una sola y no se negocia: **no deja bajar un
archivo que el resto de FixMate rechazaría.** Valida con las mismas reglas
que los cargadores de Python, y hay una prueba que compara los dos veredictos
caso por caso. Si el editor dejara pasar algo, el error aparecería con la
pauta ya bajada y el operador ya frente a la máquina, a 4.200 m y sin señal.

## 2. Abrirla

| Cómo | Para qué |
|---|---|
| `https://nilthonnn.github.io/nefer/fixmate/armar/` | Lo normal. Desde la computadora de la oficina |
| `docs/fixmate/armar/index.html` del repositorio | Sin servidor, desde el archivo |

También se instala —el navegador ofrece «Instalar»— y después abre sin
conexión. Nada de lo que escriba sale de su equipo: no hay servidor detrás.
El archivo queda donde usted lo baje.

## 3. El panel de abajo

Va fijo, y es lo único que hay que mirar sin parar. Dice tres cosas:

- **Cuánto hay.** Puntos y segundos de ronda, o funciones, fallas y modos.
- **Qué detiene el archivo.** En rojo. Son las cosas que el resto de FixMate
  rechazaría: mientras haya una, el botón de guardar está trabado.
- **Qué deja un hueco.** En ámbar. Esas **no** detienen nada. Un análisis sin
  revisión ni aprobación carga perfecto —y es un borrador que alguien va a
  usar como definitivo—; un punto sin presupuesto de segundos carga perfecto
  —y hace que no se pueda detectar una ronda firmada en vez de ejecutada—.

Son dos listas separadas a propósito. Mezclarlas tiene las dos consecuencias
malas: o se traba al que tiene prisa por un campo opcional, o se deja pasar
lo que de verdad rompe.

---

# La pauta de la ronda

## 4. El equipo

| Campo | Qué poner |
|---|---|
| **Código del activo** | El que está pintado en la máquina y ya viaja en los informes. No se inventa aquí |
| **Nombre de la pauta** | Cómo la va a pedir el operador |
| **Cada cuándo** | «Por turno» es la que de verdad se ejecuta |
| **De dónde sale** | Manual del fabricante, análisis RCM, experiencia del taller. Sin esto, dentro de un año nadie sabe por qué está este punto |

El `id` de la pauta no se le pide: se deriva del código del activo y de la
frecuencia, que es lo que lo hace único. Si abre una pauta que ya existe, su
`id` se conserva.

## 5. Los puntos

Cada punto tiene cinco cosas, y tres de ellas son las que hacen que la pauta
mida algo:

- **Qué se hace.** Cinco clases, no siete: limpiar, inspeccionar, lubricar,
  ajustar, verificar. «Detectar anomalías» y «registrar anomalía» no son
  clases de punto: son lo que *pasa* cuando un punto sale NOK. Un punto cuya
  actividad es «detectar anomalías» no tiene criterio posible —¿cuándo está
  OK detectar anomalías?— y en campo se marca OK siempre.
- **El sitio.** Un sitio **físico** donde pararse, no un sistema. «Revisar
  lubricación» no es un punto; «visor de nivel del reductor de giro» sí,
  porque el operador sabe dónde pararse.
- **El criterio de aceptación.** Tiene que decidirse **sin instrumento**. Si
  para decidir hace falta un medidor, el punto pertenece a la ruta predictiva
  y no a la ronda autónoma; mezclarlos hace que la ronda no se cumpla.
- **Los segundos que debería llevar.** Opcional, y conviene ponerlos: una
  pauta de treinta segundos despachada en cuatro no se ejecutó, se firmó. Eso
  se detecta, y se le dice al supervisor al final —no al operador a mitad de
  la máquina—.
- **La falla del catálogo que vigila.** Se elige de una lista; no se escribe.
  Es la llave hacia el análisis RCM y el historial: con ella, lo que el
  operador encuentre se cose solo con el modo de falla, sin que nadie tenga
  que escribir dos veces «radiador obstruido».

Y una casilla: **«está al alcance del operador»**. Se decide aquí, en frío,
por quien conoce el bloqueo, la herramienta y el repuesto. Preguntárselo al
operador en campo, con la máquina parada, garantiza la respuesta cómoda.

## 6. Pegar los puntos desde el Excel

Si la pauta ya está en una planilla, no la escriba otra vez. Copie el rango y
péguelo en la caja del final. Cuatro columnas, en este orden:

```
clase    punto                      criterio                        segundos
limpiar  radiador, cara de entrada  sin tierra pegada entre aletas  40
```

Sirven tabulaciones (lo que pone el Excel al copiar), punto y coma o coma. Si
la primera fila es el encabezado, se saltea.

**Las filas que no se entienden no se descartan en silencio**: vuelven con su
número de línea y el motivo. Un importador que se come filas calladas es peor
que no tener importador.

---

# El análisis RCM

## 7. El orden, que no se puede saltar

**Función → falla funcional → modo de falla.** Un modo de falla que no cuelga
de una función declarada no se puede leer: dice cómo falla algo que nadie
dijo que la máquina deba hacer.

Por eso la pantalla anida: dentro de cada función están sus fallas
funcionales, y dentro de cada falla sus modos.

## 8. La función y su estándar

La función es lo que el activo **debe hacer**. El estándar es lo que la
vuelve verificable, con número: *«entre 80 y 95 °C con carga continua al
100 % a 4.200 m»*.

**Sin estándar, el archivo no baja.** No es rigidez: una función sin estándar
no se puede fallar de forma verificable, y de ella no sale ningún modo de
falla útil. Es el único campo del análisis que la pantalla exige además de
las descripciones.

## 9. El modo de falla

Es el nivel donde se decide la tarea. Lo que se escribe aquí:

- **La descripción.** Qué produce la falla funcional.
- **La falla del catálogo.** Opcional, y al elegirla se rellenan causa,
  mecanismo y sistema **si están vacíos**: lo que usted ya escribió no se
  pisa.
- **«¿La falla se nota cuando ocurre?»** Es la **primera bifurcación de
  RCM**, no una consecuencia más. Si es oculta, el riesgo no es esta falla:
  es la **falla múltiple**, y de ahí sale una tarea de búsqueda de fallas.
  Por eso «oculta» no está entre las consecuencias; si la busca ahí, la
  pantalla se lo dice y le indica dónde va.
- **Las consecuencias.** El árbol de decisión empieza aquí: sin consecuencia
  declarada no sale tarea. Seguridad y ambiental van marcadas como graves,
  porque con ellas «operar hasta la falla» no es una salida.
- **El efecto.** Qué pasa en el equipo, qué ve u oye el operador, qué lectura
  cambia, qué alarma aparece. Responde la Q4 de JA1011; sin el efecto local,
  esa pregunta no se puede contestar.
- **El estado y la evidencia.** «Validado» **sin evidencia no se puede
  guardar**: un modo de falla validado de memoria es una opinión con sello.

## 10. Lo que esta pantalla no hace

- **No evalúa criticidad.** El método es configurable y vive en la oficina:
  `fixmate rcm` y la matriz. Si abre un análisis que ya la trae, los valores
  se conservan intactos.
- **No contesta el árbol de decisión.** Eso es la mesa de trabajo
  (`fixmate/rcm/`), con el equipo delante.
- **No arma la matriz FMECA.** Sus treinta columnas salen de
  `fixmate rcm matriz`.
- **No inventa nada.** Lo que falta, falta, y lo dice.

## 11. Abrir uno que ya exista

Se reconoce solo si es una pauta o un análisis por lo que lleva dentro. Y
—esto importa— **lo que la pantalla no edita, no lo borra**: el método de
criticidad, los valores de severidad y frecuencia de cada modo y las
respuestas del equipo al árbol de JA1011 viajan intactos al archivo nuevo.

Si no fuera así, abrir un análisis para corregir una coma borraría la reunión
entera, y lo haría en silencio: el archivo nuevo se vería perfecto.

El archivo que baja es uno **nuevo**. El original no se toca.

## 12. Qué hacer con lo que sale

| Archivo | A dónde va |
|---|---|
| `pauta-<equipo>.json` | Al teléfono del operador, en la **Ronda CIL** |
| `analisis-<equipo>.json` | A la **mesa de trabajo de RCM**, y a `fixmate rcm analizar` en la oficina |

Los dos entran también por la línea de comandos sin convertir nada: es el
mismo formato.
