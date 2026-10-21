---
tags: [guion]
---

# Guion · versión 28 minutos (v9, 37 diapositivas)

## 1 · Portada — 0:35 (acum. 0:35)
- **Objetivo:** Presentarte, presentar el título y fijar el tono: problema real de un activo de alquiler.

> Buenos días, señores miembros del jurado. Mi nombre es Nilthon Rosinaldo Chite Vilca y presento la tesis «Implementación de la metodología RCM para la reducción de fallas y maximización de la disponibilidad operativa del grupo electrógeno Rivera Diesel de 500 kW, Moquegua 2024», asesorada por el magíster Erick Hans Araca Berrios. En una faena minera, cuando un grupo como este se detiene, se detiene la operación y la empresa de alquiler deja de facturar. De eso trata mi investigación: cómo pasar de reparar fallas a prevenirlas.

- **Técnica:** La foto es un equipo Rivera Diesel de la flota (placa RCS 228), no uno de los tres equipos estudiados.
- **Transición:** Les resumo primero la investigación completa en una sola diapositiva.

> [!warning] Si preguntan por la foto: «es un equipo de la misma flota y tecnología; no es uno de los GI500 de la muestra». Prepara la frase sobre fechas: «2024 es el año del estudio; los datos históricos son 2019–2022».

## 2 · Resumen — 1:00 (acum. 1:35)
- **Objetivo:** Que el jurado tenga el mapa completo: problema, método y resultado proyectado, con la palabra «proyectado» desde el inicio.

> Tres grupos electrógenos críticos de 500 kW acumularon 113 fallas entre 2019 y 2022 y operaron entre 92,7 y 93,9 % de disponibilidad, frente a una meta de 97 %. La causa no es solo el desgaste: es un mantenimiento reactivo, con canibalización de componentes y sin trazabilidad. Apliqué la metodología RCM-II de Moubray: seleccioné los equipos por criticidad, analicé 93 modos de falla con AMEF y número de prioridad de riesgo, 47 de ellos por encima del umbral de 180, y asigné una tarea a cada modo con el árbol de decisiones. El plan resultante proyecta disponibilidades de 96,9 a 97,9 %, con MTBF de 220 a 250 horas y MTTR de 5 a 8 horas. Subrayo desde ahora que son resultados proyectados: el plan se diseñó y justificó, pero su efecto real se medirá al implementarlo.

- **Técnica:** 93 modos y 47 con NPR > 180 salen de la tabla «Matriz del NPR» (conteo verificable). D, MTBF y MTTR objetivo salen de las tablas de proyección del Cap. IV.
- **Transición:** Veamos con más detalle el problema que motivó el estudio.

> [!warning] No digas «logré» ni «se redujo». Evita citar aquí las 1 102 h/año: es la cifra más vulnerable de la tesis (ver riesgo crítico R1). Si usas la versión 10-07, su resumen dice «93 %» y «US$ 12 000»: explica que el detalle está en el Cap. IV.

## 3 · Planteamiento del estudio — 1:25 (acum. 3:00)
- **Objetivo:** Demostrar que el problema es real, medible y de gestión, no solo de desgaste.

> Los tres grupos críticos operaron entre 92,7 y 93,9 % de disponibilidad en 2019–2022, cuando la meta es 97 %. En ese periodo acumularon 113 fallas: 43 el GI500-16, 49 el GI500-19 y 21 el GI500-20. En el modelo Volvo Penta TAD1642GE con alternador Stamford las fallas se repiten: sulfatación de cables, averías del regulador AVR por humedad, desgaste de rodamientos y rotura de fajas que termina en sobrecalentamiento. Solo en el GI500-19, el costo documentado supera los 17 750 dólares en cuatro años. Y la causa de fondo es de gestión: componentes canibalizados entre equipos, hojas de servicio registradas hasta 30 días después y análisis de falla que se omite. Por eso planteo el RCM-II: pasar de reparar fallas a prevenirlas.

- **Técnica:** Disponibilidad = MTBF/(MTBF+MTTR). «Canibalización» = retirar componentes de un equipo para reparar otro; reingresan en peor estado e inducen fallas.
- **Transición:** Esto me llevó a formular el objetivo de la investigación.

> [!warning] El mercado de US$ 620 M que aparece en la v8 no tiene cita primaria en la tesis: no lo enfatices o ten la fuente. En la versión 10-07 esta diapositiva es solo texto: no la leas; cuenta el problema con las cifras de arriba.

## 4 · Objetivos e hipótesis — 0:55 (acum. 3:55)
- **Objetivo:** Mostrar la alineación objetivo → método → indicador.

