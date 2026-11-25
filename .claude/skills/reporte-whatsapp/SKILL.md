---
name: reporte-whatsapp
description: Generar el reporte del grupo de WhatsApp de equipos a partir de una orden de trabajo ya llenada en la app de actas de campo, y exportarlo a PDF o Excel.
---

# Reporte para WhatsApp

Código: `MANT.reporte` (`datos`, `texto`, `pdf`, `xlsx`). Pruebas:
`clientes/campo/tests/test_reporte.py`.

Formato fijo, negritas con *asteriscos*:

TAG · UBICACIÓN · HORÓMETRO · GRUPO (modelo + serie) · MOTOR · VOLTAJE · O.T. ·
ACTIVIDAD (viñetas) · OBSERVACIONES · ESTADO DE EQUIPO · Reportado por.

- Título según la clasificación: inspección, preventivo con su PM, correctivo
  o visita técnica.
- Estado según la aptitud declarada: «Operativo», «Operativo con
  observaciones» (si hay aviso o defecto), «Inoperativo» o «Por confirmar».
- Aviso creado, defecto RECO y falla del correctivo van en OBSERVACIONES.
- Placa sin confirmar u horómetro sin leer: «[ leer en equipo ]».
- No incluir datos internos del cliente.
- En la orden: Copiar, Compartir (menú del teléfono → WhatsApp), PDF y Excel;
  los tres con el mismo contenido.
