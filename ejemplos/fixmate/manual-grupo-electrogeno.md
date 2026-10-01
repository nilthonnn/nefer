# Manual de taller — grupo electrógeno insonorizado de 74 kW

Extracto ficticio, escrito para probar la ingesta de manuales. No sustituye al
manual del fabricante de ningún equipo real.

## Sistema de admisión de aire

El indicador de restricción de admisión se lee con el motor a régimen máximo
sin carga. Si la banda roja queda a la vista, el elemento primario está
colmatado y debe reemplazarse: un elemento soplado con aire comprimido pierde
la capa de fieltro y deja pasar polvo al turbo.

En faena sobre 3500 msnm el intervalo de cambio del elemento primario baja de
500 a 250 horas. La menor densidad del aire adelanta la restricción y el
síntoma típico es humo negro con pérdida de potencia al tomar carga.

Herramientas: llave de 13 mm, linterna de inspección.

## Sistema de inyección

El retorno de inyectores se mide en banco de probetas con el motor en ralentí
y a temperatura de trabajo. Un retorno mayor al doble del promedio de los
demás cilindros indica aguja desgastada.

Pares de apriete del sistema de inyección:

- prisionero de inyector: 30 N·m
- tuerca de cañería de alta presión: 25 N·m
- tapa de balancines: 22 N·m

Nunca reutilice la arandela de asiento del inyector: su aplastamiento define
la altura de la tobera dentro de la cámara.

## Tablero de control y códigos

El módulo de control muestra el código P0300 cuando detecta fallo de combustión
en más de un cilindro, sin poder aislar cuál. Las dos causas que más lo
disparan en esta flota son la admisión restringida y el retorno excesivo de un
inyector, en ese orden.

El código SPN 157 corresponde a presión de riel fuera de rango y se lee en el
bus J1939 del motor.

## Sistema eléctrico y baterías

El electrolito se verifica con el equipo frío. Una densidad por debajo de 1.220
en cualquier vaso condena la batería aunque el arranque todavía funcione.

Par de apriete de bornes de batería: 8 N·m. Un borne apretado de más parte el
plomo y uno flojo calienta y sulfata.
