---
tags: [generador]
---

# Excitación sin escobillas
AVR → campo (estator) de la excitatriz → inducido de la excitatriz (CA, en el rotor) → **puente de diodos giratorio** (CA→CC) → campo del rotor principal → voltaje en el estator principal.
- **Varistor:** protege el puente contra sobretensiones transitorias.
- **Diodo abierto:** aparece **rizado DC** en el campo → voltaje inestable. Por eso el plan monitorea el rizado.
- Frecuencia ← velocidad (gobernador del EMS2); voltaje ← AVR.

Relación con la tesis: modos 1A1 (varistor), 2A1 (diodos), 3A1/3A2/4A1 (AVR), 4A3 (puente) en [[AMEF]].
