---
tags: [comap, familia]
fabricante: ComAp
---

# InteliCompact NT
**Controlador sencillo para paralelismo** de grupos electrógenos, en standby o en paralelo [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]].

> **Leyenda:** [D] dato del manual · [I] explicación general (no está en el manual) · [F] pendiente

## Qué hace [D]
- Incorpora **sincronizador** y **compartidor digital isócrono de carga** ([[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]).
- Coopera hasta con **32 grupos**; mantiene encendido solo el **número óptimo** de grupos según la carga y **rota** grupos por horas de uso ([[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]).
- Protecciones del generador incluyendo **falla a tierra, pérdida de excitación y vector shift** ([[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]).
- Comunicación con motores electrónicos (EFI) por **CAN J1939** o **Modbus** ([[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]).
- Historial de eventos con reloj de tiempo real, útil para diagnóstico ([[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1|pág. 1]]).

## Modelos [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=2|pág. 2]], [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=6|pág. 6]]]
| Modelo | Código | Uso |
|---|---|---|
| **SPtM** | IC-NT SPTM | **Un** grupo en paralelo **con la red** |
| **MINT** | IC-NT MINT | **Varios** grupos en paralelo, con reparto de carga integrado (isla o con MainsCompact NT) |
| IG-NTC BaseBox | IG-NTC-BB | Versión mayor: PLC, 1 000 registros de historial, pantalla externa |

## Datos técnicos clave [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=2|pág. 2]]]
| Parámetro | Valor |
|---|---|
| Alimentación | 8–36 V DC; huecos < 50 ms no afectan |
| Temperatura | −20 a +70 °C (versión baja temp.: −40 °C) |
| Frontal | IP65 · 120 × 180 mm · LCD 128 × 64 |
| Voltaje generador y red/barra | 277 V F-N / 480 V F-F (máx. medido 300 V F-N); PT 0,1–500 (hasta 20 000 V) |
| Corriente | True RMS, 5 A (máx. 10 A); CT 1–10 000 |
| E/S | 9–25 entradas binarias, 8–24 salidas binarias, 3–7 analógicas, hasta 9 salidas analógicas |
| Salidas de control | Al **gobernador** de velocidad y al **AVR** (vía IG-AVRi) |
| Otros | Pick-up magnético, pre-excitación D+ |
| Historial | 200 registros con fecha, hora y valores |

## Aplicaciones típicas [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=4|pág. 4]]–[[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=5|pág. 5]]]
- Emergencia con **retorno suave** (sincroniza al volver la red y transfiere sin corte).
- Múltiples grupos **en paralelo a la red** (con MainsCompact NT).
- Múltiples grupos **en isla** con gestión de potencia.
- **Equipo de renta** en standby con retransferencia suave ← relevante para empresas de alquiler como Rivera Diesel [I].

## Dónde se usa (referencias del fabricante) [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=7|pág. 7]]]
- **Perú — Hidrandina**, subestación Shingal (Caraz, 2 300 m s. n. m.): 5 grupos en paralelo con la red + 1 en standby.
- Ecuador — Petroamazonas: transiciones cerradas cada 7 días entre grupos de ~300 kW.

Ver: [[Control de potencia]] · [[Sincronismo]] · [[Alarmas y protecciones]] · [[Diagnóstico]]
