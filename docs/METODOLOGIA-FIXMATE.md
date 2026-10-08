# Metodología de FixMate

> Este documento **no existía**. El encargo lo daba por existente junto con
> otros cuatro (PILOTO, CASOS-PRUEBA, MATRIZ-PILOTO, INGRESO-CASOS-PILOTO)
> que tampoco están en el repositorio. Se crea aquí desde cero en vez de
> fingir que se actualizó algo.

Esto describe **cómo decide FixMate**, no cómo se usa. Para lo segundo está
[MANUAL-FIXMATE.md](MANUAL-FIXMATE.md).

---

## 1. La regla de la que cuelga todo

> **Si no hay evidencia, no se contesta.**

No es una preferencia de diseño: es lo que separa una herramienta de
diagnóstico de un generador de texto plausible. Un diagnóstico sin
antecedente es una conjetura, y una conjetura firmada por una herramienta se
lee como un dato.

De ahí salen todas las negativas que siguen, y cada una está fijada en una
prueba que falla si alguien la relaja:

| FixMate se niega a… | Dónde | Por qué |
|---|---|---|
| Responder sin antecedente | `motor.SinEvidencia` | Ver arriba |
| Estimar un par de apriete | `motor` | Se lee igual que un dato y no lo es |
| Codificar una causa que no reconoce | `catalogo` | Un código equivocado se suma con los demás y ensucia la cuenta de toda la flota |
| Elegir entre dos causas empatadas | `catalogo.clasificar` | Elegir a la suerte es peor que no codificar |
| Entrenar con menos de 12 casos | `aprendizaje` | Un porcentaje sobre cuatro informes parece medido |
| Calcular un intervalo con una sola falla | `prediccion` | Con una aparición no hay intervalo, hay una fecha |
| Dar criticidad sin método configurado | `criticidad` | La escala codifica el apetito de riesgo del cliente |
| Marcar un análisis completo al 6/7 | `rcm.completitud` | JA1011 es binario a propósito |
| Cerrar un modo de seguridad con «operar hasta la falla» | `decision` | Firmaría la omisión |
| Enlazar una anomalía al modo «más parecido» | `anomalia.enlazar` | Contamina el MTBF por modo |
| Inventar un intervalo o un límite de tarea | `plan` | En campo eso se ejecuta |
| Calcular MTTR | `tablero` | No se registra la duración de la reparación |
| Declarar un ahorro | `decision`, §18 | No hay un solo dato económico en el sistema |

## 2. Lo que cada capa decide

```
OBSERVAR    TPM        ronda del operador, con criterio verificable
DETECTAR    TPM        anomalía, con severidad derivada de la pauta
DIAGNOSTICAR FixMate   historial + manuales, por parecido y por estadística
ANALIZAR    RCM        función → falla funcional → modo → efecto → consecuencia
DECIDIR     RCM        seis estrategias, con el camino de preguntas escrito
EJECUTAR    plan       tarea con intervalo o condición, o punto de ronda
CONFIRMAR   cierre     causa confirmada por quien desarmó, no por la máquina
APRENDER    historial  el cierre de hoy es el antecedente de mañana
MEJORAR     FMECA      la frecuencia se cuenta, no se declara
```

Las dos preguntas que más se confunden, y que aquí son distintas:

- **«¿A qué se parece esto?»** la contesta la búsqueda. Trae el
  procedimiento, porque un antecedente parecido trae lo que se hizo.
- **«¿En qué suele terminar esto?»** la contesta el clasificador sobre el
  historial entero. Dice por dónde empezar.

Las dos hacen falta y se publican por separado, con el número de casos y el
acierto medido al lado. Un 62 % sin esos dos números es un adorno.

## 3. Las tres jerarquías, y por qué no se mezclan

### ISO 14224 — qué se observó

```
modo de falla   lo que se ve           «fuga externa»
mecanismo       el proceso físico      «desgaste»
causa           la condición raíz      «sello vencido»
```

Confundirlas es el error de datos más común del rubro. Sin separarlas no hay
MTBF por modo.

**De la norma se toma la estructura, no los códigos.** `ADM.RESTRICCION.FILTRO`
es de FixMate. ISO 14224 publica sus propias listas —del estilo de `FTS`,
`ELP`, `VIB`, `OHE`—, que son material con licencia y están hechas para
equipo de proceso de petróleo y gas, no para una excavadora en un socavón.
Cada entrada admite un `codigo_iso` opcional para que una planta que tenga la
norma mapee las suyas; vacío de fábrica, porque un mapeo inventado viaja como
si fuera bueno.

