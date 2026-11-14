# Auditoría del Entrenador DSE

Fecha: 2026-11-14. Alcance: `docs/entrenador-dse/index.html`. Se revisaron la lógica de las simulaciones, los datos de los simuladores y las preguntas del examen. Las referencias fueron las normas aplicables, la documentación del fabricante y foros técnicos.

## 1. Auditoría funcional

Método: pruebas automáticas en Chromium (Playwright) que recorren cada escenario y verifican estado, registro y lecturas.

| # | Hallazgo | Efecto | Corrección | Prueba |
|---|---|---|---|---|
| F1 | El contador de intentos de arranque no se reiniciaba tras un arranque exitoso. | En la segunda falla de red el grupo empezaba en el intento 2. | Se reinicia al arrancar y con la red sana. | Pasa |
| F2 | Con el grupo parado por alarma y la red sana, Q1 no volvía a cerrar. | La carga quedaba sin energía con red disponible. | En alarma, Q1 cierra si la red está sana. | Pasa |
| F3 | Con el MSC cortado y la carga bajando, el grupo 1 mostraba 0 kW. | Se ocultaba la potencia inversa. | Lectura negativa y disparo por potencia inversa a los 3 s. | Pasa |
| F4 | En MANUAL no había retransferencia a red. | Solo se salía con STOP. | TRANSFERIR alterna entre grupo y red. | Pasa |
| F5 | El retardo de protecciones bloqueaba la toma de carga. | Agregaba unos 10 s a la transferencia. | Corre en paralelo con el calentamiento. | Pasa |
| F6 | El tiempo sin energía era un acumulado de toda la sesión. | No servía para evaluar una transferencia. | Se mide por corte y se compara con NFPA 110 Nivel 1 (10 s). | Pasa |
| F7 | El sincronizador apuntaba a 0,1 Hz aunque la ventana fuera menor. | Con ventana de 0,1 Hz nunca cerraba. | El objetivo es la mitad de la ventana. | Pasa |
| F8 | Faltaban fallas ocultas en las prácticas. | — | Se agregaron módulo fuera de AUTO, batería degradada y TC invertido. | Pasa |

Sin errores de JavaScript. Las vistas nuevas no desbordan a 390 px de ancho.

## 2. Validación de datos

| Dato | Antes | Ahora | Referencia | Estado |
|---|---|---|---|---|
| Ventana de check sync (ΔV) | 4 % | 5 % | Guía DSE 057-045: típico 0,1 Hz · 5 % · 5°. IEEE 1547-2003 (500–1 500 kVA): 0,2 Hz · 5 % · 15° | Ajustado |
| Deslizamiento y ángulo | 0,2 Hz · 10° | Sin cambio, más botones de referencia DSE e IEEE | Ídem | Validado |
| Longitud del MSC | 240 m | 240–250 m, usar el menor | DSE 056-011 y manual 8600 | Ajustado |
| Capacidad del MSC | 32 + 32, máx. 40 | Sin cambio | DSE 056-011 | Validado |
| Definiciones de temporizadores | — | Sin cambio | DSE 057-243 | Validado |
| Valores de temporizadores | 2/5/10/10/3/10/3/1/30/60 s | Sin cambio | No se encontró valor de fábrica publicado | Ejemplo |
| Prueba mensual con carga | — | Diésel ≥ 30 % de placa | NFPA 110 cap. 8 (fuentes secundarias) | Validado |
| Terminación CAN | ~60 Ω | Sin cambio | SAE J1939 (2 × 120 Ω) | Validado |
| Umbrales de protección y altitud | — | Sin cambio | Dependen del proyecto y del fabricante del motor | Ejemplo |

## 3. Examen

Las 15 preguntas originales se mantienen: ninguna contradice las fuentes. Se agregaron 5 preguntas: bloqueo de varias fuentes, TC invertido, módulo fuera de AUTO, NFPA 110 y batería. El examen queda en 20 preguntas y se aprueba con 16 (80 %).

## 4. Contenido agregado

- **Fallas**: 17 fallas, clasificadas como evidentes u ocultas, con síntoma, causas, forma de encontrarlas y el escenario donde se practican.
- **Seguridad**: marco peruano (DS 024-2016-EM, RESESATE-2013, estándares del titular), NFPA 70E y NFPA 110, cinco reglas de oro, tabla de peligros y controles, procedimientos de bloqueo, sincronización y TC, y lista de verificación.
- **Validación**: las tablas de este documento dentro de la página.

## 5. Limitaciones

- La red de la sesión no permitió abrir completos los PDF de DSE. Los valores del fabricante salen de extractos publicados por los buscadores, así que conviene contrastarlos con la revisión vigente de cada manual.
- Las normas peruanas se citan por nombre y no por artículo, porque han tenido modificaciones. Hay que verificar la versión vigente y el estándar interno del titular minero.

## Fuentes

- DSE, *Guide to Synchronising and Load Sharing Part 1* (057-045): https://jobatel.com/wp-content/uploads/2019/10/057-045_part1_guide.pdf
- DSE8610 MKII, página de producto: https://www.deepseaelectronics.com/genset/load-sharing-synchronising-control-modules/dse8610-mkii
- DSE8660 MKII, página de producto: https://www.deepseaelectronics.com/genset/load-sharing-synchronising-control-modules/dse8660-mkii
- DSE MSC Link (056-011): https://www.scribd.com/doc/299545483/056-011-MSC-Link
- DSE 8600 Configuration Suite: https://bestgenerator.spb.ru/amf-genset-deepsea-panel/pdf/dse-software/dse8600-software-manual-enu.pdf
- DSE7310/7320 MKII Configuration Suite (057-243): https://plantaselectricasdemexico.com/pdf/deepSea/DSE7310-MKII-DSE7320-MKII-Configuration-Suite-PC-Software-Manual.pdf
- Tabla IEEE 1547-2003 (manual ADVC3, Schneider Electric): https://www.productinfo.schneider-electric.com/advc-operationsmanual/pkr39809_advc_operations-manual/English/BM_ADVC3%20Operations%20Manual_0000999204.xml/$/TPC_ADVC3_OM_StandardsandGuidelinesCPT_0001050823
- Ejemplo de 0,2 Hz con DSE8610 (All Power Labs): https://www.allpowerlabs.com/wp-content/uploads/2015/05/v1-09_Section_10_GridTie.pdf
- NFPA 110, resumen de pruebas: https://industrialmonitordirect.com/blogs/knowledgebase/nfpa-110-generator-testing-requirements-and-frequency-standards
- Foros: https://www.eng-tips.com/threads/generator-tripping-while-paralleling.504585/ · https://www.eng-tips.com/threads/paralleling-generator-troubleshooting.511969/ · https://forums.mikeholt.com/threads/reverse-power-condition-or.106818/ · https://control.com/forums/threads/unbalance-load-reverse-power-in-synchronization.51018/ · https://control.com/forums/threads/generators-in-parallel-power-factor-problems.43871/
- Guía de fallas DSE7320 (terceros, MPU y CAN): https://accessories.huaquanpower.net/dse7320-controller-guide/
- DS 024-2016-EM: https://lpderecho.pe/reglamento-de-seguridad-y-salud-ocupacional-en-mineria-ds-024-2016-em/
- RESESATE-2013 (RM 111-2013-MEM/DM): https://buenaventura.com/wp-content/uploads/2024/10/RM-111-2013-EM-DM-Reglamento-de-Seguridad-y-Salud-en-el-Trabajo-en-Electricidad.pdf