> El objetivo general es implementar la metodología RCM para reducir las fallas del grupo electrógeno de 500 kW y maximizar su disponibilidad en Moquegua. El primer objetivo específico es aplicar el RCM para identificar y reducir las fallas críticas; lo respondo con el AMEF, el número de prioridad de riesgo y el árbol de decisiones. El segundo es determinar en qué medida un programa basado en confiabilidad mejora la disponibilidad; lo respondo con el plan de mantenimiento y la proyección de la disponibilidad, calculada como MTBF entre MTBF más MTTR. La variable independiente es el mantenimiento basado en RCM; la dependiente, la disponibilidad de los grupos.

- **Técnica:** La hipótesis general afirma que el RCM permite reducir fallas y maximizar la disponibilidad; en este estudio se contrasta con indicadores proyectados, no medidos.
- **Transición:** ¿Por qué vale la pena este esfuerzo? Por dos razones.

> [!warning] Riesgo metodológico: la hipótesis específica b) dice «incrementa significativamente», pero no hay prueba estadística. Si preguntan, di «significativo en sentido práctico: +2,96 a +5,18 puntos proyectados; no se aplicó prueba inferencial porque el diseño es no experimental y descriptivo».

## 5 · Justificación — 0:45 (acum. 4:40)
- **Objetivo:** Dar la razón técnica y económica, sin sobredimensionar cifras.

> La justificación técnica viene del historial del GI500-19: fugas de refrigerante, radiadores obstruidos, cables sulfatados, reguladores AVR dañados por humedad y filtros Racor obstruidos. Son fallas evitables con tareas preventivas y predictivas bien elegidas. La justificación económica: en ese mismo equipo, más de 17 750 dólares en cuatro años, 15 000 en reparaciones y 2 752 en pérdidas por inactividad. En alquiler, cada hora parada es ingreso perdido.

- **Técnica:** 15 000 + 2 752 = 17 752 (cálculo verificable). La meta de 70–80 % menos fallas críticas y > US$ 12 000/año es una afirmación de la tesis sin cálculo explícito en el Cap. I.
- **Transición:** Paso a explicar cómo lo investigué.

> [!warning] No menciones las «172 horas»: no cuadran con 49 fallas × 15,8 h ≈ 774 h. Si el jurado las cita, explica que corresponden al alcance de la justificación económica del Cap. I y que el diagnóstico usa los indicadores base.

## 6 · Metodología — 1:05 (acum. 5:45)
- **Objetivo:** Que el jurado acepte el diseño y la muestra.

> Es una investigación aplicada, de enfoque cuantitativo, con diseño no experimental y alcance aplicado: no manipulé variables; analicé la situación real con los registros de la empresa y propuse una mejora. La población son los 20 grupos electrógenos de la empresa de referencia; la muestra, no probabilística, son los tres de criticidad alta según la matriz: GI500-16, GI500-19 y GI500-20. Recogí la información con análisis documental de registros de fallas y órdenes de trabajo, entrevistas al personal técnico y observación en campo, y la procesé con estadística descriptiva: MTBF, MTTR y disponibilidad. El análisis siguió ocho pasos: diagnóstico, criticidad, taxonomía, Pareto, AMEF y NPR, árbol de decisiones, plan y proyección económica.

- **Técnica:** Diseño no experimental = se observa sin intervenir; por eso los resultados del plan son proyectados.
- **Transición:** Antes del análisis, el sustento teórico.

> [!warning] La tesis se contradice: 3.1.1 dice «cuasi-experimental» y 3.2 «no experimental». Sostén «no experimental» y reconoce la errata si te la señalan: «en 3.1.1 hay un error de redacción; el diseño aplicado es no experimental, como se fundamenta en 3.2».

## 7 · Divisor · Marco teórico — 0:08 (acum. 5:53)
- **Objetivo:** Transición.

> Pasamos al marco teórico.

- **Técnica:** —
- **Transición:** Empiezo por los antecedentes.

> [!warning] No te detengas.

## 8 · Antecedentes — 0:45 (acum. 6:38)
- **Objetivo:** Situar el estudio entre trabajos comparables documentados en la tesis.

> Entre los antecedentes nacionales, Tuesta aplicó un plan basado en confiabilidad a motores de grupos electrógenos con mejoras de 2 a 4 %, y Sayre Llana alcanzó 95 % de disponibilidad. El más cercano a mi caso es el de Illesca y Ureta, en una empresa de alquiler para minería: con RCM y TPM elevaron la disponibilidad 7,48 % y redujeron el correctivo 15 %. En el ámbito local, Achahuanco aplicó RCM y matriz de criticidad en la subestación San José. La base metodológica viene de Campos-López y de Moubray.

