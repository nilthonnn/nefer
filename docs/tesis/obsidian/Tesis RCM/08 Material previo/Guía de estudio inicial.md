---
tags: [material-previo]
---

> [!note] Primera guía de estudio generada en la sesión. Algunas cifras fueron refinadas después: ante diferencias, manda [[Riesgos de defensa]] y [[Fórmulas y cifras clave]].

# Guía de sustentación

**Tesis:** *Implementación de la metodología RCM para la reducción de fallas y maximización de la disponibilidad operativa del grupo electrógeno Rivera Diesel de 500 kW, Moquegua 2024*
**Autor:** Nilthon Rosinaldo Chite Vilca · Ingeniería Eléctrica · Universidad Continental

> Cómo usar esta guía: lee primero las secciones 1 y 2 (qué vas a decir), memoriza la 3 (cifras), estudia la 4 y la 5 (teoría y fórmulas), y dedica el mayor tiempo a la **6 (puntos débiles)** y la **7 (preguntas del jurado)**. La 8 es una lista de correcciones para hacer al documento si aún puedes.

---

## 1. Tu tesis en 60 segundos

> «Una empresa de alquiler de maquinaria opera 20 grupos electrógenos con un mantenimiento predominantemente correctivo, con canibalización de componentes y sin trazabilidad de fallas. Mediante una matriz de criticidad seleccioné los tres equipos más críticos: tres grupos de 500 kW con motor Volvo Penta TAD1642GE y alternador Stamford HCI544E1 (GI500-16, GI500-19 y GI500-20), con disponibilidades de entre 92,7 % y 93,9 % frente a un objetivo del 97 %.
> Apliqué la metodología RCM-II de Moubray: taxonomía del activo, Pareto de horas de parada, AMEF por sistema, Número de Prioridad de Riesgo y la hoja de decisión RCM. Con ello obtuve un plan de mantenimiento con tareas a condición, sustituciones cíclicas, búsqueda de fallas y rediseños, más controles de reinstalación para eliminar las fallas inducidas.
> La proyección indica que el MTTR baja de 11–16 h a 5–8 h y que la disponibilidad sube a entre 96,9 % y 97,9 %, lo que equivale a unas 1 100 horas/año recuperadas y unos 40 eventos correctivos evitados por año en los tres equipos.»

**Idea fuerza que debes repetir:** *el problema no es solo el desgaste: son las fallas inducidas por intervenciones sin control (extracciones, reinstalaciones y canibalización). El RCM ataca esa causa raíz.*

---

## 2. Guion de exposición (15–20 min, 14 diapositivas)

| # | Diapositiva | Qué decir (mensaje central) | Tiempo |
|---|---|---|---|
| 1 | Título | Título, autor, asesor. | 0:30 |
| 2 | Contexto | Mercado de alquiler (~US$ 620 M en 2023); los grupos electrógenos son de los equipos más alquilados. | 1:00 |
| 3 | Problema | Mantenimiento reactivo, canibalización, informes de hasta 10–30 días por WhatsApp o correo, disponibilidad del 92–94 % frente al 97 %. | 1:30 |
| 4 | Problema, objetivos e hipótesis | Lee el problema general y los dos objetivos específicos. | 1:00 |
| 5 | Marco teórico (síntesis) | RCM: las 7 preguntas de SAE JA1011, las consecuencias y los tipos de tarea. MTBF, MTTR y disponibilidad. | 2:00 |
| 6 | Metodología | Investigación aplicada, enfoque cuantitativo, diseño **no experimental y propositivo**; población de 20 equipos; muestra de 3 por criticidad. | 1:30 |
| 7 | Diagnóstico | Tabla de indicadores base (fallas, D, MTBF, MTTR). Curvas de confiabilidad. | 1:30 |
| 8 | Criticidad | Fórmula y resultado: 150, 140 y 130, todos de alta criticidad (C). | 1:00 |
| 9 | Taxonomía y Pareto | 8 sistemas; el motor diésel concentra el ~80 % de las horas de parada. | 1:00 |
| 10 | AMEF y NPR | Un ejemplo resuelto (obstrucción del intercooler: S=8, O=8, D=4 → NPR 256). Umbral NPR > 180. | 2:00 |
| 11 | Hoja de decisión y plan | Tipos de tarea asignados (a condición, reacondicionamiento/sustitución cíclica, búsqueda de fallas, rediseño); recursos humanos y materiales. | 2:00 |
| 12 | Resultados proyectados | MTBF, MTTR y disponibilidad: antes frente a después (tabla de la sección 3). | 1:30 |
| 13 | Análisis económico | Inversión de US$ 54 709 (para toda la flota). Beneficio conservador de ~US$ 11 900/año (solo eventos evitados) y beneficio total de ~US$ 232 000/año valorando la hora de parada. | 1:30 |
| 14 | Conclusiones y recomendaciones | Las 3 conclusiones + «cero canibalización» + piloto de 6 meses para validar. | 1:00 |

