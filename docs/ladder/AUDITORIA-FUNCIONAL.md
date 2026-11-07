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
| Hallazgos menores | 3 | **0** |
| Observaciones | 3 | **0** |
| Puntos abiertos de la primera revisión | 6 | **3**, que no se pueden cerrar desde aquí (sección 6) |
| Instrucciones conformes con IEC 61131‑3 (pruebas dirigidas) | 10/10 | **10/10** |
| Retos: la solución pasa y el programa inicial falla | 17/17 | **20/20** |
| Errores típicos que el corrector rechaza | 7/7 | **11/11** |
| Editor usable solo con teclado (WCAG 2.1.1, 2.4.3) | No | **Sí** |
| Contraste mínimo de texto, tema claro (WCAG 1.4.3 pide 4,5:1) | 3,18:1 | **4,51:1** |
| Errores de JavaScript en todas las pantallas | 0 | 0 |

**Conclusión:** el núcleo es correcto. El simulador ejecuta las instrucciones
como dice IEC 61131‑3, y los retos se corrigen contra un modelo de planta que
detecta las fallas peligrosas. Los tres hallazgos mayores estaban en el
**criterio técnico** de dos ejercicios y en el **contraste** de la interfaz; los
tres se corrigieron.

---

## 2. Alcance y método

**Objeto:** `index.html`, `lecciones.js` y `energia.js`. En la primera revisión
eran 21 lecciones, 17 retos y 6 modelos de planta; tras el cierre son 24
lecciones, 20 retos y 9 modelos de planta, más el motor del PLC simulado.

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
| **IEC 61131‑3** (lenguajes de PLC) | Símbolos LAD; TON, TOF, TP, CTU, CTD, flancos, MOVE, aritmética, EN/ENO | Conforme. Desbordamiento: ENO = 0 conforme; el valor de OUT, por confirmar en PLCSIM (6.1) |
| **IEC 60617 / IEC 61082** (símbolos) | Contactos, bobinas y cajas del editor | Conforme |
| **IEEE C37.2** (números de función ANSI) | 25, 25A, 27, 32, 52, 59, 81 | Conforme |
| **IEEE 1547‑2018**, **IEEE C50.12/C50.13** (sincronismo) | Ventanas de ΔV, Δf y Δφ del reto y de la lección | **Mayor A1, corregido** |
| **ISO 8528** (grupos electrógenos), **ISO 3046‑1** | Potencias, derrateo por altura, protecciones | Menor A5, **cerrado** con el reto de falla de arranque |
| **NFPA 110** (sistemas de emergencia) | Tipo 10 (10 s), protecciones mínimas, enfriamiento | Conforme tras A5 |
| **IEC 60947‑6‑1**, **UL 1008** (equipos de transferencia) | Abrir antes de cerrar, enclavamientos, retransferencia | Menor A6, **cerrado**: tensión residual en el modelo y reto de discrepancia |
| **IEC 60204‑1** (equipo eléctrico de máquinas) | Paro NC, sin rearranque automático tras un paro | Conforme |
| **ISO 13850** (parada de emergencia), **EN 620** (fajas de granel) | Pull‑cord enclavado con rearme manual | **Mayor A2, corregido** |
| **ISO 13849‑1 / IEC 62061** (seguridad funcional) | Que las funciones de seguridad no se presenten como lógica estándar | Conforme: la teoría lo advierte (6.2) |
| **MSHA 30 CFR 56.14201** (aviso antes de arrancar fajas) | Sirena de prearranque | Observación A7: aclarado |
| **ISO/IEC 25010** (calidad de producto) | Corrección funcional y fiabilidad de la evaluación | Menor A4, corregido |
| **WCAG 2.2 AA** | 1.4.3 contraste; 1.4.1 color; 2.4.3 orden del foco | **Mayor A3, corregido**. 2.1.1 y 2.4.3 **cerrados** (A10) |

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

**Corrección:** las dos se explican en la lección, y hay una lección nueva,
**«Falla de arranque: ciclos de arranque y reposo»**, con su reto: ciclos de
10 s (5 s de arranque y 5 s de reposo) y alarma tras el tercer intento fallido.
El modelo de planta detecta dos fallas: el arrancador que sigue engranado con
el motor en marcha y el que pasa más de 6 s seguidos energizado.

### A6 · Menor · TTA sin supervisión de discrepancia — **corregido en la teoría**

Si un interruptor no confirma su maniobra, la secuencia quedaba esperando para
siempre. Tampoco se explicaba que, con cargas de motores, hay que esperar a que
decaiga la tensión residual antes de reconectar: transición con retardo o
monitor en fase (IEC 60947‑6‑1).

