# Datos de ejemplo para RCM y TPM

Una excavadora inventada, **EX-220**, con lo justo para recorrer los casos de
[`docs/CASOS-RCM-TPM-FIXMATE.md`](../../docs/CASOS-RCM-TPM-FIXMATE.md) a mano.

| Archivo | Qué es |
|---|---|
| `historial-ex220.json` | Seis órdenes de trabajo cerradas. La misma causa escrita de tres formas distintas, a propósito |
| `analisis-ex220.json` | Análisis RCM: 1 función, 1 falla funcional, 4 modos de falla, con sus decisiones |
| `pauta-ex220.json` | Pauta de mantenimiento autónomo: 5 puntos, 31 s de presupuesto |
| `ronda-ex220-hallazgo.json` | Una ronda con una anomalía y un punto sin acceso |
| `ronda-ex220-firmada.json` | Una ronda despachada a un segundo por punto |
| `ronda-ex220-sin-enganche.json` | Una anomalía que el catálogo no puede codificar, y queda sin enlazar |
| `ronda-ex220-telefono.json` | Lo que sale del botón «Guardar» de la ronda: ejecución, anomalías y estado |

**Es un taller inventado.** Los códigos de equipo, las fechas y los nombres no
corresponden a ninguna máquina ni a ninguna persona real. Los códigos de
catálogo sí son los de verdad: salen de `nefer/fixmate/catalogo.py`.

## Lo que cada archivo está puesto para demostrar

**`analisis-ex220.json`** tiene los cuatro casos que importan, uno por modo:

| Modo | Qué demuestra |
|---|---|
| F1.1.1 · Radiador obstruido | El camino normal → CBM. Enganchado al catálogo, hereda sistema, causa y mecanismo |
| F1.1.2 · Válvula de alivio pegada | **Falla oculta** con consecuencia de seguridad → búsqueda de fallas |
| F1.1.3 · Manguera de freno fisurada | La guarda: ninguna tarea proactiva sirve y hay seguridad → **rediseño obligatorio** |
| F1.1.4 · Rodamiento del ventilador | Sin detección, con edad, no restaurable → descarte programado |

**`historial-ex220.json`** trae «Radiador obstruido por tierra», «radiador
tapado con tierra y polvo» y «RADIADOR OBSTRUIDO POR INCRUSTACION»: tres
escrituras que `fmeca.contrastar()` cuenta como **una**, porque cruza por
código de catálogo y no por texto. También trae un filtro de aire que ningún
modo del análisis cubre, y una causa que el catálogo no puede codificar.

**`ronda-ex220-firmada.json`** existe para ver el aviso de sospecha de firma:
31 s de presupuesto despachados en 5.

**`ronda-ex220-sin-enganche.json`** es la otra mitad del puente TPM → RCM, y
la que más conviene ver: el punto 5 de la pauta no declara qué modo vigila, y
«se escucha un chirrido raro al girar la pluma» el catálogo no lo codifica.
La anomalía queda **sin enlazar, y se ve**. Nunca se elige el modo «más
parecido»: un enlace que falta se nota, uno equivocado se suma con los demás.

**`ronda-ex220-telefono.json`** es el archivo tal como lo manda el teléfono:
las tres partes que la oficina espera —`ejecucion`, `anomalias` y `estado`—
en un solo `.json`. Es el que se abre en la pantalla de análisis RCM para ver
en qué modo de falla cayó lo que el operador encontró. No está escrito a
mano: sale de la app de la ronda, y una prueba lo vuelve a generar y lo
compara, para que no envejezca en silencio si la app cambia un campo.

Compárelo con `ronda-ex220-hallazgo.json`, donde el punto 1 **sí** declara
`modo_falla_id`, y por eso engancha incluso sin pasar el análisis.
