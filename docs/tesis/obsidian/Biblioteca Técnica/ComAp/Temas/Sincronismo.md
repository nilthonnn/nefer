---
tags: [comap, tema, sincronismo]
---

# Sincronismo
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> **Fuentes:** DS = Datasheet IC-NT 2013 · IC = InteliCompact NT 1.4 Reference Guide · AMF / MRS = InteliLite NT 1.5 Reference Guides
> ⚠️ Manuales de 2009–2013. El grupo de tu tesis usa **InteliGen 200** (generación nueva): los conceptos se mantienen, pero nombres y rangos de setpoints pueden cambiar.

Solo lo hacen los **InteliCompact NT** (SPtM y MINT). Los InteliLite NT AMF/MRS **no sincronizan** [I].

## 1. Antes de sincronizar: estabilización [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=93|IC p. 93]]]
- **Min Stab Time:** mientras corre, el GCB **no puede cerrarse** aunque V y f estén bien.
- **Max Stab Time:** si al terminar V o f siguen fuera de límites, salta la protección y el grupo se enfría y para.
- Regla: Min Stab Time **<** Max Stab Time ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=93|IC p. 93]]). Setpoints en [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=166|IC p. 166]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=167|IC p. 167]].

## 2. ¿Cierra directo o sincroniza? [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=94|IC p. 94]]]
| Caso | Qué hace |
|---|---|
| **Barra muerta** (SPtM: MCB abierto) | Cierra el GCB **sin sincronizar** |
| **Barra muerta** (MINT) | Además exige voltaje de barra **< 2 % del nominal** |
| Varios grupos arrancan a la vez con barra muerta | Solo **uno** cierra; los demás esperan y **se sincronizan** a él |
| **Barra con tensión** | Sincroniza primero y luego cierra el GCB |

## 3. Cómo sincroniza [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=94|IC p. 94]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95|IC p. 95]]]
1. **Igualar voltaje** (AVR): dentro de **Voltage Window**. Lazo: Voltage Gain / Voltage Int.
2. **Igualar frecuencia** (gobernador): lazo Freq Gain / Freq Int, busca deslizamiento ≈ 0.
3. **Igualar ángulo**: lazo Angle Gain (tipo **P**, los demás son PI [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=115|IC p. 115]]).
4. Cuando el ángulo está dentro de **± Phase Window** durante **Dwell Time** y el voltaje también coincide → **cierra el GCB**.
5. Si no lo logra en **Sync Timeout** → alarma **Sync Timeout**.

Durante la sincronización la pantalla cambia sola al **sincronoscopio** ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=94|IC p. 94]]).

## 4. Setpoints del grupo Sync/Load Ctrl [D]
| Setpoint | Rango | Qué es | Pág. |
|---|---|---|---|
| **Voltage Window** | 0 – 100,0 % | ΔV máxima por fase entre generador y red/barra | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=188\|IC p. 188]] |
| **Phase Window** | 0 – 90 ° | Δφ máxima. **En 0 no da orden de cierre** (modo prueba) | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=188\|IC p. 188]] |
| **Dwell Time** | 0 – 25,0 s | Tiempo que Δφ y ΔV deben quedar dentro de la ventana | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=189\|IC p. 189]] |
| **Freq Gain / Freq Int** | 0–200 % / 0–100 % | Lazo de frecuencia | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=189\|IC p. 189]] |
| **Angle Gain** | 0 – 200,0 % | Lazo de ángulo | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=189\|IC p. 189]] |
| **Sync Timeout** | 1 – 1 800 s | Tiempo máximo para sincronizar | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=191\|IC p. 191]] |

> **Los valores por defecto no están en estas tablas** del manual (solo rangos): léelos del controlador con LiteEdit [F].

## 5. Retorno de red sin corte (sincronización inversa) [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=98|IC p. 98]]]
- En SPtM, si la red vuelve y queda sana durante **MainsReturnDel**, el grupo hace **reverse synchronizing**: igual que la directa pero **cierra el MCB**.
- Si falla → alarma **RevSyncTimeout** y sigue en isla.
- Si la entrada **RevSyncDisable** está activa → **changeover** (con corte): abre GCB, espera **Transfer Del**, cierra MCB.

## 6. Fallas típicas de sincronismo [I + D]
| Síntoma | Revisar |
|---|---|
| Sync Timeout repetido | Ganancias del lazo, Speed Gov Char invertido ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=143\|IC p. 143]]), límites del gobernador |
| Salida del gobernador pegada al límite | Speed Gov Char, cableado, jumper PWM/voltaje ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=143\|IC p. 143]]) |
| kW y fp erróneos pero V e I bien | Fases de voltaje y CT no coinciden ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=142\|IC p. 142]]) |
| Bus Measure Error (MINT) | Cables de barra desconectados del controlador ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=94\|IC p. 94]]) |

## 7. Para ajustar (ver [[Control de potencia]] §PI)
Para ajustar los lazos de sincronismo sin cerrar el interruptor, pon **Phase Window = 0** y al final devuélvelo a su valor ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=117|IC p. 117]]).

## Relación con la tesis [I]
Tu checklist de sincronismo (ΔV, Δf, Δφ) corresponde a **Voltage Window**, el lazo de frecuencia y **Phase Window + Dwell Time**.

Relacionado: [[Control de potencia]] · [[Alarmas y protecciones]] · [[InteliCompact NT 1.4 Reference Guide]]
