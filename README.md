# Dimensionador de Compresores de Aire

Aplicación web ligera (HTML + CSS + JavaScript, sin dependencias ni build) para estimar
la capacidad de compresor de aire industrial necesaria a partir de un listado de
consumidores de aire comprimido, con corrección por altitud — pensada para el rango de
altitudes de Perú (desde la costa hasta ciudades mineras de gran altitud). Dimensiona
tanto un compresor **eléctrico estacionario** (sala de compresores con red eléctrica)
como uno **diésel portátil/remolcado** (el caso dominante en perforación y obra sin red
eléctrica — minería de altura, exploración, construcción), cada uno con su propia
física de derating y su propio catálogo de referencia por marca.

## Cómo usarla

No requiere instalación ni servidor. Alcanza con abrir `index.html` en un navegador,
o servir la carpeta con cualquier servidor estático:

```bash
python3 -m http.server 8080
# luego abrir http://localhost:8080
```

## Qué hace

1. **Parámetros del proyecto y del sitio**: nombre, cliente, preparado por, **tipo de
   accionamiento** (motor eléctrico estacionario / motor diésel portátil-remolcado —
   ver más abajo), **ubicación de referencia (Perú)** (atajo de UI que rellena la
   altitud típica de ciudades como Lima, Arequipa, Cusco, Puno, Cerro de Pasco o La
   Rinconada — el campo de altitud queda siempre editable con el dato real del sitio),
   altitud, temperatura ambiente, presión de trabajo requerida en el punto de uso, y
   margen de seguridad/crecimiento futuro. **Divulgación progresiva**: la tecnología del
   compresor, la caída de presión de línea, la opción de unidad de respaldo, y — solo si
   el accionamiento elegido es diésel — la tecnología del motor diésel, la eficiencia de
   transmisión mecánica, el margen de motor y el consumo específico de combustible,
   quedan colapsados bajo "Parámetros avanzados" (con valores por defecto razonables)
   sin quitar ningún campo del modelo de cálculo. El informe impreso siempre muestra los
   parámetros avanzados universales, sin importar si el bloque está colapsado en
   pantalla — pero los campos y resultados específicos del motor diésel solo se imprimen
   si el accionamiento elegido es diésel (a diferencia de los demás "avanzados", no son
   universalmente aplicables).
2. **Demanda de aire comprimido**: agregas cada consumidor (herramienta, proceso,
   instrumento) con su caudal (m³/min o CFM, "aire libre"/ANR), cantidad y **factor de
   uso/simultaneidad (%)**. Al elegir la **categoría** (herramienta intermitente, uso
   continuo, proceso/equipo fijo, instrumentación, perforación/minería subterránea,
   limpieza/soplado) se autocompleta un factor de uso típico, editable si tienes el dato
   real de tu planta. Usa el botón "Librería de consumos" para agregar equipos típicos
   del mercado (herramientas de taller, minería subterránea, construcción, pintura,
   instrumentación, proceso industrial) con estos datos precargados.
3. **Resultado**: calcula el consumo nominal y efectivo, la demanda de diseño (con
   margen), la presión atmosférica del sitio (fórmula barométrica ISA/ICAO), la presión
   de descarga requerida, la **relación de compresión real** en el sitio (con aviso si
   excede el límite práctico de una sola etapa de la tecnología elegida), la
   **corrección por densidad de aire** (altitud + temperatura), la capacidad de catálogo
   (FAD) que hay que pedir al fabricante, la potencia eléctrica estimada, y el tamaño
   comercial sugerido (kW) del catálogo de referencia. Además, convierte esa capacidad
   a CFM y la cruza contra un **catálogo de líneas de producto reales por marca**,
   mostrando qué líneas (de las marcas con nomenclatura pública y estable — ver
   "Marcas y fabricantes de referencia") cubren o están cerca de esa capacidad. Si el
   accionamiento elegido es **diésel portátil**, además calcula la potencia nominal del
   motor diésel a especificar (con su propio derating por altitud/temperatura,
   independiente del de la succión del compresor), el consumo de combustible estimado
   (L/h), y la **clase comercial de compresor portátil** (CFM @ presión nominal) que
   cubre la demanda — ver "Metodología de cálculo: accionamiento diésel" más abajo.
