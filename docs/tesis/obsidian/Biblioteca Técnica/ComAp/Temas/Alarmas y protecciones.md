---
tags: [comap, tema, alarmas]
---

# Alarmas y protecciones
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> **Fuentes:** DS = Datasheet IC-NT 2013 · IC = InteliCompact NT 1.4 Reference Guide · AMF / MRS = InteliLite NT 1.5 Reference Guides
> ⚠️ Manuales de 2009–2013. El grupo de tu tesis usa **InteliGen 200** (generación nueva): los conceptos se mantienen, pero nombres y rangos de setpoints pueden cambiar.

## Dos niveles de alarma [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=105|IC p. 105]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=107|IC p. 107]]]
| Nivel | Tipo | Qué hace el controlador |
|---|---|---|
| 🟡 **Amarillo** | **WRN** Warning | Solo avisa, no actúa sobre el grupo |
| 🔴 **Rojo** | **BOC** Breaker Open & Cool-down | Abre el GCB **de inmediato**, luego enfría y para (fallas eléctricas) |
| 🔴 **Rojo** | **STP** Slow stop | **Descarga suave**, abre el GCB, enfría y para |
| 🔴 **Rojo** | **SD** Shutdown | Abre el GCB y **para sin enfriar** |
| — | **FLS** Sensor fail | Sensor fuera de rango (muestra `####`); **no** afecta la operación |
| — | **MF** Mains failure (AMF) | Abre el MCB; **no** se escribe en la lista de alarmas ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=86\|AMF p. 86]]) |

En los **InteliLite NT** todas las protecciones eléctricas del generador son **shutdown** ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=64|AMF p. 64]]). En el **InteliCompact NT** son **BOC** (Overload BOC, Gen <V BOC…) salvo sobrevoltaje (Gen >V **Sd**) ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=173|IC p. 173]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=176|IC p. 176]]).

## Cómo se evalúa una alarma [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=105|IC p. 105]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=106|IC p. 106]]]
- **Cuándo se evalúa:** siempre / solo con motor en marcha (tras **ProtectHoldOff**, p. ej. presión de aceite) / solo con generador excitado (tras Max Stab Time o GCB cerrado: V, f y desbalance).
- **Retardo:** ajustable en alarmas integradas y analógicas; **fijo 500 ms** en entradas binarias. Si la condición desaparece antes, no se activa.
- **Estados:** **activa** · **inactiva** (desapareció pero no se reconoció) · **confirmada** (se reconoció pero sigue). Se reconoce con **Fault reset**.
- ⚠️ Con alarma roja activa o sin reconocer **no arranca**. Al reconocer, en AUT/TEST **puede arrancar solo** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=107|IC p. 107]]).
- **Sd Override** desactiva las paradas por alarma roja (uso: bombas contra incendio) ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=106|IC p. 106]]).
- Lista de alarmas: hasta **16**, se ven 7; activas en video inverso, sin reconocer con **\*** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=108|IC p. 108]]).
- Envío por **SMS/e-mail** con Yel Alarm Msg / Red Alarm Msg ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=107|IC p. 107]]).

## Alarmas integradas del InteliCompact NT [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=109|IC p. 109]]]
| ANSI | Protección |
|---|---|
| — | Parada de emergencia |
| 12 | Sobrevelocidad |
| 14 | Baja velocidad |
| — | Falla de arranque / falla de parada |
| — | Falla de medición de RPM |
| — | GCB Fail / MCB Fail |
| — | Timeout de sincronización directa / inversa |
| 32 | Sobrecarga |
| 32R | Potencia inversa |
| 59, 27 | Sobre / bajo voltaje |
| 47 | Desbalance de voltaje · secuencia de fases |
| 81H, 81L | Sobre / baja frecuencia |
| 51 | Sobrecorriente |
| 50 | Cortocircuito |
| 46 | Desbalance de corriente |
| — | Timer de mantenimiento · alternador de carga · batería · batería de respaldo baja |
| — | Gobernador / AVR al límite |