- **Técnica:** Las cifras son las que reporta cada antecedente en el Cap. II.
- **Transición:** ¿Qué tipo de mantenimiento propone el RCM? Ninguno en exclusiva.

> [!warning] Si usas la versión 10-07: «Martínez Farfán (2021), EUROLIFT» NO está en la tesis ni en las referencias. Reemplázala o no la expongas; si el jurado la pide en el documento, no la encontrará.

## 9 · Tipos de mantenimiento — 0:40 (acum. 7:18)
- **Objetivo:** Ubicar el RCM como lógica de decisión, no como un cuarto tipo de mantenimiento.

> El correctivo actúa después de la falla; es el que hoy predomina en la empresa. El preventivo actúa por horas o calendario; existe un plan del fabricante, pero no se cumple a tiempo. El predictivo actúa según la condición medida. El RCM no reemplaza a los otros: es la lógica que decide, para cada modo de falla, cuál conviene según su consecuencia. En mi análisis, 55 de los 93 modos quedaron con tareas a condición, es decir, predictivas.

- **Técnica:** 55/93 = 59 %: clasificación propia de las hojas de decisión (primera columna marcada «S»).
- **Transición:** Para medir el resultado uso tres indicadores.

> [!warning] En la versión 10-07 aparece «mantenimiento cero horas», que no está en el marco teórico de la tesis: no lo expliques como parte de tu sustento.

## 10 · Indicadores de mantenimiento — 0:50 (acum. 8:08)
- **Objetivo:** Asegurar que el jurado vea que dominas MTBF, MTTR y D.

> El MTTR, o mantenibilidad, es el tiempo total de reparación entre el número de intervenciones correctivas. El MTBF, o confiabilidad, es el tiempo de operación entre el número de fallas. La disponibilidad los combina: MTBF entre MTBF más MTTR. Con los datos del GI500-16: 145,3 entre 145,3 más 11,5 da 92,67 %. Para llegar a 97 % habría que bajar el MTTR a 4,5 horas sin cambiar el MTBF, o subir el MTBF a 372 horas sin cambiar el MTTR. Ninguna palanca sola es realista; por eso el plan actúa sobre las dos.

- **Técnica:** MTTR necesario = MTBF·(1−D)/D = 145,3·0,03/0,97 = 4,49 h. MTBF necesario = MTTR·D/(1−D) = 11,5·0,97/0,03 = 371,8 h.
- **Transición:** Con este marco, entro al desarrollo.

> [!warning] En la versión 10-07 la definición escrita del MTTR es la del MTBF: dila bien en voz alta. La ecuación es la disponibilidad inherente; la tesis la llama «operativa (Ao)». Si objetan, ver pregunta P9.4.

## 11 · Divisor · Desarrollo y análisis — 0:08 (acum. 8:16)
- **Objetivo:** Transición.

> Entramos al núcleo de la tesis: el capítulo IV.

- **Técnica:** —
- **Transición:** Primero, el diagnóstico.

> [!warning] No te detengas.

## 12 · Diagnóstico inicial — 1:05 (acum. 9:21)
- **Objetivo:** Establecer la línea base con datos documentados.

> Los indicadores 2019–2022 muestran 113 fallas, disponibilidades de 92,65 a 93,94 %, MTBF de 145 a 245 horas y MTTR de 11 a 16 horas. Frente a la meta de 97 %, la brecha va de 3,1 a 4,4 puntos; la mayor es la del GI500-16. Pesan las paradas largas: rebobinados de estator de 96 y 120 horas, una bomba de alta presión contaminada con agua de 72 horas y radiadores obstruidos. Y aparecen dos patrones: extracciones y reinstalaciones sin trazabilidad, y un plan del fabricante que no se cumple por planificación y falta de repuestos.

- **Técnica:** Brecha = 97 − D. El GI500-19 tiene el mayor MTBF (245 h) pero el mayor MTTR (15,8 h).
- **Transición:** ¿Por qué estos tres equipos y no otros? Por la matriz de criticidad.

> [!warning] 92,65 % (tabla base) vs 92,67 % (ecuación y proyecciones): es redondeo; unifica o explica.

## 13 · Selección del activo crítico — 1:00 (acum. 10:21)
- **Objetivo:** Justificar la muestra con un criterio técnico reproducible.

> Evalué los 20 grupos de la flota con una matriz de criticidad. Solo tres alcanzan criticidad alta: GI500-19 con 150, GI500-16 con 140 y GI500-20 con 130; el siguiente, el GI250-01, llega a 84. La criticidad es la frecuencia por la consecuencia, y la consecuencia combina el tiempo de reparación multiplicado por el impacto operacional, más costo, ambiente y seguridad. Para el GI500-19: 5 por 30, igual a 150. Con los rangos de la tesis quedan 3 equipos de criticidad alta, 14 media y 3 baja.