4. **Librería de consumos**: catálogo de ~23 consumidores típicos (herramientas
   neumáticas de taller, perforadoras y equipos de minería subterránea — muy relevantes
   en el sector minero peruano —, herramientas de construcción, pintura, instrumentación
   y proceso industrial) con caudal de referencia precargado. Se abre con el botón
   "📚 Librería de consumos", tiene buscador y filtro por grupo, y cada "+ Añadir" agrega
   una fila lista a la tabla.
5. **Normativa de referencia**: tarjeta con las normas eléctricas, de seguridad laboral,
   de minería y técnicas (calidad de aire, ensayo de aceptación, recipientes a presión)
   aplicables — ver sección dedicada más abajo. Se incluye también en el informe
   impreso.
6. **Marcas y fabricantes de referencia**: panorama de mercado (fabricantes premium,
   industriales generales, de gama económica, y distribución en Perú) — ver sección
   dedicada más abajo.
7. **Guardar/exportar**: autosave en el navegador (localStorage), guardar/cargar
   proyecto, exportar/importar JSON, exportar/**importar CSV** de la demanda (parser
   tolerante a variantes de encabezado), y un botón de impresión que genera un
   **informe técnico** con portada (proyecto/cliente/fecha/preparado por), parámetros,
   cuadro de demanda, resultados, composición de la demanda, normativa aplicable y
   bloque de firmas — listo para "Guardar como PDF" desde el diálogo de impresión del
   navegador.

   > El PDF se genera con la función de impresión del propio navegador (`window.print()`
   > + hoja de estilos `@media print`). Esto solo funciona abriendo `index.html`
   > directamente (o sirviéndolo localmente) — **no** funciona dentro del sandbox de un
   > Artifact/preview embebido, que bloquea descargas e impresión por seguridad.

## Metodología de cálculo

- **Consumo nominal y efectivo**: `nominal = caudal_unitario × cantidad`;
  `efectivo = nominal × factor_de_uso`. El factor de uso (0-100%) representa qué
  fracción del tiempo el consumidor realmente demanda aire — evita sobredimensionar
  asumiendo que todo opera continua y simultáneamente.
- **Demanda de diseño**: `demanda_efectiva_total × (1 + margen_de_seguridad)`.
- **Presión atmosférica del sitio**: fórmula barométrica de la Atmósfera Estándar
  Internacional (ISA/ICAO), válida en la tropósfera (0-11,000 msnm, rango que cubre
  todo el territorio peruano habitado):

  ```
  P(h) = 101.325 kPa × (1 − 2.25577×10⁻⁵ × h)^5.2559
  ```

  A modo de referencia: a nivel del mar ≈101.3 kPa; en Cerro de Pasco (~4,338 msnm)
  ≈59 kPa; en La Rinconada (~5,100 msnm) ≈53 kPa.
- **Corrección por densidad de aire** (`js/calc.js`, función `airDensityCorrectionFactor`):
  por gas ideal, la densidad del aire es proporcional a P/T. Se compara la presión y
  temperatura del sitio contra las **condiciones de referencia ISO 1217** (100 kPa,
  20°C, 0% HR — las que usan los fabricantes para certificar el caudal FAD de catálogo
  de un compresor de desplazamiento, normalmente en un banco de pruebas a nivel del
  mar). El factor resultante es menor que 1 en altura y/o con temperatura alta. No se
  modela humedad relativa (efecto secundario, ~1-2%).
- **Capacidad de catálogo requerida (FAD)**: `demanda_de_diseño / factor_de_corrección`.
  Como el compresor tiene un volumen barrido geométricamente fijo, en altura ingiere
  aire menos denso y entrega menos caudal "normal" del que indica su placa (certificada
  a nivel del mar) — hay que pedir una capacidad de catálogo mayor para que, instalado
  en el sitio, entregue la demanda real.
- **Presión de descarga y relación de compresión**: `presión_descarga_manométrica =
  presión_de_trabajo + caída_de_presión_de_línea`; la presión absoluta de descarga se
  obtiene sumando la presión atmosférica del sitio (una presión manométrica siempre se
  mide respecto a la atmósfera local). La **relación de compresión** =
  `presión_absoluta_descarga / presión_absoluta_succión`. A la misma presión
  manométrica de trabajo, un sitio en altura tiene una relación de compresión **mayor**
  que uno a nivel del mar (la presión de succión absoluta es menor) — por eso en
  ciudades mineras de gran altitud es más probable necesitar compresión en 2 etapas. Se
  compara contra el límite práctico de una sola etapa de la tecnología elegida
  (`js/calc.js`, constante `COMPRESSOR_TECH_PRESETS`, campo `maxSingleStageRatio`) y se
  advierte en pantalla si lo excede.
- **Potencia de compresión**: se modela como compresión **adiabática ideal de una etapa
  equivalente** (`js/calc.js`, función `computeIdealAdiabaticPowerKW`):

  ```
  W_ideal (kW) = P1 × Q1 × (k/(k−1)) × [(P2/P1)^((k−1)/k) − 1]
  ```

  con `P1`/`P2` en kPa absolutos (succión/descarga del sitio), `Q1` en m³/s (la
  capacidad de catálogo requerida, que es también el caudal real que ingiere el
  compresor en condiciones de sitio) y `k = 1.4` (aire seco). La potencia eléctrica
  estimada se obtiene dividiendo entre la **eficiencia global** ("de cable a aire") de
  la tecnología elegida (`COMPRESSOR_TECH_PRESETS`, campo `overallEfficiency`, calibrada
  contra la regla de mercado de ~6.5 kW por m³/min a 7 bar(g) para tornillo lubricado,
  equivalente a "~4 CFM por HP a 100 psig"). Es, a propósito, una estimación
  **conservadora**: una compresión real en 2 etapas con interenfriamiento consume algo
  menos que este modelo de 1 etapa equivalente.
- **Tamaño comercial sugerido**: se recorre la lista de tamaños comerciales de
  referencia (`js/calc.js`, constante `STANDARD_SIZES_KW`, pasos de motor IEC/NEMA
  típicos de catálogos de compresores de tornillo/pistón) en orden ascendente y se toma
  el primero que cubre la potencia eléctrica estimada.
- **Compresores de referencia por marca (filtrado por CFM)**: la capacidad de catálogo
  requerida se convierte a CFM y se compara contra `js/calc.js`, constante
  `BRAND_CATALOG` — líneas/series de producto reales de fabricantes con nomenclatura
  pública y estable (p.ej. Atlas Copco GA/GA VSD+/ZR-ZT, Kaeser SM-SK/CSD-DSD/ASD-BSD,
  Ingersoll Rand R-Series, Sullair LS-Series, CompAir L-Series, Hitachi Bebicon, Boge
  S-Series), cada una con su rango de CFM típico publicado. La función
  `findMatchingBrandModels` (`js/calc.js`) marca `exactFit: true` las líneas cuyo rango
  cubre exactamente el CFM requerido, y también muestra las que están cerca (dentro de
  un ±15% del rango, constante `BRAND_CATALOG_TOLERANCE`) para no dejar la lista vacía
  cuando la capacidad cae justo en el borde de una línea. Son rangos de la **línea
  completa** (que agrupa muchos modelos), no la ficha técnica de un modelo puntual — y
  solo cubre las marcas de nomenclatura estable; las de "gama económica" no están en
  este catálogo (ver "Marcas y fabricantes de referencia").

> ⚠️ Esta herramienta da una estimación orientativa. Para la selección final del
> compresor, valida siempre contra la ficha técnica del fabricante (curva real de FAD
> vs. presión a la altitud del sitio, potencia certificada, tren de secado/filtrado,
> número de etapas, etc.).

### Metodología de cálculo: accionamiento diésel (compresor portátil/remolcado)

Un compresor **estacionario** va acoplado a un motor **eléctrico**; uno **portátil o
remolcado** (el caso dominante en perforación y obra sin red eléctrica en Perú — minería
de altura, exploración, construcción) va acoplado a un motor **diésel**. Son dos cadenas
de accionamiento con física de derating y catálogos comerciales distintos; la app las
calcula siempre en paralelo (`js/calc.js`, función `computeDieselEngineSizing`) y el
selector "Tipo de accionamiento" solo decide cuál se muestra:

1. **Desagregar la eficiencia de motor eléctrico**: `COMPRESSOR_TECH_PRESETS.overallEfficiency`
   está calibrado contra consumo **eléctrico** real de catálogo (ver arriba), que ya
   incluye las pérdidas de un motor eléctrico típico. Un compresor diésel no tiene motor
   eléctrico en la cadena, así que se divide esa eficiencia global entre una eficiencia
   de motor eléctrico asumida (`ASSUMED_ELECTRIC_MOTOR_EFFICIENCY = 0.94`, típica de un
   motor NEMA/IE3 a plena carga) para aislar la eficiencia isentrópica+mecánica propia
   del elemento compresor: `eficiencia_acople = eficiencia_global / 0.94`.
2. **Transmisión mecánica**: la potencia en el acople del elemento compresor se divide
   entre la eficiencia de transmisión diésel→compresor (editable, `mechanicalEfficiencyPct`,
   por defecto 96% — compresores portátiles pequeños suelen llevar transmisión por
   correa; los grandes, acople directo).
3. **Margen de motor**: se aplica un margen adicional (editable, `engineMarginPct`, por
   defecto 15%) sobre la potencia absorbida, práctica habitual del sector para cubrir la
   carga parásita del ventilador de enfriamiento del propio compresor y no operar el
   motor diésel al límite de su curva de par.
4. **Derating del motor diésel**: el motor diésel deriva por altitud/temperatura **por su
   cuenta**, de forma independiente y adicional al derating de la succión del compresor
   (menor densidad de aire de admisión = menos oxígeno para la combustión) — misma regla
   general de referencia y misma estructura (`DIESEL_ENGINE_TECH_PRESETS`, con las
   mismas tres tecnologías y los mismos multiplicadores) que `ENGINE_TECH_PRESETS` del
   ["Dimensionador de Grupo Electrógeno"](https://github.com/nilthonnn/nefer) (proyecto
   hermano de este mismo repositorio). La potencia objetivo (pasos 1-3) se divide entre
   este factor de derating para obtener la **potencia nominal del motor a especificar**
   (a nivel del mar, la norma con la que los fabricantes certifican sus motores —
   ISO 3046 / SAE J1349).
5. **Consumo de combustible**: se estima a plena carga a partir de un consumo específico
   editable (`specificFuelConsumptionGPerKWh`, por defecto 210 g/kWh, típico de un
   diésel turboalimentado moderno) aplicado sobre la potencia nominal del motor,
   convertido a L/h con la densidad del diésel (`DIESEL_FUEL_DENSITY_KG_PER_L = 0.84`).
6. **Clase comercial de compresor portátil**: a diferencia del compresor estacionario
   (que se especifica por kW de motor), la industria de compresores portátiles — todas
   las marcas — converge en clases redondas de catálogo/alquiler por **caudal y presión
   nominal** (`MOBILE_COMPRESSOR_CLASSES`, p.ej. 185 CFM @ 100 psi, 400 CFM @ 150 psi,
   1300 CFM @ 350 psi). `findSuggestedMobileClass` recorre esas clases en orden
   ascendente y toma la primera que cubre **ambos** criterios — el caudal de catálogo
   requerido y la presión de descarga requerida — igual que `findSuggestedSize` hace con
   FAD+kW para el caso eléctrico.
7. **Marcas por línea portátil diésel**: `MOBILE_DIESEL_BRAND_CATALOG` (paralelo a
   `BRAND_CATALOG`) filtra por CFM las líneas portátiles reales de fabricantes con
   nomenclatura estable (Atlas Copco XAS/XATS, Doosan Portable Power — antes Ingersoll
   Rand — P-Series, Sullair, Kaeser Mobilair, Chicago Pneumatic) — son familias de
   producto **distintas** de la línea estacionaria eléctrica de la misma marca, no la
   misma máquina con otro motor.

> ⚠️ El motor diésel resultante siempre pide más kW nominales que el equivalente
> eléctrico del mismo caso — es intencional: no tiene el "empuje" de un motor eléctrico
> en la cadena, y además paga la transmisión mecánica y el margen del motor. A mayor
> altitud, la brecha crece más todavía porque el motor diésel deriva por su cuenta,
> encima del derating que ya paga la succión del propio compresor. Valida siempre contra
> la ficha técnica del fabricante del paquete portátil completo (motor + compresor ya
> emparejados de fábrica).

## Normativa de referencia

La app incluye una tarjeta con el marco normativo aplicable a dimensionamiento e
instalación de sistemas de aire comprimido, orientada a Perú con referencias
internacionales de uso extendido en la industria:

- **Eléctrica (Perú)**: Código Nacional de Electricidad (CNE), Tomo V – Utilización
  (Ministerio de Energía y Minas), para el circuito y arranque del motor del compresor;
  y la Norma Técnica **EM.010** "Instalaciones Eléctricas Interiores" del Reglamento
  Nacional de Edificaciones (RNE), aprobada por RM N.° 083-2019-VIVIENDA, para la
  instalación eléctrica de la sala de compresores.
- **Seguridad laboral (Perú)**: D.S. N.° 005-2012-TR "Reglamento de Seguridad y Salud en
  el Trabajo" — obligaciones generales del empleador respecto a equipos y recipientes a
  presión.
- **Minería (Perú)**: Reglamento de Seguridad y Salud Ocupacional en Minería
  (D.S. N.° 024-2016-EM, modificado por D.S. N.° 034-2023-EM), que incluye
  disposiciones sobre sistemas de aire comprimido, receptores de presión e inspección
  periódica en operaciones mineras. Para equipo diésel operando bajo tierra (incluidos
  compresores portátiles) exige además control de emisiones (filtro de
  partículas/catalizador) y un caudal mínimo de ventilación por HP instalado del motor —
  verificar el articulado vigente para el valor exacto exigido.
- **Emisiones diésel (referencia internacional)**: EPA Tier 4 Final (EE. UU.) / EU Stage
  V (Unión Europea), estándares de emisiones para motores diésel fuera de ruta (off-road)
  — Perú no certifica emisiones de motores fuera de ruta con norma propia, así que en la
  práctica el motor importado ya certifica contra uno de estos dos. Muchas operaciones
  mineras en Perú exigen Tier 4 Final/Stage V (o equivalente) como requisito de ingreso a
  sitio para equipo diésel.
- **Vialidad / remolque (Perú)**: Reglamento Nacional de Vehículos (D.S. N.° 058-2003-MTC
  y modificatorias), aplicable al chasis remolcado del compresor portátil: peso máximo
  por eje, luces y señalización, y sistema de frenado del remolque según su peso bruto.
- **Ruido ambiental (Perú)**: Estándares de Calidad Ambiental (ECA) para Ruido
  (D.S. N.° 085-2003-PCM) — relevante al elegir la cabina insonorizada de un compresor
  diésel portátil operando cerca de zonas residenciales/mixtas o campamentos.
- **Calidad de aire (referencia internacional)**: ISO 8573-1, que clasifica la calidad
  del aire comprimido (partículas, agua, aceite) por clase — clave para especificar el
  tren de secado/filtrado según la aplicación.
- **Ensayo de aceptación (referencia internacional)**: ISO 1217, que define las
  condiciones de referencia (100 kPa, 20°C, 0% HR) con las que los fabricantes
  certifican el caudal FAD de catálogo — la base de la corrección por altitud de esta
  app.
- **Recipientes a presión (referencia internacional)**: ASME BPVC Sección VIII, código
  de referencia (EE. UU.) de uso extendido en Perú a falta de una norma técnica peruana
  equivalente, para el tanque pulmón/receptor de aire.
- **Seguridad de uso (referencia internacional)**: OSHA 29 CFR 1910.242(b), que limita a
  ≤30 psi (~2 bar) el uso de aire comprimido para limpieza con boquilla abierta.

Es orientación general recopilada de fuentes públicas — verifica siempre el texto legal
vigente y valida con un ingeniero colegiado y la autoridad competente (municipalidad,
OSINERGMIN, Sunafil, o la gerencia de seguridad de la operación minera) antes de una
emisión de ingeniería final, ya que los requisitos exactos dependen del uso, la presión
y la ubicación específica del proyecto.

## Marcas y fabricantes de referencia

Panorama de mercado (no exhaustivo) incluido como tarjeta de referencia en la app:

- **Premium / gama alta**: Atlas Copco (Suecia), Ingersoll Rand (EE. UU.), Kaeser
  Kompressoren (Alemania), Sullair (grupo Hitachi, EE. UU./Japón).
- **Industrial general**: Gardner Denver / GD Industries (EE. UU.), Chicago Pneumatic
  (grupo Atlas Copco, Suecia), Boge, Bauer Kompressoren (Alemania), CompAir (grupo GD,
  Reino Unido), Hitachi (Japón).
- **Gama económica (China / Taiwán)**: Fusheng (Taiwán), Kaishan, Fujian Snowman
  (China), Hanbell (Taiwán, fabricante de "airends" usado por múltiples marcas
  ensambladoras).
- **Portátil diésel (remolcado)**: Atlas Copco XAS/XATS, Doosan Portable Power (antes
  Ingersoll Rand) P-Series, Sullair, Kaeser Mobilair, Chicago Pneumatic — estas mismas
  marcas tienen además una línea estacionaria eléctrica (arriba); son familias de
  producto distintas dentro de la misma empresa, no la misma máquina con otro motor.
- **Distribución en Perú**: Atlas Copco cuenta con subsidiaria propia en el país (Atlas
  Copco Perú); el resto de marcas se comercializa mediante distribuidores/representantes
  multimarca regionales.

> Confirma siempre precio, disponibilidad y representante autorizado vigente antes de
> una compra — la lista no implica recomendación de una marca sobre otra.

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
`node:assert`, requiere Node ≥18). Cubre la fórmula barométrica (contra valores de
referencia conocidos, p. ej. Cerro de Pasco ≈59 kPa), el factor de corrección de
densidad, la conversión CFM↔m³/min, el factor de uso, la regresión de que un mismo
consumo real exige más FAD de catálogo y más potencia en altura que a nivel del mar, la
advertencia de relación de compresión que excede el límite de una etapa, el orden de
magnitud de la potencia estimada contra la regla de mercado (~6.5 kW/m³-min a 7 bar(g)
para tornillo lubricado), la búsqueda de tamaño comercial, el filtrado de líneas de
producto por marca (`findMatchingBrandModels`, incluidos los casos sin coincidencias), la
cadena completa de dimensionamiento del motor diésel (`computeDieselEngineSizing`,
incluida la regresión de que el diésel siempre pide más kW que el eléctrico equivalente
y que deriva más con la altitud por su derating propio), la búsqueda de clase comercial
portátil por caudal+presión (`findSuggestedMobileClass`), el filtrado de marcas
portátiles diésel (`findMatchingMobileDieselModels`), y `csvEscape` (mitigación de
"CSV/Formula Injection" al exportar la tabla de demanda).

Un workflow de GitHub Actions (`.github/workflows/tests.yml`) corre esta misma suite en
cada `push` y `pull_request`, para que un cambio que rompa la metodología de cálculo no
pueda fusionarse sin que la suite lo detecte primero.

## Versión del esquema de cálculo

Cada proyecto guardado (localStorage o JSON exportado) lleva un campo `schemaVersion`
(`js/calc.js`, constante `CALC_SCHEMA_VERSION`). Si cargas un proyecto guardado con una
versión anterior de la metodología, la app **recalcula con la metodología actual y te
avisa explícitamente** en vez de mostrar el resultado antiguo en silencio. Incrementa
`CALC_SCHEMA_VERSION` cada vez que un cambio en `computeConsumerRow` o `computeSummary`
altere el resultado de proyectos ya guardados.

## Personalización

- Editar `CONSUMER_CATEGORY_PRESETS` en `js/calc.js` para cambiar los factores de uso
  típicos por categoría.
- Editar `STANDARD_SIZES_KW` para ajustar la lista de tamaños comerciales de referencia
  a los modelos realmente disponibles en tu mercado/proveedor.
- Editar `CONSUMER_LIBRARY` en `js/calc.js` para agregar/quitar equipos de la librería
  de consumos o ajustar sus valores de caudal a los que realmente operas/vendes.
- Editar `COMPRESSOR_TECH_PRESETS` para ajustar la eficiencia global asumida y la
  relación de compresión máxima en una etapa de cada tecnología a los datos reales del
  fabricante que uses.
- Editar `PERU_LOCATION_PRESETS` para agregar otras ubicaciones de referencia o ajustar
  las altitudes típicas.
- Editar `BRAND_CATALOG` para agregar/quitar líneas de producto por marca, ajustar sus
  rangos de CFM a datos actualizados del fabricante, o editar `BRAND_CATALOG_TOLERANCE`
  para cambiar qué tan "cerca" debe estar una línea del CFM requerido para aparecer como
  coincidencia cercana.
- Editar `DIESEL_ENGINE_TECH_PRESETS` para ajustar las tasas de derating por tecnología
  de motor diésel, `ASSUMED_ELECTRIC_MOTOR_EFFICIENCY` para cambiar la eficiencia de
  motor eléctrico que se desagrega al calcular la cadena diésel, o
  `DIESEL_FUEL_DENSITY_KG_PER_L` según el combustible/altitud (la densidad del diésel
  varía levemente con la temperatura).
- Editar `MOBILE_COMPRESSOR_CLASSES` para ajustar las clases comerciales de compresor
  portátil (caudal + presión nominal) a los modelos realmente disponibles en tu
  mercado/proveedor, o `MOBILE_DIESEL_BRAND_CATALOG` para las líneas portátiles por
  marca.

## Nota técnica: `hidden` y CSS

`css/styles.css` incluye `[hidden] { display: none !important; }`. Sin esa regla, un
elemento oculto vía `el.hidden = true` en JS se sigue mostrando en pantalla, porque una
regla de autor con la misma especificidad que el selector `[hidden]` del navegador
(como `.field { display: flex; }`) gana la cascada por orden de aparición — el atributo
`hidden` por sí solo no basta.

## Licencia y aviso legal

Este proyecto se distribuye bajo la [licencia MIT](LICENSE): software libre, sin garantía
de ningún tipo ("as is"), ver el archivo `LICENSE` para el texto legal completo.

La app misma muestra un aviso al primer uso (`<dialog id="disclaimerDialog">` en
`index.html`, lógica en `js/app.js`) que dice explícitamente que es una **herramienta de
referencia y orientación técnica preliminar**, que **no sustituye** el cálculo, diseño ni
la firma de un ingeniero colegiado, ni el cumplimiento de la normativa vigente aplicable
al proyecto específico. El usuario puede volver a leer este aviso en cualquier momento
desde el enlace "Aviso legal" al pie de la página. La aceptación se recuerda en
localStorage (`compressor-sizer:disclaimer-accepted`) y, al igual que el resto del
estado de la app, es local al navegador — no se envía a ningún servidor.
