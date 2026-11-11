# Guia de sintomas del paralelo de grupos electrogenos

Guia de referencia — no es antecedente de la flota. Generada por `nefer sincronismo guia`; no editar a mano.
Ordena las causas de cada sintoma de la mas barata de descartar a la
mas cara. No sustituye el manual del controlador ni del AVR.

## S1. No sincroniza: el interruptor no recibe orden de cierre

Funciones ANSI relacionadas: 25.

Tambien se describe como: no sincroniza; no cierra; no entra en paralelo; tarda en sincronizar; timeout sincronismo; falla de sincronismo.

1. **Ventanas del sincronoscopio mas estrechas de lo que el gobernador puede sostener.** Compare ±Δf/±ΔV/±Δφ del controlador con la estabilidad real de frecuencia en vacio (oscilacion pico a pico en 30 s).
2. **Gobernador inestable (ganancias o actuador).** Registre la frecuencia en vacio: una oscilacion > 0.1 Hz no deja que el angulo se quede en ventana. Revise varillaje y ganancias P/I.
3. **Consigna de tension del AVR distinta de la de barra.** Mida V generador y V barra en el mismo instrumento; ΔV debe quedar dentro de la ventana con margen.
4. **Medicion de barra equivocada: fusible de TP abierto, fase cruzada o relacion mal declarada.** Con la barra energizada, mida las tres tensiones de TP en bornera del controlador y compare con la barra.
5. **Secuencia de fases invertida entre generador y barra.** Secuencimetro en los dos lados del interruptor. Nunca se corrige desde el controlador.
6. **Circuito de cierre: bobina, resorte sin cargar, enclavamiento o permisivo externo abierto.** Verifique tension de mando en la bobina de cierre al momento de la orden y el estado del motor de carga de resortes.

## S2. Dispara por potencia inversa al cerrar o al bajar carga

Funciones ANSI relacionadas: 32, 25.

Tambien se describe como: potencia inversa; reverse power; 32; motoriza; dispara al cerrar; dispara al descargar.

1. **Cierre con deslizamiento negativo (generador mas lento).** Lea el deslizamiento en la orden de cierre: debe ser levemente positivo (+0.05 a +0.2 Hz).
2. **Rampa de descarga que llega a 0 kW antes de abrir.** Revise el umbral de apertura de la rampa: debe abrir antes de cruzar a potencia negativa (tipico 5–10 % kW).
3. **Restriccion de combustible: filtros, aire en la linea, bomba de transferencia.** Tome carga en escalones; si cae la frecuencia y no recupera, mida restriccion de filtros y presion de combustible.
4. **Polaridad o relacion de TC equivocada en el controlador.** Con carga resistiva conocida, compare los kW del controlador con una pinza de potencia: signo y magnitud.
5. **Ajuste de la 32 demasiado sensible o sin retardo.** Revise pickup y retardo contra el estudio de coordinacion.

## S3. Oscilacion de carga activa entre unidades (pendulea, hunting)

Funciones ANSI relacionadas: 32.

Tambien se describe como: oscila; pendulea; hunting; se pasan la carga; fluctua kw; inestable en paralelo.

1. **Ganancias del gobernador altas para el paralelo.** Baje la ganancia proporcional de a 10 % y observe la amplitud de la oscilacion de kW.
2. **Lineas de reparto de carga con ruido o sin malla aterrada en un solo extremo.** Revise el cable apantallado de las lineas de reparto: malla a tierra solo del lado del controlador.
3. **Mas de una unidad en isocrono sin reparto por lineas.** Revise el modo de cada unidad: una sola en isocrono, o todas con reparto isocrono por lineas o bus de comunicacion.
4. **Juego en el varillaje o actuador gastado.** Mueva el actuador a mano con el motor detenido y mida el juego; compare la corriente del actuador con la del manual.

## S4. Reparto de reactivos desigual o corriente circulante

Funciones ANSI relacionadas: 40.

Tambien se describe como: kvar; reactivo; reactiva; corriente circulante; factor de potencia; fp desigual; una absorbe reactivos; sobreexcitada.

1. **Consignas de tension del AVR distintas entre unidades.** Mida la tension en vacio de cada unidad con el mismo instrumento; deben coincidir dentro de 0.5 %.
2. **Estatismo de tension deshabilitado o distinto entre AVR.** Revise el ajuste de droop de cada AVR (tipico 3–5 %) y que sea igual en todas.
3. **TC de compensacion de estatismo con polaridad invertida o en la fase equivocada.** El TC de droop va en la fase que el manual del AVR indica (habitualmente B) y con su polaridad: con carga inductiva la tension debe BAJAR al aumentar la corriente.
4. **Control de factor de potencia o de kVAr del controlador peleando con el AVR.** Deje un solo lazo a cargo de los reactivos: el del controlador o el estatismo del AVR.

## S5. Disparo por perdida de excitacion

Funciones ANSI relacionadas: 40.

Tambien se describe como: perdida de excitacion; loss of excitation; 40; subexcitada; absorbe reactivos; campo.

1. **Fusible o alimentacion del AVR.** Mida la alimentacion del AVR (PMG o shunt) y la corriente de campo de la excitatriz bajo carga.
2. **Diodos rotativos o varistor en falla.** Con el equipo detenido, mida cada diodo del puente rotativo en directo e inverso, desconectado.
3. **Sensado de tension del AVR abierto o con fase faltante.** Mida la tension de sensado en la bornera del AVR.
4. **Unidad empujada a subexcitarse por otra con consigna alta.** Ver sintoma S4: el reparto de kVAr desigual termina aqui.

## S6. Golpe mecanico, ruido o pico de corriente al cerrar

Funciones ANSI relacionadas: 25.

Tambien se describe como: golpe; ruido al cerrar; pico de corriente; estruendo; brinca; cierre brusco; cierre fuera de fase.

1. **Angulo en el contacto mayor que el de la orden: tiempo de cierre del interruptor no compensado.** Mida el tiempo de cierre del interruptor y calcule el angulo de adelanto (nefer sincronismo verificar).
2. **Deslizamiento alto en el momento de la orden.** Baje la ventana de Δf o la consigna de deslizamiento.
3. **Medicion de angulo desplazada: TP en otra fase o conexion estrella/triangulo distinta entre lados.** Sincronoscopio externo en paralelo con el del controlador: los dos deben marcar cero en el mismo instante.

## S7. Reparto de carga activa desigual en regimen

Tambien se describe como: reparto desigual; no reparte; una toma toda la carga; kw desigual; load sharing; reparto de carga.

1. **Consignas de velocidad en vacio distintas (unidades en droop).** Calcule el reparto esperado (nefer sincronismo estatismo) y compare con lo medido; ajuste la consigna sugerida.
2. **Estatismo distinto entre gobernadores.** Revise que todas tengan el mismo estatismo en %.
3. **Lineas de reparto abiertas o una unidad fuera del bus de comunicacion.** Revise la tension de la linea de reparto en cada controlador y el estado del bus (CAN/intercontrolador).
4. **Unidad que no puede tomar carga: limite de combustible, temperatura de escape o derrateo por altura.** Revise si alguna unidad esta en limitacion o con derrateo activo en el controlador.