> **Consejo:** en la diapositiva 6 di explícitamente «los resultados son **proyectados**; la validación en campo es la siguiente etapa». Si lo dices tú primero, el jurado no podrá usarlo como ataque.

---

## 3. Cifras que debes saber de memoria

### 3.1 Indicadores base (periodo histórico) y proyectados

| Equipo | Fallas | MTBF base (h) | MTTR base (h) | D base | MTBF proyectado (h) | MTTR proyectado (h) | D proyectada | ΔD (pp) | h/año recuperadas |
|---|---|---|---|---|---|---|---|---|---|
| **GI500-16** | 43 | 145,3 | 11,5 | 92,67 % | 250 | 5,49 | 97,85 % | +5,18 | 454 |
| **GI500-19** | 49 | 245 | 15,8 | 93,94 % | 250 | 8 | 96,90 % | +2,96 | 259 |
| **GI500-20** | 21 | 152,8 | 10,9 | 93,34 % | 220 | 5 | 97,78 % | +4,44 | 389 |
| **Total** | 113 | | | | | | | | **≈ 1 102** |

- Objetivo (target) de disponibilidad: **97 %**.
- Eventos evitados por año: 23,1 + 0,7 + 16 = **≈ 40**, con la hipótesis de **8 000 h/año** de operación.
- Horas recuperadas: 656 h por la reducción del MTTR y 446 h por el aumento del MTBF.

### 3.2 Criticidad (matriz de 20 equipos)

| Equipo | FF | Consecuencia | Criticidad | Nivel |
|---|---|---|---|---|
| GI500-19 | 5 | 30 | **150** | C |
| GI500-16 | 5 | 28 | **140** | C |
| GI500-20 | 5 | 26 | **130** | C |
| Siguiente equipo (GI250-01) | 4 | 21 | 84 | SC |

Rangos: 5–39 = NC (no crítico) · 40–89 = SC (semicrítico) · 90–200 = C (crítico).

### 3.3 Economía

| Concepto | Valor |
|---|---|
| Inversión en instrumentos, herramientas e insumos | **US$ 54 709** (≈ S/ 190 397, tipo de cambio de 09/2025), **para toda la flota** |
| Valor de la hora de parada (Cd) | US$ 200/h |
| Costo por evento correctivo (Ce) | US$ 300/evento |
| Beneficio por horas recuperadas | US$ 220 400/año |
| Beneficio por eventos evitados | US$ 11 910/año |
| **Beneficio anual total** | **US$ 232 310** |
| Recuperación de la inversión (cálculo propio, no figura en la tesis) | ~0,24 años (≈ 3 meses) con el beneficio total; ~4,6 años con solo los eventos evitados |

### 3.4 Datos técnicos del equipo

| Elemento | Dato |
|---|---|
| Motor | Volvo Penta TAD1642GE: 6 cilindros en línea, 16,12 L, turboalimentado, relación de compresión 16,5:1, control electrónico EMS2 |
| Potencia del motor a 1 800 rpm | Prime 532 kW · Standby 585 kW (con ventilador) |
| Alternador | Stamford HCI544E1: síncrono, 500 kW a FP 0,8 (625 kVA), 60 Hz, aislamiento clase H, IP23, paso de devanado 2/3, 12 terminales |
| Excitación | Autoexcitado con AVR AS440 (±1 %), u opción PMG con MX341/MX321 (±0,5 %) |
| Lubricación | 48 L, presión de 300–650 kPa, filtro de 30 µm, cambio cada 400–600 h |
| Refrigeración | 60 L, termostato de 82–92 °C, alarma/parada EMS2 a 98/105 °C |
| Velocidad | $n = 120 f / p = 120 \cdot 60 / 4 = 1\,800$ rpm (4 polos) |

---

## 4. Teoría que te van a preguntar

### 4.1 Origen y normas del RCM

- **Origen:** Nowlan y Heap (1978), *Reliability-Centered Maintenance*, United Airlines, por encargo del Departamento de Defensa de EE. UU. Surge de la aviación (MSG-1, MSG-2, MSG-3).
- **Moubray** (1991; 2.ª ed. 1997) adaptó el método a la industria: **RCM-II**.
- **SAE JA1011 (1999, rev. 2009):** criterios mínimos que debe cumplir un proceso para llamarse RCM (las 7 preguntas).
- **SAE JA1012 (2002, rev. 2011):** guía de aplicación de JA1011.
- **ISO 14224:2016:** estructura de datos de confiabilidad y mantenimiento (taxonomía de 9 niveles); base de la taxonomía de la tesis.
- **ISO 55000/55001:2014:** gestión de activos (marco en que se inserta el RCM).
- **UNE-EN 13306:** terminología de mantenimiento · **UNE-EN 15341:** indicadores clave de mantenimiento.

### 4.2 Las 7 preguntas del RCM (SAE JA1011)