## Protecciones del generador · rangos [D]
| Protección | IC-NT ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=173\|IC p. 173]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=177\|IC p. 177]]) | IL-NT AMF ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=64\|AMF p. 64]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=67\|AMF p. 67]]) |
|---|---|---|
| Sobrecarga | Overload BOC 100–200 % | Overload 0–200 % |
| Cortocircuito | Short Crct BOC 100–500 %, 0–10 s | Short Crct Sd 100–500 %, 0–10 s |
| Sobrecorriente IDMT | Amps IDMT Del 1–600 s | Amps IDMT Del 0,1–60 s |
| Desbalance de corriente | Amps Unbal BOC 1–200 % | Amps Unbal Sd 1–200 % |
| Falla a tierra | EarthFault Sd 1–10 000 A | — |
| Sobre / bajo voltaje | Gen >V Sd / Gen <V BOC | Gen >V Sd / Gen <V Sd |
| Sobre / baja frecuencia | Gen >Freq / <Freq BOC | Gen >Freq / <Freq Sd |
| Potencia inversa | Reverse Pwr BOC 1–50 % | — |

### Curva IDMT (sobrecorriente «muy inversa») [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=65|AMF p. 65]]]
**Tiempo de reacción = Amps IDMT Del × I nominal / (I gen − I nominal)**
- Amps IDMT Del es el tiempo para **200 %** de corriente.
- Ejemplo con Amps IDMT Del = 2 s: a 200 % → 2 s; a 110 % → 20 s; a 101 % → 200 s; ≤ 100 % → no actúa.
- Si el tiempo calculado supera **900 s (15 min)**, la protección no actúa.

## Falla de interruptor (GCB/MCB Fail) [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=88|AMF p. 88]]]
Compara la **orden** (salida) con la **retroalimentación** (entrada):
- Si la retroalimentación cambia sin orden → falla **inmediata**.
- Si se da orden de abrir o cerrar y no llega la retroalimentación → falla tras **5 s** (2 s en algunos casos al cerrar).
- MCB Fail persistente: revisar **MCB Logic** (CLOSE-ON / CLOSE-OFF) ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=143|IC p. 143]], [[IL-NT-AMF-1.5-Reference Guide.pdf#page=69|AMF p. 69]]).

## Detección de falla de red (AMF) [D]
- Por voltaje, frecuencia y desbalance (Mains >V, <V, >Freq, <Freq, V Unbal con sus retardos) ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=68|AMF p. 68]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=69|AMF p. 69]]).
- IC-NT además por **vector shift**: VectorShiftLim 1–45 °, **sin retardo** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=184|IC p. 184]]).
- Secuencia: falla → espera **EmergStart Del** → arranca → abre MCB → cierra GCB. Vuelve la red → **MainsReturnDel** → abre GCB → **Transfer Del** → cierra MCB ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=67|AMF p. 67]]).

## Lista de eventos (InteliLite NT) [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=89|AMF p. 89]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=91|AMF p. 91]]]
| Evento | Tipo | Significado |
|---|---|---|
| AI1 Wrn / Sd | WRN / SD | Entrada analógica 1 (presión de aceite) **bajo** el umbral |
| AI2 Wrn / Sd | WRN / SD | Entrada analógica 2 (temperatura) **sobre** el umbral |
| Wrn Batt Volt | WRN | Batería fuera de Batt Undervolt / Overvolt |
| Sd BatteryFlat | SD | Se apagó al arrancar por batería baja |
| Sd Start Fail | SD | Falló el arranque |
| Sd Gen Lx >,<V · V Unbal · >Freq | SD | Voltaje, desbalance o frecuencia fuera de límites |
| Sd Overload · Overspeed · Underspeed | SD | Sobrecarga / sobre-velocidad / baja velocidad (se evalúa 5 s tras Starting RPM) |
| EmergencyStop | SD | Entrada de emergencia abierta |
| GCB Fail / MCB Fail | SD / MF | Falla de interruptor |
| Sd RPMMeasFail | SD | Falla del pick-up magnético |
| Sd Stop Fail | SD | No paró |
| WrnMaintenance | WRN | Se cumplieron las horas del contador de mantenimiento |
| ChargeAlt Fail | WRN | Falla del alternador de carga |
| Wrn ECU Alarm | WRN | La lista de alarmas de la ECU no está vacía |
| Low BackupBatt | WRN | Batería del reloj (RTC) baja |
| ParamFail | — | Checksum de parámetros erróneo; queda en INIT |

## Relación con tu RCM [I]
Cada alarma es un **síntoma detectable**: úsala como **D (detección)** en el NPR del AMEF y como tarea de condición (p. ej. **WrnMaintenance** = tarea programada por horas).

Relacionado: [[Diagnóstico]] · [[Sincronismo]] · [[Control de potencia]]
