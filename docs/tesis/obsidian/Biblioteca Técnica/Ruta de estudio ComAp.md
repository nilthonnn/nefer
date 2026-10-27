---
tags: [comap, estudio]
---

# Ruta de estudio ComAp
Orden pensado para tu objetivo: **potencia, sincronismo, alarmas y diagnóstico**.

| # | Estudia | Nota | Lectura en el PDF | Tiempo |
|---|---|---|---|---|
| 1 | Qué controlador hace qué | [[00 ComAp]] | [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1\|DS p. 1]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=12\|IC p. 12]] | 15 min |
| 2 | Alarmas: niveles y tipos | [[Alarmas y protecciones]] | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=105\|IC p. 105]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=109\|IC p. 109]] | 40 min |
| 3 | Lista de eventos e IDMT | [[Alarmas y protecciones]] | [[IL-NT-AMF-1.5-Reference Guide.pdf#page=64\|AMF p. 64]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=67\|AMF p. 67]], [[IL-NT-AMF-1.5-Reference Guide.pdf#page=89\|AMF p. 89]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=91\|AMF p. 91]] | 40 min |
| 4 | Diagnóstico: estados, historial, ECU | [[Diagnóstico]] | [[IL-NT-AMF-1.5-Reference Guide.pdf#page=89\|AMF p. 89]], [[IL-NT-AMF-1.5-Reference Guide.pdf#page=91\|AMF p. 91]], [[IL-NT-MRS-1.5-Reference Guide.pdf#page=67\|MRS p. 67]]–[[IL-NT-MRS-1.5-Reference Guide.pdf#page=68\|MRS p. 68]] | 40 min |
| 5 | Sincronismo | [[Sincronismo]] | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=93\|IC p. 93]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95\|IC p. 95]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=187\|IC p. 187]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=191\|IC p. 191]] | 60 min |
| 6 | Control de potencia y lazos PI | [[Control de potencia]] | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=95\|IC p. 95]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=98\|IC p. 98]], [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=114\|IC p. 114]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=117\|IC p. 117]] | 60 min |
| 7 | Solución de problemas | [[Diagnóstico]] | [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=141\|IC p. 141]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=143\|IC p. 143]] | 20 min |

## Preguntas de repaso
1. ¿Qué diferencia hay entre una alarma **BOC**, **STP** y **SD**?
2. ¿Por qué la presión de aceite se evalúa «solo con motor en marcha» y qué setpoint lo retrasa?
3. ¿Qué tres condiciones deben cumplirse para cerrar el GCB al sincronizar y con qué setpoints?
4. ¿Para qué sirve poner **Phase Window = 0**?
5. Con Amps IDMT Del = 4 s, ¿en cuánto tiempo dispara con 150 % de corriente? *(Respuesta: 4 × 1 / 0,5 = 8 s.)*
6. ¿Qué lazos están activos en paralelo con la red en SPtM? *(Potencia y fp.)*
7. Un SPN/FMI con FMI = 1, ¿sale como WRN o FLS?
8. ¿Qué datos del historial mirarías ante un disparo por sobrecarga?
9. Un MCB Fail que no se quita con reset, ¿qué setpoint revisas?
10. ¿Por qué un InteliLite NT AMF no puede poner el grupo en paralelo con la red?

Relacionado: [[00 Índice]]