**No existe la categoría «Otro».** Es recomendación explícita de la norma, y
la razón es empírica: «Otro» termina siendo el código más usado de cualquier
base mal llevada. Aquí lo que no casa queda **sin codificar y se cuenta**, y
ese número es la medida honesta de cuánto cubre el catálogo.

### SAE JA1011 — por qué importa

Las siete preguntas, verificadas una por una. El criterio es binario: un
proceso que no las responde todas no es RCM, lleve la etiqueta que lleve. La
norma existe porque a finales de los noventa se vendían metodologías
incompletas con ese nombre.

### TPM — quién lo hace

Sólo el pilar 1, Jishu Hozen. Los otros siete no están, y decir «TPM
implementado» por tener una lista de verificación es la clase de afirmación
que vuelve inservible la palabra.

## 4. Las dos guardas que no se negocian

**Primera.** Con consecuencia de seguridad o ambiental, «operar hasta la
falla» no sale nunca, en ninguna combinación de respuestas. Comprobado por
fuerza bruta sobre las 3⁶ = 729 combinaciones posibles, para fallas
evidentes y ocultas. Si ninguna tarea proactiva reduce el riesgo a un nivel
tolerable, la salida es **rediseño**, obligatorio.

**Segunda.** Una tarea de seguridad tampoco se **transfiere** al operador
desde el tamiz. Transferir no es eliminar —la tarea sigue haciéndose— pero
mover una verificación de seguridad a alguien no entrenado para ella no cabe
en cuatro preguntas. Va a JA1011 completo, que es donde se decide con quién
se queda.

## 5. Tres hechos que el código encodifica, con su fuente

**El 89 %.** Nowlan y Heap (United Airlines, 1978) encontraron que el 89 % de
los ítems no tiene zona de desgaste identificable —patrones D, E y F—, de
modo que un límite de edad no previene nada en la gran mayoría de los casos.
Sólo el 11 % lo justifica. Por eso la pregunta del intervalo de edad va
*después* de la detección por condición, y por eso el código avisa cuando la
respuesta es «no hay intervalo».

**El RPN.** Multiplica escalas ordinales, que es estadísticamente
indefendible: severidad 2 × frecuencia 3 × detección 5 y severidad 5 ×
frecuencia 3 × detección 2 dan el **mismo 30**, y el segundo mata gente.
AIAG-VDA lo eliminó en 2019 y lo reemplazó por una tabla de prioridad que
pondera severidad primero, sin multiplicar. Las dos están disponibles; el
RPN viaja con su advertencia pegada a cada resultado.

**La falla oculta.** Por sí sola no produce ningún efecto: la máquina sigue
trabajando. Lo que produce es que, cuando ocurra la segunda falla, no haya
nada que la detenga. El riesgo que se trata es el de la **falla múltiple**, y
por eso su tratamiento por defecto es búsqueda de fallas y se decide antes
que nada. En el modelo es un booleano obligatorio, no una categoría de
consecuencia.

## 6. `None` no es cero, y no es `False`

Tres valores distintos que la mayoría de los sistemas colapsan en uno:

| Valor | Significa |
|---|---|
| `0` / `False` | Se midió o se evaluó, y el resultado es ese |
| `None` | Nadie lo midió ni se lo preguntó |
| `""` | El campo existe y está vacío a propósito |

Un tablero que muestra 0 % de cumplimiento sin ninguna ronda dice «lo
hicieron mal» cuando lo que pasa es que no hay dato. Un árbol de decisión que
trata «no se evaluó» como «no» produce un plan que nadie revisó y que parece
revisado.

## 7. Cómo se amplía

Lo que falte no se parchea en el código: se agrega al catálogo.

```
nefer fixmate estado        dice qué porcentaje del historial reconoce el
                            catálogo, y lista lo más repetido que no reconoce
```

Esa segunda lista es la de mayor rendimiento: mientras esas causas estén
ahí, se agrupan por parecido de palabras y no se pueden comparar entre
equipos ni entre años. Se agregan con `catalogo.cargar()`, y el catálogo
recalcula el peso de cada pista cuando cambia.

## 8. Lo que FixMate no es

- **No es mantenimiento predictivo.** No hay sensores. Hay analítica de
  confiabilidad sobre fechas y horómetro anotados a mano.
- **No calcula vida útil remanente.** Prometerlo haría que alguien comprara
  otra cosa distinta de la que se le entrega.
- **No reemplaza al manual OEM ni al procedimiento de bloqueo del taller.**
  El texto lo dice en voz alta en cada respuesta que lleva pasos.
- **No valida el juicio de un análisis RCM.** Verifica que las siete
  preguntas estén respondidas; no puede juzgar si están bien respondidas.
  Eso pide un facilitador y a los mantenedores en la sala.