- **Técnica:** Consecuencia = TPR × IO + Costo + Ambiental + Seguridad (reconstruida y verificada en los 20 equipos; la tesis solo escribe Frecuencia × Consecuencia).
- **Transición:** ¿Qué tan confiables son hoy esos tres equipos?

> [!warning] Errata: el texto dice «16 consecuencias» para el GI500-20; son 26 (5 × 26 = 130). Inconsistencia: frecuencia 5 = «> 20 fallas/año», pero el GI500-20 tuvo 21 fallas en cuatro años.

## 14 · Confiabilidad por equipo — 0:50 (acum. 11:11)
- **Objetivo:** Traducir el MTBF en probabilidad de operar sin falla.

> La confiabilidad responde a una pregunta: ¿qué probabilidad tiene un equipo de operar cierto tiempo sin fallar? Con la ecuación de la tesis, R de t igual a e a la menos t sobre MTBF, a las 200 horas el GI500-16 tiene 25 %, el GI500-20 27 % y el GI500-19, el mejor, 44 %. Coincide con las curvas que presenta la tesis. La consecuencia práctica es que las inspecciones críticas deben programarse por debajo de ese horizonte.

- **Técnica:** R(200) = e^(−200/145,3) = 0,25; e^(−200/245) = 0,44; e^(−200/152,8) = 0,27. Modelo exponencial (β = 1, tasa de falla constante).
- **Transición:** Para analizar las fallas, primero hay que ordenar el equipo en sistemas.

> [!warning] La tesis llama «Weibull» a la curva del GI500-19 sin reportar β ni η. No afirmes que estimaste Weibull. En la versión 10-07 esta diapositiva muestra el Pareto de equipos y la curva: explica la curva igual.

## 15 · Taxonomía del activo — 0:45 (acum. 11:56)
- **Objetivo:** Mostrar la estructura sistema → subsistema → componente que ordena el AMEF.

> Con la taxonomía, cada falla tiene un lugar. El grupo se divide en 8 sistemas y 22 subsistemas: motor diésel, generador, control y automatización, distribución eléctrica, arranque, carrocería, instrumentación y suministro externo de combustible. El motor diésel concentra 79 de las 102 fallas del periodo 2021–2022, el 77 %: por eso el AMEF empieza por él.

- **Técnica:** Estructura alineada con la lógica de ISO 14224 (taxonomía de equipos).
- **Transición:** El Pareto confirma ese orden.

> [!warning] 102 fallas (Pareto 2021–2022) ≠ 113 fallas (indicadores 2019–2022): son periodos distintos; dilo antes de que pregunten.

## 16 · Criticidad de sistemas (Pareto) — 0:45 (acum. 12:41)
- **Objetivo:** Justificar el orden del AMEF.

> El Pareto de fallas por sistema es claro: motor diésel 79, generador 8, control y automatización 7, distribución 5, combustible externo 2 y arranque 1. Motor, generador y control suman el 92 % de las fallas. Por eso el AMEF se hace primero en el motor diésel y luego en el generador.

- **Técnica:** 79/102 = 77 %; (79+8+7)/102 = 92 %.
- **Transición:** Para priorizar dentro de cada sistema usé el número de prioridad de riesgo.

> [!warning] La tesis dice «80 % de las fallas» y titula la figura «horas acumuladas», pero el eje es número de fallas: di 77 % de las fallas. En la versión 10-07 la tabla de esta diapositiva (8 fallas, 31,5 h) NO está en la tesis: no la expongas.

## 17 · Número de prioridad de riesgo (NPR) — 1:10 (acum. 13:51)
- **Objetivo:** Explicar cómo priorizaste y qué encontraste en la cima.

> El NPR es severidad por ocurrencia por detección. Con las escalas de la tesis el máximo es 800, y fijé la prioridad en NPR mayor a 180. De 93 modos de falla, 47 superan el umbral: la mitad. En el motor son 31 de 67; en el generador, 7 de 8. Lo más revelador está en la cima: el NPR más alto, 336, no es un desgaste: es un filtro de combustible de especificación incorrecta, con detección 8; y el filtro de aceite incorrecto aparece con 280. Son errores de instalación que casi no se ven hasta que el motor falla. Por eso el plan exige controles de reinstalación.

- **Técnica:** 336 = 7 × 6 × 8. 12 modos tienen NPR exactamente 180; con «≥ 180» serían 59.
- **Transición:** Veamos cómo se lee una fila del AMEF del motor.

