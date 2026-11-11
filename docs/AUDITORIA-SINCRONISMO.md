# Auditoria de funcionalidad — nefer sincronismo

Autoevaluacion reproducible (`nefer sincronismo auditoria`), no certificacion. Las normas se verifican por su contenido publico general.

**Conformidad: 56/60 requisitos cumplen (93.3 %).**

| Norma | Cumple | Parcial | No cumple |
|---|---:|---:|---:|
| ISO/IEC 25010 | 29 | 0 | 0 |
| SAE JA1011 | 9 | 0 | 0 |
| IEC 60812:2018 | 12 | 1 | 0 |
| AIAG-VDA 2019 | 2 | 0 | 0 |
| ISO 14224 | 0 | 2 | 1 |
| IEEE 1547-2018 | 1 | 0 | 0 |
| IEEE C37.2 | 1 | 0 | 0 |
| NFPA 110 (referencia) | 2 | 0 | 0 |


## ISO/IEC 25010

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Adecuacion funcional · completitud | La funcion «Permisivo de cierre ANSI 25» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo verificar → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Reparto actual kW/kVAr» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo reparto → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Prediccion por estatismo» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo estatismo → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Revision de protecciones» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo protecciones → codigo 1 |  |
| Adecuacion funcional · completitud | La funcion «Tendencias y reincidencias» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo tendencia → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Guia de sintomas» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo diagnostico → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Informe priorizado» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo informe → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Protocolo de puesta en marcha» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo protocolo → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Plantilla de planta» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo plantilla → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Diagrama TTA» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo diagrama → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Diagrama de sincronismo» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo diagrama → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Lamina didactica TTA» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo lamina → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Lamina didactica sincronismo» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo lamina → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Hoja de parametros» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo parametros → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Revision de parametros» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo parametros → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Menu de fallas RCM/AMEF» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo fallas → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Decodificador SPN/FMI» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo codigo → codigo 0 |  |
| Adecuacion funcional · completitud | La funcion «Flota mixta solo / paralelo» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo flota → codigo 1 |  |
| Adecuacion funcional · completitud | La funcion «AMEF completa y plan de accion» se ejecuta con los datos de ejemplo | **cumple** | nefer sincronismo amef → codigo 0 |  |
| Adecuacion funcional · correccion | Angulo de adelanto = 360 · 0.1 Hz · 0.1 s = 3.6° | **cumple** | esperado 3.6, obtenido 3.6 |  |
| Adecuacion funcional · correccion | Ventana IEEE 1547 para 625 kVA = 0.2 Hz / 5 % / 15° | **cumple** | esperado (0.2, 5.0, 15.0), obtenido (0.2, 5.0, 15.0) |  |
| Adecuacion funcional · correccion | Estatismo 4 %, vacio 62.4 Hz, plena carga → 60 Hz | **cumple** | esperado 60.0, obtenido 60.0 |  |
| Adecuacion funcional · correccion | Tendencia +0.2/dia desde 10 cruza 30 al dia 100 | **cumple** | esperado 2026-04-11, obtenido 2026-04-11 |  |
| Adecuacion funcional · correccion | Prioridad AIAG-VDA: S5 O1 D1 → baja | **cumple** | esperado baja, obtenido baja |  |
| Adecuacion funcional · correccion | Prioridad AIAG-VDA: S5 O1 D2 → alta (severidad manda) | **cumple** | esperado alta, obtenido alta |  |
| Adecuacion funcional · pertinencia | El objetivo «Eficaz (decidir bien en sitio)» esta cubierto | **cumple** | Funciones: Permisivo de cierre ANSI 25, Guia de sintomas, Lamina didactica sincronismo, Decodificador SPN/FMI |  |
| Adecuacion funcional · pertinencia | El objetivo «Proactivo (anticipar sin que pregunten)» esta cubierto | **cumple** | Funciones: Informe priorizado, Revision de protecciones, Revision de parametros, Flota mixta solo / paralelo |  |
| Adecuacion funcional · pertinencia | El objetivo «Predictivo (fecha de cruce)» esta cubierto | **cumple** | Funciones: Tendencias y reincidencias |  |
| Adecuacion funcional · pertinencia | El objetivo «Confiabilidad (RCM/AMEF)» esta cubierto | **cumple** | Funciones: Menu de fallas RCM/AMEF, AMEF completa y plan de accion |  |

