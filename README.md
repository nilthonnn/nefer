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
   del sitio.
2. **Tabla de cargas**: agregas cada equipo/carga con su potencia (kW o HP), cantidad,
   factor de potencia (cos φ), **categoría** (Motor, Iluminación, Electrónica/VFD o
   Resistiva) y tipo de arranque. Categoría y tipo de arranque son independientes: una
   carga puede ser "Electrónica/VFD" (no lineal, aporta armónicos) sin tener arranque
   brusco. Al elegir el tipo de arranque (directo, estrella-triángulo, arranque suave o
   variador de frecuencia) se autocompleta un factor de arranque típico, editable si
   tienes el dato real del fabricante. Las cargas de categoría "Electrónica/VFD" además
   llevan una **severidad de armónicos** (baja/media/alta).
3. **Resultado**: calcula la carga total en régimen, el pico de arranque estimado, aplica
   el margen de seguridad, el derating por altitud/temperatura y una sobredimensión
   adicional del alternador según la fracción de carga no lineal (armónicos), y sugiere
   el tamaño de generador (kVA/kW) recomendado junto con el tamaño comercial estándar
   más cercano.
4. **Librería de cargas**: catálogo de ~45 equipos típicos del mercado (motores trifásicos
   por HP estándar NEMA/IEC, soldadoras inversoras y convencionales, bombas, compresores,
   HVAC, iluminación, hornos, cargadores/UPS, herramientas) con potencia, cos φ, eficiencia
   y tipo de arranque precargados. Se abre con el botón "📚 Librería de cargas", tiene
   buscador y filtro por grupo, y cada "+ Añadir" agrega una fila lista a la tabla.
5. **Guardar/exportar**: autosave en el navegador (localStorage), guardar/cargar proyecto,
   exportar/importar JSON, exportar/**importar CSV** de las cargas (parser tolerante a
   variantes de encabezado), y un botón de impresión que genera un **informe técnico**
   con portada (proyecto/cliente/fecha/preparado por), parámetros, cuadro de cargas,
   resultados, composición de la carga y bloque de firmas — listo para "Guardar como PDF"
   desde el diálogo de impresión del navegador.

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
  por cada °C sobre 25 °C.
- **Carga no lineal / armónicos**: se suma el kVA de las cargas de categoría
  "Electrónica/VFD", ponderado por su severidad de armónicos (baja ×0.5, media ×1.0,
  alta ×1.5), y se calcula qué fracción representa del kVA total del sistema. Esa
  fracción determina una sobredimensión adicional del alternador por tramos
  (`js/app.js`, constante `HARMONIC_OVERSIZE_BRACKETS`): sin sobredimensión hasta 10%,
  ×1.10 hasta 30%, ×1.20 hasta 60%, ×1.35 por encima. Es una heurística de referencia,
  no un cálculo de THD real — para cargas no lineales dominantes (grandes VFD,
  rectificadores, UPS) se requiere un estudio de armónicos y una especificación de
  alternador (paso de bobinado, reactancia subtransitoria) con el fabricante.
- **kW recomendado**: `kVA_recomendado × factor_de_potencia_del_generador` (por defecto 0.8).
- **Tamaño comercial sugerido**: primer valor de una lista de tamaños estándar de
  referencia (`js/app.js`, constante `STANDARD_SIZES_KVA`) que sea igual o mayor al
  kVA recomendado.

> ⚠️ Esta herramienta da una estimación orientativa. Para la selección final del grupo
> electrógeno, valida siempre contra la ficha técnica del fabricante (curvas reales de
> arranque de motores, derating específico del modelo, tipo de carga no lineal, THD, etc.).

## Estructura del proyecto

```
index.html        Estructura de la app
css/styles.css     Estilos (incluye estilos de impresión)
js/app.js          Estado, motor de cálculo y lógica de UI
```

## Personalización

- Editar `STARTING_PRESETS` en `js/app.js` para cambiar los factores de arranque típicos.
- Editar `STANDARD_SIZES_KVA` para ajustar la lista de tamaños comerciales de referencia
  a los modelos realmente disponibles en tu mercado/proveedor.
- Editar `LOAD_LIBRARY` en `js/app.js` para agregar/quitar equipos de la librería de
  cargas o ajustar sus valores de placa a los que realmente vendes/instalas.
