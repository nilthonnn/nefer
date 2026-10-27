---
tags: [comap, tema, potencia]
---

# Control de potencia
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> **Fuentes:** DS = Datasheet IC-NT 2013 · IC = InteliCompact NT 1.4 Reference Guide · AMF / MRS = InteliLite NT 1.5 Reference Guides
> ⚠️ Manuales de 2009–2013. El grupo de tu tesis usa **InteliGen 200** (generación nueva): los conceptos se mantienen, pero nombres y rangos de setpoints pueden cambiar.

## Idea base [I]
- **kW** ← combustible/velocidad → el controlador actúa sobre el **gobernador** (salida SRO).
- **kVAr y fp** ← excitación → actúa sobre el **AVR** (salida VRO, módulo IG-AVRi [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=26|IC p. 26]]).
- En **isla con un solo grupo** el controlador **no regula**: V y f los mantienen el AVR y el gobernador ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=97|IC p. 97]]).

## SPtM — un grupo en paralelo con la red [D]
| Fase | Qué pasa | Setpoint | Pág. |
|---|---|---|---|
| Subida de carga | Rampa hasta la carga pedida | **Load Ramp** (s para 0→100 %) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95\|IC p. 95]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=190\|IC p. 190]] |
| Carga constante | Mantiene kW fijos | **Baseload** (0 … potencia nominal, kW) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95\|IC p. 95]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=150\|IC p. 150]] |
| fp constante | Regula fp | **Base PF** (0,7 – 1,0) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95\|IC p. 95]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=150\|IC p. 150]] |
| Límite de exportación | No exporta más de lo fijado | **Export Limit** + **Export kW** (negativo = límite de importación) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=150\|IC p. 150]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=151\|IC p. 151]] |
| Arranque por carga / peak shaving | Arranca si la carga supera PeakLevelStart | **PeakLevelStart / Stop / PeakAutS/S Del** | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=96\|IC p. 96]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=152\|IC p. 152]] |
| Bajada de carga | Baja hasta GCB Open Level y abre | **GCB Open Level** (%), **GCB Open Del** (timeout) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=96\|IC p. 96]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=190\|IC p. 190]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=191\|IC p. 191]] |

Ejemplo de Load Ramp [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=190|IC p. 190]]]: si el cambio es del 50 % de la potencia nominal, la rampa dura el 50 % del setpoint.
El peak shaving necesita el módulo **IC-NT-CT-BIO7** para medir la corriente de red ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=96|IC p. 96]]).

## MINT — varios grupos [D]
- **#SysLdCtrl PtM** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=151|IC p. 151]]): **BASELOAD** (cada grupo toma una parte igual de **#SysBaseLoad**) o **LDSHARING** (todos al mismo % de carga) ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=97|IC p. 97]]).
- En isla: reparto de **kW** (LoadShare Gain/Int, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=191|IC p. 191]]) y de **kVAr** (VAr Share Gain/Int, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=193|IC p. 193]]).
- Desde SW 1.4.1, solo el controlador con **menor dirección CAN** regula el voltaje; los demás siguen la barra ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=115|IC p. 115]]).
- **Power management** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=99|IC p. 99]]): enciende/apaga grupos según reserva y prioridades.

## Qué lazo está activo en cada estado [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=114|IC p. 114]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=116|IC p. 116]]]
| Estado | Gobernador (kW/f) | AVR (V/fp) |
|---|---|---|
| Sin carga, GCB abierto | Valor fijo **Speed Gov Bias** | Valor fijo **AVRi Bias** |
| Sincronizando | Frecuencia → ángulo | Voltaje |
| Isla (SPtM) | Valor fijo | Voltaje |
| Paralelo con red | **Potencia** (Load Gain/Int) | **fp** (PF Gain/Int) |
| Isla MINT | **Reparto de carga** | **Reparto de VAr** |

## Ajuste de un lazo PI [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=116|IC p. 116]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=117|IC p. 117]]]
1. Desactiva temporalmente las alarmas relacionadas y pon Sync Timeout al máximo.
2. **Ganancia 5 %, integral 0 %**.
3. Modo **MAN**, arranca y lleva el grupo a la fase donde trabaja ese lazo.
4. Sube la ganancia hasta que **oscile**; déjala en **la mitad**.
5. Sube la integral hasta una respuesta aceptable (poca = lento; mucha = sobreimpulso u oscilación).
⚠️ Ten a mano la **parada de emergencia** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=117|IC p. 117]]).

## Protecciones de potencia [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=173|IC p. 173]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=177|IC p. 177]]]
| Protección | Setpoint | Rango |
|---|---|---|
| Sobrecarga (ANSI 32) | Overload BOC / Del | 100–200 % · 0–600 s |
| Potencia inversa (32R) | Reverse Pwr BOC / Del | 1–50 % · 0–600 s |
| Pérdida de excitación (40) | ExcitationLoss | −32 000 … 0 kVAr |

Relacionado: [[Sincronismo]] · [[Alarmas y protecciones]] · [[InteliCompact NT 1.4 Reference Guide]]