## SAE JA1011

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Pregunta 1 | ¿Cuales son las funciones y los estandares de desempeño del activo en su contexto operacional actual? | **cumple** | cada funcion declarada, con su estandar: contestada |  |
| Pregunta 2 | ¿De que maneras puede fallar en el cumplimiento de sus funciones? | **cumple** | al menos una falla funcional por funcion: contestada |  |
| Pregunta 3 | ¿Que causa cada falla funcional? | **cumple** | al menos un modo de falla por falla funcional: contestada |  |
| Pregunta 4 | ¿Que sucede cuando ocurre cada modo de falla? | **cumple** | el efecto descrito en cada modo de falla: contestada |  |
| Pregunta 5 | ¿En que forma importa cada falla? | **cumple** | evidente u oculta, y al menos una consecuencia clasificada: contestada |  |
| Pregunta 6 | ¿Que debe hacerse para predecir o prevenir cada falla? | **cumple** | una decision de estrategia registrada por modo de falla: contestada |  |
| Pregunta 7 | ¿Que debe hacerse si no se encuentra una tarea proactiva adecuada? | **cumple** | la accion por defecto registrada donde no hubo tarea proactiva: contestada |  |
| 5.7 | Las fallas ocultas tienen busqueda de fallas o una tarea que reduzca la falla multiple | **cumple** | 13 ocultas; sin tarea adecuada: ninguna |  |
| 5.7 | Con consecuencia de seguridad no se elige operar hasta la falla | **cumple** | Modos de seguridad: 7; con operar hasta la falla: ninguno |  |

## IEC 60812:2018

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Planificacion | Alcance, contexto, equipo, fecha y revision documentados | **cumple** | activo PLANTA-GE-TTA, fecha 2026-11-11, revision 1, 2 participantes |  |
| Estructura | Cada modo de falla esta ubicado en sistema y componente | **cumple** | sin ubicacion: ninguno |  |
| Funciones | Cada funcion declara su estandar de desempeño | **cumple** | sin estandar: ninguna |  |
| Analisis de fallas | Cadena efecto – modo – causa completa | **cumple** | incompletos: ninguno |  |
| Analisis de riesgo | Controles actuales de prevencion y deteccion registrados | **cumple** | sin controles: ninguno |  |
| Analisis de riesgo | Escala de severidad, ocurrencia y deteccion documentada y propia de la organizacion | **parcial** | metodo: RPN clasico (EJEMPLO) | Reescribir los niveles de la escala de EJEMPLO con lo que significan en la planta. |
| Optimizacion | Toda prioridad alta tiene acciones | **cumple** | incumplen: ninguno |  |
| Optimizacion | Cada accion tiene responsable, plazo y verificacion | **cumple** | incumplen: ninguno |  |
| Optimizacion | La severidad solo baja con rediseño | **cumple** | incumplen: ninguno |  |
| Optimizacion | Las fallas ocultas tienen prueba con intervalo | **cumple** | incumplen: ninguno |  |
| Optimizacion | Las acciones son coherentes con la estrategia RCM | **cumple** | incumplen: ninguno |  |
| Optimizacion | Re-evaluacion del riesgo despues de las acciones | **cumple** | sin re-evaluar: ninguno |  |
| Documentacion | La AMEF se exporta en un formato de intercambio | **cumple** | CSV con columnas IEC 60812 / AIAG-VDA |  |

## AIAG-VDA 2019

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Paso 5 | La priorizacion usa prioridad de accion (severidad primero), no solo el NPR | **cumple** | El plan se ordena por prioridad, severidad y luego NPR; el NPR lleva su advertencia |  |
| Paso 6 | Ningun modo de severidad critica queda con prioridad residual alta sin escalar | **cumple** | pendientes: ninguno |  |

## ISO 14224

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Taxonomia | Cada modo de falla codificado en la taxonomia | **parcial** | 4/34 con codigo del catalogo de fabrica; 34/34 con codigo de la planta (catalogo-sincronismo.json) | El cargador RCM de FixMate solo valida contra el catalogo de fabrica: los codigos de sincronismo y TTA viajan como «codigo_planta». Integrar catalogos de planta al cargador. |
| Codigos de la norma | Los codigos propios mapean a los de ISO 14224 | **no cumple** | 0 entradas con codigo ISO mapeado | Los codigos de la norma son material con licencia: la planta los mapea en «codigo_iso» si tiene la norma. |
| Calidad de datos | La ocurrencia sale del historial de la propia instalacion | **parcial** | 33/34 modos con ocurrencia propuesta desde fuentes publicas | Reemplazar la ocurrencia con el historial de OT (nefer fixmate rcm contrastar). |

## IEEE 1547-2018

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Tabla 5 | Las ventanas de cierre por potencia se aplican al permisivo y a la revision de parametros | **cumple** | verificacion.LIMITES_IEEE1547 y parametros.revisar las usan |  |

## IEEE C37.2

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Numeros de dispositivo | Las protecciones se nombran por su numero ANSI (25, 32, 40, 27, 59, 81) | **cumple** | protecciones.FUNCIONES |  |

## NFPA 110 (referencia)

| Clausula | Requisito | Resultado | Evidencia | Accion |
|---|---|---|---|---|
| Mantenimiento y pruebas | Ejercicio mensual con carga del grupo y de la transferencia | **cumple** | Busqueda de «ejercicio» y «mensual» en el plan de accion |  |
| Mantenimiento y pruebas | Inspeccion semanal | **cumple** | Busqueda de «semanal» en el plan de accion |  |
