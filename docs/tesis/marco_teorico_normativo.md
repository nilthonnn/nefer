# CAPÍTULO II — MARCO TEÓRICO Y MARCO NORMATIVO

**Tesis:** *Evaluación Técnico-Económica para la Implementación de un Sistema BESS (500 kW / 1 MWh) en la Microred Aislada de la Unidad Minera El Santo – Caylloma*
**Autor:** Nilthon Rosinaldo Chite Vilca
**Programa:** Ingeniería Eléctrica — Universidad Continental (Perú)

> [!IMPORTANT]
> **Nota de verificación normativa (para el autor, retirar antes de la versión final).**
> Las normas internacionales y las normas peruanas consolidadas (D.L. 25844, Ley 28832, D.S. 020-97-EM, CNE) se citan con su identificación oficial. El marco peruano de almacenamiento, en cambio, **está en plena transición** (Ley N.° 32249 de enero de 2025 y sus reglamentos en proyecto o recién aprobados). Al cierre de esta redacción no se pudo confirmar en *El Peruano* un decreto supremo publicado con el título exacto «Reglamento para la Transición Energética y Almacenamiento de Energía». Antes de sustentar, verifique en el portal de normas legales de *El Peruano* y del MINEM: (a) el número y fecha del decreto supremo reglamentario de la Ley 32249; (b) el reglamento de sistemas eléctricos aislados (proyecto prepublicado con R.M. N.° 125-2025-MINEM/DM); (c) la edición vigente de UL 9540, UL 9540A y NFPA 855. Los apartados marcados con ⚠️ dependen de esa verificación.

---

## Índice del capítulo