> [!warning] El umbral 180 es un criterio de la tesis, no una norma. En la versión 10-07 la tabla (NPR 256, 288, 224, 224) no coincide con la Matriz del NPR: no hay ningún NPR 288 en el motor.

## 18 · AMEF del motor diésel — 1:10 (acum. 15:01)
- **Objetivo:** Mostrar dominio de la cadena función → falla funcional → modo → efecto.

> El AMEF responde las primeras preguntas del RCM. La función 9 del motor es retener agua y partículas en dos etapas: el prefiltro Racor y el filtro principal. Su falla funcional es que el filtro principal deja pasar partículas finas. ¿Por qué? Porque se instala un filtro de especificación incorrecta o vencido. El efecto: contaminantes en la inyección y desgaste de inyectores. Severidad 7, ocurrencia 6, detección 8: NPR 336. En total el motor tiene 20 funciones, 27 fallas funcionales y 67 modos; 31 superan 180, y 20 de ellos están en admisión de aire y refrigeración. Por eso el foco es el paquete térmico.

- **Técnica:** Falla funcional = el «qué» (pérdida de función). Modo de falla = el «por qué» (causa física).
- **Transición:** El segundo sistema es el generador.

> [!warning] El subsistema escape figura en la taxonomía pero no en el AMEF del motor: «no registró fallas relevantes en el histórico». El NPR promedio por subsistema es indicador propio.

## 19 · AMEF del generador — 0:50 (acum. 15:51)
- **Objetivo:** Mostrar el componente eléctrico de la tesis: excitación.

> El generador tiene solo 8 modos, pero 7 superan 180, y 6 de ellos están en la excitación: varistor, diodos rotativos y regulador AVR. El de mayor riesgo es un varistor en cortocircuito por una descarga transitoria: se quema y deja sin protección a los diodos y a la tarjeta AVR; severidad 7, ocurrencia 8, detección 5, NPR 280. Además, los 8 modos tienen detección 5: se descubren tarde. Mejorar la detección baja todos los NPR del generador a la vez.

- **Técnica:** En un alternador sin escobillas, el AVR controla la corriente de campo de la excitatriz; el puente de diodos rotativo rectifica la salida de la excitatriz hacia el rotor principal; el varistor limita sobretensiones transitorias en ese puente.
- **Transición:** Con los modos priorizados, el árbol de decisiones asigna la tarea.

> [!warning] El AMEF menciona «STAMFORD HCI444C1» en la función 5; el activo es HCI544E1 (errata).

## 20 · Árbol de decisiones RCM — 1:00 (acum. 16:51)
- **Objetivo:** Explicar la lógica de Moubray y el resultado agregado.

> El árbol de decisiones toma cada modo del AMEF. Primero pregunta si la falla es evidente para el operador; si no lo es, es una falla oculta. Luego evalúa la consecuencia: seguridad, ambiente u operación. Después busca la tarea en un orden fijo: primero, ¿se puede medir la condición?; si no, ¿sirve un reacondicionamiento cíclico?; si no, ¿una sustitución cíclica?; y si nada de eso es factible, tareas a falta de: búsqueda de fallas, rediseño o ningún mantenimiento programado. En los 93 modos, 55 quedaron a condición, 20 con reacondicionamiento, 12 con sustitución y 2 a falta de. Medir primero; intervenir por tiempo solo cuando medir no es posible.

- **Técnica:** Conteo propio sobre las hojas de decisión; 4 filas del motor no tienen columna marcada.
- **Transición:** En el motor el patrón cambia según el subsistema.

> [!warning] No muestres conteos por tipo de consecuencia: las columnas S/E/O del Anexo están incompletas.

## 21 · Árbol de decisiones · motor diésel — 0:45 (acum. 17:36)
- **Objetivo:** Mostrar que las decisiones dependen del mecanismo de deterioro.

> En el motor, 39 de los 67 modos quedaron a condición. Admisión, lubricación y combustible se controlan sobre todo midiendo; la refrigeración, en cambio, con reacondicionamientos cíclicos: limpieza del intercooler, cambio de refrigerante y reacondicionamiento de la bomba, porque en el entorno minero la obstrucción por polvo es predecible. Para el filtro de combustible, la hoja asigna reemplazo cada 250 horas.

- **Técnica:** Tarea cíclica = se ejecuta por intervalo, aunque el componente esté bien; tarea a condición = se ejecuta solo si la medición supera un umbral.
- **Transición:** En el generador la decisión es aún más clara.

> [!warning] Para 9B1 la hoja dice «sustitución cada 250 h» y el plan «cambio por ΔP con sensor WIF». Dilo como refinamiento del plan.

## 22 · Árbol de decisiones · generador — 0:35 (acum. 18:11)
- **Objetivo:** Cerrar el árbol con el sistema eléctrico.

