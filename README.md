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

1. **Parámetros del proyecto**: tensión, fases, frecuencia, margen de seguridad,
   factor de potencia del generador, altitud y temperatura ambiente del sitio.
2. **Tabla de cargas**: agregas cada equipo/carga con su potencia (kW o HP), cantidad,
   factor de potencia (cos φ) y tipo de arranque. Al elegir el tipo (resistiva, motor
   con arranque directo, estrella-triángulo, arranque suave o variador de frecuencia)
   se autocompleta un factor de arranque típico, editable si tienes el dato real del
   fabricante.
3. **Resultado**: calcula la carga total en régimen, el pico de arranque estimado, aplica
   el margen de seguridad y el derating por altitud/temperatura, y sugiere el tamaño de
   generador (kVA/kW) recomendado, junto con el tamaño comercial estándar más cercano.
4. **Guardar/exportar**: autosave en el navegador (localStorage), guardar/cargar proyecto,
   exportar/importar JSON y exportar CSV de las cargas, más un botón de impresión con
   estilos listos para generar un informe en PDF desde el navegador.

## Metodología de cálculo

- **kW → kVA** de cada carga: `kVA = kW / cos φ`.
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