- [2.1 Marco Normativo y Regulatorio](#21-marco-normativo-y-regulatorio)
  - [2.1.1 Marco normativo del sector eléctrico peruano](#211-marco-normativo-del-sector-eléctrico-peruano)
  - [2.1.2 Estándares internacionales de seguridad y diseño de BESS](#212-estándares-internacionales-de-seguridad-y-diseño-de-bess)
  - [2.1.3 Normas complementarias de interconexión, calidad y altitud](#213-normas-complementarias-de-interconexión-calidad-y-altitud)
  - [2.1.4 Matriz de aplicabilidad normativa al proyecto](#214-matriz-de-aplicabilidad-normativa-al-proyecto)
- [2.2 Fundamentación Teórica de los Sistemas BESS](#22-fundamentación-teórica-de-los-sistemas-bess)
  - [2.2.1 Arquitectura de microredes aisladas](#221-arquitectura-de-microredes-aisladas)
  - [2.2.2 Componentes tecnológicos del BESS](#222-componentes-tecnológicos-del-bess)
  - [2.2.3 Eficiencia energética del BESS](#223-eficiencia-energética-del-bess)
  - [2.2.4 Fenómenos físicos a gran altitud (4 500 msnm)](#224-fenómenos-físicos-a-gran-altitud-4-500-msnm)
  - [2.2.5 Teoría de degradación electroquímica](#225-teoría-de-degradación-electroquímica)
- [2.3 Definición de términos básicos](#23-definición-de-términos-básicos)
- [2.4 Referencias del capítulo](#24-referencias-del-capítulo)

---

## 2.1 Marco Normativo y Regulatorio

El diseño, la instalación y la operación de un Sistema de Almacenamiento de Energía en Baterías (BESS, *Battery Energy Storage System*) dentro de una unidad minera aislada del Sistema Eléctrico Interconectado Nacional (SEIN) se rigen por tres capas normativas superpuestas:

1. **Capa regulatoria nacional**, que define el régimen de títulos habilitantes, la calidad del suministro y la seguridad de las instalaciones eléctricas en el Perú.
2. **Capa de certificación y seguridad internacional**, que el Perú no impone por ley de forma explícita para BESS, pero que constituye la práctica reconocida de ingeniería (*good engineering practice*), exigida por aseguradoras, financistas y por los estándares corporativos de las empresas mineras.
3. **Capa técnica complementaria**, compuesta por normas IEC/IEEE que resuelven los aspectos que las dos capas anteriores no cubren: interconexión de recursos basados en inversores, armónicos y corrección por altitud.

### 2.1.1 Marco normativo del sector eléctrico peruano

#### a) Ley de Concesiones Eléctricas — D.L. N.° 25844 y su Reglamento (D.S. N.° 009-93-EM)

La Ley de Concesiones Eléctricas (LCE) es la norma marco del subsector y divide la industria en tres actividades: generación, transmisión y distribución. Sus disposiciones relevantes para el proyecto son:

| Disposición | Contenido | Implicancia para el BESS de El Santo |
|---|---|---|
| Art. 3° | Requieren **concesión** las actividades de generación con recursos hidráulicos y geotérmicos superiores a 500 kW, así como la transmisión y la distribución de servicio público. | No aplica de forma directa: el BESS no es generación hidráulica ni presta servicio público. |
| Art. 4° | Requieren **autorización** la generación termoeléctrica y otras fuentes cuya potencia instalada supere 500 kW. | La central diésel existente y la planta FV, si superan 500 kW, deben contar con su autorización o registro. El BESS de 500 kW se sitúa en el umbral, lo que obliga a revisar su encuadre (ver nota). |
| Art. 7° | Las actividades de generación que no requieren concesión ni autorización pueden ejecutarse libremente, cumpliendo las normas técnicas y de conservación del ambiente. | Aplica a instalaciones de uso propio por debajo de los umbrales. |
| Art. 9° | El Estado vela por la conservación del ambiente y el uso racional de los recursos. | Fundamenta la evaluación ambiental bajo el D.S. N.° 014-2019-EM. |

> [!NOTE]
> **El almacenamiento en la LCE.** El texto original de la LCE (1992) no define el almacenamiento de energía como actividad autónoma: un BESS no es en sentido estricto «generación» (no convierte una fuente primaria) ni «transmisión». Ese vacío se ha abordado mediante la Ley N.° 28832 y su modificación por la Ley N.° 32249, que introducen el mercado de **servicios complementarios**, donde el almacenamiento participa naturalmente (regulación de frecuencia, reserva, control de tensión). En una microred minera privada y aislada, el BESS se encuadra como **instalación de uso propio asociada a la generación del titular minero (autoproductor)**, sin venta de energía a terceros.

#### b) Ley N.° 28832 — Ley para Asegurar el Desarrollo Eficiente de la Generación Eléctrica, modificada por la Ley N.° 32249 ⚠️

La Ley 28832 (2006) estableció el régimen de licitaciones, el rol del COES y el **Mecanismo de Compensación para Sistemas Aislados** (Art. 30°). La **Ley N.° 32249**, promulgada en enero de 2025, constituye la reforma más importante del sector desde 2006. Sus ejes relevantes para la tesis son:

- **Contratación por bloques horarios** y separación de los productos potencia y energía, lo que crea señales de precio para el desplazamiento temporal de energía (*energy time-shift*), que es la función básica de un BESS.
- **Mercado de servicios complementarios**, con el principio de que el agente que causa la necesidad de un servicio de estabilidad asume su costo. El almacenamiento es la tecnología de mayor velocidad de respuesta para la regulación primaria de frecuencia.
- **Sistemas eléctricos aislados:** se faculta al MINEM a encargar al COES la coordinación de sistemas aislados que superen ciertos umbrales de potencia y número de generadores (proyecto de reglamento prepublicado con R.M. N.° 125-2025-MINEM/DM).

> [!WARNING]
> **Reglamento específico de almacenamiento.** El enunciado de la tesis se refiere a un «Reglamento para la Transición Energética y Almacenamiento de Energía». Al cierre de esta redacción, ese título exacto no se pudo verificar como decreto supremo vigente. El tratamiento regulatorio del almacenamiento en el Perú se ha desarrollado por tres vías: (i) los reglamentos de la Ley 32249; (ii) el proyecto de marco nacional de planificación energética de 2026 (R.M. N.° 270-2026-MINEM/DM), que incorpora escenarios de solar y almacenamiento; y (iii) la regulación tarifaria de OSINERGMIN para sistemas aislados. Cite en la versión final el número de decreto supremo exacto que esté vigente a la fecha de sustentación.

#### c) Regulación de generación en sistemas aislados (OSINERGMIN)

En los sistemas aislados regulados, OSINERGMIN fija anualmente los **Precios en Barra de Sistemas Aislados** con base en el costo eficiente de un **sistema económicamente adaptado**. Ese costo se compone de:

$$
C_{\text{eficiente}} = \underbrace{\text{aVNR}_{G}}_{\text{anualidad de inversión}} + \underbrace{\text{COyM}_{G}}_{\text{operación y mantenimiento}} + \underbrace{\sum_{t} c_{\text{comb}}\, \text{SFC}\, E_{\text{diésel}}(t)}_{\text{costo de combustible}}
$$

donde $\text{aVNR}$ es la anualidad del Valor Nuevo de Reemplazo, $c_{\text{comb}}$ el precio del combustible puesto en planta (US$/gal), $\text{SFC}$ el consumo específico de combustible (gal/kWh) y $E_{\text{diésel}}$ la energía despachada por los grupos.

Los elementos de esta regulación relevantes para la tesis son:

1. **Mecanismo de Compensación para Sistemas Aislados (MCSA)** — Ley 28832, Art. 30°, reglamentado por el D.S. N.° 069-2006-EM y reforzado por el numeral 5.2 de la Ley N.° 29970. Compensa la diferencia entre el precio en barra del sistema aislado y el del SEIN.
2. **Reconocimiento de baterías en el diseño de plantas FV aisladas.** OSINERGMIN, en sus procesos tarifarios de 2025, ya considera la capacidad de almacenamiento en baterías dentro del dimensionamiento eficiente de plantas fotovoltaicas en sistemas aislados, en función de la demanda proyectada a lo largo de la vida útil.
3. **Sustitución de diésel:** el criterio de costo eficiente valida metodológicamente la comparación económica que desarrolla esta tesis. El BESS es eficiente si reduce el costo total actualizado del sistema:

$$
\Delta \text{VAN} = \sum_{t=1}^{N} \frac{\Delta C_{\text{comb},t} + \Delta C_{\text{OyM},t} + \Delta C_{\text{repos},t}}{(1+i)^t} - I_{0,\text{BESS}} > 0
$$

> [!NOTE]
> La U.M. El Santo es un **sistema privado de autogeneración**, no un sistema aislado regulado con tarifa. La regulación de OSINERGMIN para sistemas aislados no le es exigible directamente, pero su **metodología de costo eficiente** es el referente técnico-económico aceptado en el Perú y se adopta en esta tesis como criterio de comparación. La fiscalización de seguridad de las instalaciones eléctricas de la unidad minera sí corresponde a OSINERGMIN y, en lo ocupacional, al D.S. N.° 024-2016-EM.

#### d) Norma Técnica de Calidad de los Servicios Eléctricos — NTCSE (D.S. N.° 020-97-EM)

La NTCSE fija las tolerancias de calidad de producto en el punto de entrega. En una microred aislada el BESS es el principal actuador para mantenerlas en el **Punto de Conexión Común (PCC)**, por lo que sus valores se adoptan como requisitos de desempeño del PCS:

| Parámetro | Indicador NTCSE | Tolerancia | Función del BESS |
|---|---|---|---|
| **Tensión** | $\Delta V_k(\%) = \dfrac{V_k - V_N}{V_N}\times 100$ | ±5 % $V_N$ (urbano); ±7,5 % en sistemas urbano-rurales y rurales | Control Q–V, soporte dinámico de tensión durante el arranque de motores. |
| **Frecuencia — variaciones sostenidas** | $\Delta f_k(\%) = \dfrac{f_k - f_N}{f_N}\times 100$ (intervalos de 15 min) | ±0,6 % (±0,36 Hz) | Regulación primaria P–f (*droop*). |
| **Frecuencia — variaciones súbitas** | Excursión instantánea | ±1,0 Hz | Inercia sintética y respuesta rápida de frecuencia (FFR). |
| **Frecuencia — variación diaria integrada** | $\text{VDF} = \int_{0}^{24h}(f - f_N)\,dt$ | ±600 ciclos/día | Control secundario del EMS. |
| **Flicker** | Índice de severidad $P_{st}$ (IEC 61000-4-15) | $P_{st} \le 1$ en el 95 % del período | Compensación de fluctuaciones por cargas intermitentes (molinos, chancadoras, nubosidad sobre la planta FV). |
| **Armónicos de tensión** | $\text{THD}_V = \dfrac{\sqrt{\sum_{h=2}^{40} V_h^2}}{V_1}\times 100$ | ≤ 8 % para $V_N \le 60$ kV; ≤ 3 % para $V_N > 60$ kV | Filtrado activo; el PCS no debe inyectar armónicos que excedan el límite. |

> [!TIP]
> Para sistemas rurales y aislados existe además la **Norma Técnica de Calidad de los Servicios Eléctricos Rurales (NTCSER)**, cuyas tolerancias son más amplias. Por tratarse de una carga minera crítica, esta tesis adopta las tolerancias de la NTCSE, más estrictas, como criterio de diseño conservador. Los límites de corriente armónica inyectada se verifican complementariamente con IEEE Std 519-2022.

#### e) Código Nacional de Electricidad (Suministro 2011 y Utilización 2006)

El CNE-Suministro 2011 (R.M. N.° 214-2011-MEM/DM) y el CNE-Utilización (R.M. N.° 037-2006-MEM/DM) rigen la seguridad de las instalaciones. Los aspectos críticos a 4 500 msnm son:

**1. Puesta a tierra en terrenos de alta resistividad.** En la puna de Caylloma predominan suelos rocosos, secos o congelados, con resistividades aparentes de $\rho = 1\,000$ a $10\,000\ \Omega\cdot\text{m}$. La resistencia de un electrodo vertical de longitud $L$ y radio $a$ (fórmula de Dwight) es:

$$
R_{\text{varilla}} = \frac{\rho}{2\pi L}\left[\ln\left(\frac{4L}{a}\right) - 1\right]
$$

Con $\rho = 2\,000\ \Omega\cdot\text{m}$, $L = 2{,}4$ m y $a = 0{,}0079$ m se obtiene $R \approx 893\ \Omega$, valor muy superior al de 25 Ω que el CNE-Utilización (Sección 060) toma como referencia para un electrodo. De ahí que se requieran:

- mallas extendidas con contrapesos horizontales;
- compuestos de mejora de baja resistividad (bentonita, GEM) y tratamiento contra el congelamiento;
- verificación de **tensiones de toque y de paso** según IEEE Std 80-2013, en lugar de un valor de resistencia aislado.

$$
E_{\text{toque},50\text{kg}} = \left(1\,000 + 1{,}5\,C_s\,\rho_s\right)\frac{0{,}116}{\sqrt{t_s}}
\qquad
E_{\text{paso},50\text{kg}} = \left(1\,000 + 6\,C_s\,\rho_s\right)\frac{0{,}116}{\sqrt{t_s}}
$$

donde $\rho_s$ es la resistividad de la capa superficial (grava), $C_s$ su factor de reducción y $t_s$ el tiempo de despeje de la falla.

**2. Distancias de seguridad y aislamiento corregidos por altitud.** Las distancias mínimas del CNE están establecidas para altitudes de hasta 1 000 msnm. Por encima de esa cota deben incrementarse según la menor rigidez dieléctrica del aire (§ 2.2.4-c).

**3. Esquema de puesta a tierra del sistema DC.** Los bancos de baterías operan típicamente entre 1 000 y 1 500 V DC. Se emplea un esquema IT flotante con monitoreo de aislamiento (IMD) conforme a IEC 61557-8, porque una primera falla a tierra no debe interrumpir el servicio pero sí debe alarmarse.

> [!WARNING]
> **Seguridad minera.** Toda instalación eléctrica dentro de la U.M. se rige además por el **Reglamento de Seguridad y Salud Ocupacional en Minería (D.S. N.° 024-2016-EM y sus modificatorias)**, que exige estudios de riesgo, bloqueo y etiquetado (LOTO) y planes de respuesta a emergencias. El escenario de fuga térmica del BESS debe incorporarse al IPERC de la unidad.

#### f) Protección ambiental

El **Reglamento para la Protección Ambiental en las Actividades Eléctricas (D.S. N.° 014-2019-EM)** es el marco con el que la DGAAE del MINEM ha evaluado proyectos de almacenamiento con baterías en el Perú (p. ej., modificaciones de instrumentos ambientales de centrales térmicas que incorporan BESS). En una unidad minera, la incorporación del BESS se tramita normalmente como modificación del instrumento de gestión ambiental minero vigente, mediante un Informe Técnico Sustentatorio (ITS) cuando el impacto es no significativo.

---

### 2.1.2 Estándares internacionales de seguridad y diseño de BESS

La seguridad de un BESS de ion-litio se organiza en una **jerarquía de niveles**: celda → módulo → rack → sistema → instalación. Cada estándar cubre uno o varios niveles:

```
 NIVEL            ESTÁNDAR PRINCIPAL         PREGUNTA QUE RESPONDE
 ───────────────  ─────────────────────────  ─────────────────────────────────────────────
 Celda / módulo   IEC 62619 / UL 1973        ¿La celda es segura ante abuso eléctrico,
                                             térmico y mecánico?
 Celda → unidad   UL 9540A (método de        ¿Si una celda entra en fuga térmica, se
                  ensayo)                    propaga? ¿Qué gases y qué calor libera?
 Sistema          UL 9540                    ¿El conjunto batería + PCS + BMS + EMS está
                                             integrado y certificado como un todo?
 Instalación      NFPA 855                   ¿Dónde y cómo se instala: distancias,
                                             ventilación, detección y extinción?
```

#### a) UL 9540 — *Standard for Energy Storage Systems and Equipment* ⚠️

UL 9540 es el estándar de **certificación de sistema**. No evalúa la celda de forma aislada: certifica que la **integración** del almacenamiento (batería), el **PCS** (convertidor), el **BMS** y el **EMS**, junto con los sistemas auxiliares (HVAC, detección, supresión), opera de forma segura como un conjunto.

Aspectos que verifica:

- **Seguridad eléctrica:** aislamiento, protección contra sobrecorriente DC/AC, coordinación de protecciones entre el BMS y el PCS.
- **Seguridad funcional:** los controles críticos para la seguridad (desconexión por sobretensión, sobretemperatura y sobrecorriente) deben cumplir requisitos de seguridad funcional (referencia a UL 991/UL 1998 o IEC 60730-1).
- **Componentes certificados:** las baterías deben cumplir UL 1973; los inversores, UL 1741 (o IEC 62109 / IEC 62477-1).
- **Desempeño frente a incendio:** desde su 2.ª edición, exige ensayos según UL 9540A cuando el sistema pretende reducir las distancias de separación de NFPA 855.

> [!IMPORTANT]
> **Requisito de especificación técnica:** el pliego de compra del BESS de El Santo debe exigir que la **unidad completa** (contenedor con baterías, PCS, BMS y EMS) esté listada como sistema bajo **UL 9540** por un laboratorio reconocido (NRTL), no solo sus componentes por separado. Un *rack* UL 1973 acoplado a un PCS UL 1741 **no** equivale a un sistema UL 9540.

#### b) UL 9540A — *Test Method for Evaluating Thermal Runaway Fire Propagation in BESS* ⚠️

UL 9540A **no es un estándar de aprobación o rechazo**, sino un **método de ensayo** que produce datos cuantitativos para que el diseñador y la autoridad competente decidan sobre distancias, ventilación y supresión. Se desarrolla en cuatro niveles secuenciales:

| Nivel | Objeto | Datos que produce | Criterio para pasar al siguiente nivel |
|---|---|---|---|
| **1. Celda** | Se induce la fuga térmica (calentamiento externo) | Temperatura de venteo, temperatura de inicio de fuga térmica, **composición y volumen de gases** (H₂, CO, CO₂, CH₄, C₂H₄), límite inferior de inflamabilidad (LFL) de la mezcla | Si la celda no entra en fuga térmica, el ensayo concluye. |
| **2. Módulo** | Fuga térmica iniciada en una celda | ¿Se propaga a celdas adyacentes? Tasa de liberación de calor (HRR), gases | Si no hay propagación fuera de la celda iniciadora y los gases no son inflamables, puede concluir. |
| **3. Unidad** | Rack completo en configuración de instalación | Propagación entre módulos y racks, flujo de calor sobre unidades adyacentes, riesgo de deflagración | Si no hay propagación entre unidades ni llama exterior, puede concluir. |
| **4. Instalación** | Recinto o contenedor con su sistema de supresión real | Eficacia de la supresión y de la ventilación de deflagración | Final. |

La química **LFP** (LiFePO₄) muestra en estos ensayos temperaturas de inicio de fuga térmica notablemente mayores y una liberación de calor menor que la NMC, porque la estructura olivina retiene el oxígeno. Sin embargo, la LFP **libera proporcionalmente más hidrógeno** en el venteo, lo que hace crítica la **ventilación contra deflagración** aunque el riesgo de llama sea menor.

> [!WARNING]
> **Interacción con la altitud.** Los ensayos UL 9540A se ejecutan a presión cercana a la del nivel del mar. A 4 500 msnm ($p \approx 57{,}7$ kPa) la mezcla de gases de venteo se diluye en un aire con ~43 % menos oxígeno por unidad de volumen, lo que altera los límites de inflamabilidad y la dinámica de una deflagración. El diseño de los paneles de alivio (NFPA 68) y el sistema de dilución (NFPA 69) debe basarse en la **masa** de gas liberada, recalculada a las condiciones de sitio, y no en volúmenes nominales.

#### c) IEC 62619:2022 — *Secondary cells and batteries containing alkaline or other non-acid electrolytes — Safety requirements for secondary lithium cells and batteries, for use in industrial applications*

IEC 62619 es la referencia internacional (no UL) para la seguridad de celdas y baterías de litio en aplicaciones industriales estacionarias. Define:

**Ensayos de uso indebido razonablemente previsible (celda/batería):**

| Ensayo | Condición | Criterio de aceptación |
|---|---|---|
| Cortocircuito externo | Resistencia total ≤ 30 mΩ a 25 °C | Sin fuego ni explosión |
| Impacto | Caída de masa sobre barra transversal a la celda | Sin fuego ni explosión |
| Caída (*drop*) | Altura según la masa de la batería | Sin fuego ni explosión |
| Abuso térmico | Calentamiento en horno hasta 85 °C (o superior, según el fabricante) | Sin fuego ni explosión |
| Sobrecarga | Carga a corriente elevada hasta superar la tensión máxima | Sin fuego ni explosión |
| Descarga forzada | Inversión de polaridad | Sin fuego ni explosión |
| **Propagación** | Fuga térmica inducida en una celda del módulo | **La fuga térmica no debe propagarse** con fuego fuera de la batería. |

**Seguridad funcional del BMS:** IEC 62619 exige que el BMS supervise la **tensión, la corriente y la temperatura** y actúe ante la superación de sus límites, con un nivel de seguridad funcional evaluado según IEC 61508 / IEC 60730-1. Para los sistemas de almacenamiento de energía, la serie **IEC 62933** (en particular IEC 62933-5-2, requisitos de seguridad para BESS electroquímicos conectados a la red) complementa a IEC 62619 en el nivel de sistema.

#### d) NFPA 855 — *Standard for the Installation of Stationary Energy Storage Systems* ⚠️

NFPA 855 regula la **instalación**. Sus disposiciones principales, aplicadas a un contenedor exterior de ~1 MWh, son:

| Requisito | Disposición NFPA 855 (síntesis) | Aplicación a El Santo |
|---|---|---|
| **Umbral de aplicación** | Aplica a ion-litio por encima de 20 kWh (cantidad umbral). | Aplica plenamente (1 000 kWh). |
| **Tamaño máximo por grupo** | Grupos de hasta 50 kWh separados ≥ 0,9 m (3 ft), salvo que ensayos UL 9540A a gran escala justifiquen otra configuración. | El contenedor integrado debe acreditar la configuración con datos UL 9540A de nivel unidad o instalación. |
| **Distancia de instalaciones exteriores** | ≥ 3 m (10 ft) a linderos, edificaciones, vías públicas, materiales combustibles y salidas, reducible con barreras ensayadas o con datos UL 9540A. | Separar del grupo electrógeno diésel, del almacén de combustible y de las subestaciones. |
| **Control de explosión** | Ventilación de deflagración según **NFPA 68** o prevención por ventilación/dilución mecánica según **NFPA 69** (mantener < 25 % del LFL). | Obligatorio en contenedores de entrada (*walk-in*) y no *walk-in*. |
| **Detección** | Detección de humo/calor y, según el diseño, detección de gases (H₂, CO). | Sensores de gas recalibrados para la presión de sitio. |
| **Supresión** | Sistema automático (agua, agente limpio, aerosol), justificado con datos UL 9540A. | El agua puede congelarse a 4 500 msnm: considerar sistemas secos o de preacción con trazado calefactado. |
| **Parada de emergencia y señalización** | E-stop accesible, señalización de riesgos, plan de respuesta a emergencias. | Integrar al plan de respuesta a emergencias de la U.M. |
| **Puesta en servicio y desmantelamiento** | Plan de comisionamiento, plan de desmantelamiento y gestión de baterías al final de su vida útil. | Incluir el costo de disposición final en el análisis económico. |

> [!CAUTION]
> NFPA 855 no tiene fuerza de ley en el Perú. Sin embargo, el **Art. 7° de la LCE** obliga a cumplir «normas técnicas», el CNE remite a normas internacionales reconocidas cuando no existe norma nacional, y las aseguradoras de la industria minera exigen NFPA 855 como condición de cobertura. En la práctica, es **obligatoria por vía contractual**.

---

### 2.1.3 Normas complementarias de interconexión, calidad y altitud

| Norma | Alcance | Uso en la tesis |
|---|---|---|
| **IEEE Std 1547-2018** | Interconexión de recursos distribuidos: ride-through de tensión/frecuencia, funciones volt-var y frecuencia-watt. | Requisitos de control del PCS en modo *grid-following*. |
| **IEEE Std 2800-2022** | Recursos basados en inversores (IBR) conectados a la red de transmisión. | Referencia para el desempeño de las funciones de soporte de red. |
| **IEEE Std 2030.7-2017 / 2030.8-2018** | Especificación y ensayo de controladores de microred. | Funciones del EMS: despacho y transición entre modos de operación. |
| **IEEE Std 519-2022** | Límites de armónicos de tensión y de corriente en el PCC. | Verificación del PCS. |
| **IEC 61000-4-30 / 4-15 / 4-7** | Métodos de medición de calidad de energía, flicker y armónicos. | Metodología de medición en campo. |
| **IEC 62477-1 / IEC 62109-1** | Seguridad de convertidores electrónicos de potencia. Ambas incluyen corrección por altitud de las distancias de aislamiento. | Certificación del PCS. |
| **IEC 60664-1** | Coordinación de aislamiento para equipos de baja tensión; Tabla A.2 de factores de corrección por altitud. | Distancias en el aire (*clearances*) del PCS y los tableros DC. |
| **IEC 60071-2 / IEC 62271-1** | Coordinación de aislamiento en MT/AT; factor de corrección atmosférica $K_a$. | Transformador elevador y celdas de MT. |
| **IEC 60076-11 / IEEE C57.12.00** | Transformadores; desclasificación por altitud superior a 1 000 m. | Transformador del PCS. |
| **ISO 3046-1** | Desclasificación de motores de combustión por altitud y temperatura. | Potencia efectiva de los grupos diésel existentes. |
| **IEC 61557-8** | Monitores de aislamiento en sistemas IT. | Sistema DC flotante. |

---

### 2.1.4 Matriz de aplicabilidad normativa al proyecto

| Subsistema | Norma regulatoria (Perú) | Norma de certificación | Norma de diseño/instalación |
|---|---|---|---|
| Celdas y módulos LFP | — | IEC 62619, UL 1973 | IEC 62933-5-2 |
| Propagación térmica | — | UL 9540A | NFPA 855, NFPA 68/69 |
| Sistema integrado (batería + PCS + BMS + EMS) | LCE Art. 7° (cumplimiento técnico) | **UL 9540** | IEC 62933 |
| PCS / inversor | NTCSE (calidad en el PCC) | UL 1741, IEC 62109, IEC 62477-1 | IEEE 1547, IEEE 519 |
| EMS / control de microred | Ley 32249 (servicios complementarios, por analogía) | — | IEEE 2030.7/2030.8 |
| Puesta a tierra | CNE-Utilización Secc. 060, CNE-Suministro | — | IEEE 80, IEEE 142 |
| Aislamiento a 4 500 msnm | CNE (distancias de seguridad) | IEC 60664-1 | IEC 60071-2 |
| Seguridad ocupacional | D.S. 024-2016-EM | — | NFPA 855 (plan de emergencia) |
| Ambiental | D.S. 014-2019-EM / IGA minero | — | — |
| Evaluación económica | Metodología de costo eficiente de OSINERGMIN (referencial) | — | — |

---

## 2.2 Fundamentación Teórica de los Sistemas BESS

### 2.2.1 Arquitectura de microredes aisladas

#### a) Definición y topología

Una **microred** es un conjunto de cargas y recursos energéticos distribuidos (DER) dentro de límites eléctricos claramente definidos, que actúa como una **entidad controlable única** (IEEE 2030.7). En la U.M. El Santo, la microred opera **permanentemente aislada** (*islanded*), por lo que no existe una red infinita que fije la tensión y la frecuencia: estas deben ser **formadas** por algún recurso interno.

```
                         BARRA PRINCIPAL MT (PCC interno)
   ════════════╤══════════════════╤═══════════════════╤══════════════════╤═════════
               │                  │                   │                  │
         ┌─────┴─────┐      ┌─────┴─────┐       ┌─────┴─────┐      ┌─────┴──────┐
         │  Grupos   │      │ Planta FV │       │   BESS    │      │  Cargas    │
         │  diésel   │      │ (inversor │       │ 500 kW /  │      │  mineras   │
         │  (G1…Gn)  │      │ grid-fol- │       │  1 MWh    │      │ (molinos,  │
         │  máquina  │      │  lowing)  │       │ PCS grid- │      │ bombas,    │
         │ síncrona  │      │           │       │ forming   │      │ chancado,  │
         └─────┬─────┘      └─────┬─────┘       └─────┬─────┘      │ ventilac.) │
               │                  │                   │            └────────────┘
               └──────────────────┴───────┬───────────┘
                                          │
                                   ┌──────┴──────┐
                                   │  EMS / Con- │  ← despacho, peak shaving,
                                   │ trolador de │    gestión de reserva rodante
                                   │   microred  │
                                   └─────────────┘
```

#### b) Modos de operación del convertidor: *Grid-Following* vs. *Grid-Forming*

| Característica | **Grid-Following (GFL)** | **Grid-Forming (GFM)** |
|---|---|---|
| Comportamiento eléctrico equivalente | **Fuente de corriente** controlada | **Fuente de tensión** controlada detrás de una impedancia |
| Sincronización | PLL (*Phase-Locked Loop*): necesita medir una tensión ya existente | Genera su propia referencia de ángulo; se sincroniza por intercambio de potencia (como una máquina síncrona) |
| Variables que impone | $P$ y $Q$ | $V$ y $f$ |
| Capacidad de arranque en negro | No | Sí |
| Respuesta inercial | Solo emulada, con retardo del PLL | Intrínseca e instantánea (subtransitoria) |
| Estabilidad en redes débiles (SCR bajo) | Degradada; riesgo de inestabilidad del PLL | Robusta |
| Aplicación en El Santo | Inversores FV existentes | **Modo requerido para el PCS del BESS** |

**Control por estatismo (*droop control*)** — base de la operación GFM en paralelo con los grupos diésel:

$$
f = f_0 - m_p\,(P - P_0) \qquad\qquad V = V_0 - n_q\,(Q - Q_0)
$$

donde $m_p$ (Hz/kW) y $n_q$ (V/kvar) son las pendientes de estatismo. Dos fuentes en paralelo reparten la carga en proporción inversa a sus pendientes:

$$
\frac{\Delta P_1}{\Delta P_2} = \frac{m_{p,2}}{m_{p,1}}
$$

**Máquina Síncrona Virtual (VSM/VSG).** El PCS emula la ecuación de oscilación de un generador:

$$
2H_v\,\frac{d\omega}{dt} = P_{\text{ref}} - P_e - D_v\,(\omega - \omega_0)
$$

donde $H_v$ es la constante de inercia virtual (s) y $D_v$ el coeficiente de amortiguamiento virtual. A diferencia de un generador real, $H_v$ y $D_v$ son **parámetros de software** que pueden ajustarse en línea según el estado de la microred.

#### c) Inercia sintética y estabilidad de frecuencia

La inercia equivalente de la microred es:

$$
H_{\text{sis}} = \frac{\sum_{i} H_i\, S_i}{S_{\text{sis}}}
$$

Ante un desbalance $\Delta P$ (disparo de un grupo o arranque de un molino), la tasa inicial de cambio de frecuencia (RoCoF) es:

$$
\text{RoCoF} = \left.\frac{df}{dt}\right|_{t=0^+} = -\frac{\Delta P\, f_0}{2\,H_{\text{sis}}\,S_{\text{sis}}}
$$

**Ejemplo ilustrativo.** Con $S_{\text{sis}} = 2{,}5$ MVA de grupos diésel ($H \approx 1{,}0$ s, típico de grupos de alta velocidad) y un escalón de carga de $\Delta P = 0{,}4$ MW:

$$
\text{RoCoF} = -\frac{0{,}4 \times 60}{2 \times 1{,}0 \times 2{,}5} = -4{,}8\ \text{Hz/s}
$$

Ese valor es muy severo y llevaría la frecuencia fuera de la banda NTCSE de ±1 Hz en unos 200 ms. Con un BESS que aporta inercia sintética:

$$
\Delta P_{\text{BESS}}(t) = -K_H\,\frac{df}{dt} - K_D\,\Delta f
$$

y $K_H$ equivalente a $H_v = 4$ s sobre 0,5 MVA, la inercia del sistema sube a $H_{\text{sis}} = (2{,}5 \cdot 1 + 0{,}5 \cdot 4)/3{,}0 = 1{,}5$ s, y el RoCoF se reduce a −3,2 Hz/s antes incluso de la acción de estatismo, que el PCS ejecuta en decenas de milisegundos frente a los segundos que necesita un regulador diésel.

#### d) Reserva rodante virtual (*Virtual Spinning Reserve*)

En operación diésel convencional, el criterio N−1 obliga a mantener grupos en línea con margen de reserva:

$$
\sum_{i \in \text{en línea}} P_{\text{nom},i} \ge P_{L}(t) + R_{\text{rod}}, \qquad R_{\text{rod}} \ge \max\left(P_{G,\max},\ \Delta P_{L,\max}\right)
$$

Esto provoca que los grupos operen a baja carga (30–50 %), con alto consumo específico (SFC) y riesgo de *wet stacking* (acumulación de combustible no quemado en el escape). El BESS sustituye parte de esa reserva:

$$
R_{\text{rod}} = R_{\text{diésel}} + R_{\text{BESS}}, \qquad R_{\text{BESS}}(t) = \min\left(P_{\text{PCS,disp}},\ \frac{(SoC(t) - SoC_{\min})\,E_{\text{nom}}\,\eta_{\text{dis}}}{T_{\text{puente}}}\right)
$$

donde $T_{\text{puente}}$ es el tiempo que el BESS debe sostener la carga hasta que un grupo frío arranque, se sincronice y tome carga (típicamente 5–15 min). Un BESS de 500 kW / 1 MWh permite **apagar al menos un grupo**, y los restantes operan cerca de su punto de mínimo SFC (75–85 % de carga).

#### e) Particularidad: cargas inductivas pesadas de minería

El arranque directo de motores de inducción demanda entre 5 y 7 veces la corriente nominal con un factor de potencia de 0,2 a 0,4. En una microred débil esto produce **huecos de tensión** que pueden disparar otros procesos. El PCS en modo GFM aporta potencia reactiva instantánea, pero su **corriente de falla está limitada** (típicamente 1,1–1,5 p.u. por la capacidad térmica de los IGBT), a diferencia de las 3–5 p.u. de una máquina síncrona.

> [!WARNING]
> **Coordinación de protecciones.** Si los grupos diésel se apagan y la microred queda alimentada mayoritariamente por inversores, la corriente de cortocircuito disponible puede no alcanzar los umbrales de los relés de sobrecorriente existentes. Antes de operar en «modo solo inversores», el estudio de coordinación debe verificar la sensibilidad de las protecciones, o bien migrar a protecciones de tensión, direccionales o diferenciales.

---

### 2.2.2 Componentes tecnológicos del BESS

```
    ┌───────────────────────────── CONTENEDOR BESS ──────────────────────────────┐
    │                                                                            │
    │  ┌───────── BATERÍA (DC) ─────────┐   ┌──── PCS ────┐   ┌── TRANSF. ──┐    │
    │  │ Celdas LFP → Módulos → Racks   │══▶│ Inversor    │══▶│ BT/MT       │════╪══▶ Barra MT
    │  │  (1 000–1 500 V DC)            │◀══│ bidireccio- │◀══│ (Dyn11)     │    │
    │  └──────────┬─────────────────────┘   │ nal IGBT    │   └─────────────┘    │
    │             │                         └──────┬──────┘                      │
    │       ┌─────┴─────┐                          │                             │
    │       │  BMS      │◀── CAN / Modbus ────────▶│                             │
    │       │ (3 nive-  │                          │                             │
    │       │  les)     │                    ┌─────┴──────┐                      │
    │       └─────┬─────┘                    │    EMS     │◀── SCADA de la U.M.  │
    │             └──────────────────────────▶ (despacho) │                      │
    │                                        └────────────┘                      │
    │  Auxiliares: HVAC/calefacción · detección de gas · supresión · E-stop      │
    └────────────────────────────────────────────────────────────────────────────┘
```

#### a) Química de celdas: LiFePO₄ (LFP) vs. NMC

Las reacciones de semicelda para LFP son:

$$
\text{Cátodo: } \mathrm{FePO_4 + Li^+ + e^- \ \rightleftharpoons\ LiFePO_4} \qquad
\text{Ánodo: } \mathrm{LiC_6\ \rightleftharpoons\ C_6 + Li^+ + e^-}
$$

| Parámetro | **LFP (LiFePO₄)** | **NMC (LiNi$_x$Mn$_y$Co$_z$O₂)** |
|---|---|---|
| Tensión nominal de celda | 3,2 V | 3,6–3,7 V |
| Energía específica (celda) | 90–180 Wh/kg | 150–270 Wh/kg |
| Vida cíclica (80 % SoH, 100 % DoD) | 4 000–8 000+ ciclos | 1 500–3 000 ciclos |
| Temperatura de inicio de fuga térmica | ≈ 250–270 °C | ≈ 150–210 °C |
| Liberación de O₂ en la descomposición del cátodo | Mínima (enlace P–O covalente fuerte) | Significativa (cátodo laminar) |
| Contenido de cobalto/níquel | Ninguno | Sí (costo, riesgo de suministro e impacto social) |
| Curva OCV–SoC | **Muy plana** (dificulta estimar el SoC) | Pendiente marcada |
| Desempeño a baja temperatura | Pobre en carga por debajo de 0 °C (riesgo de *lithium plating*) | Algo mejor, también limitado |
| Costo nivelado de almacenamiento | Menor | Mayor |
| **Idoneidad para El Santo** | **Preferida** | No recomendada |

> [!NOTE]
> **Justificación de la selección de LFP.** Para una aplicación estacionaria con ciclado diario, en un emplazamiento remoto con capacidad limitada de respuesta de bomberos, la LFP ofrece el mejor equilibrio entre seguridad intrínseca, vida cíclica y costo. Su menor densidad energética no es una restricción relevante en aplicaciones estacionarias. Su principal debilidad, la **carga a baja temperatura**, es crítica en Caylloma (temperaturas nocturnas inferiores a −10 °C) y obliga a un sistema de **calefacción del contenedor**, cuyo consumo auxiliar se incluye en el cálculo del RTE (§ 2.2.3).

#### b) Sistema de Gestión de Baterías (BMS)

El BMS se organiza en una **arquitectura jerárquica de tres niveles**:

1. **BMU / CSC (nivel módulo):** mide la tensión de cada celda (resolución de ±1–2 mV) y la temperatura de varios puntos; ejecuta el balanceo.
2. **BCU / RBMS (nivel rack):** mide la corriente del rack, calcula el SoC y el SoH, y comanda los contactores DC y el fusible.
3. **BAU / MBMS (nivel sistema):** agrega los racks, se comunica con el PCS y el EMS, y publica los límites dinámicos de potencia de carga y descarga.

**Funciones lógicas principales:**

*Estimación del Estado de Carga (SoC).* El método base es el conteo de Coulomb:

$$
SoC(t) = SoC(t_0) + \frac{1}{Q_{\text{nom}}}\int_{t_0}^{t} \eta_c\, i(\tau)\, d\tau
$$

Ese método acumula error por la deriva del sensor de corriente. En LFP, la curva OCV plana impide corregirlo mediante la tensión en la zona de 20–90 % de SoC, por lo que se emplean **filtros de Kalman extendidos (EKF)** sobre un modelo de circuito equivalente de Thevenin:

$$
V_t = V_{\text{OCV}}(SoC, T) - i\,R_0 - V_{RC}, \qquad \frac{dV_{RC}}{dt} = -\frac{V_{RC}}{R_1 C_1} + \frac{i}{C_1}
$$

y una recalibración periódica en los extremos de la curva (carga completa).

*Estado de Salud (SoH):*

$$
SoH_Q = \frac{Q_{\text{act}}}{Q_{\text{nom}}}\times 100\ \%, \qquad SoH_R = \frac{R_{\text{EoL}} - R_{\text{act}}}{R_{\text{EoL}} - R_{\text{nom}}}\times 100\ \%
$$

El fin de vida (EoL) se define convencionalmente en $SoH_Q = 80\ \%$ para aplicaciones de red.

*Balanceo de celdas.* El balanceo **pasivo** disipa en resistencias la energía de las celdas de mayor tensión; el balanceo **activo** transfiere energía entre celdas. El desbalance limita la capacidad útil del string a la de la celda más débil:

$$
Q_{\text{string}} = \min_{k}\left(Q_k\right) \quad \text{(sin balanceo)}
$$

*Protecciones y límites dinámicos.* El BMS calcula en tiempo real la corriente máxima admisible:

$$
I_{\max,\text{car}}(t) = f\left(SoC,\ T_{\text{celda}},\ V_{\text{celda,máx}}\right), \qquad I_{\max,\text{car}} \to 0 \ \text{ si } T_{\text{celda}} < 0\ ^\circ\text{C}
$$

y los transmite al PCS, que **debe** respetarlos. La desconexión por hardware (contactores) actúa como última barrera ante sobretensión, subtensión, sobrecorriente, sobretemperatura y falla de aislamiento.

#### c) Sistema de Conversión de Potencia (PCS) e inversor bidireccional

El PCS es un **convertidor fuente de tensión (VSC) bidireccional** trifásico, de dos o tres niveles (NPC), basado en IGBT y que opera en los cuatro cuadrantes del plano P–Q. Su capacidad está limitada por la corriente, no por la potencia activa:

$$
P^2 + Q^2 \le S_{\text{nom}}^2 \qquad\Rightarrow\qquad Q_{\text{disp}}(P) = \sqrt{S_{\text{nom}}^2 - P^2}
$$

Para modular la tensión de red en sistemas de 2 niveles con SVPWM se requiere:

$$
V_{DC,\min} \ge \sqrt{2}\, V_{LL,\text{rms}}\,(1 + \text{margen})
$$

Por ejemplo, para una salida de 400 V AC se necesitan al menos ~600 V DC en el bus. Esto fija la tensión mínima del banco de baterías al final de la descarga, y con ella el número de celdas en serie.

**Arquitectura de control en cascada (modo GFM):**

1. **Lazo externo de potencia:** *droop* P–f / Q–V o VSM → genera las referencias de $\theta$ y $|V|$.
2. **Lazo de tensión:** controla la tensión sobre el filtro LC.
3. **Lazo interno de corriente:** el más rápido (ancho de banda de ~1 kHz); **limita la corriente** para proteger los IGBT.
4. **Modulación PWM / SVPWM.**

**Filtro de salida LCL.** Atenúa los armónicos de conmutación. La frecuencia de resonancia debe cumplir:

$$
f_{\text{res}} = \frac{1}{2\pi}\sqrt{\frac{L_1 + L_2}{L_1 L_2 C_f}}, \qquad 10 f_1 < f_{\text{res}} < \frac{f_{\text{sw}}}{2}
$$

#### d) Sistema de Gestión de Energía (EMS) y *Dynamic Peak Shaving*

El EMS es el nivel de **control terciario** de la microred: decide **cuánta** potencia intercambia el BESS en cada intervalo, mientras que el PCS decide **cómo** se ejecuta.

**Modelo de estado del almacenamiento (tiempo discreto, paso $\Delta t$):**

$$
SoC_{t+1} = SoC_t + \frac{\Delta t}{E_{\text{nom}}}\left(\eta_{\text{ch}}\,P^{\text{ch}}_t - \frac{P^{\text{dis}}_t}{\eta_{\text{dis}}}\right)
$$

$$
SoC_{\min} \le SoC_t \le SoC_{\max}, \qquad 0 \le P^{\text{ch}}_t \le P_{\max}\,u_t, \qquad 0 \le P^{\text{dis}}_t \le P_{\max}\,(1 - u_t), \quad u_t \in \{0,1\}
$$

**Peak shaving estático** (umbral fijo $P_{\text{lim}}$):

$$
P^{\text{dis}}_t = \max\left(0,\ P_{L,t} - P_{FV,t} - P_{\text{lim}}\right)
$$

**Peak shaving dinámico.** El umbral $P_{\text{lim},t}$ se recalcula en cada horizonte de despacho, a partir del pronóstico de carga y de irradiancia, para **minimizar el costo total de operación diésel** sujeto al balance de energía:

$$
\min_{P^{\text{ch}},\,P^{\text{dis}},\,n_G}\ \sum_{t=1}^{T}\left[\sum_{i=1}^{n_{G,t}} c_{\text{comb}}\,F_i\!\left(P_{G_i,t}\right) + c_{\text{arr}}\,y_{i,t} + c_{\text{deg}}\left(P^{\text{ch}}_t + P^{\text{dis}}_t\right)\Delta t\right]
$$

$$
\text{s.a.}\quad \sum_i P_{G_i,t} + P_{FV,t} + P^{\text{dis}}_t - P^{\text{ch}}_t = P_{L,t}, \qquad \sum_{i} P_{\text{nom},i} - \sum_i P_{G_i,t} + R_{\text{BESS},t} \ge R_{\text{req}}
$$

La curva de consumo de combustible de un grupo diésel se modela como lineal con término fijo:

$$
F_i(P) = a_i\,P_{\text{nom},i} + b_i\,P \qquad [\text{L/h}]
$$

El término fijo $a_i P_{\text{nom},i}$ explica por qué **apagar un grupo** (reducir $n_G$) ahorra mucho más combustible que reducir la carga de varios grupos en paralelo. Esta es la principal fuente de ahorro de un BESS en microredes diésel. El costo de degradación $c_{\text{deg}}$ (§ 2.2.5-e) evita que el optimizador cicle la batería cuando el ahorro marginal es inferior al desgaste que produce.

---

### 2.2.3 Eficiencia energética del BESS

#### a) Eficiencia de ida y vuelta (RTE)

La eficiencia de ida y vuelta (*Round-Trip Efficiency*) relaciona la energía AC entregada en descarga con la energía AC absorbida en carga, a lo largo de un ciclo completo que regresa al mismo SoC:

$$
\eta_{\text{RTE}} = \frac{E_{\text{AC,dis}}}{E_{\text{AC,ch}}} = \eta_{\text{TR}}^2 \cdot \eta_{\text{PCS,ch}} \cdot \eta_{\text{bat}} \cdot \eta_{\text{PCS,dis}}
$$

La eficiencia de la batería se descompone en eficiencia coulómbica y eficiencia de tensión:

$$
\eta_{\text{bat}} = \eta_{\text{coul}}\cdot\eta_{V} = \frac{\int i_{\text{dis}}\,dt}{\int i_{\text{ch}}\,dt}\cdot\frac{\bar V_{\text{dis}}}{\bar V_{\text{ch}}}
$$

donde $\bar V_{\text{dis}} = V_{\text{OCV}} - I R_{\text{int}}$ y $\bar V_{\text{ch}} = V_{\text{OCV}} + I R_{\text{int}}$. Por lo tanto, $\eta_V$ disminuye al aumentar la tasa C y la resistencia interna (es decir, con el envejecimiento y con el frío).

**RTE neto (de sistema), que incluye los consumos auxiliares:**

$$
\eta_{\text{RTE,neto}} = \frac{E_{\text{AC,dis}} - E_{\text{aux,dis}}}{E_{\text{AC,ch}} + E_{\text{aux,ch}}}
\qquad\text{con}\qquad
E_{\text{aux}} = \int\left(P_{\text{HVAC}} + P_{\text{calef}} + P_{\text{BMS}} + P_{\text{ctrl}}\right)dt
$$

**Valores típicos:**

| Componente | Eficiencia |
|---|---|
| Transformador BT/MT (por paso) | 98,5–99,0 % |
| PCS (por paso) | 97,5–98,5 % |
| Batería LFP (a 0,5C) | 94–97 % |
| **RTE AC–AC sin auxiliares** | **≈ 88–92 %** |
| **RTE neto con auxiliares (clima de altura)** | **≈ 82–88 %** |

> [!NOTE]
> **Efecto del clima de Caylloma sobre el RTE.** A diferencia de los climas cálidos, donde domina el consumo de aire acondicionado, a 4 500 msnm el auxiliar dominante es la **calefacción nocturna** para mantener las celdas por encima de 5–10 °C. La baja densidad del aire reduce además la eficacia de los intercambiadores (§ 2.2.4-a). En la evaluación económica debe usarse el $\eta_{\text{RTE,neto}}$ anual, ponderado por el perfil térmico de sitio, y no el valor de placa del fabricante.

#### b) Energía útil y relación con el dimensionamiento

$$
E_{\text{útil}} = E_{\text{nom}}\cdot\left(SoC_{\max} - SoC_{\min}\right)\cdot SoH(t)\cdot\eta_{\text{dis}}
$$

Para el BESS de 1 MWh, con una ventana operativa de 10–95 % y un SoH al final de su vida de 80 %:

$$
E_{\text{útil,EoL}} = 1\,000 \times 0{,}85 \times 0{,}80 \times 0{,}96 \approx 653\ \text{kWh}
$$

Ese valor debe cubrir el requerimiento energético de diseño al final de la vida útil. De lo contrario, debe preverse un **aumento de capacidad (*augmentation*)**.

---

### 2.2.4 Fenómenos físicos a gran altitud (4 500 msnm)

#### a) Atmósfera a gran altitud: presión, densidad y temperatura

Según la Atmósfera Estándar Internacional (ISA, ISO 2533), en la troposfera:

$$
p(h) = p_0\left(1 - \frac{L\,h}{T_0}\right)^{\frac{g\,M}{R\,L}} = 101{,}325\left(1 - 2{,}25577\times10^{-5}\,h\right)^{5{,}25588}\ \text{kPa}
$$

$$
T(h) = T_0 - L\,h, \qquad \rho(h) = \frac{p(h)\,M}{R\,T(h)}
$$

con $T_0 = 288{,}15$ K, $L = 0{,}0065$ K/m, $M = 0{,}028964$ kg/mol y $R = 8{,}314$ J/(mol·K).

| Magnitud | Nivel del mar | 1 000 m | 2 000 m | **4 500 m (El Santo)** |
|---|---|---|---|---|
| Presión $p$ (kPa) | 101,3 | 89,9 | 79,5 | **57,7** |
| $p/p_0$ | 1,000 | 0,887 | 0,785 | **0,570** |
| Temperatura ISA (°C) | 15,0 | 8,5 | 2,0 | **−14,3** |
| Densidad relativa ISA $\rho/\rho_0$ | 1,000 | 0,907 | 0,822 | **0,634** |
| Densidad relativa a 5 °C ambiente | — | — | — | **0,590** |
| Punto de ebullición del agua (°C) | 100 | ≈ 97 | ≈ 93 | **≈ 85** |

#### b) Transferencia de calor por convección en aire enrarecido

El calor disipado por convección desde una superficie (disipador de los IGBT, módulos de batería) es:

$$
\dot Q_{\text{conv}} = h\,A\,(T_s - T_\infty), \qquad h = \frac{\text{Nu}\cdot k}{L_c}
$$

La conductividad térmica del aire $k$ es prácticamente independiente de la presión, pero el número de Nusselt depende de la densidad a través de los números de Reynolds (convección forzada) y de Grashof (convección natural):

$$
\text{Re} = \frac{\rho\,u\,L_c}{\mu}, \qquad \text{Gr} = \frac{g\,\beta\,\rho^2\,(T_s - T_\infty)\,L_c^3}{\mu^2}
$$

Como la viscosidad dinámica $\mu$ tampoco depende de la presión:

| Régimen | Correlación | Dependencia de $h$ | Factor a 4 500 m ($\rho/\rho_0 = 0{,}634$) |
|---|---|---|---|
| Forzada, flujo turbulento | $\text{Nu} \propto \text{Re}^{0{,}8}\,\text{Pr}^{1/3}$ | $h \propto \rho^{0{,}8}$ | $0{,}634^{0{,}8} = $ **0,694** (−31 %) |
| Forzada, flujo laminar | $\text{Nu} \propto \text{Re}^{0{,}5}\,\text{Pr}^{1/3}$ | $h \propto \rho^{0{,}5}$ | $0{,}634^{0{,}5} = $ **0,796** (−20 %) |
| Natural, laminar | $\text{Nu} \propto (\text{Gr}\,\text{Pr})^{1/4}$ | $h \propto \rho^{0{,}5}$ | **0,796** (−20 %) |
| Natural, turbulenta | $\text{Nu} \propto (\text{Gr}\,\text{Pr})^{1/3}$ | $h \propto \rho^{0{,}67}$ | **0,738** (−26 %) |

**Ventiladores de caudal volumétrico constante.** Un ventilador axial mueve aproximadamente el mismo caudal volumétrico $\dot V$ independientemente de la densidad, por lo que el **caudal másico** cae proporcionalmente:

$$
\dot Q = \dot m\,c_p\,\Delta T_{\text{aire}} = \rho\,\dot V\,c_p\,\Delta T_{\text{aire}} \quad\Rightarrow\quad \Delta T_{\text{aire}}\big|_{4500} = \frac{\Delta T_{\text{aire}}\big|_{0}}{0{,}634} \approx 1{,}58\ \Delta T_{\text{aire}}\big|_{0}
$$

Es decir, para la misma potencia disipada, **el aire de refrigeración se calienta un 58 % más**. Ese efecto se compensa parcialmente con la menor temperatura ambiente de sitio: es el fundamento físico del *derating* combinado altitud-temperatura.

#### c) Rigidez dieléctrica del aire y coordinación de aislamiento

**Ley de Paschen.** La tensión de ruptura de un gap uniforme depende del producto presión-distancia:

$$
V_b = \frac{B\,p\,d}{\ln\left(A\,p\,d\right) - \ln\left[\ln\left(1 + \dfrac{1}{\gamma_{se}}\right)\right]}
$$

En el rango de interés (a la derecha del mínimo de Paschen), $V_b$ **decrece** al disminuir $p$. Para la rigidez dieléctrica en función de la densidad relativa del aire $\delta$ (IEC 60060-1):

$$
\delta = \frac{p}{p_0}\cdot\frac{273 + t_0}{273 + t}, \qquad V_{b}(\delta) \approx \delta^{m}\,V_{b,0}, \quad m \in [0{,}5;\ 1{,}0]
$$

Con $p = 57{,}7$ kPa y $t = 5$ °C se obtiene $\delta = 0{,}570 \times 293/278 = 0{,}600$, es decir, una **pérdida de rigidez dieléctrica del orden del 25–40 %** respecto de las condiciones de referencia.

**Factor de corrección de altitud para aislamiento externo (IEC 60071-2):**

$$
K_a = e^{\,m\,\frac{H - 1\,000}{8\,150}}
$$

donde $H$ es la altitud de instalación (m) y $m = 1$ para tensiones de corta duración a frecuencia industrial y para impulsos atmosféricos (se toma $H - 1\,000$ porque el equipo está normalizado hasta 1 000 m). Para El Santo:

$$
K_a = e^{\,\frac{3\,500}{8\,150}} = e^{0{,}4294} \approx 1{,}54
$$

Por lo tanto, **el nivel de aislamiento requerido en el sitio debe especificarse 54 % superior** al de un equipo estándar, lo que en MT conduce frecuentemente a seleccionar la clase de tensión inmediatamente superior.

**Baja tensión (IEC 60664-1, Tabla A.2):** factores multiplicadores de las distancias en el aire (*clearances*):

| Altitud (m) | 2 000 | 3 000 | 4 000 | **4 500** (interpolado) | 5 000 |
|---|---|---|---|---|---|
| Factor de multiplicación | 1,00 | 1,14 | 1,29 | **≈ 1,38** | 1,48 |

Esto afecta directamente a los tableros DC de 1 500 V del banco de baterías y al PCS.

#### d) *Derating* térmico de semiconductores de potencia (IGBT del PCS)

**Modelo térmico.** La temperatura de unión del IGBT en régimen permanente es:

$$
T_j = T_a + P_{\text{loss}}\left(R_{th,jc} + R_{th,ch} + R_{th,ha}\right)
$$

con pérdidas de conducción y de conmutación:

$$
P_{\text{loss}} = \underbrace{V_{CE0}\,I_{\text{avg}} + r_{CE}\,I_{\text{rms}}^2}_{\text{conducción}} + \underbrace{f_{sw}\,\left(E_{on} + E_{off}\right)\frac{V_{DC}}{V_{\text{ref}}}\frac{I}{I_{\text{ref}}}}_{\text{conmutación}}
$$

Solo la resistencia disipador-ambiente $R_{th,ha} = 1/(h\,A_{\text{eff}})$ depende de la altitud. Imponiendo la temperatura de unión máxima admisible ($T_{j,\max} = 150$ o $175$ °C, con un margen de diseño de ~25 K):

$$
P_{\text{loss,adm}}(H) = \frac{T_{j,\max} - T_a}{R_{th,jc} + R_{th,ch} + \dfrac{1}{h(H)\,A_{\text{eff}}}}
$$

Como $P_{\text{loss}} \propto I^{\alpha}$ (con $1 < \alpha < 2$), la corriente admisible del PCS cae con la altitud.

**Regla práctica de los fabricantes.** Los fabricantes de PCS/inversores especifican típicamente un *derating* lineal a partir de una altitud de referencia $H_{\text{ref}}$ (1 000–2 000 m según el modelo):

$$
k_{\text{alt}} = 1 - c_{\text{alt}}\cdot\frac{H - H_{\text{ref}}}{100}, \qquad c_{\text{alt}} \approx 0{,}01\ \text{p.u./100 m (valor típico, a confirmar con la hoja de datos)}
$$

$$
S_{\text{PCS,nom}} \ge \frac{P_{\text{BESS}}}{k_{\text{alt}}\cdot k_{T}\cdot \text{FP}_{\min}}
$$

**Ejemplo:** con $H_{\text{ref}} = 2\,000$ m y $c_{\text{alt}} = 1\ \%$/100 m, se obtiene $k_{\text{alt}} = 1 - 0{,}25 = 0{,}75$. Para entregar 500 kW con $\text{FP} = 0{,}9$ y $k_T = 1{,}0$ (temperatura de sitio baja):

$$
S_{\text{PCS,nom}} \ge \frac{500}{0{,}75 \times 1{,}0 \times 0{,}9} \approx 741\ \text{kVA}
$$

> [!IMPORTANT]
> El ejemplo anterior es **ilustrativo**. El *derating* real debe tomarse de la **curva altitud-temperatura de la hoja de datos** del PCS seleccionado. Muchos fabricantes certifican sus equipos solo hasta 3 000–4 000 m: un PCS sin certificación explícita para 4 500 m **no debe** especificarse, aunque aplicar el factor de *derating* parezca compensar el déficit, porque el límite de aislamiento (§ 2.2.4-c) y el de radiación cósmica (§ 2.2.4-e) no se resuelven con *derating* térmico.

#### e) Radiación cósmica y fallas por *Single Event Burnout* (SEB) en IGBT

Los neutrones atmosféricos de alta energía, cuyo flujo aumenta con la altitud, pueden desencadenar una avalancha destructiva en un IGBT bloqueando alta tensión DC. El modelo empírico de tasa de fallas de Kaminski y Kopta (ABB, nota de aplicación 5SYA 2042) es:

$$
\lambda(V_{DC}, T_j, h) = C_3\cdot\exp\left(\frac{C_2}{C_1 - V_{DC}}\right)\cdot\exp\left(\frac{25 - T_j}{47{,}6}\right)\cdot\exp\left(\frac{1 - \left(1 - \dfrac{h}{44\,300}\right)^{5{,}26}}{0{,}143}\right)\quad[\text{FIT}]
$$

donde el último factor es el multiplicador por altitud. Para $h = 4\,500$ m:

$$
\left(1 - \frac{4\,500}{44\,300}\right)^{5{,}26} = 0{,}569 \quad\Rightarrow\quad \exp\left(\frac{1 - 0{,}569}{0{,}143}\right) = e^{3{,}01} \approx 20
$$

La tasa de fallas por rayos cósmicos es **~20 veces mayor que a nivel del mar** para la misma tensión DC. Como $\lambda$ crece exponencialmente con $V_{DC}$, la medida de mitigación de diseño es **reducir la tensión DC de operación** respecto de la tensión de bloqueo del IGBT (por ejemplo, operar un IGBT de 1 700 V a no más de ~900–1 000 V DC), o elegir un dispositivo de mayor clase de tensión. Esto restringe la tensión máxima del banco de baterías.

#### f) Otros efectos de la altitud relevantes para el BESS

| Fenómeno | Efecto | Medida de diseño |
|---|---|---|
| Baja temperatura ambiente (−15 a +18 °C, con ciclos diarios amplios) | Prohíbe cargar LFP por debajo de 0 °C (deposición de litio metálico) y aumenta la resistencia interna | Calefacción, aislamiento térmico del contenedor y precalentamiento antes de cargar |
| Ciclado térmico diario amplio | Fatiga de las uniones soldadas y del *wire-bonding* de los IGBT ($N_f \propto \Delta T_j^{-n}$, ley de Coffin-Manson) | Control térmico activo para reducir $\Delta T_j$ |
| Radiación UV intensa | Degradación de cables, juntas y pinturas | Materiales resistentes a UV |
| Descargas atmosféricas (alta densidad de rayos en la puna) | Sobretensiones inducidas | DPS tipo 1+2 en AC y DC; apantallamiento |
| Desclasificación de los grupos diésel (ISO 3046-1) | Los grupos entregan ~25–35 % menos de su potencia nominal | **Aumenta el valor relativo del BESS** como reserva y soporte de potencia |
| Ebullición del refrigerante a menor temperatura | Afecta a los sistemas de refrigeración líquida de las baterías | Circuitos presurizados; glicol con punto de congelación adecuado |
| Menor capacidad de interrupción de arcos en aire | Interruptores y fusibles DC/AC | Equipos certificados para la altitud o desclasificados |

---

### 2.2.5 Teoría de degradación electroquímica

#### a) Mecanismos físicos

La pérdida de capacidad y el aumento de la resistencia interna en celdas LFP/grafito se deben principalmente a:

1. **Crecimiento de la interfase sólido-electrolito (SEI)** en el ánodo de grafito: consume litio cíclable (**LLI**, *Loss of Lithium Inventory*). Es el mecanismo dominante en LFP.
2. **Pérdida de material activo (LAM)** por fracturas mecánicas debidas a la expansión y contracción volumétrica durante el ciclado.
3. **Deposición de litio metálico (*lithium plating*)** al cargar a baja temperatura o con tasa C alta. Es irreversible y puede generar dendritas que provoquen cortocircuitos internos.
4. **Descomposición del electrolito** a alta temperatura y con alto SoC (potencial anódico bajo).

La degradación total se modela como la superposición de dos componentes:

$$
Q_{\text{loss}}(t) = Q_{\text{loss,cal}}(t) + Q_{\text{loss,cic}}(t), \qquad SoH(t) = 1 - Q_{\text{loss}}(t)
$$

#### b) Degradación calendárica

Ocurre **en reposo**, incluso sin ciclado. Su cinética es de tipo difusivo (el crecimiento de la SEI está limitado por la difusión a través de la propia capa):

$$
Q_{\text{loss,cal}}(t) = k_{\text{cal}}(T, SoC)\cdot t^{\,z}, \qquad z \approx 0{,}5
$$

La dependencia con la temperatura sigue la **ley de Arrhenius**:

$$
k_{\text{cal}}(T, SoC) = A_{\text{cal}}\cdot\exp\left(-\frac{E_a}{R\,T}\right)\cdot g(SoC)
$$

donde $E_a$ es la energía de activación (para LFP/grafito, del orden de 20–50 kJ/mol según el estudio) y $g(SoC)$ es una función creciente del SoC. **Almacenar a alto SoC acelera la degradación calendárica**, porque el bajo potencial del ánodo litiado favorece la reducción del electrolito.

> [!TIP]
> **Ventaja climática del sitio.** Por la ley de Arrhenius, una temperatura de celda media de 15 °C (frente a 30 °C en climas cálidos) reduce $k_{\text{cal}}$ en un factor:
> $$\frac{k(288\ \text{K})}{k(303\ \text{K})} = \exp\left[-\frac{E_a}{R}\left(\frac{1}{288} - \frac{1}{303}\right)\right] \approx 0{,}38 \quad (E_a = 47{,}2\ \text{kJ/mol})$$
> El frío de Caylloma es **beneficioso** para la vida calendárica, siempre que se evite la carga por debajo de 0 °C.

#### c) Degradación cíclica

Se debe al paso de carga (*throughput*) y a los esfuerzos mecánicos del ciclado. El modelo semiempírico de Wang et al. (2011) para celdas LFP/grafito es:

$$
Q_{\text{loss,cic}} = B(C_{\text{rate}})\cdot\exp\left(\frac{-31\,700 + 370{,}3\cdot C_{\text{rate}}}{R\,T}\right)\cdot\left(A_h\right)^{0{,}55}
$$

donde $A_h$ es el *throughput* acumulado de carga (Ah) y $B$ un factor preexponencial que depende de la tasa C.

**Dependencia con la profundidad de descarga (DoD).** La vida cíclica disminuye con la DoD según una ley de potencia (tipo Wöhler):

$$
N_{\text{ciclos}}(DoD) = N_{100}\cdot DoD^{-k_p}, \qquad k_p \approx 0{,}8 \text{ – } 2{,}1
$$

donde $N_{100}$ es la vida a 100 % de DoD. Como $k_p > 1$ en muchas químicas, **dos ciclos al 50 % de DoD degradan menos que uno al 100 %**, aunque transfieran la misma energía. La degradación por ciclo individual es:

$$
d_{\text{ciclo}}(DoD) = \frac{1 - SoH_{\text{EoL}}}{N_{\text{ciclos}}(DoD)} = \frac{0{,}2}{N_{100}}\,DoD^{\,k_p}
$$

**Conteo de ciclos irregulares (algoritmo *rainflow*, ASTM E1049).** El perfil de SoC real de un BESS de peak shaving es irregular. El algoritmo *rainflow* lo descompone en ciclos completos y medios ciclos de profundidad $DoD_j$, y la degradación cíclica acumulada se obtiene por la **regla de Palmgren-Miner**:

$$
D_{\text{cic}} = \sum_{j} n_j\cdot d_{\text{ciclo}}(DoD_j)\cdot S_{\text{SoC}}(\overline{SoC}_j)\cdot S_T(T_j)
$$

donde $n_j \in \{0{,}5;\ 1\}$, y $S_{\text{SoC}}$ y $S_T$ son factores de esfuerzo por el SoC medio del ciclo y por la temperatura (modelo de Xu et al., 2018).

#### d) Ciclos completos equivalentes (EFC)

$$
\text{EFC} = \frac{\int \left|P_{\text{bat}}(t)\right|\,dt}{2\,E_{\text{nom}}}
$$

Es la métrica que usan las garantías de los fabricantes (por ejemplo, «6 000 EFC o 10 años, lo que ocurra primero, con SoH ≥ 70–80 %»).

#### e) Costo de degradación para el despacho económico

Para que el EMS (§ 2.2.2-d) internalice el desgaste, se define un costo marginal de degradación por kWh transferido:

$$
c_{\text{deg}} = \frac{C_{\text{reemplazo}}\ [\text{US\$}]}{2\cdot N_{\text{ciclos}}(DoD)\cdot DoD\cdot E_{\text{nom}}\cdot\sqrt{\eta_{\text{RTE}}}} \quad [\text{US\$/kWh}]
$$

**Ejemplo:** con $C_{\text{reemplazo}} = 200\,000$ US\$ (celdas de 1 MWh), $N = 6\,000$ ciclos a $DoD = 0{,}8$ y $\eta_{\text{RTE}} = 0{,}88$:

$$
c_{\text{deg}} = \frac{200\,000}{2 \times 6\,000 \times 0{,}8 \times 1\,000 \times 0{,}938} \approx 0{,}022\ \text{US\$/kWh}
$$

Este costo se compara con el costo marginal de la energía diésel desplazada. A 4 500 msnm, considerando el transporte de combustible en altura, este último suele estar en el rango de 0,25–0,40 US\$/kWh. La gran diferencia entre ambos valores justifica el ciclado diario del BESS.

#### f) Estrategias de operación derivadas de la teoría

| Principio teórico | Regla operativa del EMS |
|---|---|
| $k_{\text{cal}}$ crece con el SoC | No mantener el BESS al 100 % de SoC en reposo; usar una ventana de 10–90 % y cargar «justo a tiempo» antes del pico. |
| $N(DoD) \propto DoD^{-k_p}$ | Preferir ciclos parciales cuando el ahorro marginal lo permita. |
| Arrhenius | Mantener las celdas en 15–25 °C; evitar sobrecalentamiento en descargas sostenidas. |
| *Lithium plating* por debajo de 0 °C | Bloquear la carga (BMS) y precalentar con energía FV de la mañana. |
| Rainflow + Miner | Registrar el historial de SoC para recalcular el SoH y planificar el aumento de capacidad (*augmentation*). |

---

## 2.3 Definición de términos básicos

| Término | Definición |
|---|---|
| **BESS** | *Battery Energy Storage System.* Sistema que integra baterías, PCS, BMS, EMS y auxiliares para almacenar y entregar energía eléctrica. |
| **BMS** | *Battery Management System.* Sistema electrónico que supervisa y protege las celdas, estima el SoC y el SoH y comunica los límites al PCS. |
| **C-rate** | Tasa de corriente normalizada a la capacidad: 1C descarga la capacidad nominal en 1 h. Un BESS de 500 kW / 1 MWh opera a 0,5C. |
| **DoD** | *Depth of Discharge.* Fracción de la capacidad descargada en un ciclo: $DoD = 1 - SoC_{\min}$ para un ciclo que parte del 100 %. |
| **EFC** | *Equivalent Full Cycles.* Throughput de energía normalizado a ciclos completos. |
| **EMS** | *Energy Management System.* Controlador de nivel superior que decide el despacho del BESS. |
| **Grid-Forming** | Modo de control en el que el convertidor actúa como fuente de tensión e impone la tensión y la frecuencia. |
| **Grid-Following** | Modo de control en el que el convertidor actúa como fuente de corriente sincronizada mediante un PLL. |
| **LFP** | Química de cátodo de fosfato de hierro y litio (LiFePO₄). |
| **PCC** | *Point of Common Coupling.* Punto de conexión común entre el BESS y la red de la microred. |
| **PCS** | *Power Conversion System.* Convertidor bidireccional DC/AC con sus controles y protecciones. |
| **Peak shaving** | Recorte de los picos de demanda mediante la descarga del BESS. Es *dinámico* cuando el umbral se ajusta en función de pronósticos. |
| **RoCoF** | *Rate of Change of Frequency.* Tasa de cambio de la frecuencia (Hz/s). |
| **RTE** | *Round-Trip Efficiency.* Eficiencia de ida y vuelta (energía descargada/energía cargada). |
| **SEB** | *Single Event Burnout.* Falla destructiva de un semiconductor causada por una partícula cósmica. |
| **SoC** | *State of Charge.* Estado de carga (0–100 %). |
| **SoH** | *State of Health.* Estado de salud (capacidad actual/capacidad nominal). |
| **Fuga térmica** (*thermal runaway*) | Reacción exotérmica autoacelerada en una celda, en la que el calor generado supera al disipado. |
| **Derating** | Desclasificación: reducción de la capacidad nominal de un equipo por condiciones ambientales (altitud, temperatura). |

---

## 2.4 Referencias del capítulo

> Formato sugerido: APA 7.ª edición (verifique la guía de estilo vigente de la Universidad Continental). Las normas se citan por su organismo emisor.

**Normativa peruana**

- Decreto Ley N.° 25844 (1992). *Ley de Concesiones Eléctricas*. Diario Oficial *El Peruano*.
- Decreto Supremo N.° 009-93-EM (1993). *Reglamento de la Ley de Concesiones Eléctricas*.
- Ley N.° 28832 (2006). *Ley para Asegurar el Desarrollo Eficiente de la Generación Eléctrica*.
- Ley N.° 32249 (2025). *Ley que modifica la Ley N.° 28832, Ley para Asegurar el Desarrollo Eficiente de la Generación Eléctrica*. ⚠️ Verificar el título oficial exacto.
- Decreto Supremo N.° 069-2006-EM. *Reglamento del Mecanismo de Compensación para Sistemas Aislados*.
- Ley N.° 29970 (2012). *Ley que afianza la seguridad energética y promueve el desarrollo del polo petroquímico en el sur del país* (numeral 5.2, compensación en sistemas aislados).
- Decreto Supremo N.° 020-97-EM (1997). *Norma Técnica de Calidad de los Servicios Eléctricos*.
- Resolución Ministerial N.° 214-2011-MEM/DM (2011). *Código Nacional de Electricidad — Suministro 2011*.
- Resolución Ministerial N.° 037-2006-MEM/DM (2006). *Código Nacional de Electricidad — Utilización*.
- Decreto Supremo N.° 024-2016-EM (2016). *Reglamento de Seguridad y Salud Ocupacional en Minería*.
- Decreto Supremo N.° 014-2019-EM (2019). *Reglamento para la Protección Ambiental en las Actividades Eléctricas*.
- Resolución Ministerial N.° 125-2025-MINEM/DM. Prepublicación del proyecto de reglamento sobre sistemas eléctricos aislados (Ley 32249). ⚠️ Verificar si ya fue aprobado.

**Estándares internacionales**

- UL. *UL 9540 — Standard for Energy Storage Systems and Equipment*. Underwriters Laboratories. ⚠️ Citar la edición vigente.
- UL. *UL 9540A — Test Method for Evaluating Thermal Runaway Fire Propagation in Battery Energy Storage Systems*. ⚠️ Citar la edición vigente.
- UL. *UL 1973 — Batteries for Use in Stationary and Motive Auxiliary Power Applications*.
- IEC. (2022). *IEC 62619:2022 — Safety requirements for secondary lithium cells and batteries, for use in industrial applications*.
- IEC. *IEC 62933-5-2 — Electrical energy storage (EES) systems — Safety requirements for grid-integrated EES systems — Electrochemical-based systems*.
- NFPA. *NFPA 855 — Standard for the Installation of Stationary Energy Storage Systems*. National Fire Protection Association. ⚠️ Citar la edición vigente (2023 o 2026).
- NFPA. *NFPA 68 — Standard on Explosion Protection by Deflagration Venting*; *NFPA 69 — Standard on Explosion Prevention Systems*.
- IEEE. (2018). *IEEE Std 1547-2018 — Interconnection and Interoperability of DER with Associated Electric Power Systems Interfaces*.
- IEEE. (2022). *IEEE Std 2800-2022 — Interconnection and Interoperability of Inverter-Based Resources Interconnecting with Associated Transmission Electric Power Systems*.
- IEEE. (2017). *IEEE Std 2030.7-2017 — Specification of Microgrid Controllers*.
- IEEE. (2022). *IEEE Std 519-2022 — Harmonic Control in Electric Power Systems*.
- IEEE. (2013). *IEEE Std 80-2013 — Guide for Safety in AC Substation Grounding*.
- IEC. *IEC 60664-1 — Insulation coordination for equipment within low-voltage supply systems*.
- IEC. *IEC 60071-2 — Insulation co-ordination — Part 2: Application guidelines*.
- IEC. *IEC 60060-1 — High-voltage test techniques — General definitions and test requirements*.
- ISO. *ISO 2533 — Standard Atmosphere*.
- ISO. *ISO 3046-1 — Reciprocating internal combustion engines — Performance*.

**Literatura científica y técnica**

- Wang, J., Liu, P., Hicks-Garner, J., Sherman, E., Soukiazian, S., Verbrugge, M., Tataria, H., Musser, J., & Finamore, P. (2011). Cycle-life model for graphite-LiFePO₄ cells. *Journal of Power Sources, 196*(8), 3942–3948.
- Xu, B., Oudalov, A., Ulbig, A., Andersson, G., & Kirschen, D. S. (2018). Modeling of lithium-ion battery degradation for cell life assessment. *IEEE Transactions on Smart Grid, 9*(2), 1131–1140.
- Naumann, M., Schimpe, M., Keil, P., Hesse, H. C., & Jossen, A. (2018). Analysis and modeling of calendar aging of a commercial LiFePO₄/graphite cell. *Journal of Energy Storage, 17*, 153–169.
- Kaminski, N., & Kopta, A. *Failure rates of HiPak modules due to cosmic rays* (Application Note 5SYA 2042). ABB Switzerland Ltd., Semiconductors.
- Rocabert, J., Luna, A., Blaabjerg, F., & Rodríguez, P. (2012). Control of power converters in AC microgrids. *IEEE Transactions on Power Electronics, 27*(11), 4734–4749.
- Zhong, Q.-C., & Weiss, G. (2011). Synchronverters: Inverters that mimic synchronous generators. *IEEE Transactions on Industrial Electronics, 58*(4), 1259–1267.
- Plett, G. L. (2015). *Battery Management Systems, Volume I: Battery Modeling*. Artech House.
- Incropera, F. P., DeWitt, D. P., Bergman, T. L., & Lavine, A. S. (2007). *Fundamentals of Heat and Mass Transfer* (6.ª ed.). Wiley.
- Kuffel, E., Zaengl, W. S., & Kuffel, J. (2000). *High Voltage Engineering: Fundamentals* (2.ª ed.). Newnes.
- Feng, X., Ouyang, M., Liu, X., Lu, L., Xia, Y., & He, X. (2018). Thermal runaway mechanism of lithium ion battery for electric vehicles: A review. *Energy Storage Materials, 10*, 246–267.

---

> [!NOTE]
> **Sobre originalidad.** Este capítulo está redactado con formulación propia. Aun así, las definiciones normativas y las ecuaciones clásicas (Arrhenius, Paschen, Dwight, IEEE 80) coinciden necesariamente con la literatura. Para el informe de originalidad, mantenga la cita explícita de cada norma y ecuación en el punto donde aparece, y parafrasee con sus propias palabras cualquier texto que incorpore de las fuentes recuperadas por su motor RAG.
