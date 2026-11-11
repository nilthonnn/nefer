# Hoja de configuracion — Sincronismo

Planta: ____  ·  Tension 380 V  ·  60 Hz  ·  Fecha ____  ·  Tecnico ____

Los nombres DSE orientan la busqueda en Configuration Suite y pueden variar con la version del modulo. Ningun valor por defecto del fabricante se toma como recomendado.

## Sincronizador

### Ventana de frecuencia (deslizamiento)  (Hz)

- **En DSE:** Synchroniser · Check sync · frequency / slip
- **Que hace:** Diferencia maxima de frecuencia entre generador y barra para permitir el cierre.
- **Como decidir:** IEEE 1547-2018 tabla 5: 0.3 Hz hasta 500 kVA, 0.2 Hz hasta 1500 kVA, 0.1 Hz por encima. Guia DSE de sincronismo 057-045 parte 1: 0.2 Hz en ediciones antiguas y 0.1 Hz en las posteriores, como valor con el que se parlela bien.
- **Si queda mal:** Ancha: cierre con golpe y oscilacion de potencia. Estrecha: el gobernador no la sostiene y el grupo no sincroniza nunca.
- **Como se comprueba:** nefer sincronismo verificar con las lecturas del cierre; sincronoscopio externo.
- **Valor ajustado:** ________

### Ventana de tension  (%)

- **En DSE:** Synchroniser · Check sync · voltage
- **Que hace:** Diferencia maxima de tension entre generador y barra para cerrar.
- **Como decidir:** IEEE 1547-2018: 10 % / 5 % / 3 % segun kVA. Guia DSE 057-045: 5 %.
- **Si queda mal:** Ancha: al cerrar circulan reactivos y salta la 40 o la sobrecorriente.
- **Como se comprueba:** Medir V gen y V barra en el mismo instrumento antes del cierre.
- **Valor ajustado:** ________

### Ventana de angulo de fase  (°)

- **En DSE:** Synchroniser · Check sync · phase angle
- **Que hace:** Angulo maximo entre fasores al dar la orden de cierre.
- **Como decidir:** IEEE 1547-2018: 20° / 15° / 10° segun kVA. Guia DSE 057-045: 5°. Mas estrecho si el interruptor es lento.
- **Si queda mal:** Ancha: par de choque en el acoplamiento y el devanado.
- **Como se comprueba:** Registrar el angulo del cierre en el historial del modulo.
- **Valor ajustado:** ________

### Deslizamiento objetivo / sentido  (Hz)

- **En DSE:** Synchroniser · slip frequency
- **Que hace:** Con cuanto exceso de velocidad se acerca el generador a la barra.
- **Como decidir:** Levemente positivo (generador mas rapido) para entrar tomando carga, no absorbiendola. Menor que la ventana de frecuencia.
- **Si queda mal:** Negativo: entra motorizado y dispara la 32. Grande: el angulo pasa rapido por la ventana y el cierre llega tarde.
- **Como se comprueba:** Observar el sincronoscopio: debe girar lento en sentido rapido.
- **Valor ajustado:** ________

### Tiempo de cierre del interruptor (compensacion)  (ms)

- **En DSE:** Breaker · close time / advance
- **Que hace:** Lo que tarda el interruptor en juntar contactos; el modulo adelanta la orden.
- **Como decidir:** Medido con analizador de tiempos o de la placa del interruptor; no se estima.
- **Si queda mal:** Sin compensar: el angulo en el contacto es mayor que el de la orden.
- **Como se comprueba:** Prueba de tiempos del interruptor; nefer sincronismo verificar --t-cierre.
- **Valor ajustado:** ________

### Tiempo maximo de sincronizacion  (s)

- **En DSE:** Synchroniser · fail to sync timer
- **Que hace:** Si no sincroniza en este tiempo, alarma.
- **Como decidir:** Mayor que el tiempo normal de sincronizacion medido, con margen. Vigilar su tendencia: subir es aviso de gobernador gastado.
- **Si queda mal:** Corto: alarmas falsas. Muy largo: el grupo queda buscando y la carga espera.
- **Como se comprueba:** nefer sincronismo tendencia sobre tiempo_sincronizacion_s.
- **Valor ajustado:** ________

### Cierre en barra muerta  (on/off · V)

- **En DSE:** Bus · dead bus close / dead bus voltage
- **Que hace:** Permite a la primera unidad cerrar sobre la barra sin tension.
- **Como decidir:** Activo, con umbral de barra muerta bien por debajo de la nominal y arbitraje por MSC para que cierre una sola.
- **Si queda mal:** Dos unidades cierran a la vez sobre la barra muerta, fuera de fase.
- **Como se comprueba:** Prueba de arranque simultaneo: debe cerrar una sola.
- **Valor ajustado:** ________

## Reparto de carga

### Modo: isocrono compartido / estatismo  (—)

- **En DSE:** Load share · load sharing / droop active
- **Que hace:** Como reparten kW las unidades.
- **Como decidir:** Con MSC: isocrono compartido (frecuencia fija). Estatismo solo si no hay enlace o se trabaja con red.
- **Si queda mal:** Mezcla sin coordinar: unidades que se disputan la carga.
- **Como se comprueba:** nefer sincronismo estatismo; ver el reparto a 25/50/75/100 %.
- **Valor ajustado:** ________

### Estatismo de velocidad (si se usa)  (%)

