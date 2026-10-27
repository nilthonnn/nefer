---
tags: [comap, tema, diagnostico]
---

# Diagnóstico
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> **Fuentes:** DS = Datasheet IC-NT 2013 · IC = InteliCompact NT 1.4 Reference Guide · AMF / MRS = InteliLite NT 1.5 Reference Guides
> ⚠️ Manuales de 2009–2013. El grupo de tu tesis usa **InteliGen 200** (generación nueva): los conceptos se mantienen, pero nombres y rangos de setpoints pueden cambiar.

## 1. Leer el estado del grupo [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=89|AMF p. 89]]]
| Estado motor | Significa |
|---|---|
| Init | Autotest al encender |
| Not ready | No está listo para arrancar (p. ej. alarma roja) |
| Prestart / Cranking / Pause | Pre-arranque / arrancando / pausa entre intentos |
| Starting / Running / Loaded | Alcanzó velocidad de arranque / nominal / con GCB cerrado |
| Cooling / Stop / Shutdown | Enfriando / parada / parada por alarma |
| Ready | Listo para arrancar |

| Estado eléctrico (AMF) | Significa |
|---|---|
| MainsOper / MainsFlt / IslOper / MainsRet | Red presente / falla de red / isla / retorno de red |
| MinStabTO / MaxStabTO | Timeout de estabilización mínima / máxima |
| Trans Del | Retardo entre abrir GCB y cerrar MCB |

## 2. Lista de alarmas y lista de la ECU [D]
- **Alarmlist:** ver [[Alarmas y protecciones]] ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=108|IC p. 108]]).
- **ECU Alarmlist:** códigos del motor; cada falla es un par **SPN / FMI** + **OC** (contador de ocurrencias) ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]).
  - **FMI 0 o 1 → WRN**; cualquier otro FMI → **FLS** ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]).
  - Los códigos frecuentes salen en texto; los demás en número: búscalos en la norma **SAE J1939** o en la lista del fabricante del motor ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]).
  - Scania: códigos en hexadecimal ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]).
- Identificar la ECU configurada: en la pantalla principal pulsa **PAGE + ENTER** y busca «ESF:xx.y - (zzz)»; zzz = Motor ID (p. ej. 1 = Volvo EMS/EMS2, 255 = J1939 estándar) ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=67|MRS p. 67]]).
- Valores leídos de la ECU: velocidad, presión de aceite, temperatura de refrigerante, horas, consumo, presión de sobrealimentación… ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=67|MRS p. 67]]–[[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]). **No se guardan en el historial, salvo los códigos de falla** ([[IL-NT-MRS-1.5-Reference Guide.pdf#page=68|MRS p. 68]]).

## 3. Historial (history log) [D]
- Guarda una **foto** del sistema en cada evento importante, tipo FIFO ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=109|IC p. 109]]).
- Capacidad: IC-NT **más de 100** registros ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=109|IC p. 109]]); IL-NT AMF **117** ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=91|AMF p. 91]]) — varía con los módulos configurados. *(La ficha comercial dice 200: [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=2|DS p. 2]].)*
- Cada registro: número, causa, fecha, hora, modo, RPM, kW, fp, frecuencia, V e I por fase, red (o barra), batería, presión de aceite, temperatura, combustible, entradas/salidas binarias, salida al gobernador (**SRO**) y al AVR (**VRO**), y **FC/FMI** de la ECU ([[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=110|IC p. 110]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=111|IC p. 111]], [[IL-NT-AMF-1.5-Reference Guide.pdf#page=91|AMF p. 91]]).
- ⚠️ El primer registro tras encender o reprogramar tiene valores de diagnóstico **sin sentido**: ignóralo ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=91|AMF p. 91]]).
- **Descargar:** LiteEdit → ventana **History** → **History | Read history** ([[IL-NT-AMF-1.5-Reference Guide.pdf#page=91|AMF p. 91]]). En el panel: [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=80|IC p. 80]].

## 4. Rutina de diagnóstico en campo [I]
1. Anotar **estado** del grupo y **modo** (OFF/MAN/AUT/TEST).
2. Leer **Alarmlist** y **ECU Alarmlist** (no reconocer todavía).
3. Descargar el **historial** y ver los registros **antes** de la falla: ¿cayó V o f? ¿subió temperatura? ¿SRO/VRO al límite?
4. Si hay SPN/FMI, buscar en el manual del motor (tu tesis: Volvo Penta TAD1642GE, EMS2 → herramienta VODIA).
5. Reconocer con **Fault reset** solo después de registrar todo.

## 5. Solución de problemas del controlador [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=141|IC p. 141]]–[[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=143|IC p. 143]]]
| Síntoma | Causa / solución |
|---|---|
| Pantalla apagada | Sin alimentación o boot-jumper puesto |
| Solo luz de fondo | Contraste: PAGE ×5, luego ENTER + UP; o firmware inválido |
| «Configuration table error» | Reprogramar la configuración |
| Queda en **INIT** | Checksum de setpoints: cambiar un setpoint con LiteEdit → Controller → *Reset from init state*; o batería RTC agotada |
| No responde a los botones de modo | Entrada de modo remoto o **Access Lock** activa; setpoint con contraseña |
| No arranca / no cierra GCB | No está en MAN, hay alarma roja, o V/f fuera de límites |
| kW y fp erróneos con V e I correctos | Fases de voltaje y CT cruzadas |
| Gobernador pegado al límite | Speed Gov Char invertido, cableado, jumper PWM |
| Corta el arranque muy pronto | **Starting Oil P** muy bajo; autodetección del terminal W |
| MCB Fail permanente | **MCB Logic** mal ajustado |
| Sin CAN con otros equipos | El bus no es lineal (tiene ramales) |
| Olvidó la contraseña | Anotar n.º de serie y *password decode* y pedir al distribuidor |

## 6. Mantenimiento del controlador [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=107|AMF p. 107]]–[[IL-NT-AMF-1.5-Reference Guide.pdf#page=108|AMF p. 108]]]
Batería de respaldo **CR1225** cada **5–7 años** o cuando salga **Low BackupBatt**; después, ajustar fecha/hora y revisar setpoints.

Relacionado: [[Alarmas y protecciones]] · [[Comunicación y software]]
