# Hoja de configuracion — Transferencia automatica (TTA)

Planta: ____  ·  Tension 380 V  ·  60 Hz  ·  Fecha ____  ·  Tecnico ____

Los nombres DSE orientan la busqueda en Configuration Suite y pueden variar con la version del modulo. Ningun valor por defecto del fabricante se toma como recomendado.

## Deteccion de falla de red

### Subtension de red  (V o %)

- **En DSE:** Mains · under voltage
- **Que hace:** Tension de red por debajo de la cual se considera falla.
- **Como decidir:** Por debajo del minimo que la carga tolera; respecto de 380 V entre fases.
- **Si queda mal:** Alta: arranca por caidas normales de la red. Baja: la carga sufre antes de transferir.
- **Como se comprueba:** Bajar la tension con variac en prueba, o revisar el historial de eventos.
- **Valor ajustado:** ________

### Sobretension de red  (V o %)

- **En DSE:** Mains · over voltage
- **Que hace:** Tension de red por encima de la cual se considera falla.
- **Como decidir:** Por encima del maximo normal de la red local.
- **Si queda mal:** Baja: transferencias por sobretensiones normales.
- **Como se comprueba:** Historial de eventos.
- **Valor ajustado:** ________

### Sub y sobrefrecuencia de red  (Hz)

- **En DSE:** Mains · under/over frequency
- **Que hace:** Frecuencia de red fuera de la cual se transfiere.
- **Como decidir:** Alrededor de 60 Hz segun la estabilidad de la red local.
- **Si queda mal:** Estrecha: transferencias innecesarias.
- **Como se comprueba:** Historial de eventos.
- **Valor ajustado:** ________

### Secuencia de fases de red  (on/off)

- **En DSE:** Mains · phase rotation
- **Que hace:** Considera falla si la red llega con la secuencia invertida.
- **Como decidir:** Activa si hay motores en la carga.
- **Si queda mal:** Inactiva: tras un trabajo en la red, los motores giran al reves.
- **Como se comprueba:** Secuencimetro.
- **Valor ajustado:** ________

## Temporizadores

### Retardo de falla de red (transitorio)  (s)

- **En DSE:** Timers · mains transient delay
- **Que hace:** Cuanto debe durar la falla para considerarla real.
- **Como decidir:** Mayor que las interrupciones breves de la red (recierres).
- **Si queda mal:** Corto: arranca por parpadeos. Largo: la carga queda sin energia mas tiempo.
- **Como se comprueba:** Historial: arranques por falla de red de pocos segundos.
- **Valor ajustado:** ________

### Retardo de arranque  (s)

- **En DSE:** Timers · start delay
- **Que hace:** Espera entre la falla confirmada y el arranque.
- **Como decidir:** Corto si la carga es critica.
- **Si queda mal:** Largo: mas tiempo sin energia.
- **Como se comprueba:** Medir desde la falla hasta el arranque.
- **Valor ajustado:** ________

### Calentamiento antes de tomar carga  (s)

- **En DSE:** Timers · warm up
- **Que hace:** Tiempo en vacio antes de cerrar KM2.
- **Como decidir:** Lo que pide el fabricante del motor; cero si la carga es de emergencia.
- **Si queda mal:** Largo: carga sin energia. Cero en motor frio: humo y caida de f.
- **Como se comprueba:** Medir del arranque al cierre de KM2.
- **Valor ajustado:** ________

### Tiempo muerto de transferencia  (s)

- **En DSE:** Timers · transfer time / breaker interlock
- **Que hace:** Tiempo con ambos contactores abiertos al pasar de una fuente a otra.
- **Como decidir:** Mayor que cero y que el tiempo de apertura del contactor; mas si hay motores grandes (tension residual).
- **Si queda mal:** Cero o menor que la apertura: red y grupo en paralelo un instante.
- **Como se comprueba:** Osciloscopio o registro en las bobinas KM1/KM2.
- **Valor ajustado:** ________

### Retardo de retorno de red  (s)

- **En DSE:** Timers · mains return delay
- **Que hace:** Cuanto debe estar estable la red antes de retransferir.
- **Como decidir:** Mayor que el retardo de falla: confirmar que la red volvio de verdad.
- **Si queda mal:** Corto: ida y vuelta varias veces si la red esta inestable.
- **Como se comprueba:** Historial: transferencias seguidas.
- **Valor ajustado:** ________

### Enfriamiento  (s)

- **En DSE:** Timers · cooling
- **Que hace:** Tiempo en vacio despues de retransferir, antes de parar.
- **Como decidir:** Lo que pide el fabricante del motor (turbo).
- **Si queda mal:** Cero: el turbo se queda sin aceite caliente; dano al rodamiento.
- **Como se comprueba:** Medir de la retransferencia a la parada.
- **Valor ajustado:** ________

## Salidas

### Salida «cerrar red» / «abrir red»  (salida)

- **En DSE:** Outputs · close mains output
- **Que hace:** Que salida del modulo mueve KM1.
- **Como decidir:** La que este cableada al rele K1; con el contacto NC de KM2 en serie.
- **Si queda mal:** Salida invertida (abrir en vez de cerrar): la carga queda sin red con red buena.
- **Como se comprueba:** Forzar la salida desde el modulo con la potencia aislada.
- **Valor ajustado:** ________

### Salida «cerrar grupo» / «abrir grupo»  (salida)

- **En DSE:** Outputs · close generator output
- **Que hace:** Que salida del modulo mueve KM2.
- **Como decidir:** La cableada al rele K2; con el NC de KM1 en serie.
- **Si queda mal:** Igual que la anterior.
- **Como se comprueba:** Forzar la salida con la potencia aislada.
- **Valor ajustado:** ________

## Entradas

### Auxiliares de KM1 y KM2  (entrada)

- **En DSE:** Inputs · mains / generator closed auxiliary
- **Que hace:** Confirmacion al modulo de que cada contactor cerro.
- **Como decidir:** Activas si estan cableadas; dan alarma de falla de contactor.
- **Si queda mal:** Sin ellas el modulo no detecta un contactor que no cerro.
- **Como se comprueba:** Abrir el contactor a mano: el modulo debe alarmar.
- **Valor ajustado:** ________

## Programacion

### Prueba programada (ejercicio)  (dia/hora)

- **En DSE:** Scheduler · exercise
- **Que hace:** Arranque periodico del grupo, con o sin carga.
- **Como decidir:** Semanal o segun el plan de mantenimiento; con carga si es posible.
- **Si queda mal:** Sin ejercicio: la falla del grupo aparece el dia del corte.
- **Como se comprueba:** Historial: ejercicios registrados.
- **Valor ajustado:** ________
