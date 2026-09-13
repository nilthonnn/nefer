# Tipografía alojada aquí

Barlow y Barlow Condensed, subconjunto **latin**, en `woff2`. Se alojan en el
propio repositorio en vez de pedirlas a Google por dos razones medidas, que
están en [../../AUDITORIA-CALIDAD.md](../../AUDITORIA-CALIDAD.md):

1. Pedirlas fuera bloqueaba el primer pintado **12 888 ms** cuando la red no
   respondía, que es la condición para la que se hizo esta aplicación.
2. Era la única llamada a un tercero: cada apertura de un acta le comunicaba
   a Google la IP del operador.

| Archivo | Familia | Peso | Tamaño |
|---|---|---:|---:|
| `barlow-400.woff2` | Barlow | 400 | 21,7 KB |
| `barlow-600.woff2` | Barlow | 600 | 22,2 KB |
| `barlow-700.woff2` | Barlow | 700 | 22,3 KB |
| `barlow-cond-600.woff2` | Barlow Condensed | 600 | 21,8 KB |
| `barlow-cond-700.woff2` | Barlow Condensed | 700 | 21,9 KB |

Sólo esos cinco cortes: son los únicos pesos que el diseño declara. El
subconjunto latin cubre el español entero —tildes, `ñ`, `¿`, `¡`, `°`, `—`,
comillas españolas—. Lo que no cubre, como el triángulo `▾` de los
desplegables, lo pone la tipografía del sistema sin que se note.

La familia monoespaciada de las etiquetas pequeñas **no** se aloja: `ui-monospace`
ya da SF Mono en iPhone y Roboto Mono en Android, y no cuesta un solo byte.

## Licencia

Barlow es de Jeremy Tribby y se distribuye bajo la **SIL Open Font License
1.1**, que permite alojarla y redistribuirla siempre que se acompañe de la
licencia. Está en [`LICENCIA-OFL.txt`](LICENCIA-OFL.txt), y no debe separarse
de estos archivos.

## Cómo actualizarlas

Los cinco archivos salieron del subconjunto latin que sirve Google Fonts para
`Barlow:wght@400;600;700` y `Barlow+Condensed:wght@600;700`. Para renovarlos,
pedir la hoja de estilos con un agente de navegador moderno —si no, entrega
`ttf` en vez de `woff2`—, quedarse con los bloques marcados `/* latin */` y
descargar esas URL.