1. ¿Cuáles son las **funciones** y los estándares de desempeño del activo en su contexto operacional?
2. ¿De qué manera **falla** en cumplir sus funciones? (fallas funcionales)
3. ¿Cuál es la **causa** de cada falla funcional? (modos de falla)
4. ¿Qué **sucede** cuando ocurre cada falla? (efectos de falla)
5. ¿En qué sentido **importa** cada falla? (consecuencias)
6. ¿Qué se puede hacer para **predecir o prevenir** cada falla? (tareas proactivas e intervalos)
7. ¿Qué hacer si no se encuentra una tarea proactiva adecuada? (**acciones a falta de**)

> Las preguntas 1–4 corresponden a la **hoja de información (AMEF)**; las 5–7, a la **hoja de decisión**.

### 4.3 Categorías de consecuencias (pregunta 5)

| Categoría | Criterio | Ejemplo en tu tesis |
|---|---|---|
| **Ocultas (H)** | La falla no es evidente para los operadores en condiciones normales. | Protección por alta temperatura del EMS2 que no actúa; calentador de admisión que no se usa hasta un arranque en frío. |
| **Seguridad / medio ambiente (S/E)** | Puede herir o matar, o incumplir una norma ambiental. | Derrame de combustible desde el tanque externo; incendio por recalentamiento. |
| **Operacionales (O)** | Afecta la producción o el servicio. | Parada del grupo → pérdida de horas facturables del alquiler. |
| **No operacionales (N)** | Solo cuesta la reparación. | Una fuga menor detectada sin parada. |

### 4.4 Tipos de tarea (pregunta 6 y 7) — códigos de tu tesis

| Código | Tarea | Cuándo aplica | Ejemplo en tu plan |
|---|---|---|---|
| **OC** | A condición (predictiva) | Existe una condición de falla potencial detectable (intervalo P-F). | ΔP/ΔT en radiador e intercooler; rizado de la corriente de campo; IR/PI; vibraciones. |
| **RC** | Reacondicionamiento cíclico | Hay una edad identificable de desgaste y se puede restaurar. | Calibración en banco de la bomba de alta presión e inyectores. |
| **SC** | Sustitución cíclica | Hay una edad de desgaste y es más barato reemplazar. | Fajas, rodamientos del cubo del ventilador, mangueras. |
| **FF** | Búsqueda de fallas (*failure finding*) | Solo para fallas **ocultas**: prueba funcional periódica. | Prueba de los disparos del EMS2 a 98/105 °C; prueba del calentador. |
| **RD** | Rediseño | Si la consecuencia es de seguridad y no hay tarea eficaz, es **obligatorio**. | Techado de la casa de fuerza, sellado y desecantes en gabinetes, mallas antipolvo. |
| **NMP** | Ningún mantenimiento programado | Consecuencia solo económica y la tarea cuesta más que la falla. | Componentes de bajo costo que se cambian al fallar. |

### 4.5 Curva P-F y patrones de falla

- **Curva P-F:** P es el punto en que la falla potencial se vuelve detectable; F es la falla funcional. La tarea a condición debe ejecutarse con un intervalo **menor que el intervalo P-F** (regla práctica: la mitad, P-F/2).
- **Seis patrones de falla (Nowlan y Heap):** A (bañera), B (desgaste), C (desgaste gradual), D (aumento inicial y luego constante), E (aleatorio) y F (mortalidad infantil).
  - Solo alrededor del **11 %** de los componentes estudiados en la aviación tenía un patrón ligado a la edad (A, B, C); alrededor del **89 %** no lo tenía.
  - Por eso el mantenimiento por calendario no basta y **el RCM prioriza las tareas a condición**.
  - El patrón F (mortalidad infantil) incluye las **fallas inducidas por intervención**, que es exactamente tu hallazgo de reinstalaciones sin control.

### 4.6 Indicadores

| Indicador | Fórmula | Nota |
|---|---|---|
| MTBF | $\dfrac{\text{tiempo total de operación}}{\text{n.° de fallas}}$ | Confiabilidad |
| MTTR | $\dfrac{\text{tiempo total de reparación}}{\text{n.° de reparaciones}}$ | Mantenibilidad |
| Tasa de fallas | $\lambda = 1/\text{MTBF}$ | Supone λ constante |
| Disponibilidad | $D = \dfrac{\text{MTBF}}{\text{MTBF}+\text{MTTR}}$ | Ver la diferencia entre $A_i$ y $A_o$ abajo |
| Confiabilidad (exponencial) | $R(t) = e^{-\lambda t}$ | Fallas aleatorias, β = 1 |
| Confiabilidad (Weibull) | $R(t) = e^{-(t/\eta)^\beta}$ | β < 1: infantil · β = 1: aleatoria · β > 1: desgaste |

**Tipos de disponibilidad (pregunta casi segura):**

- **Inherente** $A_i = \dfrac{MTBF}{MTBF+MTTR}$: solo considera el tiempo activo de reparación.
- **Alcanzada** $A_a = \dfrac{MTBM}{MTBM+\bar M}$: incluye el mantenimiento preventivo.
- **Operacional** $A_o = \dfrac{MTBM}{MTBM+MDT}$: incluye las demoras logísticas y administrativas (MLDT).

