---
tags: [tesis, concepto]
---

# AMEF (análisis de modos y efectos de falla)
Responde las preguntas 1–4 del [[RCM]]: función → falla funcional → modo de falla → efecto. Ver [[Falla funcional vs modo de falla]].

**Ejemplo (motor, función 9):** filtrar agua y partículas (Racor + filtro principal) → el filtro principal deja pasar partículas finas → filtro de especificación incorrecta o vencido → desgaste de inyectores. [[NPR]] = 7 × 6 × 8 = **336**.

| Sistema | Modos | NPR > 180 |
|---|---|---|
| Motor diésel | 67 | 31 (20 en admisión y refrigeración) |
| Generador | 8 | 7 (6 en excitación) |
| Distribución/control | 9 | 4 |
| Combustible externo | 6 | 3 |
| Arranque | 3 | 2 |
| **Total** | **93** | **47** |

Generador: varistor en cortocircuito (280), diodos rotativos (245), AVR corrosión/sulfatación (240/210), falla del AVR (280); D = 5 en los 8 modos. Ver [[Generador Stamford HCI544E1]] y [[Excitación sin escobillas]].
