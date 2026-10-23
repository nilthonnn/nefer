---
tags: [moc, comap]
---

# ComAp · índice
> **Leyenda:** [D] dato del manual (con página) · [I] explicación general · [F] pendiente
> **Fuentes:** DS = Datasheet IC-NT 2013 · IC = InteliCompact NT 1.4 Reference Guide · AMF / MRS = InteliLite NT 1.5 Reference Guides
> ⚠️ Manuales de 2009–2013. El grupo de tu tesis usa **InteliGen 200** (generación nueva): los conceptos se mantienen, pero nombres y rangos de setpoints pueden cambiar.

## ¿Qué controlador hace qué?
| Controlador | Aplicación | ¿Sincroniza? | Manual |
|---|---|---|---|
| **InteliCompact NT SPtM** | 1 grupo **en paralelo con la red** + AMF [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=12\|IC p. 12]]] | ✅ | [[InteliCompact NT 1.4 Reference Guide]] |
| **InteliCompact NT MINT** | Varios grupos en paralelo entre sí, reparto de carga [D, [[InteliCompact-NT-1.4-Reference Guide-r4.pdf#page=12\|IC p. 12]]] | ✅ | [[InteliCompact NT 1.4 Reference Guide]] |
| **InteliLite NT AMF** (AMF20/25) | 1 grupo de **emergencia**: arranca solo si falla la red y transfiere con MCB/GCB [D, [[IL-NT-AMF-1.5-Reference Guide.pdf#page=1\|AMF p. 1]]] | ❌ | [[IL-NT AMF 1.5 Reference Guide]] |
| **InteliLite NT MRS** (MRS10/11/15/16) | 1 grupo con arranque **manual o remoto**, sin medir red [D, [[IL-NT-MRS-1.5-Reference Guide.pdf#page=4\|MRS p. 4]]] | ❌ | [[IL-NT MRS 1.5 Reference Guide]] |
| MainsCompact NT | Controlador de red para grupos MINT [D, [[InteliCompact_NT_Datasheet_2013-06_CPLSICNT.pdf#page=1\|DS p. 1]]] | — | *(no recibido)* |
| InteliGen 200 | Paralelo, generación actual (foto de tu tesis) [I] | ✅ | *(descargar Global Guide)* |

**Regla rápida [I]:** si el trabajo es **sincronismo o control de kW/fp** → InteliCompact NT. Si es **alarmas, arranque y diagnóstico de un grupo solo** → InteliLite NT (AMF si hay red, MRS si no).

## Manuales
| Manual | Págs. | Estado |
|---|---|---|
| [[InteliCompact NT Datasheet 2013]] | 8 | ✅ |
| [[InteliCompact NT 1.4 Reference Guide]] | 274 | ✅ |
| [[IL-NT AMF 1.5 Reference Guide]] | 115 | ✅ |
| [[IL-NT MRS 1.5 Reference Guide]] | 105 | ✅ |

## Temas
[[Control de potencia]] · [[Sincronismo]] · [[Alarmas y protecciones]] · [[Diagnóstico]] · [[Comunicación y software]] · [[Machine learning en RCM]] · [[Glosario ComAp]] · [[Ruta de estudio ComAp]]