> Tu fórmula (4) es la de $A_i$. Tu defensa: *«En esta tesis el MTTR se calculó con el tiempo total de indisponibilidad registrado, que incluye la espera de repuestos y las demoras administrativas; por eso el indicador se aproxima a la disponibilidad operacional»*.

### 4.7 Criticidad y NPR

- **Criticidad** = Frecuencia × Consecuencia, donde Consecuencia = (Costo + Seguridad + Ambiental) + (Impacto operacional × Tiempo de reparación).
  - Máximo: 5 × [(5+5+5) + 5×5] = 5 × 40 = 200.
- **NPR** = Severidad × Ocurrencia × Detección.
  - Con tus escalas (S hasta 8; O y D hasta 10), el máximo es 800.
  - Usaste el umbral NPR > 180 para priorizar.

---

## 5. Cálculos resueltos con tus datos (para la pizarra)

**Disponibilidad del GI500-16 (base):**
$$D = \frac{145{,}3}{145{,}3 + 11{,}5} = \frac{145{,}3}{156{,}8} = 0{,}9267 = 92{,}67\ \%$$

**Disponibilidad del GI500-16 (proyectada):**
$$D = \frac{250}{250 + 5{,}49} = 0{,}9785 = 97{,}85\ \%$$

**Horas recuperadas por año:**
$$\Delta h = \Delta D \times 8\,760 = 0{,}0518 \times 8\,760 = 454\ \text{h/año}$$

**Eventos por año** (con 8 000 h/año): $8\,000/145{,}3 = 55{,}1$ → $8\,000/250 = 32$, por lo que se evitan $\approx 23$.

**Criticidad del GI500-19:**
Consecuencia = (5 + 5 + 4) + (4 × 4) = 14 + 16 = 30 → Criticidad = 5 × 30 = **150**.

**NPR por obstrucción del intercooler:** 8 × 8 × 4 = **256**.

**Confiabilidad exponencial del GI500-16 a 100 h:**
$\lambda = 1/145{,}3 = 0{,}00688$ h⁻¹ → $R(100) = e^{-0{,}688} = 0{,}50$ (50 % de probabilidad de llegar a 100 h sin fallar).

**Recuperación de la inversión:** $54\,709 / 232\,310 = 0{,}24$ años; con el escenario conservador, $54\,709 / 11\,910 = 4{,}6$ años.

> Todas estas cifras las verifiqué contra tu documento y **cuadran aritméticamente**. Puedes rehacerlas con seguridad frente al jurado.

---

## 6. Puntos débiles: lo que el jurado puede atacar y cómo responder

Ordenados del más al menos peligroso.

### 🔴 6.1 «¿Implementó o propuso? Sus resultados son proyectados.»
- **Riesgo:** el título y el objetivo dicen «implementar», pero el resumen dice «carácter proyectado».
- **Respuesta:** «La tesis desarrolla el análisis RCM completo y el plan de implementación. Los indicadores de resultado se obtienen por **proyección determinística** a partir de la línea base histórica y de los tiempos objetivo de cada tarea. La validación con datos post-implementación queda como la siguiente etapa, que recomiendo hacer con un piloto de 6 meses en el GI500-16.»
- **No digas** que ya se implementó si no hay datos posteriores.

### 🔴 6.2 Diseño: ¿cuasi-experimental o no experimental?
- **Riesgo:** el Capítulo III dice **ambas cosas**: «cuasi-experimental» en el apartado de método y «no experimental» en el de diseño.
- **Respuesta (elige una y sostenla):** «El diseño es **no experimental, de tipo propositivo**: no se manipuló la variable sobre los equipos durante el estudio. Se diagnosticó la situación real y se propuso un plan. La mención a cuasi-experimental es un error de redacción.»
- Del mismo modo, «aplicada» es el **tipo** de investigación, no el alcance. El **alcance** es **descriptivo-propositivo** (o explicativo, si lo justificas).

### 🔴 6.3 ¿Cómo contrastó la hipótesis?
- **Respuesta:** «Mediante la comparación de los indicadores base (MTBF, MTTR y D) con los proyectados por equipo. La hipótesis se sostiene si la disponibilidad proyectada alcanza el objetivo del 97 %: se cumple en el GI500-16 (97,85 %) y en el GI500-20 (97,78 %), y el GI500-19 queda en 96,90 %, a 0,1 pp. Es una contrastación **por proyección**, no estadística inferencial.»
- **Tenlo claro:** el GI500-19 **no llega** al 97 %. Admítelo y explica que su MTBF ya era alto (245 h) y que la mejora viene casi toda del MTTR.

