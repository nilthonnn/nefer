# Protocolo de piloto de validación de FixMate

## 1. Propósito

Definir una prueba controlada de FixMate con técnicos de campo para comprobar si facilita la búsqueda de información técnica y el registro de fallas, e identificar errores antes de ampliar su uso.

El piloto evalúa el comportamiento del prototipo en condiciones delimitadas. No demuestra por sí solo una reducción de fallas, ahorro económico ni precisión industrial generalizable.

## 2. Alcance

Evaluar, según las funciones que estén disponibles en la versión probada:

- Recuperación de información desde manuales OEM e historial de fallas.
- Utilidad y pertinencia de la evidencia mostrada.
- Claridad de las hipótesis de diagnóstico y de los pasos sugeridos.
- Registro y cierre de casos, si están habilitados.
- Estabilidad de la ingesta y sincronización, si forman parte del escenario.

No se considerará que FixMate reemplaza el criterio del técnico, los procedimientos de seguridad ni las instrucciones vigentes del fabricante.

## 3. Preparación

Antes de iniciar, el responsable del piloto debe documentar:

1. Versión o commit de FixMate, configuración y fuentes de datos utilizadas.
2. Equipos, familias de activos y tipos de fallas incluidos.
3. Técnicos participantes, función y experiencia relevante, usando códigos en los registros.
4. Manuales, historial y documentos autorizados para la prueba.
5. Funciones que se probarán y funciones fuera de alcance.
6. Línea base, duración y criterios de aceptación acordados con la empresa antes de observar resultados.

Seleccionar casos representativos y, cuando sea posible, incluir casos con documentación suficiente y casos con información incompleta. No introducir fallas reales ni intervenir equipos solo para probar el sistema.

## 4. Protocolo de ejecución

Para cada caso:

1. Asignar un identificador único y registrar equipo, síntoma y contexto operacional disponible.
2. Confirmar que existe una respuesta de referencia revisada por personal competente y sustentada en documentación o evidencia verificable. Si no existe, marcar el caso como exploratorio y excluirlo de métricas de exactitud.
3. Pedir al técnico que resuelva la consulta con el procedimiento habitual y registrar el tiempo de búsqueda, sin interferir con el trabajo seguro.
4. Presentar la misma consulta en FixMate, manteniendo constantes los datos disponibles. Registrar el tiempo desde el envío hasta que el técnico identifica la información útil.
5. Guardar la respuesta y las fuentes recuperadas. El técnico debe clasificar la evidencia como pertinente, parcialmente pertinente, irrelevante o insuficiente.
6. El técnico valida o rechaza las hipótesis y los pasos sugeridos. Toda recomendación relacionada con seguridad, torque, ajuste o intervención debe verificarse contra el manual OEM/procedimiento aplicable.
7. Registrar correcciones, omisiones, información potencialmente peligrosa, errores de ingesta y fallos de sincronización.
8. Si se prueba el cierre de fallas, registrar la causa confirmada y la solución solo después de la validación técnica correspondiente.
9. Al finalizar, recopilar observaciones del técnico y documentar cualquier interrupción o condición que afecte la comparación.

No retrasar una reparación, no omitir controles y no ejecutar una acción únicamente porque FixMate la sugiera.

## 5. Métricas y definiciones

| Métrica | Definición operacional | Registro |
|---|---|---|
| Tiempo de búsqueda habitual | Minutos desde que el técnico inicia la búsqueda hasta que identifica información suficiente para continuar de forma segura | Minutos por caso |
| Tiempo de búsqueda con FixMate | Minutos desde el envío de la consulta hasta que identifica evidencia útil; si no la encuentra, registrar el tiempo hasta abandonar | Minutos por caso y resultado |
| Pertinencia de evidencia | Evaluación del técnico sobre la relación de los fragmentos recuperados con el caso | Pertinente / parcial / irrelevante / insuficiente |
| Hipótesis aceptadas | Hipótesis de FixMate que coinciden con la causa validada, cuando existe referencia confirmada | Conteo por caso; no llamar “precisión” sin definir denominador y conjunto evaluable |
| Correcciones o rechazos | Respuestas o pasos que el técnico corrige, descarta o considera incompletos | Conteo y descripción |
| Incidentes críticos | Respuesta que podría inducir una acción insegura o contradice una instrucción aplicable | Conteo, severidad y revisión obligatoria |
| Errores de ingesta | Documentos que no se procesan, se procesan incompletamente o quedan asociados incorrectamente | Conteo sobre documentos probados |
| Errores de sincronización | Registros que no se transfieren, se duplican o presentan discrepancias entre dispositivos/servidor | Conteo por intento |
| Uso recurrente | Participantes que vuelven a utilizar FixMate durante el periodo definido | Participantes y sesiones; interpretar con el tamaño de muestra |

Comparar tiempos solo entre tareas equivalentes y reportar cantidad de casos, mediana y rango. Separar casos con referencia confirmada de casos exploratorios. No convertir una muestra pequeña en una afirmación general de desempeño.

## 6. Plantilla de registro por caso

| Campo | Valor |
|---|---|
| ID del caso | |
| Fecha y versión de FixMate | |
| Código del técnico | |
| Equipo / familia | |
| Síntoma y contexto | |
| Fuente de referencia validada | |
| ¿Caso evaluable? ¿Por qué? | |
| Tiempo de búsqueda habitual (min) | |
| Tiempo con FixMate (min) | |
| Evidencia recuperada | |
| Pertinencia de evidencia | |
| Hipótesis mostradas | |
| Resultado de validación técnica | |
| Pasos corregidos o rechazados | |
| ¿Hubo incidente crítico? | |
| Error de ingesta/sincronización | |
| Observaciones del técnico | |
| Revisor y fecha de validación | |

## 7. Seguridad, privacidad y control de datos

- Usar únicamente manuales y registros autorizados por la organización.
- Minimizar datos personales y comerciales; identificar técnicos mediante códigos.
- Restringir el acceso a registros del piloto al equipo autorizado.
- No cargar información confidencial en servicios externos sin autorización expresa.
- Mantener trazabilidad de versión, fuentes y cambios de configuración.
- Tratar cualquier posible recomendación insegura como incidente: detener la prueba del caso, conservar evidencia y escalar para revisión.
- La decisión final de diagnóstico, aislamiento y reparación corresponde al personal autorizado, siguiendo los procedimientos vigentes.

## 8. Análisis y cierre

Al terminar el periodo acordado:

1. Verificar que los registros estén completos y separar casos evaluables de exploratorios.
2. Calcular las métricas definidas, indicando numeradores, denominadores y cantidad de casos.
3. Revisar individualmente los errores, especialmente los relacionados con seguridad, información OEM y fuentes no pertinentes.
4. Comparar los resultados con la línea base y los criterios de aceptación establecidos antes del piloto.
5. Clasificar cada hallazgo como defecto, limitación conocida, problema de datos o necesidad de capacitación.
6. Documentar decisiones y responsables.

La conclusión debe limitarse a la versión, fuentes, participantes, equipos y periodo evaluados. No afirmar causalidad ni beneficios económicos sin un diseño y datos que los sustenten.

## 9. Decisión posterior

- **Continuar:** se cumplieron los criterios previamente acordados y no quedan incidentes críticos sin resolver.
- **Ajustar y repetir:** existen problemas corregibles de recuperación, usabilidad, datos o flujo de trabajo.
- **Detener o restringir:** se detectan riesgos no mitigados, problemas de privacidad o resultados que no permiten un uso responsable.

Los umbrales numéricos deben definirse con la empresa antes del piloto; este protocolo no presupone resultados ni fija metas arbitrarias.
