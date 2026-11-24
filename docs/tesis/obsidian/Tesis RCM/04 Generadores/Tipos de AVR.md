---
tags: [generador]
---

# Tipos de tarjeta AVR
**Por fuente de energía**
| Tipo | Alimentación | Ventaja | Limitación |
|---|---|---|---|
| Shunt (autoexcitado) | Salida del propio estator | Simple, económico | Sensible a caídas y armónicos; poca corriente de cortocircuito |
| PMG | Imanes permanentes en el eje | Excitación constante, inmune a distorsión; no requiere flashear | Más caro |
| AREP (Leroy-Somer) | Devanados auxiliares de voltaje y corriente | Alta corriente de cortocircuito (300 %/10 s, LSA) | De una marca |

**Stamford:** SX460 (autoexcitado, marcado obsoleto) · **AS440** (autoexcitado, droop CT para paralelo; estándar del HCI544E) · MX341 (PMG, protección de sobreexcitación) · MX321 (MX341 + sensado trifásico RMS).
**Digitales** (no verificados en búsqueda): Stamford DM110, Leroy-Somer D350/D550, Basler DECS.
**Funciones:** sensado mono/trifásico · UFRO (baja voltaje si cae la frecuencia) · droop (reparto de kVAr) · protección de sobreexcitación · arranque suave.

> [!tip] Respuesta: «El equipo tiene un SX460 autoexcitado; la ficha actual usa el AS440, su reemplazo funcional». Confírmalo en campo.

Fuentes: [ficha HCI534/544E](https://wincogen.com/wp-content/uploads/PD/Spec_Sheets/GenEnds/HCI_534-544E-311.pdf) · [Caterpillar, Excitation Selections](https://www.cat.com/en_AU/by-industry/electric-power/Articles/White-papers/excitation-selections.html) · [Nidec/Leroy-Somer](https://weh.maritime.edu/EN-3111/references/nidec-excitation-systems.pdf)