### 🔴 6.4 La frecuencia de fallas en la matriz de criticidad
- **Riesgo:** asignaste FF = 5 («más de 20 fallas/año») a los tres equipos, pero tus datos dicen 49, 43 y 21 fallas en el periodo histórico. Si el periodo es de ~4 años, eso son ~12, ~11 y ~5 fallas/año, que corresponden a FF = 3, 3 y 2.
- **Recalculado con esos valores:** GI500-19 = 3 × 30 = 90 (sigue siendo **C**) · GI500-16 = 3 × 28 = 84 (**SC**) · GI500-20 = 2 × 26 = 52 (**SC**).
- **Antes de la sustentación, verifica qué conteo usaste.** Si contaste **todas las órdenes de trabajo correctivas** (incluidas paradas menores sin indisponibilidad larga) y no solo las 43/49/21 fallas con parada, dilo así: «la frecuencia de la matriz considera todos los eventos correctivos registrados por año, no solo los que generaron indisponibilidad».
- Si no tienes ese sustento, la respuesta honesta es: «el GI500-19 resulta crítico con cualquier criterio, y los tres comparten modelo, contexto y modos de falla, por lo que el análisis de uno es extensible a los otros».

### 🟠 6.5 Base de horas: 8 760 frente a 8 000 frente a la utilización real
- **Riesgo:** las horas recuperadas usan 8 760 h/año, los eventos usan 8 000 h/año, y la utilización histórica fue menor. Por ejemplo, el GI500-16 tiene 43 × 145,3 ≈ 6 250 h de operación en todo el periodo, pero la proyección supone 55 eventos/año.
- **Respuesta:** «Normalicé la proyección a un régimen de **operación continua de un contrato minero** (8 000 h/año) para comparar los tres equipos en igualdad de condiciones. Las horas recuperadas son un **techo** en régimen continuo; con menor utilización, el beneficio escala proporcionalmente.»

### 🟠 6.6 La incongruencia entre US$ 12 000 y US$ 232 310
- **Riesgo:** el resumen y la justificación dicen «ahorro superior a US$ 12 000/año», pero el análisis económico da US$ 232 310/año.
- **Respuesta:** «Son dos escenarios. **US$ 11 910** es el ahorro **directo y conservador** (eventos correctivos evitados × US$ 300, que coincide con el costo histórico de ~US$ 306 por evento: US$ 15 000 / 49). **US$ 232 310** añade el **valor de las horas de disponibilidad recuperadas** (a US$ 200/h), que la empresa puede facturar como alquiler. En el resumen informé el valor conservador.»

### 🟠 6.7 Valor de la hora de parada: US$ 200/h frente a US$ 16/h
- **Riesgo:** en la justificación, US$ 2 752 / 172 h ≈ **US$ 16/h**; en el análisis económico, **US$ 200/h**.
- **Respuesta:** prepara de dónde sale el valor de US$ 200/h (tarifa de alquiler de un equipo de 500 kW con operador, penalidades contractuales o costo de un equipo de reemplazo). Si no lo tienes documentado, di: «US$ 16/h es el lucro cesante directo registrado; US$ 200/h incluye penalidades y el costo de reposición con otro equipo. El escenario conservador de US$ 11 910 no depende de ese valor».

### 🟠 6.8 Las 172 horas de inactividad del GI500-19
- **Riesgo:** la justificación habla de «172 h de inactividad en 4 años» para el GI500-19, pero 49 fallas × 15,8 h = **774 h**.
- **Respuesta:** aclara si las 172 h corresponden solo a ciertos sistemas (enfriamiento, eléctrico y combustible) o si es un dato a corregir.

### 🟠 6.9 Curvas de confiabilidad sin parámetros
- **Riesgo:** describes la curva del GI500-16 como «exponencial, característica de fallas tempranas», pero la exponencial corresponde a **fallas aleatorias** (β = 1), no tempranas. Para el GI500-19 hablas de «fallas tempranas» y de «fase de desgaste» a la vez, lo que es contradictorio. Y no reportas β ni η.
- **Preparación:** busca en tu Excel los valores de **β y η** de cada equipo. Interpretación: β < 1 = mortalidad infantil (coherente con las fallas inducidas por reinstalación); β ≈ 1 = aleatorias; β > 1 = desgaste.
- **Respuesta tipo:** «β = __ indica predominio de [mortalidad infantil], coherente con las fallas inducidas por intervenciones sin control; por eso el plan prioriza los controles de reinstalación y las pruebas de liberación.»

### 🟡 6.10 Periodos que no coinciden
- **Riesgo:** el título dice 2024; el problema, el objetivo y la hipótesis dicen 2020–2023; la tabla base, 2019–2022; el texto del GI500-16, 2019–2021; el Pareto, 2021–2022; la delimitación, 2023–2025.
- **Respuesta:** «El **histórico analizado** es 2019–2022/2023; la **propuesta** se formula en 2024.» Ten una frase única y repítela.

### 🟡 6.11 Moquegua frente a Tacna; «Rivera Diesel» frente a Volvo Penta
- **Moquegua frente a Tacna:** «Los equipos operan en Moquegua y dependen de la sede de la empresa en Tacna/Arequipa (Sede Sur).» Confirma cuál es la correcta.
- **Rivera Diesel frente a Volvo Penta:** «Rivera Diesel es el fabricante o ensamblador del grupo; el motor es Volvo Penta y el alternador es Stamford.» Confirma este dato.