> En el generador, los 8 modos se controlan a condición: se mide la continuidad del varistor, la caída de voltaje en los diodos, el estado del AVR, la resistencia del bobinado y las vibraciones de rodamientos, y se interviene solo si la medición lo indica. Dos modos son fallas ocultas: el varistor en cortocircuito y la interrupción del puente de diodos; solo se revelan con pruebas.

- **Técnica:** Falla oculta: su pérdida de función no es evidente en operación normal.
- **Transición:** Las decisiones se convierten en un plan con frecuencia y responsable.

> [!warning] Moubray gestiona fallas ocultas con búsqueda de fallas (H4); la hoja las marca a condición (H1). Respuesta: la prueba periódica cumple la función de detección.

## 23 · Plan de mantenimiento · motor diésel — 0:45 (acum. 18:56)
- **Objetivo:** Mostrar la estructura del plan.

> El plan del motor traduce los 67 modos en 67 actividades con frecuencia, personal y justificación. 34 se ejecutan a diario o cada 250 horas o menos: inspecciones cortas y frecuentes, coherentes con equipos que difícilmente pasan 200 horas sin fallar. Solo 7 son de 1 500 horas o más: inyectores, turbo y calefactores. El técnico electromecánico lidera 44 de las 67: es el recurso crítico del plan.

- **Técnica:** Agrupación propia por frecuencia y por responsable principal.
- **Transición:** ¿Qué hace el plan con los modos de mayor riesgo?

> [!warning] Si usas la versión 10-07, sus diapositivas 23 a 25 son capturas de tablas: no las leas; explica dos o tres filas.

## 24 · Plan · tareas para los mayores NPR — 0:50 (acum. 19:46)
- **Objetivo:** Demostrar que las tareas tienen criterio medible.

> Para el modo de mayor riesgo, el filtro de combustible fuera de especificación, el plan cambia los filtros según la caída de presión e incorpora un sensor de agua en el Racor con drenaje automático. El filtro de aceite debe ser de 30 micras o menos; el intercooler se limpia cada 1 000 horas para mantener el aire de carga bajo 113 °C; y la protección térmica, que es una falla oculta, se prueba simulando la alarma a 98 °C y el apagado a 105 °C. El error de instalación en sí se ataca con kits estandarizados y checklist de reinstalación.

- **Técnica:** Umbrales del plan: ΔP ≤ 5 kPa en intercooler, T aire ≤ 113 °C, aceite 30–48 L, 250–300 kPa, consumo ≤ 0,12 L/h.
- **Transición:** En el generador el plan se apoya en mediciones eléctricas.

> [!warning] El sensor WIF detecta agua, no la especificación del filtro: la especificación la cubre el kitting y el checklist.

## 25 · Plan · generador — 0:35 (acum. 20:21)
- **Objetivo:** Mostrar las técnicas eléctricas de diagnóstico.

> Para el varistor, ensayo de tensión de clamp y termografía: si se desvía más de 10 % del nominal o hay un punto 20 °C más caliente, se cambia. Para los diodos, la tendencia del rizado DC y del desbalance de corriente de campo. El AVR se evalúa con un step-test cada 1 000 horas, y su falla se vigila con monitoreo continuo de voltaje y frecuencia, con alarmas por excepción.

- **Técnica:** Rizado DC = componente alterna en la corriente de excitación; crece cuando un diodo del puente rotativo se abre o entra en corto.
- **Transición:** Ejecutar este plan requiere personas y recursos.

> [!warning] Frecuencias del plan y de la hoja difieren (2A1: 2 000 h vs 500 h por tendencia): el plan es la versión vigente.

## 26 · Recurso humano — 0:35 (acum. 20:56)
- **Objetivo:** Mostrar quién ejecuta y quién analiza.

> El plan necesita cinco perfiles: técnico electromecánico, que participa en 67 de las 93 actividades; operario; planner de planta; personal predictivo; y servicios externos. Para el análisis RCM propongo un equipo multidisciplinario: facilitador, supervisor de producción, operador de campo, técnico de taller y supervisor de ingeniería.

- **Técnica:** Participación por perfil: cálculo propio sobre los tres planes.
- **Transición:** Y requiere recursos materiales.

> [!warning] La tesis no cuantifica horas-hombre ni número de técnicos: reconócelo.

## 27 · Recurso material — 0:30 (acum. 21:26)
- **Objetivo:** Conectar instrumentos con mantenimiento a condición.

> El plan requiere 91 recursos materiales por 54 709 dólares; el 85 % es instrumentación de medición: vibraciones, termografía, presión, calidad del combustible, aislamiento, armónicos y diagnóstico electrónico con VODIA. Sin instrumentos no hay mantenimiento a condición. La tesis precisa que este equipamiento es para toda la flota.