- **En DSE:** Governor · droop %
- **Que hace:** Cuanto cae la frecuencia de vacio a plena carga.
- **Como decidir:** Igual en todas las unidades. Con la consigna en vacio que da nefer estatismo para que repartan parejo.
- **Si queda mal:** Distinto entre unidades: reparto desigual a toda carga.
- **Como se comprueba:** nefer sincronismo estatismo planta.json.
- **Valor ajustado:** ________

### Estatismo de tension / reparto de kVAr  (%)

- **En DSE:** AVR · voltage droop / kvar share
- **Que hace:** Reparto de reactivos entre unidades.
- **Como decidir:** Igual en todas; con MSC, reparto de kVAr activo.
- **Si queda mal:** Corriente reactiva circulante y disparos por 40.
- **Como se comprueba:** nefer sincronismo reparto (kvar por unidad).
- **Valor ajustado:** ________

### Rampa de toma de carga  (%/s)

- **En DSE:** Load control · ramp up rate
- **Que hace:** Velocidad con que la unidad toma su parte despues de cerrar.
- **Como decidir:** Lo que el motor acepta sin caida de frecuencia: el escalon de carga admisible del motor (ISO 8528-5 / dato del fabricante del motor).
- **Si queda mal:** Rapida: caida de frecuencia y humo. Lenta: las demas cargan de mas un rato.
- **Como se comprueba:** Registrar f durante la toma de carga.
- **Valor ajustado:** ________

### Rampa de descarga  (%/s)

- **En DSE:** Load control · ramp down rate
- **Que hace:** Velocidad con que se descarga antes de abrir.
- **Como decidir:** Tal que las demas unidades absorban la carga sin sobrecargarse.
- **Si queda mal:** Rapida: escalon a las demas. Lenta: retrasa la parada.
- **Como se comprueba:** Observar kW de las demas durante la descarga.
- **Valor ajustado:** ________

### Nivel de apertura al final de la rampa  (% kW)

- **En DSE:** Load control · ramp down / unload level
- **Que hace:** Carga a la que se abre el 52G al terminar la descarga.
- **Como decidir:** Por ENCIMA del pickup de potencia inversa: se abre antes de motorizar.
- **Si queda mal:** Por debajo del pickup de la 32: cada parada termina en disparo por potencia inversa.
- **Como se comprueba:** Revision automatica de nefer (nivel_apertura > p32_pickup).
- **Valor ajustado:** ________

### Arranque / parada por demanda  (% kW)

- **En DSE:** Load demand · start/stop levels
- **Que hace:** Niveles de carga a los que entra o sale una unidad.
- **Como decidir:** Nivel de parada claramente menor que el de arranque, para que no cicle.
- **Si queda mal:** Niveles cercanos: unidades que arrancan y paran en ciclo.
- **Como se comprueba:** Contar arranques por dia en el historial.
- **Valor ajustado:** ________

## Protecciones

### Potencia inversa (32): pickup  (% kW)

- **En DSE:** Generator protection · reverse power
- **Que hace:** Potencia absorbida a la que dispara.
- **Como decidir:** Segun estudio de coordinacion; referencia de taller diesel 5–15 %.
- **Si queda mal:** Alto: el grupo se motoriza sin disparar. Bajo: dispara en cada transitorio.
- **Como se comprueba:** Prueba de 32 en la puesta en marcha.
- **Valor ajustado:** ________

### Potencia inversa (32): retardo  (s)

- **En DSE:** Generator protection · reverse power delay
- **Que hace:** Tiempo sosteniendo potencia inversa antes de disparar.
- **Como decidir:** Mayor que la oscilacion del cierre; referencia 1–10 s.
- **Si queda mal:** Corto: dispara al cerrar. Largo: el motor arrastrado se daña.
- **Como se comprueba:** Prueba de 32.
- **Valor ajustado:** ________

### Perdida de excitacion (40)  (kVAr · s)

- **En DSE:** Generator protection · loss of excitation / kvar negative
- **Que hace:** Dispara la unidad que absorbe reactivos de la barra.
- **Como decidir:** Segun la curva de capacidad del alternador y el estudio.
- **Si queda mal:** Deshabilitada: una unidad sin campo arrastra la tension de la barra.
- **Como se comprueba:** Revisar que este habilitada en todas.
- **Valor ajustado:** ________

### Sub y sobretension (27/59)  (% · s)

- **En DSE:** Generator protection · under/over voltage
- **Que hace:** Limites de tension del generador.
- **Como decidir:** Segun la carga y el estudio; respecto de 380 V nominal.
- **Si queda mal:** Estrechos: disparos en transitorios de toma de carga.
- **Como se comprueba:** Revisar umbrales contra la nominal declarada.
- **Valor ajustado:** ________

### Sub y sobrefrecuencia (81U/81O)  (% · s)

- **En DSE:** Generator protection · under/over frequency
- **Que hace:** Limites de frecuencia del generador.
- **Como decidir:** En estatismo, 81O por encima de la frecuencia en vacio.
- **Si queda mal:** 81O por debajo de la f en vacio: disparo al quedar sin carga.
- **Como se comprueba:** Revision automatica de nefer (81O > f en vacio).
- **Valor ajustado:** ________

### Falla del enlace MSC  (accion)

- **En DSE:** MSC · link failure action
- **Que hace:** Que hace la unidad si pierde el enlace con las demas.
- **Como decidir:** Una accion definida (alarma, pasar a estatismo o descargar y abrir).
- **Si queda mal:** Sin accion: unidades en isocrono sin enlace que se disputan la carga.
- **Como se comprueba:** Desconectar el MSC en prueba y observar.
- **Valor ajustado:** ________