### 🟡 6.12 Escala de severidad del NPR hasta 8
- **Pregunta posible:** «¿Por qué la severidad va hasta 8 y no hasta 10?»
- **Respuesta:** «Adapté la escala de Yssaad, Khiat y Chaker a la **duración de la interrupción del servicio**: 8 h o más equivale a la máxima severidad para un contrato de alquiler. El NPR se usa para **jerarquizar** modos de falla, no como valor absoluto.»

### 🟡 6.13 Consumo de combustible
- La taxonomía indica **180–200 L/h** a plena carga. Para un motor de ~530 kW, un consumo específico típico (~0,20 kg/kWh) da del orden de **125–130 L/h**.
- **Verifica el dato en la hoja de datos de Volvo Penta.** Si te lo preguntan y no lo has verificado, di que es un dato de campo que incluye pérdidas y operación con sobrecarga.

---

## 7. Banco de preguntas probables con respuesta modelo

### A. Metodología
1. **¿Qué tipo de investigación es?** Aplicada, de enfoque cuantitativo, con diseño no experimental, transversal y propositivo.
2. **¿Por qué una muestra no probabilística?** Porque el RCM se aplica a los **activos críticos**: la selección por criticidad es intencional por definición del método.
3. **¿Población y muestra?** 20 grupos electrógenos; 3 críticos (GI500-16, GI500-19 y GI500-20).
4. **¿Qué instrumentos usó?** Análisis documental (histórico de fallas y órdenes de trabajo), entrevistas al personal, fichas de observación y matrices AMEF, NPR y de decisión.
5. **¿Cómo validó los instrumentos?** Prepara la respuesta: juicio de expertos (el asesor y el equipo RCM) y consistencia con los formatos estándar de Moubray y SAE JA1011.
6. **¿Qué estadística usó?** Descriptiva: frecuencias, Pareto, promedios (MTBF/MTTR) y ajuste de distribución de confiabilidad (exponencial/Weibull).

### B. Teoría RCM
7. **Defina RCM.** Proceso para determinar qué debe hacerse para que un activo siga cumpliendo sus funciones en su contexto operacional (Moubray).
8. **Enumere las 7 preguntas.** Ver la sección 4.2.
9. **¿Diferencia entre falla funcional y modo de falla?** La falla funcional es la incapacidad de cumplir la función con el estándar requerido (el «qué»). El modo de falla es el evento que la causa (el «por qué»).
10. **¿Qué es una falla oculta? Dé un ejemplo de su tesis.** Ver la sección 4.3. La tarea correspondiente es de búsqueda de fallas (FF).
11. **¿Qué es el intervalo P-F y cómo fija la frecuencia de una tarea a condición?** Ver la sección 4.5: frecuencia ≤ P-F/2.
12. **¿Diferencia entre RCM y TPM?** RCM decide **qué** mantenimiento hacer, según funciones y consecuencias. TPM decide **quién y cómo**, involucrando a los operadores mediante el mantenimiento autónomo y las 5S. Son complementarios (Illesca y Ureta, 2024).
13. **¿Diferencia entre AMEF y AMFEC (FMECA)?** El AMFEC añade la cuantificación de la criticidad de cada modo de falla; tu NPR cumple ese papel.
14. **¿Por qué el RCM no es solo «hacer más preventivo»?** Porque alrededor del 89 % de las fallas no dependen de la edad: el preventivo por calendario puede **introducir** fallas (mortalidad infantil), que es justo lo que muestra tu histórico.

### C. Resultados
15. **¿Cuál es el principal hallazgo?** Que las fallas inducidas (extracciones, reinstalaciones y canibalización) amplifican la recurrencia; el problema es de **gestión**, no solo de desgaste.
16. **¿Qué sistema concentra las paradas?** El motor diésel (~80 % de las horas, según el Pareto): refrigeración, combustible y ventilación. En el alternador, la excitación y el AVR.
17. **¿Por qué el GI500-19 mejora tan poco en MTBF (245 → 250)?** Porque su MTBF ya era alto; su problema son los **eventos largos** (rebobinado de 96 h, bomba de alta de 72 h). Por eso la palanca es el MTTR (15,8 → 8 h) mediante el cambio modular del AVR y el stock crítico.
18. **¿Cómo justifica un MTTR de 5 h?** Con kitting, job plans estándar, ruta de diagnóstico única (ΔP/ΔT), subconjuntos preajustados y pruebas de liberación. Se eliminan las esperas y los retrabajos, que eran la mayor parte del MTTR.
19. **¿Qué pasa si la empresa no elimina la canibalización?** Las fallas inducidas reaparecen y el MTBF proyectado no se alcanza; es el principal riesgo (sección 4.4.4.13).

### D. Económico
20. **¿Es rentable?** Sí, en ambos escenarios: se recupera en ~3 meses con el valor de las horas recuperadas y en ~4,6 años solo con el ahorro directo. Además, la inversión de US$ 54 709 sirve **a toda la flota**, no solo a los 3 equipos.
21. **¿Por qué no calculó el VAN ni la TIR?** «La empresa no proporcionó su flujo de caja (información confidencial); por eso evalué el **ahorro anual** y la recuperación simple.» Ofrece calcularlo si te lo piden: con 5 años, una tasa del 12 % y US$ 11 910/año, el VAN ≈ −US$ 11 800 (no rentable); con US$ 232 310/año es claramente positivo. **Mejor defiende el escenario total, explicando el valor de US$ 200/h.**
22. **¿Por qué hay 16 multímetros y 25 linternas?** Porque la inversión está dimensionada para **toda la flota y todos los técnicos de la Sede Sur**, no para 3 equipos. Revisa las cantidades por si te piden detalle.