- **Técnica:** Agrupación por categoría: cálculo propio sobre la tabla presupuestal.
- **Transición:** Pasemos al análisis de costos y proyecciones.

> [!warning] Precios sin cotización citada: «son precios referenciales».

## 28 · Divisor · Costos y proyecciones — 0:08 (acum. 21:34)
- **Objetivo:** Transición.

> Veamos cuánto cuesta y cuánto mejora.

- **Técnica:** —
- **Transición:** Primero, la inversión.

> [!warning] No te detengas.

## 29 · Inversión en herramientas e insumos — 0:30 (acum. 22:04)
- **Objetivo:** Mostrar dónde está el dinero.

> Diez instrumentos concentran el 66 % de la inversión; los mayores son el analizador de armónicos y los scanners VODIA, con 6 000 dólares cada uno. La inversión se concentra en diagnóstico eléctrico y del motor, donde están los modos de mayor NPR.

- **Técnica:** Top 10 = US$ 36 200 de US$ 54 709.
- **Transición:** ¿Cuánto mejora la disponibilidad?

> [!warning] En la versión 10-07 la columna «Por qué es relevante según tu tesis» es texto de chatbot con afirmaciones falsas («Refrigeración concentra el 80 % del Pareto»). Elimínala antes de sustentar.

## 30 · Disponibilidad proyectada — 1:00 (acum. 23:04)
- **Objetivo:** Presentar el resultado principal con honestidad.

> Con el plan, la disponibilidad proyectada sube de 92,67 a 97,85 % en el GI500-16, de 93,94 a 96,90 % en el GI500-19 y de 93,34 a 97,78 % en el GI500-20. Las tres cifras son coherentes con la ecuación: por ejemplo, 250 entre 250 más 5,49 da 97,85 %. Y lo digo con transparencia: el GI500-19 queda en 96,90 %, una décima por debajo de la meta; su palanca es reducir el MTTR de 15,8 a 8 horas. Son proyecciones coherentes; la confirmación vendrá de medirlas.

- **Técnica:** La proyección se apoya en tareas concretas: diagnóstico por ΔP/ΔT, rizado DC, kits de repuestos y checklist de reinstalación.
- **Transición:** ¿De dónde sale esa mejora?

> [!warning] No digas «los tres superan la meta». Si preguntan cómo se fijó un MTTR de 5,49 h con dos decimales, ver P9.3.

## 31 · MTBF y MTTR proyectados — 0:50 (acum. 23:54)
- **Objetivo:** Explicar las palancas y acotar la cifra de horas recuperadas.

> El MTTR baja casi a la mitad en los tres equipos; el MTBF sube donde era bajo: de 145 a 250 horas en el GI500-16 y de 153 a 220 en el GI500-20. La tesis estima unas 1 102 horas de servicio recuperadas al año y cerca de 40 eventos correctivos evitados, bajo el supuesto de que cada equipo opera alrededor de 8 000 horas al año. Precisaré ese supuesto en la evaluación económica, porque es el que más influye en el resultado.

- **Técnica:** 1 102 h = ΔA × 8 760 h por equipo; 39,7 eventos = 8 000 h/año ÷ MTBF base − 8 000 h/año ÷ MTBF objetivo.
- **Transición:** Pasemos a la evaluación económica.

> [!warning] RIESGO CRÍTICO R1: la parada histórica registrada es ≈ 374 h/año en total (494,5 + 774,2 + 228,9 h en cuatro años). En la v9 esta diapositiva ya muestra las tres cifras (1 102 h de la tesis, 374 h del registro y 226 h acotadas): recórrelas de izquierda a derecha y nombra el supuesto antes de que lo haga el jurado.

## 32 · Inversión vs beneficio — 0:50 (acum. 24:44)
- **Objetivo:** Mostrar el cálculo y sus supuestos.

> La inversión es de 54 709 dólares. El beneficio anual proyectado en la tesis, 232 310 dólares, tiene dos componentes: 220 400 por horas recuperadas, que son 1 102 horas a 200 dólares la hora, y 11 910 por eventos evitados, 39,7 a 300 dólares cada uno. Quiero ser transparente: el 95 % del beneficio depende de dos supuestos, las 8 000 horas de operación al año y el valor de 200 dólares por hora de parada. Por eso, en la siguiente diapositiva presento escenarios más conservadores.

- **Técnica:** La tesis justifica el valor de la hora como ahorro por hora de parada «que puede ser facturada como modelo de negocio de renta» (4.5); no presenta flujo de caja.
- **Transición:** Veamos el retorno en distintos escenarios.

