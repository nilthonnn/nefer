# Auditoría funcional de LadderLab

Revisión de la app de aprendizaje de Ladder (`docs/ladder/`) contra las normas
internacionales que gobiernan **lo que enseña** y **lo que simula**: el lenguaje
y sus instrucciones, la protección y transferencia de grupos electrógenos, el
sincronismo, la seguridad de máquinas y fajas, y la calidad y accesibilidad del
propio software.

No es una certificación: eso lo emite un organismo acreditado, no un informe
interno. Es la revisión que haría un auditor con el instrumental que hay aquí:
cada resultado se obtuvo ejecutando la app en un navegador, y se puede volver a
medir.

- [1. Resumen](#1-resumen)
- [2. Alcance y método](#2-alcance-y-método)
- [3. Matriz de conformidad por norma](#3-matriz-de-conformidad-por-norma)
- [4. Hallazgos y correcciones](#4-hallazgos-y-correcciones)
- [5. Evidencia de las pruebas](#5-evidencia-de-las-pruebas)
- [6. Lo que queda abierto](#6-lo-que-queda-abierto)

---

## 1. Resumen

| Medida | Antes | Después |
|---|---:|---:|
| Hallazgos mayores | 3 | **0** |
| Hallazgos menores | 3 | 0 en el contenido; 2 ejercicios propuestos |
| Observaciones | 3 | 0 |
| Puntos abiertos (sección 6) | — | 6 |
| Instrucciones conformes con IEC 61131‑3 (pruebas dirigidas) | 10/10 | **10/10** |
| Retos: la solución pasa y el programa inicial falla | 17/17 | **17/17** |
| Errores típicos que el corrector rechaza | 7/7 | **7/7** |
| Contraste mínimo de texto, tema claro (WCAG 1.4.3 pide 4,5:1) | 3,18:1 | **4,51:1** |
| Errores de JavaScript en todas las pantallas | 0 | 0 |

**Conclusión:** el núcleo es correcto. El simulador ejecuta las instrucciones
como dice IEC 61131‑3, y los retos se corrigen contra un modelo de planta que
detecta las fallas peligrosas. Los tres hallazgos mayores estaban en el
**criterio técnico** de dos ejercicios y en el **contraste** de la interfaz; los
tres se corrigieron.

---

## 2. Alcance y método

**Objeto:** `index.html`, `lecciones.js` y `energia.js`: 21 lecciones, 17 retos,
6 modelos de planta y el motor del PLC simulado.

**Método:**

1. **Pruebas dirigidas** del motor contra el comportamiento que IEC 61131‑3
   especifica para cada instrucción (sección 5.1).
2. **Pruebas de los retos:** la solución de referencia debe pasar y el programa
   inicial debe fallar (5.2).
3. **Pruebas negativas:** errores típicos de un alumno que el corrector tiene que
   rechazar, y con qué mensaje (5.3).
4. **Revisión documental:** cada cifra y criterio técnico de las lecciones se
   comparó con la norma correspondiente.
5. **Accesibilidad:** contraste medido con la fórmula de luminancia relativa de
   WCAG 2.2, y recorrido de las pantallas a 390 px y 1400 px.

---

## 3. Matriz de conformidad por norma

| Norma | Qué se verificó | Resultado |
|---|---|---|
| **IEC 61131‑3** (lenguajes de PLC) | Símbolos LAD; TON, TOF, TP, CTU, CTD, flancos, MOVE, aritmética, EN/ENO | Conforme. El desbordamiento de Int está abierto (6.1) |
| **IEC 60617 / IEC 61082** (símbolos) | Contactos, bobinas y cajas del editor | Conforme |
| **IEEE C37.2** (números de función ANSI) | 25, 25A, 27, 32, 52, 59, 81 | Conforme |
| **IEEE 1547‑2018**, **IEEE C50.12/C50.13** (sincronismo) | Ventanas de ΔV, Δf y Δφ del reto y de la lección | **Mayor A1, corregido** |
| **ISO 8528** (grupos electrógenos), **ISO 3046‑1** | Potencias, derrateo por altura, protecciones | Menor A5: corregido en la teoría; ejercicio propuesto |
| **NFPA 110** (sistemas de emergencia) | Tipo 10 (10 s), protecciones mínimas, enfriamiento | Conforme tras A5 |
| **IEC 60947‑6‑1**, **UL 1008** (equipos de transferencia) | Abrir antes de cerrar, enclavamientos, retransferencia | Menor A6: corregido en la teoría; modelo pendiente (6.4) |
| **IEC 60204‑1** (equipo eléctrico de máquinas) | Paro NC, sin rearranque automático tras un paro | Conforme |
| **ISO 13850** (parada de emergencia), **EN 620** (fajas de granel) | Pull‑cord enclavado con rearme manual | **Mayor A2, corregido** |
| **ISO 13849‑1 / IEC 62061** (seguridad funcional) | Que las funciones de seguridad no se presenten como lógica estándar | Conforme: la teoría lo advierte (6.2) |
| **MSHA 30 CFR 56.14201** (aviso antes de arrancar fajas) | Sirena de prearranque | Observación A7: aclarado |
| **ISO/IEC 25010** (calidad de producto) | Corrección funcional y fiabilidad de la evaluación | Menor A4, corregido |
| **WCAG 2.2 AA** | 1.4.3 contraste; 1.4.1 color; 2.4.3 orden del foco | **Mayor A3, corregido**. 2.4.3 abierto (6.3) |

---

## 4. Hallazgos y correcciones

### A1 · Mayor · Ventana de sincronismo más amplia que la norma — **corregido**

El reto permitía cerrar con **Δf hasta 0,25 Hz**, con ±10° de ángulo.
IEEE 1547‑2018 admite como máximo:

| Potencia del grupo | Δf | ΔV | Δφ |
|---|---:|---:|---:|
| Hasta 500 kVA | 0,3 Hz | 10 % | 20° |
| Más de 500 hasta 1 500 kVA | 0,2 Hz | 5 % | 15° |
| Más de 1 500 kVA | **0,1 Hz** | **3 %** | **10°** |

Para máquinas síncronas grandes, IEEE C50.12/C50.13 piden un deslizamiento
todavía menor (≈ 0,067 Hz). Los grupos de una planta minera superan
1 500 kVA, así que el reto enseñaba a cerrar fuera de norma.

**Corrección:**
- El reto pide ahora 0 ≤ Δf ≤ 0,10 Hz; el regulador sube la velocidad con
  Δf < 0,05 Hz y la baja con Δf > 0,10 Hz.
- El modelo de planta rechaza cualquier cierre con Δf fuera de −0,05 a +0,15 Hz.
- La lección explica la tabla por potencia.
- La prueba del paso 3 exige ahora que la frecuencia quede entre 60,04 y 60,10 Hz.

### A2 · Mayor · Pull‑cord modelado como pulsador momentáneo — **corregido**

Al soltar el cable, la entrada volvía sola a 1. Un interruptor de tirón real
**queda enclavado** y se rearma a mano en el propio interruptor (EN 620,
ISO 13850). Así se obliga a ir a revisar la faja antes de volver a ponerla en
servicio.

**Corrección:**
- Hay un tipo de entrada nuevo, `pullcord`: NC y enclavado. Un toque lo dispara
  y otro lo rearma.
- La lección explica que rearmarlo no vuelve a arrancar nada: hace falta una
  orden de marcha nueva (IEC 60204‑1).

### A3 · Mayor · Contraste insuficiente — **corregido**

| Color de texto (tema claro) | Antes | Después |
|---|---:|---:|
| Texto secundario sobre blanco | 3,55:1 | **5,33:1** |
| Texto secundario sobre gris de caja | 3,18:1 | **4,77:1** |
| Verde de estado sobre blanco | 3,57:1 | **5,03:1** |
| Texto secundario, tema oscuro | 4,40:1 | **5,27:1** |

WCAG 1.4.3 pide 4,5:1 para texto normal. Lo afectado eran direcciones,
subtítulos y valores en vivo, es decir, el texto que más se lee en el simulador.

El estado de la corriente cumple 1.4.1 (no depende solo del color): «conduce»
es una línea continua y «no conduce» una línea punteada.

### A4 · Menor · Ver la solución daba la misma recompensa — **corregido**

Cargar la solución y pulsar *Comprobar* sumaba los mismos XP e insignias que
resolver el reto. Eso falsea el progreso que muestra la app (ISO/IEC 25010,
corrección funcional).

**Corrección:** el reto queda completado, pero no suma XP ni da su insignia. La
app lo avisa al cargar la solución.

### A5 · Menor · Faltaban dos protecciones del grupo — **corregido en la teoría**

NFPA 110 e ISO 8528‑4 incluyen la parada por **falla de arranque**
(*overcrank*) y una **parada de emergencia** cableada que corta el combustible.

**Corrección:** las dos se explican en la lección. La falla de arranque queda
propuesta como ejercicio con un CTU y dos TON (6.5).

### A6 · Menor · TTA sin supervisión de discrepancia — **corregido en la teoría**

Si un interruptor no confirma su maniobra, la secuencia quedaba esperando para
siempre. Tampoco se explicaba que, con cargas de motores, hay que esperar a que
decaiga la tensión residual antes de reconectar: transición con retardo o
monitor en fase (IEC 60947‑6‑1).

**Corrección:** ambos puntos se explican en la lección. Modelarlos en la
planta queda pendiente (6.4).

### A7 · Observación · Duración de la sirena de prearranque — **aclarado**

El reto usa 5 s. En planta el aviso dura lo suficiente para que el personal se
retire, del orden de 10 a 30 s (MSHA 30 CFR 56.14201 y los reglamentos mineros
nacionales). La lección aclara que el tiempo está acortado para la práctica.

### A8 · Observación · Atajo de teclado no verificable — **corregido**

La lección decía «F11» para abrir las referencias cruzadas, un atajo que no
pude confirmar. Ahora indica la ruta del menú contextual.

### A9 · Observación · Línea redundante en el TP — **corregido**

Había una condición que nunca cambiaba el resultado. Se eliminó sin cambio de
comportamiento, como confirma la prueba 5.1.

---

## 5. Evidencia de las pruebas

### 5.1 Instrucciones contra IEC 61131‑3

| Prueba | Resultado |
|---|---|
| TON: Q a los PT; ET se detiene en PT (Q = 0 a 990 ms, Q = 1 a 1010 ms, ET = 1000 ms) | ✓ |
| TON: IN = 0 reinicia Q y ET | ✓ |
| TOF: Q inmediata; cae PT después de que cae IN | ✓ |
| TP: pulso de duración PT exacta, no redisparable | ✓ |
| CTU: cuenta flancos; Q = CV ≥ PV; R tiene prioridad sobre CU | ✓ |
| CTD: LD carga PV; Q = CV ≤ 0 | ✓ |
| Flanco P: RLO = 1 durante un solo ciclo (1 de 50) | ✓ |
| Doble asignación de una bobina: gana el último segmento | ✓ |
| MOVE con EN = 0 conserva OUT; DIV entre 0 da ENO = 0 | ✓ |
| ADD Int desbordado da ENO = 0 | ✓ (el valor de OUT queda abierto, 6.1) |

### 5.2 Retos

Los 17 retos se probaron: la solución de referencia pasa y el programa inicial
falla. Esto incluye los 6 de la ruta de grupos y minería, con la nueva ventana
de sincronismo.

### 5.3 Errores típicos que el corrector rechaza

| Error del alumno | Rechazo |
|---|---|
| Sincronismo sin ventana de fase | Paso 4: «Cierre fuera de sincronismo: Δφ = −144°» |
| Sincronismo sin verificar la tensión | Paso 3: «Cierre con diferencia de tensión fuera de rango» |
| Protección de presión de aceite sin inhibición | Paso 1: alarma con el grupo parado |
| Fajas sin retardos de cascada | Paso 4: CV‑01 arranca antes de tiempo |
| TTA sin confirmación de falla | Paso 2: el grupo arranca por un microcorte |
| TTA sin enfriamiento | Paso 8: el grupo para sin enfriarse |
| Arranque por demanda sin temporizador | Paso 2: G2 arranca por un pico |

---

## 6. Lo que queda abierto

1. **Desbordamiento de Int.** El simulador da ENO = 0 y satura el resultado en
   32 767. No pude confirmar qué valor escribe TIA Portal en OUT al desbordar.
   Hay que comprobarlo en S7‑PLCSIM e igualarlo.
2. **Seguridad funcional.** Los pull‑cord, paros y emergencias se programan en
   lógica estándar, como ejercicio. La teoría advierte que en planta van por un
   relé o PLC de seguridad (F‑CPU), con el nivel PL/SIL que fije la evaluación
   de riesgos (ISO 13849‑1, IEC 62061). Simular una F‑CPU queda fuera del
   alcance.
3. **Foco del editor (WCAG 2.4.3).** El cuadro de edición no retiene el foco
   del teclado ni lo devuelve al elemento editado al cerrarse.
4. **TTA y sincronismo en el modelo de planta.** Faltan dos cosas: la
   supervisión de discrepancia entre orden y realimentación del interruptor
   (con su tiempo límite) y la tensión residual de motores.
5. **Ejercicios propuestos:** falla de arranque del grupo (*overcrank*) y
   reparto de carga activa y reactiva entre grupos.
6. **Validación en un equipo real.** La comparación se hizo contra la
   especificación de IEC 61131‑3 y la documentación del fabricante, no contra
   un S7‑1200 o un PLCSIM. Lo ideal es repetir 5.1 en PLCSIM.