### E. Ingeniería eléctrica (el jurado es de Eléctrica: prepara esto a fondo)
23. **¿Cómo funciona la excitación sin escobillas del Stamford?** El AVR alimenta en CC el campo **estacionario** de la excitatriz. La armadura **rotante** de la excitatriz genera CA, que el **puente rectificador rotante** (6 diodos) convierte en CC para el campo del rotor principal. El AVR regula la tensión de salida variando la corriente de campo de la excitatriz.
24. **¿Qué función cumple el varistor en el rectificador rotante?** Suprime las sobretensiones transitorias (por ejemplo, ante un cortocircuito o un mal sincronismo) que dañarían los diodos. Un varistor en corto deja al campo sin excitación.
25. **¿Cómo detecta un diodo dañado midiendo el rizado?** Un diodo **abierto** convierte el puente trifásico en semionda en una fase: **aumenta el rizado** de la corriente de campo de la excitatriz y el AVR exige más corriente para sostener la tensión, lo que provoca calentamiento. Un diodo **en corto** provoca una corriente de excitación muy alta, caída de tensión e incluso disparo del AVR.
26. **¿Qué es el IR y el PI? ¿Qué valores acepta?** Según IEEE 43-2013:
    - **IR** es la resistencia de aislamiento a 1 min, corregida a 40 °C.
    - **PI** es el cociente IR₁₀ min / IR₁ min.
    - Mínimos: IR ≥ 5 MΩ para devanados aleatorios o de menos de 1 kV; **PI ≥ 2,0** para aislamiento clase F/H.
    - Si el aislamiento está húmedo (tu caso de sulfatación), se **seca** antes de energizar.
27. **¿Por qué paso de devanado 2/3?** Elimina el **tercer armónico** (y sus múltiplos) en la tensión fase-neutro. Así reduce las corrientes de circulación por el neutro al operar **en paralelo** y la distorsión con cargas no lineales.
28. **¿Qué verifica antes de sincronizar (función ANSI 25)?** ΔV, Δf, Δφ y la secuencia de fases. Valores de referencia de IEEE 1547:
    - Para más de 500 y hasta 1 500 kVA (tu caso, 625 kVA): Δf ≤ 0,2 Hz, ΔV ≤ 5 %, Δφ ≤ 15°.
    - Hasta 500 kVA: 0,3 Hz, 10 % y 20°.
29. **¿Qué significa prime frente a standby (ISO 8528-1)?**
    - **Prime (PRP):** potencia continua con carga variable, con un promedio de hasta el 70 % en 24 h y un 10 % de sobrecarga durante 1 h cada 12 h.
    - **Standby (ESP):** solo para emergencias, con horas limitadas al año y sin sobrecarga.
    - Para alquiler en minería corresponde el régimen **prime**.
30. **¿Cómo relaciona 500 kW con los 532 kW del motor?**
    - $P_{\text{eléctrica}} = P_{\text{mecánica}} \cdot \eta_{\text{gen}} \approx 532 \times 0{,}95 \approx 505$ kW, de modo que el motor está dimensionado al límite en prime.
    - 500 kW a FP 0,8 equivalen a **625 kVA**.
31. **¿Qué mide el analizador de armónicos y qué límite aplica?** Mide el THD de tensión. El fabricante garantiza menos del 5 % en vacío. Para calidad en el punto de entrega aplican IEEE 519 y, en el Perú, la NTCSE (THDv ≤ 8 % en ≤ 60 kV).
32. **¿Por qué la humedad daña el AVR?** Provoca corrosión y sulfatación de pistas y conectores, fugas superficiales, mediciones erróneas de tensión y oscilaciones. Por eso el plan incluye **rediseño (RD)**: sellado, desecantes y control de humedad relativa.
33. **¿Qué es el control *droop* y por qué importa en paralelo?** La frecuencia cae proporcionalmente con la carga (típicamente 3–5 %) para repartir la potencia activa entre grupos en paralelo. Un regulador de velocidad mal ajustado provoca «oscilaciones de RPM», uno de tus modos de falla.

### F. Normativa
34. **¿Bajo qué norma se rige el RCM?** SAE JA1011/JA1012. La taxonomía sigue ISO 14224, y los indicadores, UNE-EN 15341.
35. **¿Qué norma aplica a la seguridad eléctrica en el Perú?** El Código Nacional de Electricidad (Utilización 2006 y Suministro 2011). Si el equipo opera en una mina, también el **D.S. 024-2016-EM** (Reglamento de Seguridad y Salud Ocupacional en Minería): LOTO, permisos y el IPERC.
36. **¿Qué norma aplica a los grupos electrógenos?** ISO 8528 (desempeño y regímenes de potencia), IEC 60034-1 (máquinas eléctricas rotativas) y NFPA 110 (sistemas de emergencia y respaldo: pruebas mensuales con carga).
37. **¿Qué norma usa para la limpieza del combustible?** ISO 4406 (código de limpieza por conteo de partículas), que tu plan aplica con el contador láser.

