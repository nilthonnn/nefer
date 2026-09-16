# Demo de registro de camal: qué hace y dónde se rompe

`demo_camal.html` es el prototipo de conteo y pesaje de faenamiento (alpaca,
llama, cordero y sus partes) tal como venía en el PDF, sin una sola línea
cambiada. Este documento recoge lo que pasó al ejecutarlo de verdad en un
navegador, con una pantalla de celular (390 × 844) y con la configuración
regional del Perú.

La prueba se reproduce con:

```bash
python3 demos/camal/probar_demo.py salidas/
```

Abre el demo en Chromium, hace las tres pruebas que propone el PDF, guarda las
capturas y descarga el CSV. `probar_bordes.py` hace lo otro: teclear mal.

## Las tres funciones del PDF funcionan

| Prueba | Resultado |
|---|---|
| Arranque con datos precargados | 3 registros, 86.3 kg, S/ 1149.40 |
| `+ Alpaca` con peso 38.5 | 4 registros, 124.8 kg, S/ 1688.40 |
| Menudencias / Panzas, 5.5 kg | 5 registros, 130.3 kg, S/ 1765.40 |
| `Cargar Más Datos Demo` | 7 registros, 203.8 kg, S/ 2776.40 |
| `Exportar a Excel (.CSV)` | `Reporte_Demo_Camal.csv`, 353 bytes, con BOM |

Los totales cuadran a mano, la tabla pinta el último registro arriba, el campo
de peso se limpia solo después de guardar, guardar sin peso avisa y cancelar el
cuadro de peso no registra nada. No hay errores de página ni mensajes de
consola. El CSV abre en Excel con las tildes correctas: lleva BOM.

Como demostración de escritorio, está bien. Lo que sigue es lo que hay que
arreglar antes de que alguien lo use una mañana entera en el camal.

## Lo que hay que arreglar antes de usarlo en el camal

### 1. Al recargar, la jornada desaparece

El arreglo de registros vive solo en memoria. Recargar la página —o que el
sistema operativo del celular descarte la pestaña mientras se atiende una
llamada, que es lo normal en una jornada de cinco horas— devuelve los tres
registros de demostración y borra todo lo contado. No se guarda nada en
`localStorage`: cero claves después de recargar.

Es el defecto más grave. Un contador de camal que pierde la cuenta al bloquear
el teléfono no se puede usar en producción. Se resuelve guardando en
`localStorage` en cada `actualizarVista()` y releyendo al arrancar.

### 2. El peso con coma se registra mal, y en silencio

En el Perú el peso se escribe con coma. `parseFloat("38,5")` devuelve `38`.

```
peso tecleado "38,5"  ->  peso: 38, subtotal: S/ 532   (debía ser 38.5 y S/ 539)
```

Medio kilo perdido por animal, sin aviso, sin nada raro en pantalla. En una
jornada de doscientas cabezas es un descuadre de cien kilos contra la balanza.
Se arregla con `parseFloat(peso.replace(",", "."))`.

### 3. El conteo rápido acepta cualquier cosa

`guardarEntrada()` valida `peso > 0`; `registrarPasoRapido()` no valida nada.
El `|| 0` convierte lo que no entiende en cero y lo registra igual:

```
peso tecleado "asd"   ->  peso: 0,   subtotal: S/ 0
peso tecleado "-12"   ->  peso: -12, subtotal: S/ -0.00   (resta del total)
precio en blanco      ->  precio: 0, subtotal: S/ 0
```

Un peso negativo resta del consolidado del día. Los tres casos necesitan la
misma validación que ya tiene el botón de guardar, y el campo de precio debería
negarse a quedar vacío.

### 4. No se puede corregir ni borrar un registro

No hay botón de deshacer, ni de editar, ni de eliminar: la tabla es de solo
lectura y en la página no existe más botón que los ocho de contar, guardar,
exportar y cargar datos. Un peso mal tecleado se queda en el reporte para
siempre, y la única salida es recargar —que borra la jornada entera (defecto 1).
Hace falta, como mínimo, una `×` por fila.

### 5. El precio es uno solo para todas las categorías

El conteo rápido toma el precio del campo de la sección 2, que vale 14.00 para
todo. Pero los propios datos precargados usan 18.00 para el cuero y 12.00 para
la alpaca observada: el demo se contradice, porque con los botones no hay forma
de reproducir esos precios sin volver a la sección 2 y cambiar el campo antes de
cada toque. Hace falta una tabla de precio por categoría.

### 6. El PDF promete un contador por especie que no existe

El instructivo dice «verás cómo el contador y los totales cambian al instante».
Los totales sí; el contador por especie no está: el resumen solo muestra el
número total de registros. En un camal lo que se reporta es cuántas alpacas,
cuántas llamas, cuántos corderos. Falta el desglose por categoría.

### 7. `prompt()` es mal sitio para pedir un peso

El cuadro del navegador no ofrece teclado numérico en Android —sale el teclado
de texto, y hay que buscar el punto—, los navegadores incrustados de WhatsApp y
Facebook lo bloquean, y Chrome deja de mostrarlo si el usuario marca «no volver
a mostrar». Con guantes y a las seis de la mañana, es el peor control posible.
Mejor un campo numérico con `inputmode="decimal"` dentro de la propia página.

### 8. Detalles menores

- **La hora sale en dos formatos.** Los datos precargados dicen `07:30:15`; los
  nuevos, `8:51:04 a. m.`. Ordenar por hora en Excel no funciona. Basta
  `toLocaleTimeString("es-PE", { hour12: false })`.
- **No hay fecha, solo hora.** El reporte no dice de qué día es. Dos jornadas
  exportadas no se distinguen.
- **El nombre del archivo es siempre el mismo.** `Reporte_Demo_Camal.csv`
  pisa al anterior en la carpeta de descargas. Debería llevar la fecha.
- **El zoom está bloqueado** (`maximum-scale=1.0, user-scalable=no`). iOS lo
  ignora desde hace años; Android no.
- **El `objectURL` no se libera** tras exportar. Es una fuga pequeña, pero se
  cierra con una línea.
