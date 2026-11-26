---
name: orden-trabajo
description: Llenar, revisar o regularizar una orden de trabajo (OT) de mantenimiento de grupos electrógenos en la app de actas de campo — clasificación (inspección, preventivo PM1–PM4, correctivo, visita), operaciones 0010/0020 con HH, desviaciones, aviso, aptitud y cierre técnico. Úsala también para anular registros hechos por error sin perder trazabilidad.
---

# Orden de trabajo (ficha de trabajo para mantenimiento)

Código: `clientes/campo/docs/app/index.html`, bloques `MANT.modelo`,
`MANT.validaciones` y `MANT.ordenes`. Pruebas: `clientes/campo/tests/test_ordenes.py`.

## Pasos

1. **Un TAG por orden.** Debe existir la ficha del equipo (Mant. › Equipos). Si
   no existe, se crea con lo que dice la placa; nunca se inventan datos.
2. **Clasificar** al crear la orden (sección 2 del informe):
   - 2.1 Inspección · 2.2 Preventivo · 2.3 Supervisión/visita técnica · 2.4 Correctivo.
   - Preventivo: rutina por horómetro, anidada — 250 h PM1, 500 h PM2,
     1000 h PM3, 2000 h PM4 (la mayor incluye a las menores). La app la
     sugiere con `MANT.modelo.sugerirPM(horas)`; si se elige otra, avisa.
3. **Confirmar la placa**: la ficha se muestra al lado y el técnico confirma
   con su nombre. Nunca se copia sola.
4. **Seguridad antes de iniciar** (lo que exige el aviso de la orden):
   equipo bloqueado y etiquetado según la matriz de bloqueo, IPERC continuo
   según PETS, HIRA revisado, batería desconectada; maleta mecánica y
   dieléctrica; instrumentos (pirómetro, pinza, multímetro, revelador de
   tensión) con serie y vencimiento de calibración. Cada marca guarda su hora.
   Registrar inicio de trabajo sin bloqueo confirmado es **crítico**; al
   cerrar, registrar el desbloqueo antes de energizar.
5. **Cabecera SAP**: N° orden, descripción, aviso, ubicación técnica,
   puesto de trabajo, fechas. Si la descripción termina en `_TAG` de otro
   equipo, es un error crítico: un informe = un TAG.
6. **Operaciones** 0010 (eléctrico) y 0020 (mecánico): inicio, fin, personas,
   HH (trabajo total) y N° de empleado. HH = duración × personas; si no
   cuadra, se avisa, no se corrige solo.
7. **Desviaciones**: sólo las que ocurrieron, con la causa impresa del
   formato y su duración.
8. **Cierre**: observaciones, defecto RECO («Sin defecto detectado» o el
   concreto), series de entrada/salida, valor de contador, crear aviso S/N
   (con texto si es S), aptitud operativa SÍ/NO con quién la declara, tarea
   completa SÍ (notificación final y cierre técnico) / NO (notificación
   parcial e imprimir otra ficha), firmas.
9. **Correctivo**: falla, causa, acción y pruebas después de reparar. No se
   declara apto sin acción ni pruebas (aviso).
10. Revisar los avisos (`MANT.validaciones.validarMantenimiento`). Avisan, no
   bloquean; «Lo revisé, sigo» deja constancia con fecha y técnico.

## Regularizar registros

- **Registrado por error** (despacho, recepción u orden): se **anula** con
  motivo y nombre (`CAMPO.proyectos.anular(id, motivo, por)`). No se borra:
  queda en la lista con sello ANULADA y su historial.
- **Duplicado**: la lista marca POSIBLE DUPLICADO (mismo equipo y N° de acta,
  o la misma OT). Se anula el que sobra; para rehacer uno anulado, Duplicar.
- **Clasificación equivocada**: se corrige en la orden; la casilla 2.x del
  informe se actualiza sola.
