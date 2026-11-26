---
name: informe-grupo-electrogeno
description: Generar o revisar el informe técnico de grupo electrógeno (secciones 1–8 del formato en papel) desde la placa confirmada, lo leído en el panel y lo que hizo el técnico, en la app de actas de campo.
---

# Informe técnico de grupo electrógeno

Textos y estructura: `MANT.modelo.FORMATO.informe`; modelo `MANT.modelo.informe()`.

1. **Encabezado**: cliente, dirección, O/T, fecha. Cuadro EQUIPO: grupo, motor
   y generador con marca, modelo/serie, SPEC y horas (CPL del motor).
   - El alternador tiene placa propia (frame, serie, WDG): no confundirla con
     la del grupo. Series repetidas entre placas → aviso.
2. **1. Generalidades**: voltaje (lo que escribe el técnico, que puede ser lo
   medido), velocidad, módulo de control (marca/modelo), fases, frecuencia,
   derrateo (msnm).
3. **2. Tipo de servicio**: una sola casilla, la de la clasificación de la orden.
4. **3. Motor** 3.1–3.12 y **4. Generador y tablero** 4.1.1–4.2.6: OK / NO / NA.
   «Fugas» = OK si no hay fugas. Otros: texto libre.
5. **5. Repuestos** 5.1–5.14: sólo lo cambiado. Guía de remisión.
6. **6. Parámetros de operación y prueba**: columnas VALOR INICIAL, VACÍO,
   25 %, 50 %, 100 %; filas Voltaje AC, Corriente, kW, kVA, Hz, Volt. batería,
   presión de aceite (PSI), T° refrigerante (°C), RPM. Lo leído en el panel.
7. **7. Observaciones**: hallazgos de seguridad, reloj desfasado, etc.
8. **8. Grupo operativo** SÍ/NO (es la aptitud de la orden) y firmas: dos por
   la empresa, dos por el cliente.

Reglas: un informe = un TAG; lo no leído queda vacío o «[ leer en equipo ]»,
nunca se inventa; las validaciones avisan, no bloquean.

PDF: `MANT.documentos.pdf(m, ["informe"])` (también "ficha", "baterias",
"anexo", o los cuatro en uno). Sigue el papel sección por sección; lo vacío
sale en blanco. Pruebas: `clientes/campo/tests/test_documentos.py`.
