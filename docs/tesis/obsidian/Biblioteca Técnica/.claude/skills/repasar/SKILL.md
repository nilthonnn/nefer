---
name: repasar
description: Toma una práctica o simulacro de estudio con las notas de esta bóveda (ComAp: potencia, sincronismo, alarmas, diagnóstico). Úsala cuando el usuario diga «repasar», «tómame examen», «pregúntame de sincronismo», «/repasar alarmas» o quiera practicar.
---

# Repaso con preguntas

Argumento opcional: el tema (sincronismo, potencia, alarmas, diagnóstico, todo). Sin argumento, pregunta cuál y ofrece «todo».

## Cómo hacerlo
1. Lee la nota del tema en `ComAp/Temas/` y `Ruta de estudio ComAp.md`. Usa solo datos marcados [D]; para cada pregunta ten a mano su página del PDF.
2. Haz **una pregunta por turno** y espera la respuesta. Mezcla tipos:
   - concepto (¿qué diferencia hay entre BOC y SD?),
   - setpoint (¿qué setpoint fija el tiempo máximo de sincronización?),
   - cálculo (curva IDMT: tiempo = Amps IDMT Del × In / (I − In)),
   - caso de campo (aparece «MCB Fail» que no se borra, ¿qué revisas?).
3. Califica de **1 a 5**, explica en 2–3 líneas lo que faltó y da la cita `[[archivo.pdf#page=N]]` para releer.
4. Cada 5 preguntas, o cuando el usuario diga «fin», muestra un resumen: puntaje promedio, temas flojos y páginas a releer.
5. Si el usuario lo pide, guarda el resultado en `Repasos/AAAA-MM-DD <tema>.md` (preguntas, respuestas, nota, páginas).

## Reglas
- No inventes datos: si la respuesta no está en las notas ni en el PDF, dilo.
- Lenguaje sencillo. Relaciona con su tesis de RCM cuando ayude (alarmas = detección en el AMEF).
