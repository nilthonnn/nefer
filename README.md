# Dimensionador de Grupo Electrógeno

Aplicación web ligera (HTML + CSS + JavaScript, sin dependencias ni build) para estimar
el tamaño de grupo electrógeno (generador) necesario a partir de un listado de cargas
eléctricas.

## Cómo usarla

No requiere instalación ni servidor. Alcanza con abrir `index.html` en un navegador,
o servir la carpeta con cualquier servidor estático:

```bash
python3 -m http.server 8080
# luego abrir http://localhost:8080
```

## Qué hace

1. **Parámetros del proyecto**: nombre, cliente, preparado por, tensión, fases, frecuencia,
   margen de seguridad, factor de potencia del generador, altitud y temperatura ambiente
   del sitio, **tecnología del motor** (aspirado natural / turboalimentado / turbo +
   intercooler — escala la tasa de derating), **régimen de operación** (Standby / Prime /
   Continuous — Continuous suma holgura porque no admite sobrecarga transitoria), y
   **reactancia X"d del alternador + clase de rendimiento ISO 8528-5** (G1–G4) para el
   criterio de caída de tensión de arranque.
2. **Tabla de cargas**: agregas cada equipo/carga con su potencia (kW o HP), cantidad,
   factor de potencia (cos φ), **categoría** (Motor, Iluminación, Electrónica/VFD o
   Resistiva) y tipo de arranque. Categoría y tipo de arranque son independientes: una
   carga puede ser "Electrónica/VFD" (no lineal, aporta armónicos) sin tener arranque
   brusco. Al elegir el tipo de arranque (directo, estrella-triángulo, arranque suave o
   variador de frecuencia) se autocompleta un factor de arranque típico, editable si
   tienes el dato real del fabricante. Las cargas de categoría "Electrónica/VFD" además
   llevan una **severidad de armónicos** (baja/media/alta).
3. **Resultado**: calcula la carga total en régimen, el pico de arranque estimado, aplica
   el margen de seguridad, el derating por altitud/temperatura (según tecnología del
   motor), una sobredimensión adicional del alternador según la fracción de carga no
   lineal (armónicos), y el factor de régimen de operación. Estima además la **caída de
   tensión de arranque** (%dip) contra la clase ISO 8528-5 elegida, y busca en el
   catálogo de tamaños comerciales el primero que cumpla tanto la demanda continua como
   ese %dip — si el criterio de tensión exige más que el simple redondeo por kVA, el
   tamaño sugerido sube y queda explicado en pantalla.
4. **Librería de cargas**: catálogo de ~45 equipos típicos del mercado (motores trifásicos
   por HP estándar NEMA/IEC, soldadoras inversoras y convencionales, bombas, compresores,
   HVAC, iluminación, hornos, cargadores/UPS, herramientas) con potencia, cos φ, eficiencia
   y tipo de arranque precargados. Se abre con el botón "📚 Librería de cargas", tiene
   buscador y filtro por grupo, y cada "+ Añadir" agrega una fila lista a la tabla.
5. **Normativa de referencia**: tarjeta con las normas eléctricas, de calidad de energía
   y de vialidad/accesos aplicables (Perú e internacional) — ver sección dedicada más
   abajo. Se incluye también en el informe impreso.
6. **Marcas y fabricantes de referencia**: panorama de mercado (fabricantes de motor,
   empaquetadores de grupo completo, alternadores, controladores AMF/ATS, y distribución
   en Perú) — ver sección dedicada más abajo.