**Corrección:**
- **Tensión residual:** el modelo de la TTA simula la tensión que dejan los
  motores de la barra al quedar sin alimentación, decayendo con τ = 0,4 s.
  Rechaza cualquier cierre mientras quede más del 25 %. El reto exige ahora
  **transición con retardo**: 52R cierra 1 s después de cumplir las condiciones.
  La solución anterior, sin retardo, ahora falla en el paso 8 con el mensaje
  «Cierre contra la tensión residual de los motores (78 %)».
- **Discrepancia:** hay una lección nueva, **«Supervisión de interruptores:
  discrepancia orden‑estado»**, con su reto. Pide 0,5 s de tolerancia, alarma
  memorizada, retiro y bloqueo de la orden, y detección del interruptor que no
  cierra o que se dispara estando cerrado.

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

### A10 · Accesibilidad del editor (WCAG 2.1.1, 2.4.3) — **cerrado**

- Cada instrucción del segmento es enfocable con Tab y se edita con Enter o
  Espacio.
- El cuadro de edición retiene el foco: Tab y Shift+Tab circulan dentro de él.
- Al cerrarlo con Esc, el foco vuelve a la instrucción editada, aunque el
  segmento se haya vuelto a dibujar. Una prueba automática lo confirma.

### A11 · Desbordamiento de Int (IEC 61131‑3) — **cerrado en lo que se puede verificar**

La documentación de Siemens confirma que ADD pone ENO = 0 cuando el resultado
se sale del rango. La lección de datos enseña ahora a tratarlo:
- comprobar ENO;
- no usar el valor de OUT tras un desbordamiento;
- calcular en DInt y limitar el resultado antes de guardarlo en un Int.

El valor exacto que TIA deja en OUT sigue sin confirmar (6.1).

### A12 · Reparto de carga (ejercicio propuesto) — **cerrado**

Hay una lección nueva, **«Reparto de carga entre grupos en paralelo»**:
gobernador y kW, AVR y kVAr, isócrono frente a *droop* (ISO 8528‑5), y banda
muerta. El reto pide igualar los kW de dos grupos ante cambios de demanda. El
modelo de planta dispara la protección 32 (potencia inversa) si G2 queda
motorizado más de 0,5 s.

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

Los 20 retos se probaron: la solución de referencia pasa y el programa inicial
falla. Esto incluye los 9 de la ruta de grupos y minería, con la ventana de
sincronismo de IEEE 1547 y la transición con retardo de la TTA.

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
| TTA sin transición con retardo | Paso 8: «Cierre contra la tensión residual de los motores (78 %)» |
| Arrancador sin límite de tiempo ni reposo | Paso 7: el arrancador no descansa |
| Discrepancia sin tiempo de tolerancia | Paso 2: alarma falsa en una maniobra normal |
| Reparto de carga con subir y bajar invertidos | Paso 1: G2 baja en vez de subir |

### 5.4 Teclado

| Prueba | Resultado |
|---|---|
| Enter sobre una instrucción enfocada abre el editor con el foco dentro | ✓ |
| 30 pulsaciones de Tab no sacan el foco del cuadro de edición | ✓ |
| Esc cierra y devuelve el foco a la misma instrucción | ✓ |

---

## 6. Lo que queda abierto

De los seis puntos de la primera revisión se cerraron tres: el foco del editor
(A10), el modelo de la TTA (A6) y los ejercicios propuestos (A5 y A12). Los
otros tres no se pueden cerrar desde aquí:

1. **Valor de OUT al desbordar un Int.** Lo que se puede verificar (ENO = 0) es
   conforme, y la app enseña a no usar OUT en ese caso. Para igualar el valor
   exacto que deja TIA hace falta medirlo en S7‑PLCSIM o en una CPU.
2. **Seguridad funcional (fuera de alcance).** Los pull‑cord, paros y
   emergencias se programan en lógica estándar, como ejercicio. La teoría
   advierte que en planta van por un relé o PLC de seguridad (F‑CPU), con el
   nivel PL/SIL que fije la evaluación de riesgos (ISO 13849‑1, IEC 62061).
   Simular una F‑CPU y su certificación está fuera del alcance de una app de
   estudio.
3. **Validación en un equipo real.** La comparación se hizo contra la
   especificación de IEC 61131‑3 y la documentación del fabricante, no contra
   un S7‑1200 o un PLCSIM. Para hacerla: repetir las pruebas de 5.1 en
   S7‑PLCSIM y anotar las diferencias.
