---
tags: [comap, tema, machine-learning, rcm]
---
# Machine learning en RCM
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> El demo usa **datos simulados**; en la tesis esto va como **trabajo futuro**, no como resultado medido.

Demo interactivo: [Flota Sur ML](https://claude.ai/artifact/SUKwxFbWcSJX8c1GoRba35) · Capítulo 8 del [Aula ComAp](https://claude.ai/artifact/Ea2rDwHpkqJXCF4Wyak7RN)

## Idea central [I]
El RCM decide qué modos de falla importan y qué tarea corresponde; el machine learning mejora:
- **D (detección):** avisa antes que la alarma del controlador.
- **O (ocurrencia):** se estima con datos (Weibull) en vez de a criterio.
- **Intervalo P-F:** se mide cuántos días hay entre la primera señal y la falla.

## Datos necesarios
- El historial del controlador no basta: FIFO de unos 100 registros [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=109|IC p. 109]]] y no guarda los valores de la ECU, solo los códigos [D, [[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]].
- Hace falta **registro continuo** (Modbus cada minuto) de kW, temperatura del refrigerante, presión de aceite, consumo, voltaje de batería y temperatura ambiente [I].

## Métodos del demo [I]
| Método | Qué detecta | Cómo |
|---|---|---|
| Residuo de temperatura | Radiador obstruido | T esperada = a + b·kW + c·T amb; alerta si el residuo > 3σ 3 días seguidos |
| Residuo de presión de aceite | Desgaste de cojinetes | P esperada = a + b·kW |
| Residuo de consumo | Inyectores (no tiene alarma en el controlador) | Consumo esperado = a + b·kW, en % |
| Tendencia de batería | Batería degradada | Voltaje mínimo al arrancar; días hasta 18 V |
| Isolation Forest | Fallas multivariables | Bosque entrenado con la flota sana; umbral fijado con días no vistos |
| Weibull | Vida de baterías | β (forma), η (vida característica), B10 = η·(−ln 0,9)^(1/β) |

## Reglas para no engañarse [I]
- Con pocas fallas no se entrena un clasificador de fallas: se modela lo **normal**.
- El umbral se calcula con datos que el modelo no vio.
- Bajar el umbral avisa antes pero da más falsas alarmas.
- Reportar siempre: días de adelanto **y** tasa de falsas alarmas.

Relacionado: [[Alarmas y protecciones]] · [[Diagnóstico]] · [[Progreso ComAp]]