7. **Guardar/exportar**: autosave en el navegador (localStorage), guardar/cargar proyecto,
   exportar/importar JSON, exportar/**importar CSV** de las cargas (parser tolerante a
   variantes de encabezado), y un botón de impresión que genera un **informe técnico**
   con portada (proyecto/cliente/fecha/preparado por), parámetros, cuadro de cargas,
   resultados, composición de la carga, normativa aplicable y bloque de firmas — listo
   para "Guardar como PDF" desde el diálogo de impresión del navegador.

   > El PDF se genera con la función de impresión del propio navegador (`window.print()`
   > + hoja de estilos `@media print`). Esto solo funciona abriendo `index.html`
   > directamente (o sirviéndolo localmente) — **no** funciona dentro del sandbox de un
   > Artifact/preview embebido, que bloquea descargas e impresión por seguridad.

## Metodología de cálculo

- **HP → kW eléctrico**: la potencia en HP es un rating mecánico de *salida* del motor;
  el kW eléctrico consumido (lo que debe suministrar el generador) es mayor por la
  eficiencia de conversión: `kW_eléctrico = HP × 0.746 / η`. Las cargas ingresadas
  directamente en kW (iluminación, electrónica, resistivas) ya representan consumo
  eléctrico y no usan este ajuste.
- **kW → kVA** de cada carga: `kVA = kW_eléctrico / cos φ`.
- **kVA de arranque** de cada carga: `kVA_arranque = kVA_nominal × factor_de_arranque`.
- **Pico de arranque del sistema**: se identifica la carga con el mayor salto
  (`kVA_arranque − kVA_nominal`) y se asume que arranca de última, con el resto de
  cargas ya en régimen permanente (peor caso habitual usado por fabricantes de grupos
  electrógenos):

  ```
  pico = (Σ kVA_nominal de todas las cargas − kVA_nominal de la carga crítica)
         + kVA_arranque de la carga crítica
  ```

- **Margen de seguridad**: se aplica como porcentaje sobre el pico anterior.
- **Derating por sitio**: regla general de referencia (no reemplaza la ficha técnica del
  fabricante): ~1% de reducción de capacidad por cada 100 msnm sobre 1000 msnm, y ~1%
  por cada °C sobre 25 °C, para un motor **turboalimentado** (la línea base). La
  **tecnología del motor** escala esa tasa (`js/calc.js`, constante
  `ENGINE_TECH_PRESETS`): aspirado natural ×1.8 en altitud / ×1.3 en temperatura
  (derating más agresivo), turbo + intercooler ×0.6 / ×0.8 (menos agresivo).
- **Carga no lineal / armónicos**: se suma el kVA de las cargas de categoría
  "Electrónica/VFD", ponderado por su severidad de armónicos (baja ×0.5, media ×1.0,
  alta ×1.5), y se calcula qué fracción representa del kVA total del sistema. Esa
  fracción determina una sobredimensión adicional del alternador por tramos
  (`js/calc.js`, constante `HARMONIC_OVERSIZE_BRACKETS`): sin sobredimensión hasta 10%,
  ×1.10 hasta 30%, ×1.20 hasta 60%, ×1.35 por encima. Es una heurística de referencia
  inspirada en el criterio de IEEE 519 (ver "Normativa de referencia"), no un cálculo de
  THD real — para cargas no lineales dominantes (grandes VFD, rectificadores, UPS) se
  requiere un estudio de armónicos y una especificación de alternador (paso de bobinado,
  reactancia subtransitoria) con el fabricante.
- **Régimen de operación** (`js/calc.js`, constante `REGIME_PRESETS`): Standby (ESP) y
  Prime (PRP) no llevan ajuste adicional (el margen de seguridad ya cubre el uso típico);
  Continuous (COP) suma ×1.10 porque debe operar al 100% sin ninguna capacidad de
  sobrecarga transitoria disponible.
- **kW recomendado**: `kVA_recomendado × factor_de_potencia_del_generador` (por defecto 0.8).
- **Caída de tensión de arranque (%dip)**: aproximación de preselección (ISO 8528-5 /
  guías de fabricante) `%dip = X"d(%) × kVA_arranque_carga_crítica / kVA_generador`.
  Cada clase de rendimiento define el %dip máximo aceptado al aplicar el escalón de
  carga más severo: G1 ≤25%, G2 ≤20%, G3 ≤15%, G4 a medida (tú defines el máximo).
- **Tamaño comercial sugerido**: se recorre la lista de tamaños estándar de referencia
  (`js/calc.js`, constante `STANDARD_SIZES_KVA`) en orden ascendente y se toma el primero
  que cumpla **ambos** criterios — kVA recomendado por carga continua, y %dip dentro del
  límite de la clase elegida. Si ninguno del catálogo cumple el %dip, se marca la
  advertencia correspondiente en pantalla (se requiere una unidad fuera de este catálogo
  o una clase de rendimiento menos exigente).

> ⚠️ Esta herramienta da una estimación orientativa. Para la selección final del grupo
> electrógeno, valida siempre contra la ficha técnica del fabricante (curvas reales de
> arranque de motores, derating específico del modelo, tipo de carga no lineal, THD, etc.).

## Normativa de referencia

La app incluye una tarjeta con el marco normativo aplicable a dimensionamiento e
instalación de grupos electrógenos, orientada a Perú con referencias internacionales:

- **Eléctrica (Perú)**: Código Nacional de Electricidad (CNE), Tomo V – Utilización,
  Sección 240 "Sistemas de Emergencia" (Ministerio de Energía y Minas); y la Norma
  Técnica **EM.010** "Instalaciones Eléctricas Interiores" del Reglamento Nacional de
  Edificaciones (RNE), aprobada por RM N.° 083-2019-VIVIENDA.
- **Instalación / distancias (referencia internacional)**: NFPA 37 y NFPA 110 —
  separación mínima orientativa de 1.5 m (5 ft) desde aberturas, ventanas, rejillas de
  ventilación y materiales combustibles; el aire de escape no debe recircular hacia la
  edificación.
- **Vialidad / accesos (Perú)**: RNE Norma **A.010** "Condiciones Generales de Diseño"
  (accesos vehiculares: ancho máximo ≈12 m, ángulo 30°–45°) y Norma **GH.020**
  "Componentes de Diseño Urbano" (vías de habilitación urbana).
- **Fuera de Perú**: IEC 60364 (instalaciones eléctricas de baja tensión) y NFPA 70/NEC
  (Estados Unidos), artículos 700/701/702 sobre sistemas de emergencia y espera.
- **Calidad de energía / armónicos**: IEEE 519 "Recommended Practice and Requirements for
  Harmonic Control in Electric Power Systems" — referencia detrás de la sobredimensión
  por armónicos que calcula la app.

Para vías internas de una operación minera (fuera del alcance del RNE), rige en su lugar
el **Reglamento de Seguridad y Salud Ocupacional en Minería** (D.S. N.° 024-2016-EM,
modificado por D.S. N.° 034-2023-EM).

Es orientación general recopilada de fuentes públicas — verifica siempre el texto legal
vigente y valida con un ingeniero colegiado y la autoridad competente (municipalidad,
OSINERGMIN, Indeci, o la gerencia de seguridad de la operación minera) antes de una
emisión de ingeniería final, ya que los requisitos exactos dependen del uso, la potencia
y la ubicación específica del proyecto.

## Marcas y fabricantes de referencia

Panorama de mercado (no exhaustivo) incluido como tarjeta de referencia en la app:

- **Motor · premium/misión crítica**: Caterpillar, Cummins, MTU/Rolls-Royce Power Systems, Mitsubishi.
- **Motor · industrial general**: Perkins, Volvo Penta, John Deere, Deutz, Doosan, Iveco/FPT, Yanmar, Kohler-Lombardini, Hatz.
- **Motor · gama económica**: Weichai (incl. Baudouin), Yuchai, SDEC, Ricardo, FAW (China); Kirloskar, Mahindra Powerol (India).
- **Empaquetador (grupo completo)**: FG Wilson, Rehlko (antes Kohler Power Systems, incl. SDMO), Himoinsa, Pramac, Aksa, Generac, Atlas Copco QAS, Olympian.
- **Alternador**: Stamford, Leroy-Somer, Mecc Alte, Marathon, AVK, Sincro, ENGGA.
- **Control AMF/ATS**: DeepSea Electronics, ComAp, Woodward, Basler.
- **Distribución en Perú**: Ferreyros/Unimaq (Caterpillar); Arcring Perú, Rivera Diesel, Grupos Electrógenos Perú (multimarca).

> El fabricante del motor (OEM) casi siempre es distinto del empaquetador que arma el
> grupo completo — la app lo explica en la propia tarjeta.

## Estructura del proyecto

```
index.html          Estructura de la app
css/styles.css       Estilos (incluye estilos de impresión)
js/calc.js           Motor de cálculo puro (sin DOM) — constantes y funciones de cómputo
js/app.js            Estado de la UI, render y eventos del DOM (usa las funciones de calc.js)
tests/calc.test.js   Suite de regresión del motor de cálculo (node --test)
```

`js/calc.js` se carga como `<script>` clásico **antes** de `js/app.js` (comparten el
scope global del navegador, sin módulos ni build), y también se puede `require()` desde
Node gracias al guard de `module.exports` al final del archivo — así la suite de
pruebas corre contra la implementación real, no una reimplementación aparte.

## Pruebas

```bash
node --test
```

Corre `tests/calc.test.js` contra `js/calc.js` (sin dependencias, usa `node:test` /
`node:assert`, requiere Node ≥18). Cubre la conversión HP→kW, el cálculo de arranque, la
sobredimensión por armónicos, el ajuste por régimen de operación, el derating por
tecnología de motor, y la búsqueda de tamaño comercial por %dip (incluido el caso donde
ningún tamaño del catálogo alcanza).

## Versión del esquema de cálculo

Cada proyecto guardado (localStorage o JSON exportado) lleva un campo `schemaVersion`
(`js/calc.js`, constante `CALC_SCHEMA_VERSION`). Si cargas un proyecto guardado con una
versión anterior de la metodología (por ejemplo, de antes del ajuste de eficiencia
HP→kW o de la sobredimensión por armónicos), la app **recalcula con la metodología
actual y te avisa explícitamente** en vez de mostrar el resultado antiguo en silencio.
Incrementa `CALC_SCHEMA_VERSION` cada vez que un cambio en `computeLoadRow` o
`computeSummary` altere el resultado de proyectos ya guardados.

## Personalización

- Editar `STARTING_PRESETS` en `js/calc.js` para cambiar los factores de arranque típicos.
- Editar `STANDARD_SIZES_KVA` para ajustar la lista de tamaños comerciales de referencia
  a los modelos realmente disponibles en tu mercado/proveedor.
- Editar `LOAD_LIBRARY` en `js/calc.js` para agregar/quitar equipos de la librería de
  cargas o ajustar sus valores de placa a los que realmente vendes/instalas.
- Editar `HARMONIC_SEVERITY` y `HARMONIC_OVERSIZE_BRACKETS` en `js/calc.js` para ajustar
  los pesos de severidad y los umbrales/factores de sobredimensión por armónicos.
- Editar `REGIME_PRESETS` y `ENGINE_TECH_PRESETS` en `js/calc.js` para ajustar los
  factores de régimen de operación y las tasas de derating por tecnología de motor a
  los datos reales del fabricante que uses.
- Editar `PERFORMANCE_CLASS_PRESETS` en `js/calc.js` para ajustar los límites de %dip
  por clase ISO 8528-5.