> [!warning] Si el jurado pregunta la fuente de los US$ 200/h: es un supuesto de la tesis sin cotización citada.

## 33 · Beneficio por equipo y periodo de retorno — 1:10 (acum. 25:54)
- **Objetivo:** Defender la viabilidad económica de forma robusta, no inflada.

> Con los supuestos de la tesis, la inversión se recupera en unos 2,8 meses. Pero hice dos verificaciones conservadoras. Primera: si valoro la hora de parada en los 16 dólares que resultan del capítulo I, el retorno sube a 1,9 años. Segunda, la más importante: si en lugar de 8 000 horas al año uso las horas de operación que realmente muestra el registro histórico, las horas recuperables bajan a unas 226 por año y el beneficio a unos 47 000 dólares; el retorno sería de aproximadamente 1,2 años con 200 dólares la hora. Y como el equipamiento sirve para toda la flota de 20 grupos, asignando solo la parte proporcional a estos tres equipos, la inversión se recupera en menos de dos años incluso en el escenario más bajo. La viabilidad se mantiene, pero el resultado real depende de medir las horas de operación y el costo de parada.

- **Técnica:** Escenario acotado (cálculo propio): parada/año = fallas/4 × MTTR; parada futura = (fallas/4 × MTBF base/MTBF objetivo) × MTTR objetivo. Ahorro ≈ 89 + 98 + 39 = 226 h/año; eventos evitados ≈ 6,4/año. Con US$ 16/h y asignación 3/20 de la inversión (US$ 8 206): beneficio ≈ US$ 5 518/año → ≈ 1,5 años.
- **Transición:** Con esto, paso a las conclusiones.

> [!warning] La v9 muestra los cinco escenarios en una tabla. El caso 4 (US$ 16/h y horas del registro, ≈ 9,9 años) está a la vista: no lo escondas; explícalo con el caso 5 (inversión repartida en la flota, ≈ 1,5 años).

## 34 · Divisor · Conclusiones — 0:08 (acum. 26:02)
- **Objetivo:** Transición.

> Para cerrar, las conclusiones.

- **Técnica:** —
- **Transición:** —

> [!warning] No te detengas.

## 35 · Conclusiones — 1:10 (acum. 27:12)
- **Objetivo:** Responder cada objetivo con lenguaje de propuesta y proyección.

> Primera conclusión: la aplicación del RCM permite llevar la gestión de un esquema correctivo y poco trazable a uno proactivo y verificable; el AMEF y el árbol de decisiones priorizaron tres focos: combustible externo, excitación y AVR, y paquete térmico con ventilación. Segunda, para el primer objetivo: al sustituir tareas por calendario por tareas a condición, la disponibilidad proyectada mejora entre 2,96 y 5,18 puntos según el equipo. Tercera, para el segundo objetivo: el programa lleva el MTTR objetivo a 5–8 horas, el MTBF a 220–250 horas y la disponibilidad a 96,9 % o más. Reconozco el límite principal: son proyecciones; validarlas exige medir disponibilidad, MTBF y MTTR durante al menos un año de implementación.

- **Técnica:** La correspondencia conclusión → objetivo es una lectura propia (la tesis no las rotula así).
- **Transición:** Dejo tres recomendaciones.

> [!warning] La conclusión primera de la tesis dice «migró»; tú di «permite migrar». Las ≈ 1 102 h y ≈ 40 eventos: si los mencionas, di «bajo el supuesto de 8 000 h/año».

## 36 · Recomendaciones — 0:35 (acum. 27:47)
- **Objetivo:** Mostrar visión de continuidad.

> Recomiendo, primero, un diagnóstico profundo del proceso real de mantenimiento; segundo, profundizar el AMEF y simular escenarios antes y después; y tercero, comparar con casos similares y justificar explícitamente el cálculo de MTBF, MTTR y sus supuestos. Para la empresa, el plan ya propone checklists de reinstalación, kits de repuestos, trazabilidad en CMMS, control de humedad y el fin de la canibalización.

- **Técnica:** La tercera recomendación responde precisamente a la debilidad de los supuestos económicos.
- **Transición:** Termino.

> [!warning] —

## 37 · Cierre — 0:22 (acum. 28:09)
- **Objetivo:** Cerrar con una idea memorable y ceder la palabra.

> En síntesis: analicé 93 modos de falla, prioricé 47 y propuse un plan que proyecta llevar la disponibilidad a 96,9–97,9 %. Muchas gracias por su atención; quedo atento a sus preguntas.

- **Técnica:** —
- **Transición:** —

> [!warning] Detén el cronómetro, mira la cámara y espera la primera pregunta sin agregar más.