### G. Preguntas de cierre
38. **¿Cuál es su aporte original?** Integrar el RCM con controles de **reinstalación y trazabilidad** (cero canibalización), una causa raíz que los antecedentes no abordan.
39. **¿Qué haría distinto?** Recolectar datos post-implementación, ajustar Weibull con más datos y calcular el VAN con información financiera real.
40. **¿Es replicable?** Sí, en el resto de la flota (17 equipos) y en otras empresas de alquiler, porque el método es estándar (SAE JA1011) y los formatos están en los anexos.

---

## 8. Correcciones al documento antes de imprimir o sustentar

**Urgentes (el jurado las verá):**
- [ ] **Capítulo IV, final del comentario de la matriz NPR:** borrar la frase «*Avísame si deseas el cuadro con ranking de criticidad priorizado para planificar intervenciones de mejora de inmediato.*». Es texto de un chatbot y es lo más grave del documento.
- [ ] **Capítulo III, método:** «según la clasificación… **tu** investigación se enmarca…» → «la presente investigación se enmarca…». También es texto de un chatbot.
- [ ] **Capítulo III:** unificar el diseño (no experimental) y eliminar «cuasi-experimental».
- [ ] **Capítulo II (criticidad):** «se realizará la selección de **()** grupos electrógenos» → «de **tres (3)** grupos».
- [ ] **Capítulo IV (selección del activo crítico):** «**16** consecuencias y una criticidad de 130» → «**26** consecuencias».
- [ ] **Referencias:** se citan en el texto pero **no están en la lista**: Mora Gutiérrez (2009), Cárcel Carrasco (2014), Souris (1990), Jiménez Raya (2015), Pistarelli (2010), Moubray (1991), Hadi Mohamed et al. (2023), Arias Gonzales (2020) y Hernández Sampieri (2014). Además, Yssaad et al. figura como 2013 en el texto y 2014 en la lista.
- [ ] **Referencia a Moubray (2005):** quitar el enlace `es.b-ok.lat` (sitio de descargas no autorizadas).

**De coherencia:**
- [ ] Unificar el periodo (histórico 2019–2022/2023 y propuesta 2024) en el título, el problema, el objetivo, la hipótesis, la delimitación y el Pareto.
- [ ] Moquegua frente a Tacna en la delimitación.
- [ ] Hipótesis específica a): está redactada como objetivo. Por ejemplo: «La aplicación de la metodología RCM permite identificar los modos de falla críticos y reducir su frecuencia, incrementando la disponibilidad operativa del grupo electrógeno.»
- [ ] Resumen: aclarar «ahorro **directo** superior a US$ 12 000/año; beneficio total estimado de US$ 232 310/año».
- [ ] Resumen: «elevar el MTBF de 120–150 h a 220–250 h» no aplica al GI500-19 (245 h). Por ejemplo: «elevar el MTBF de 145–153 h a 220–250 h en los equipos GI500-16 y GI500-20».

**Erratas:**
- [ ] «Guitiérrez» → Gutiérrez; «Cata|strófica» → Catastrófica; «GI500'16» → GI500-16; «2,1900 h» → 21 900 h; «intensión» → intención; «costo benefició» → costo-beneficio; «+Estrategias de mantenimiento» (sobra el «+»); «formulación del problema» → «Formulación del problema»; «rivera Diesel» → «Rivera Diesel».

---

## 9. Plan de estudio sugerido (7 días)

| Día | Tarea |
|---|---|
| 1 | Leer la tesis completa con esta guía al lado. Hacer las correcciones urgentes de la sección 8. |
| 2 | Memorizar las secciones 3 y 4.2–4.4. Rehacer a mano los cálculos de la sección 5. |
| 3 | Preparar las diapositivas según la sección 2. Buscar β y η en tu Excel (punto 6.9) y el sustento de US$ 200/h (punto 6.7). |
| 4 | Estudiar las preguntas A–D de la sección 7. Responder en voz alta, cronometrado (máximo 1 min por respuesta). |
| 5 | Estudiar las preguntas E–G (eléctrica y normativa). Repasar el principio de funcionamiento del alternador sin escobillas con un esquema dibujado. |
| 6 | Simulacro completo con alguien que haga de jurado y use la sección 6 para atacarte. |
| 7 | Ensayo final de la exposición (≤ 18 min). Descanso. |

> **Regla de oro en la sustentación:** si no sabes algo, di «no lo consideré en el alcance de esta tesis; lo propongo como recomendación». No inventes cifras. Cuando un dato tuyo sea débil, **reconócelo y redirige al hallazgo fuerte**: las fallas inducidas y el control de reinstalación.
