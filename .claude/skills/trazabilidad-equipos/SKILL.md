---
name: trazabilidad-equipos
description: Reglas que no se pueden olvidar al tocar la app de actas de campo o al llenar, revisar o regularizar registros de mantenimiento de grupos electrógenos — un TAG por informe, placa confirmada, lecturas de fotos como propuesta, anular en vez de borrar, sin duplicados, historial por equipo, seguridad previa, sin datos fuera del teléfono y sin nombres de empresa. Úsala antes de cambiar el modelo, las validaciones o cualquier pantalla de Mantenimiento, y al auditar registros.
---

# Trazabilidad de equipos y mantenimiento — lo que no se olvida

Código: `clientes/campo/docs/app/index.html` (`MANT.*`, `CAMPO.proyectos`).
Pruebas que lo vigilan: `clientes/campo/tests/`.

## Identidad del equipo

1. **Un informe = un TAG.** El TAG vive en la cabecera de la orden; las piezas
   no guardan otro. Una descripción de orden o una foto que nombra otro TAG
   es **crítico**.
2. **El equipo se reconoce por lo que lleva escrito**: etiqueta QR
   (`EQUIPO:<TAG>`) o el TAG leído en la foto contra las fichas. No hay
   reconocimiento de caras: es dato biométrico sensible (Ley 29733) y no
   hace falta.
3. **Placa confirmada por el técnico.** Lo de la ficha —tecleado o leído de
   una foto— es propuesta; la orden pide confirmarla con nombre y hora, y
   vuelve a pedirlo si la ficha cambia.

## Lo que se registra

4. **Clasificación**: inspección, preventivo con su PM (sugerido por
   horómetro, rutinas anidadas 250/500/1000/2000 h), correctivo o visita.
5. **Seguridad antes de iniciar** (lo que exige el aviso): bloqueo y
   etiquetado, IPERC según PETS, HIRA, batería desconectada; desbloqueo al
   cerrar; herramientas e instrumentos con calibración. Cada marca, con hora.
6. **Fotos por casilla**, cada componente con su estado OK / Observado /
   Falla y nota; el criterio del especialista a la vista, la decisión del
   técnico. Nada de diagnóstico automático.
7. **Valores leídos de fotos** (horómetro, placas, panel, batería,
   probador): siempre propuesta editable; lo usado queda en `lecturas` con
   foto, fecha y texto leído.
8. **Aptitud operativa** (sí/no) con quién y cuándo; un correctivo no se
   declara apto sin acción ni pruebas.

## Corregir sin perder el rastro

9. **Anular, no borrar**: motivo y nombre; queda en la lista y en el
   historial del equipo. Para rehacer, Duplicar (la copia dice de dónde viene).
10. **Sin duplicados**: misma OT, o mismo equipo y N° de acta → aviso; se
    anula el que sobra.
11. **Historial por equipo** (ficha › Historial): sale de los proyectos
    guardados; no hay otra copia que pueda desincronizarse.

## Reglas de siempre

12. Las validaciones **avisan, no bloquean**; «Lo revisé, sigo» deja constancia.
13. **Nada sale del teléfono**: ni fotos ni datos del cliente a servicios
    externos. El lector de fotos corre en el aparato.
14. **Sin nombres de empresa** en el repositorio (prueba
    `test_ningun_archivo_del_repositorio_lleva_nombres_de_empresa`); la
    identidad se configura en Ajustes, en el teléfono.
15. **Normas**: sólo se cita lo que está en el texto oficial guardado
    (el DS 024-2016-EM está pendiente de cargar en `.claude/skills/cne-peru/normas/`).
