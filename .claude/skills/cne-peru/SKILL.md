---
name: cne-peru
description: >
  Memorias de cálculo, cuadros de cargas, caída de tensión, dimensionamiento de
  conductores y protecciones, grupos electrógenos y transferencias (TTA) e informes
  técnicos eléctricos para Perú, con trazabilidad al Código Nacional de Electricidad
  (CNE Utilización y CNE Suministro) y, en minería, al DS 024-2016-EM. Úsala cuando el
  trabajo eléctrico sea en Perú o el usuario mencione CNE, MINEM, OSINERGMIN, DS 024,
  memoria de cálculo, cuadro de cargas, expediente técnico o informe técnico eléctrico.
  Cada valor normativo debe salir del texto de la norma guardado en normas/, con
  artículo citado; lo que no esté ahí se marca como supuesto (S).
---

# CNE Perú: cálculos y documentos eléctricos con trazabilidad normativa

Produce documentos técnicos eléctricos para Perú en los que **cada criterio, límite o
factor tiene su referencia** a la norma peruana, y nada se completa «de memoria».

## Marco normativo

| Norma | Ámbito | Archivo en `normas/` |
|---|---|---|
| **CNE – Utilización** | Instalaciones interiores, cargas, conductores, protecciones, puesta a tierra | `cne-utilizacion.md` |
| **CNE – Suministro** | Redes de distribución y transmisión, distancias de seguridad, subestaciones | `cne-suministro.md` |
| **DS 024‑2016‑EM** (Reglamento de SSO en minería) y sus modificatorias | Seguridad eléctrica en operaciones mineras | `ds-024-2016-em.md` |
| Normas de la empresa o del proyecto | Criterios propios del cliente | `criterios-proyecto.md` |

Las versiones vigentes las publica el MINEM. **Antes de usar una norma, comprueba que el
archivo en `normas/` exista y diga su versión y fecha** (ver `normas/LEEME.md`).

## Protocolo (obligatorio)

1. **Sin texto, no hay cita.** Si el archivo de la norma no está en `normas/`, dilo y pide
   el texto vigente. No escribas valores del CNE desde la memoria del modelo: los números
   de tablas, factores y límites cambian entre ediciones.
2. **Consulta por índice.** Abre primero `normas/indice.md`, localiza la sección o tabla
   y lee solo ese rango de líneas. No cargues la norma entera.
3. **Cita cada valor** en el formato `[CNE‑U §050‑106]` o `[DS 024‑2016‑EM Art. 384]`
   (sección o artículo, tal como figuren en el texto guardado).
4. **Marca los supuestos.** Todo valor que no sale de la norma (dato de fabricante,
   criterio de diseño, estimación) lleva **(S)** y se lista en «Supuestos y datos de
   entrada» con su origen.
5. **Unidades siempre**, y cálculos con su fórmula y sus datos, para que se puedan
   revisar a mano.
6. **Cierre:** todo entregable termina con «Sujeto a revisión y firma de ingeniero
   colegiado habilitado».

## Entregables y con qué se hacen

| Entregable | Contenido mínimo | Formato |
|---|---|---|
| Memoria de cálculo | Objeto, normas (con versión), datos de entrada, criterios citados, cálculos, resultados, supuestos, conclusiones | Word (skill `docx`) o PDF (skill `pdf`) |
| Cuadro de cargas | Circuito, carga instalada, factor de demanda citado, máxima demanda, corriente, conductor, protección, caída de tensión | Excel (skill `xlsx`) con fórmulas vivas |
| Caída de tensión | Fórmula usada, longitudes, sección, % por tramo y acumulado frente al límite citado | Excel o tabla en la memoria |
| Grupo electrógeno y TTA | Carga a respaldar, arranque de motores, derrateo por altura y temperatura según la hoja del fabricante (ISO 8528‑1), carga entre 30 % y 80 % de la potencia derrateada, lógica de transferencia | Memoria + lógica en LAD (ver LadderLab) |
| Informe técnico | Antecedentes, inspección, hallazgos con evidencia, normas incumplidas citadas, recomendaciones | Word |

Para los criterios internacionales y la ingeniería general (IEC, IEEE, NFPA, ISO 8528)
usa la skill `ingeniero-electrico`; para cortocircuito y flujo de carga con números
reales, la skill `pandapower`. La norma peruana manda cuando hay diferencia.

## Plantilla de verificación de cada valor

```
Valor: <dato>  ·  Fuente: [CNE-U §...] | (S) <origen>  ·  Verificado contra: normas/<archivo>.md líneas <a>-<b>
```

## Lo que esta skill no hace

- No reemplaza la revisión ni la firma de un ingeniero colegiado.
- No garantiza que la norma guardada sea la vigente: eso se verifica en la fuente oficial.
- No inventa artículos ni números de tabla cuando el texto no está disponible.

Método de trazabilidad adaptado de la skill `auditor-normativo` de
[LuiccianDev/tunel-casmas-huaraz-pa14](https://github.com/LuiccianDev/tunel-casmas-huaraz-pa14)
(MIT): consulta por rangos de líneas y marcado de supuestos.
