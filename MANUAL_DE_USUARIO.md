# Manual de usuario · FixMate

**Sistema de confiabilidad y mantenimiento para flotas de maquinaria pesada**

| | |
|---|---|
| **Versión del documento** | 1.0 |
| **Fecha** | 2026-10-09 |
| **Alcance** | El paquete `nefer/fixmate/`, sus cuatro pantallas publicadas y la interfaz de línea de comandos `nefer fixmate` |
| **Dirigido a** | Administradores del sistema y jefes de mantenimiento · Técnicos de mantenimiento en planta · Operadores de maquinaria |
| **Documentos relacionados** | [`docs/MANUAL-ARMAR.md`](docs/MANUAL-ARMAR.md) · [`docs/MANUAL-RONDA-CIL.md`](docs/MANUAL-RONDA-CIL.md) · [`docs/MANUAL-ANALISIS-RCM.md`](docs/MANUAL-ANALISIS-RCM.md) · [`docs/MANUAL-FIXMATE.md`](docs/MANUAL-FIXMATE.md) · [`docs/AUDITORIA-RCM-TPM.md`](docs/AUDITORIA-RCM-TPM.md) |

---

> [!IMPORTANT]
> **Cómo leer este manual.** Describe lo que el sistema hace hoy, verificado
> comando por comando. Donde una función de uso corriente en un software de
> mantenimiento **no existe** en FixMate, el manual lo dice en su sitio en vez
> de callarlo — con un recuadro `[!WARNING]` y, cuando corresponde, qué dato
> haría falta para tenerla.
>
> Esto no es modestia: un manual que promete lo que el sistema no hace se
> convierte en un compromiso con el cliente, y el que queda mal frente a él es
> quien lo leyó. Las secciones 3.2, 3.3, 4 y 6 contienen vacíos declarados.
> Léalas antes de prometer nada.

---

## Tabla de contenido

1. [Introducción y propósito del sistema](#1-introducción-y-propósito-del-sistema)
2. [Guía de inicio rápido](#2-guía-de-inicio-rápido)
3. [Módulos del sistema y flujos de trabajo](#3-módulos-del-sistema-y-flujos-de-trabajo)
   - [3.1 Registrar y gestionar maquinaria](#31-registrar-y-gestionar-maquinaria)
   - [3.2 Crear, asignar y cerrar una orden de trabajo](#32-crear-asignar-y-cerrar-una-orden-de-trabajo)
   - [3.3 Programar un mantenimiento preventivo](#33-programar-un-mantenimiento-preventivo)
   - [3.4 Reportar una avería o falla crítica](#34-reportar-una-avería-o-falla-crítica)
4. [Interpretación de KPIs y reportes](#4-interpretación-de-kpis-y-reportes)
5. [Preguntas frecuentes y solución de problemas](#5-preguntas-frecuentes-y-solución-de-problemas)
6. [Matriz de roles y permisos](#6-matriz-de-roles-y-permisos)
7. [Glosario](#7-glosario)

---

## 1. Introducción y propósito del sistema

### 1.1 Qué problema resuelve

En un taller de maquinaria pesada, lo que se sabe de una máquina está repartido
en tres sitios que no se hablan: el **historial de fallas** en un Excel, los
**manuales del fabricante** en PDF, y la **cabeza del técnico con más años**.
Cuando ese técnico está de descanso, el equipo vuelve a diagnosticar desde cero
una falla que ya se resolvió tres veces.

FixMate cose esos tres sitios y añade los dos marcos que convierten la
experiencia en un plan: **RCM** (confiabilidad, SAE JA1011) y el **primer pilar
de TPM** (mantenimiento autónomo).

### 1.2 Los cuatro módulos, y a quién sirve cada uno

| Módulo | Dónde corre | Para quién | Qué hace |
|---|---|---|---|
| **Armar** | Computadora de oficina | Jefe de mantenimiento, planificador | Escribe la pauta de la ronda y el análisis RCM. De aquí salen los archivos que abren los otros dos |
| **Ronda CIL** | Teléfono del operador | Operador de maquinaria | La ronda de limpieza, inspección y lubricación del arranque de turno. Sin señal |
| **Análisis RCM** | Tableta o laptop, en mesa de trabajo | Equipo de confiabilidad | Lleva cada modo de falla por el árbol de decisión de JA1011 y muestra el camino |
| **Diagnóstico** | Teléfono o laptop, en el patio | Técnico de mantenimiento | Pregunta por una falla en lenguaje de taller y recibe antecedentes del historial y de los manuales, con su cita |
| **Línea de comandos** | Servidor u oficina | Administrador del sistema | Indexa, valida, exporta la matriz FMECA, calcula indicadores, levanta la API |

### 1.3 Las tres reglas de la casa

Son decisiones de diseño, no limitaciones temporales. Explican la mayoría de
los «¿por qué no me deja…?» de la sección 5.

> [!NOTE]
> **1. Si no hay evidencia, no se inventa.** Cada afirmación del sistema cita
> de dónde sale: un informe del historial, una sección de manual, una entrada
> del catálogo. Lo que no tiene respaldo aparece como hueco declarado, nunca
> como dato.
>
> **2. `None` no es cero.** Un indicador que no se puede calcular se muestra
> como *sin dato*, no como `0`. Un tablero que marca 0 % de cumplimiento
> cuando aún no hay ninguna ronda está diciendo «lo hicieron mal» cuando lo
> que pasa es que no hay dato — y es la forma más rápida de que un tablero deje
> de mirarse.
>
> **3. Nada sale del equipo.** No hay servicio en la nube. El motor y el índice
> son de biblioteca estándar; las pantallas trabajan en el navegador. Lo que
> viaja, viaja en archivos `.json` que usted mueve por WhatsApp, correo o red
> interna.

### 1.4 Lo que FixMate **no** es

> [!WARNING]
> - **No es un ERP ni un GMAS/CMMS completo.** No hay módulo de almacén, ni de
>   compras, ni de costos, ni de personal.
> - **No hay mantenimiento predictivo por sensores.** No lee telemetría ni
>   vibración en línea. Lo «predictivo» de FixMate es estadística sobre el
>   historial de fallas.
> - **No hay autenticación ni control de acceso.** Ver la sección 6 completa
>   antes de exponer nada en red.
> - **No valida el juicio técnico.** Verifica que las siete preguntas de JA1011
>   estén respondidas; no puede juzgar si están *bien* respondidas. Eso es el
>   equipo en la sala, y es lo que la norma pide.

---

## 2. Guía de inicio rápido

### 2.1 Requisitos previos

| Perfil | Qué necesita |
|---|---|
| **Operador de maquinaria** | Un teléfono Android y, una sola vez, señal para instalar. Nada más |
| **Técnico en planta** | Un teléfono o laptop con navegador. Opcionalmente el archivo `fixmate-app.html` recibido por WhatsApp |
| **Administrador del sistema** | Python **3.10 o superior**. Las dependencias base son `openpyxl` y `pillow` |

Dependencias opcionales, cada una para una cosa concreta:

| Extra | Instala | Para qué |
|---|---|---|
| `fixmate-api` | `fastapi`, `uvicorn` | Levantar la API HTTP (`fixmate servir`) |
| `fixmate-pg` | `psycopg2-binary` | Usar PostgreSQL con pgvector en vez del índice en archivo |
| `fixmate-docs` | `pypdf` | Mejor respeto de la disposición de página al leer PDF. El lector propio funciona sin esto |
| `dev` | `pytest`, `fastapi`, `httpx`, `psycopg2-binary`, `pyyaml` | Correr la suite de pruebas |

### 2.2 Instalación

```bash
git clone https://github.com/nilthonnn/nefer
cd nefer
pip install -e .                      # base
pip install -e ".[fixmate-api]"       # si va a servir la API
```

Verifique que quedó instalado:

```bash
python3 -m nefer fixmate --help
```

### 2.3 Primeros pasos según su perfil

#### Operador de maquinaria — 2 minutos

1. En el teléfono, abra **<https://nilthonnn.github.io/nefer/fixmate/ronda/>**
2. Toque el botón **INSTALAR** de la barra superior. Queda como una app en la
   pantalla de inicio.
3. Desde ese momento **abre sin señal**, que es la condición real: interior
   mina, y el turno no espera a que haya línea.
4. Si la política de la mina no permite instalar desde el navegador, descargue
   el `.apk` desde los [releases del repositorio](https://github.com/nilthonnn/nefer/releases?q=fixmate-ronda&expanded=true).

> [!NOTE]
> **Permisos del `.apk`, completos**, porque es lo que va a preguntar seguridad
> informática de la mina:
>
> | Permiso | Estado |
> |---|---|
> | `INTERNET` | **No se pide.** La ronda no habla con nadie: todo viaja dentro del APK y lo que el operador registra se queda en el teléfono hasta que él mismo lo exporte |
> | `WRITE_EXTERNAL_STORAGE` | Se pide **sólo en Android 9 y anteriores** (`maxSdkVersion="28"`), para poder guardar el archivo de la ronda. Desde Android 10 se guarda en Descargas por MediaStore, que no pide permiso |
>
> Ningún otro. Es comprobable en la ficha de la aplicación y en
> `movil/fixmate-ronda/android/app/src/main/AndroidManifest.xml`.

#### Técnico de mantenimiento — 5 minutos

1. Abra **<https://nilthonnn.github.io/nefer/fixmate/app/>** e instálela igual.
2. Cargue el índice que le pase la oficina (un `.json`). Queda guardado en el
   teléfono para la próxima vez.
3. Escriba la falla como se la contaría a un compañero:
   *«humo negro y pierde fuerza en la subida»*.

#### Administrador del sistema — 15 minutos

```bash
# 1. Indexar lo que ya tiene: historial en Excel, manuales en PDF o Word
python3 -m nefer fixmate -i indice.json indexar historial.xlsx manuales/ actas/

# 2. Ver qué quedó dentro y qué tan bien recupera
python3 -m nefer fixmate -i indice.json estado

# 3. Probar una consulta real
python3 -m nefer fixmate -i indice.json consultar \
    "humo negro y pierde fuerza en la subida" --dtc P0300

# 4. Los indicadores del historial
python3 -m nefer fixmate -i indice.json tablero
```

Para montar un taller completo de prueba, con datos ficticios y todos los
comandos corridos de seguida:

```bash
python3 herramientas/demo-fixmate.py --dir /tmp/taller
```

> [!CAUTION]
> **El `-i` va antes del subcomando, no después.** Es la opción global que
> indica qué índice usar:
>
> ```bash
> python3 -m nefer fixmate -i indice.json rcm listar   # correcto
> python3 -m nefer fixmate rcm listar -i indice.json   # ERROR
> ```
>
> Sin `-i`, se usa `indice-fixmate.json` del directorio actual.

### 2.4 Mapa de comandos

```
nefer fixmate
├── indexar      historial, manuales y actas → índice
├── estado       qué hay en el índice y qué tan bien aprende
├── consultar    preguntar por una falla
├── predecir     qué le va a pasar a un equipo, según lo que ya le pasó
├── cerrar       registrar la falla resuelta en el historial y en el índice
├── recibir      meter en el historial lo que el teléfono cerró en faena
├── tablero      MTBF y recurrencia sobre el historial cargado
├── servir       levantar la API HTTP
├── subir / sql  índice en PostgreSQL con pgvector
├── rcm
│   ├── analizar    validar un análisis contra las siete preguntas
│   ├── taxonomia   los nueve niveles de ISO 14224 del análisis
│   ├── listar      los modos de falla del índice
│   ├── matriz      exportar la matriz FMEA/FMECA en CSV
│   └── tareas      el plan que sale del análisis
└── tpm
    ├── checklist   validar una pauta
    ├── ejecutar    registrar una ronda
    └── pendientes  anomalías abiertas
```

---

## 3. Módulos del sistema y flujos de trabajo

### 3.1 Registrar y gestionar maquinaria

#### Cómo funciona realmente

> [!WARNING]
> **No existe un comando de alta de activos ni un padrón de maquinaria.** No
> hay `fixmate activos crear`. El activo no es una ficha que se registra: es un
> **código que aparece dentro de los documentos**, y FixMate lo reconoce donde
> lo encuentra.

El activo entra al sistema por tres vías, y las tres usan el mismo código:

| Vía | Dónde se escribe | Quién |
|---|---|---|
| **El análisis RCM** | Pantalla **Armar** → sección «El activo» | Jefe de mantenimiento |
| **La pauta de ronda** | Pantalla **Armar** → campo «Código del activo» | Jefe de mantenimiento |
| **El historial** | Columna `codigo_equipo` del Excel, o el bloque `HISTORIAL EQUIPO : XXX` | Ya existe en sus archivos |

#### Campos del activo

Se escriben en **Armar → Nuevo análisis RCM → El activo**:

| Campo | Obligatorio | Nota |
|---|---|---|
| `codigo` | **Sí** | El que está pintado en la máquina. **No se genera**: lo pone el taller |
| `nombre` | **Sí** | |
| `marca`, `modelo`, `serie` | No | |
| `categoria` | No | La familia. Sirve para preferir antecedentes de máquinas parecidas cuando no hay de la misma |
| `instalacion` | No | La obra o unidad minera. Es el **nivel 3 de ISO 14224** y el único de los de localización que cambia por activo en una flota que se mueve |
| `contexto` | No | Texto libre a propósito: ningún enum captura «turno continuo en interior mina, 4.200 m, con polvo de sílice» |

> [!CAUTION]
> **El código del activo es la única llave entre los módulos.** Si el historial
> dice `EX-220-03`, la pauta dice `EX220-03` y el análisis dice `ex 220 03`,
> FixMate los tratará como **tres máquinas distintas**: el MTBF se calculará
> sobre un tercio de las fallas, y las anomalías de la ronda no engancharán con
> ningún modo de falla. Fije el formato del código **antes** de cargar nada y
> documéntelo.

#### El activo y el contexto operacional

> [!IMPORTANT]
> El análisis RCM está amarrado al activo **y a su contexto**, no al activo
> solo. La misma bomba en dos contextos son **dos análisis**. Copiar uno sobre
> el otro sin reconfirmarlo es el atajo que llena los planes de tareas que no
> aplican.
>
> Por eso «Armar» avisa cuando el contexto queda vacío: sin él declarado,
> copiar el análisis sobre otra máquina parece legítimo.

#### Ver qué activos conoce el sistema

```bash
python3 -m nefer fixmate -i indice.json estado --archivos
python3 -m nefer fixmate -i indice.json predecir --flota
python3 -m nefer fixmate rcm taxonomia analisis.json      # la taxonomía ISO 14224
```

---

### 3.2 Crear, asignar y cerrar una orden de trabajo

> [!WARNING]
> **FixMate no tiene una entidad «Orden de Trabajo».** No hay creación, no hay
> asignación a un técnico, no hay cambio de estado desde la interfaz, no hay
> bandeja de trabajo y no hay notificaciones.
>
> Lo que sí existe son **dos registros distintos** que cubren parte de ese
> flujo. Esta sección documenta los dos y marca exactamente dónde se corta cada
> uno, para que nadie construya un procedimiento sobre un paso que no existe.

#### 3.2.1 La anomalía — el ciclo de vida que sí existe

Es lo más cercano a una orden de trabajo. **Nace en la ronda del operador**,
cuando un punto sale NOK.

**Estados** (cuatro):

| Estado | Significado | ¿Cuenta como abierta? |
|---|---|---|
| `abierta` | Registrada, nadie la tomó | Sí |
| `en_proceso` | Alguien está en ella | Sí |
| `cerrada` | Resuelta, con acción y responsable | No |
| `descartada` | Se revisó y no era una anomalía | No |

**Severidad** — es la prioridad, y la pone el sistema a partir de la pauta:

| Severidad | Significado |
|---|---|
| `detiene` | Se detiene la máquina ahora |
| `programable` | Se atiende en la próxima ventana |
| `oportunidad` | Cuando se abra una ocasión |

**Campos de trazabilidad:** `detectada_por`, `fecha`, `punto_id`,
`condicion_observada`, `codigo_catalogo`, `modo_falla_id`, `responsable`,
`accion`, `fecha_cierre`, y `dias_abierta()` calculado.

**Flujo real, paso a paso:**

```bash
# 1. El operador hace la ronda en el teléfono y marca un punto como ANOMALÍA.
#    Escribe en sus palabras qué vio. El teléfono genera la anomalía con su
#    severidad y la exporta en el .json de la ronda.

# 2. La oficina recibe ese .json y lo procesa, cruzándolo con el análisis RCM
python3 -m nefer fixmate tpm ejecutar \
    -p pauta-ex220.json \
    --rcm analisis-ex220.json \
    ronda-del-telefono.json
```

Salida real de ese comando:

```
cil-ex220-2026-03-16-A · EX-220 · (operador del turno A)
5/5 puntos · 3 OK · 1 NOK · 1 sin ver · 33 s de 31
Ronda INCOMPLETA
  Un punto que no se pudo ver no cuenta como visto: la ronda no vale como
  completa aunque esten los demas.

cil-ex220-2026-03-16-A.cil-ex220.1 · programable · El panal esta tapado con
  tierra, no pasa la luz por el tercio inferior
   modo F1.1.1
```

> [!NOTE]
> Esa salida es de los archivos de ejemplo del repositorio
> (`ejemplos/rcm-tpm/`), corrida tal cual. La excavadora EX-220 es un equipo
> inventado y los nombres están en blanco a propósito: sirve para ver cómo
> funciona, no para firmar nada.

Esa última línea es el valor del cruce: la anomalía **engancha con su modo de
falla** del análisis, por código de catálogo y no por parecido de texto.

```bash
# 3. Listar lo que sigue abierto
python3 -m nefer fixmate -i indice.json tpm pendientes
```

> [!WARNING]
> **Dónde se corta.** `tpm pendientes` es **sólo de lectura**, y **no hay
> comando para cerrar una anomalía ni para asignarla**. El cambio de estado
> existe en la biblioteca (`Anomalia.cerrar(accion, responsable)`) pero no está
> expuesto en la línea de comandos ni en ninguna pantalla.
>
> **Procedimiento recomendado mientras eso no exista:** lleve la asignación y
> el cierre en su sistema actual (la OT en papel o el ERP), y use FixMate para
> lo que sí hace: **detectar** la anomalía en campo con trazabilidad de quién y
> cuándo, y **enlazarla** con el modo de falla analizado.

#### 3.2.2 El cierre del diagnóstico — donde el campo alimenta al sistema

Esto sí es un flujo completo, y es el que hace que el sistema no envejezca.
Cuando el técnico resuelve una falla, la registra **desde la misma herramienta
con la que consultó**.

```bash
python3 -m nefer fixmate -i indice.json cerrar \
    --equipo GE074-01 \
    --falla "humo negro y pierde fuerza en la subida" \
    --causa "filtro de aire primario colmatado" \
    --solucion "reemplazo de filtro primario y secundario, limpieza de carcasa" \
    --dtc P0300 \
    --horometro 2050 \
    --ot 001-0042245 \
    --paso "verificar indicador de restriccion" \
    --paso "reemplazar P533781 y P533782" \
    --repuesto "P533781" --repuesto "P533782" \
    --herramienta "llave de filtro"
```

| Campo | Obligatorio | Nota |
|---|---|---|
| `--falla`, `--causa`, `--solucion` | **Sí** | Un informe sin causa ni solución no es un antecedente: es una queja |
| `--ot` | No | **El código de la orden de trabajo.** Si no lo pone, se genera un correlativo del año |
| `--equipo`, `--categoria`, `--dtc`, `--horometro` | No | |
| `--paso`, `--herramienta`, `--repuesto` | No | Repetibles |

> [!NOTE]
> El informe se añade **al historial en disco y al índice que ya está
> cargado**, de modo que la siguiente consulta —la del compañero que está a
> cuarenta kilómetros— ya lo encuentra.
>
> **Una OT repetida se rechaza.** Duplicaría la evidencia y haría contar dos
> veces lo que pasó una.

Lo que se cerró en el teléfono sin señal llega después:

```bash
python3 -m nefer fixmate -i indice.json recibir envio-del-telefono.json
```

#### 3.2.3 Resumen de la cobertura

| Paso de un flujo de OT | ¿Existe en FixMate? | Dónde |
|---|---|---|
| Detectar la novedad en campo | **Sí** | Ronda CIL (operador) |
| Clasificar por prioridad | **Sí** | Severidad automática desde la pauta |
| Enlazar con el modo de falla analizado | **Sí** | `tpm ejecutar --rcm` |
| Diagnosticar antes de intervenir | **Sí** | Pantalla de diagnóstico / `consultar` |
| **Crear una OT como registro propio** | **No** | — |
| **Asignar a un técnico** | **No** | — |
| **Cambiar el estado desde la interfaz** | **No** | Sólo desde la biblioteca |
| Registrar el cierre con causa y solución | **Sí** | `cerrar` / `recibir` |
| Dejar trazado quién y cuándo | **Sí** | `detectada_por`, `operador`, `responsable` |
| **Notificar o escalar** | **No** | — |

---

### 3.3 Programar un mantenimiento preventivo

> [!WARNING]
> **FixMate no tiene calendario, ni vencimientos automáticos, ni avisos.** No
> envía correos, no genera OT programadas y no bloquea nada por atraso.
>
> Lo que hace es **decirle qué tarea corresponde, por qué, y cuándo toca según
> el uso real del equipo**. Poner eso en un calendario es un paso suyo.

Hay tres caminos, y se complementan.

#### 3.3.1 Desde el análisis RCM — qué tarea corresponde y por qué

El árbol de decisión de JA1011 produce la **estrategia**, y de la estrategia
sale la tarea.

```bash
python3 -m nefer fixmate rcm tareas analisis-con-decisiones.json
```

Salida real:

```
4 tareas · 0 listas · 4 en borrador

T001-F1.1.1 · cbm (condicion)
   modo F1.1.1 · panal del radiador
   falta: que se hace, en una frase imperativa
   falta: que parametro se mide
   falta: el limite y su fuente: tiene que venir del OEM o de un estandar, no de esta herramienta
   falta: el procedimiento, o la referencia al del OEM

T002-F1.1.2 · descarte (intervalo)
   modo F1.1.2 · embrague viscoso
   falta: que se hace, en una frase imperativa
   falta: cada cuanto: el analisis dice que existe un intervalo, no cual es. Hay que medirlo
   falta: el procedimiento, o la referencia al del OEM

T003-F1.1.3 · busqueda_fallas (intervalo)
   modo F1.1.3 · valvula de alivio
   falta: que se hace, en una frase imperativa
   falta: cada cuanto: el analisis dice que existe un intervalo, no cual es. Hay que medirlo
   falta: el procedimiento, o la referencia al del OEM

T004-F2.1.1 · rediseno (proyecto)
   ...
```

Las cuatro estrategias que se ven ahí son las cuatro salidas posibles del
árbol: `cbm` a condición, `descarte` por intervalo, `busqueda_fallas` para la
falla oculta, y `rediseno` cuando con consecuencia de seguridad no hay tarea
proactiva que sirva.

> [!IMPORTANT]
> **Esos «falta» son el producto, no un defecto.** Una tarea sale **en
> borrador** y no es «aplicable» hasta que no le falte nada. El sistema se
> niega a inventar el intervalo y el límite, porque el límite tiene que venir
> del OEM o de un estándar — y un límite inventado se mete en un plan y nadie
> vuelve a preguntar de dónde salió.
>
> Una tarea es **aplicable** (se puede poner en un calendario sin inventar
> nada) sólo cuando la lista de faltantes está vacía.

#### 3.3.2 Desde el historial — cuándo toca, según el uso real

```bash
python3 -m nefer fixmate -i indice.json predecir GE074-01
```

Salida real:

```
EQUIPO GE074-01 · 3 registros fechados

USO
  5.71 h/dia (3 lecturas en 238 dias); horometro 2050.0 al 2026-07-08

PROXIMO SERVICIO
  2500 h: faltan 56.0 h (~10 dias, 2026-09-25)

MTBF
  119 dias entre fallas, en promedio

LO QUE LE VUELVE A PASAR
  VENCIDA · Filtro de aire colmatado
      2 casos · cada ~122 dias · ultima 2026-03-14 (hace 185 dias)
  Inyector con retorno excesivo o goteo
      1 casos · sin intervalo aun · ultima 2026-07-08 (hace 69 dias)

REPUESTOS QUE CONVIENE TENER
  · Filtro de aire primario P533781
  · Filtro de aire secundario P533782

  aviso: Solo 3 registros de este equipo. Tomelo como lo que es: una señal debil.
```

| Qué leer | Cómo usarlo |
|---|---|
| **PROXIMO SERVICIO** | Fecha estimada a partir de horas/día reales y el horómetro. Es lo que va al calendario |
| **VENCIDA** | La causa ya debió volver y no se ha registrado. Revísela antes de que se detenga la máquina |
| **REPUESTOS** | Lo que esta máquina consumió en fallas anteriores. Para tenerlo en bodega antes |
| **aviso** | Cuántos registros respaldan el pronóstico. Con tres, es una señal débil y el sistema lo dice |

#### 3.3.3 La ronda autónoma — el preventivo que hace el operador

La pauta de ronda es el preventivo de todos los días, y se escribe en **Armar**.
Frecuencias disponibles:

| Frecuencia | Cuándo usarla |
|---|---|
| `por_turno` | **La que de verdad se ejecuta.** Al arranque del turno |
| `diaria` | |
| `semanal`, `quincenal`, `mensual` | |
| `por_horas` | Atada al horómetro, no al calendario |

**Verificar la pauta desde la oficina** antes de mandarla al teléfono. La
pantalla «Armar» ya valida mientras se escribe, pero este comando es el que
usa quien recibe una pauta hecha por otro:

```bash
python3 -m nefer fixmate tpm checklist pauta-ex220.json
```

```
cil-ex220 · EX-220 · Ronda de arranque de turno
5 puntos · por_turno · presupuesto 31 s
  cil-ex220.1 limpiar       Panal del radiador, lado admision  [operador] Se ve
    la luz a traves del panal; sin costra de tierra que tape celdas
  cil-ex220.3 verificar     Pedal de freno, antes de salir del taller [TECNICO]
    El pedal hace tope firme a media carrera y la maquina retiene en rampa
```

> [!NOTE]
> Fíjese en la etiqueta `[TECNICO]` del punto 3: ese punto **no está al alcance
> del operador**, y la ronda lo marca para que la anomalía salga dirigida al
> técnico. Se decide al escribir la pauta, en frío, por quien conoce el
> bloqueo, la herramienta y el repuesto — preguntárselo al operador en campo,
> con la máquina parada, garantiza la respuesta cómoda.

> [!NOTE]
> La pauta autónoma es la herramienta de mantenimiento con mejor relación
> costo/beneficio que existe, y también **la que se degrada más rápido, siempre
> igual: deja de ejecutarse y empieza a firmarse.** A los tres meses la
> planilla está impecable y la máquina igual de sucia.
>
> Contra eso, FixMate **mide el tiempo de cada punto**. Una pauta de treinta
> segundos despachada en cuatro no se ejecutó: se firmó. El sistema lo detecta
> y se lo dice al supervisor al final — no al operador a mitad de la máquina.

#### 3.3.4 Procedimiento recomendado para armar el programa

1. **Armar** → análisis RCM del activo crítico (función → falla funcional →
   modo de falla).
2. **Pantalla de Análisis RCM** → el equipo contesta las siete preguntas con el
   árbol a la vista.
3. `rcm tareas` → la lista de tareas con sus huecos.
4. **Complete los huecos con el manual del OEM.** Este es el paso que el
   sistema no puede hacer por usted, y es deliberado.
5. **Meta el análisis al índice** (ver 3.3.5). Sin este paso, el análisis existe
   como archivo y el resto del sistema no lo ve.
6. `predecir` por equipo → la fecha del próximo servicio y las reincidencias
   vencidas.
7. Lleve los puntos 4 y 6 a su calendario o a su ERP.
8. Lo que sea del alcance del operador, páselo a la pauta en **Armar**.

#### 3.3.5 El eslabón que se olvida: meter el análisis al índice

> [!IMPORTANT]
> Un análisis validado sigue siendo **un archivo suelto** hasta que se indexa.
> Mientras no se haga, `rcm listar`, la ruta `/rcm` de la API y la recuperación
> del análisis desde una consulta de campo **no lo ven**.

```bash
python3 -m nefer fixmate -i indice.json rcm analizar analisis.json \
    --indexar --hoy 2026-09-15
```

| Opción | Qué hace |
|---|---|
| `--indexar` | Mete los modos de falla al índice, para que el motor los recupere |
| `--hoy AAAA-MM-DD` | Comprueba además si la revisión del análisis está **vencida** |

Salida real de ese comando sobre el análisis de ejemplo:

```
Registro: El analisis esta identificado y es auditable.
  [observacion] 2 de 4 modos no tienen codigo de catalogo: no se agregan con
  los de la flota ni se enganchan con la ronda.

4 modos de falla indexados. Ahora una consulta de campo los recupera como
cualquier otro antecedente.
```

Y recién entonces:

```bash
python3 -m nefer fixmate -i indice.json rcm listar
```

```
4 modos de falla analizados

EQUIPO     MODO       SISTEMA     ESTRATEGIA                       CRITICIDAD  ESTADO
EX-220     F1.1.1     termico     Mantenimiento segun condicion    alta        validado
EX-220     F1.1.2     termico     Descarte programado              media       propuesto
EX-220     F1.1.3     termico     Busqueda de fallas               alta        propuesto
EX-220     F2.1.1     frenos      Rediseño o cambio de ingenieria  alta        propuesto
```

> [!NOTE]
> Fíjese en la observación de la salida: **2 de 4 modos sin código de catálogo**
> no se agregan con los de la flota ni se enganchan con la ronda. Es el mismo
> aviso que explica la mayoría de los casos de «las anomalías no enganchan» de
> la sección 5.3.

---

### 3.4 Reportar una avería o falla crítica

#### 3.4.1 Si usted es el operador — una anomalía desde la ronda

1. Abra la **Ronda CIL** y cargue la pauta del equipo.
2. Escriba su nombre o ficha. **Una ronda sin responsable no se puede discutir
   después.**
3. En cada punto, tres botones del **mismo tamaño**:

| Botón | Cuándo |
|---|---|
| **OK** | Cumple el criterio escrito en pantalla |
| **ANOMALÍA** | Algo no está como debe. Se le pedirá escribir qué vio, en sus palabras |
| **NO PUDE VER** | Guarda cerrada, máquina en marcha, andamio desarmado |

> [!IMPORTANT]
> **«No pude ver» mide exactamente lo mismo que «OK» y está en la misma
> columna.** Si fuera más chico o estuviera más abajo, el operador marcaría OK,
> y un OK falso contamina la ronda entera.
>
> Un «no pude» registrado **es un dato**; un OK falso es una mentira que se
> arrastra meses. Una ronda con un punto sin ver **no está completa**, y el
> sistema lo dice así.

4. Al terminar, **Guardar el archivo de la ronda** y mándelo a la oficina por
   WhatsApp o correo.

> [!NOTE]
> **Lo que escriba no se normaliza.** Escríbalo como se lo contaría a un
> compañero. La oficina es la que lo casa con el catálogo; el teléfono no lo
> hace porque ahí no está el análisis.

#### 3.4.2 Si usted es el técnico — una falla en el patio

1. Abra la **pantalla de diagnóstico** y describa la falla:
   *«humo negro y pierde fuerza en la subida»*. Si el tablero dio un código,
   agréguelo.
2. Lea los antecedentes. **Cada uno viene con su cita**: qué informe, qué
   sección de manual, qué equipo y cuándo.
3. **Lea las precauciones antes de tocar.** El sistema las deduce de los
   sistemas que el propio procedimiento nombra: si los pasos hablan de un
   cilindro hay energía hidráulica almacenada; si hablan del arranque, energía
   eléctrica.

> [!CAUTION]
> Las precauciones vienen rotuladas en dos clases, y la diferencia importa:
>
> - **Lo que dice el manual indexado** — copiado literal y citado. Es evidencia.
> - **La regla de la herramienta** — una precaución fija que no afirma nada
>   sobre *esta* máquina: dice qué hay que verificar antes de intervenir.
>
> **Nada de esto reemplaza al manual OEM ni al procedimiento de bloqueo del
> taller**, y el propio texto lo dice en voz alta.

4. Resuelto, regístrelo con `cerrar` (sección 3.2.2) o desde la app de campo,
   que lo guarda y lo manda cuando haya señal.

#### 3.4.3 Si la falla es crítica

> [!WARNING]
> **FixMate no escala, no notifica y no avisa a nadie.** No hay alertas por
> correo, ni SMS, ni guardia. Una anomalía `detiene` queda registrada con esa
> severidad y **espera a que alguien mire el archivo**.
>
> El aviso inmediato de una falla crítica sigue siendo por radio o por teléfono,
> como hasta ahora. FixMate aporta el **registro trazable** y el enlace con el
> análisis, no la comunicación urgente.

Con consecuencia de seguridad, lo que el sistema sí hace es negarse a una
salida:

> [!CAUTION]
> Si un modo de falla tiene **consecuencia de seguridad o ambiental** y ninguna
> tarea proactiva reduce el riesgo a un nivel tolerable, el árbol de decisión
> **no ofrece «operar hasta la falla» por ninguna vía**: el dictamen es
> **rediseño obligatorio**. No es una opción de configuración.

---

## 4. Interpretación de KPIs y reportes

```bash
python3 -m nefer fixmate -i indice.json tablero
```

### 4.1 Los tres tableros

| Tablero | Quién lo mira | Qué contiene |
|---|---|---|
| **Confiabilidad** | Jefe de mantenimiento | MTBF por equipo, fallas, lecturas fechadas, reincidencias vencidas |
| **RCM** | Jefe de confiabilidad | Activos analizados, modos, modos graves, ocultos, validados, completitud, tareas por estrategia |
| **TPM** | Supervisor de producción | Pautas, ejecuciones, completas, sospechosas, cumplimiento, anomalías abiertas/cerradas, días medios de cierre |

### 4.2 MTBF — sí se calcula

**Mean Time Between Failures.** Días promedio entre fallas, sobre base
calendario, por equipo.

Salida real:

```
Equipos con historial: 8
Fallas registradas:    18

MTBF por equipo (dias entre fallas, base calendario):
  EX336-01      34 d
  EX336-03      81 d
  GE074-01     119 d
  GE074-02     134 d
  GE074-03      24 d
  TI09-02       12 d
  TI09-04      139 d
  (1 sin MTBF: con una sola aparicion no hay intervalo, hay una fecha)

MTTR y disponibilidad: sin dato. FixMate registra cuando ocurrio una falla,
no cuanto duro la reparacion. Un MTTR inventado se usa para dimensionar
un taller, asi que no se calcula.

Reincidencias vencidas: 2
```

> [!IMPORTANT]
> **«Fallas registradas» cuenta sólo lo que tiene causa.** Un historial de
> verdad trae, además de órdenes de trabajo, actas de recepción y guías de
> remisión: la máquina entrando y saliendo. Eso no es una avería, y contarlo
> como tal diría «245 fallas» de un equipo de alquiler que se despacha varias
> veces al año sin que se le rompa nada.
>
> Lo fechado sin causa sale aparte, como **«Otras lecturas fechadas»**: no son
> averías, pero su fecha y su horómetro son una **lectura**, y de las lecturas
> salen el ritmo de uso y la fecha del próximo servicio. «No es una falla» no
> es «no sirve».

| Cómo leerlo | |
|---|---|
| **MTBF bajo** (TI09-02, 12 d) | Falla cada doce días. Candidato número uno a un análisis RCM |
| **MTBF alto** | O es confiable, o **no se está registrando lo que le pasa**. Compruebe contra las horas trabajadas antes de celebrar |
| **«sin MTBF»** | Una sola aparición. **No hay intervalo, hay una fecha.** El equipo no aparece en la lista en vez de mostrar un número inventado |

> [!CAUTION]
> El MTBF de FixMate es **sobre base calendario**, no sobre horas de operación.
> Un equipo parado dos meses y un equipo en doble turno dan MTBF comparables
> aunque su exposición a la falla sea muy distinta. Para decisiones de
> inversión, cruce el MTBF con las horas/día que reporta `predecir`.

### 4.3 MTTR y disponibilidad — **no se calculan, a propósito**

> [!WARNING]
> El tablero lo dice con estas palabras:
>
> ```
> MTTR y disponibilidad: sin dato. FixMate registra cuando ocurrio una falla,
> no cuanto duro la reparacion. Un MTTR inventado se usa para dimensionar
> un taller, asi que no se calcula.
> ```
>
> Los campos existen en la estructura de datos y devuelven `null`. **No es un
> error ni una función pendiente de conectar: es una negativa deliberada.**

**Por qué.** El MTTR (*Mean Time To Repair*) exige saber cuánto duró cada
reparación. La disponibilidad exige además cuántas horas estuvo la máquina
detenida. El historial que FixMate indexa registra **cuándo** ocurrió la falla
—fecha, horómetro, causa, solución—, no la duración de la intervención.
Derivar el MTTR de lo que hay obligaría a suponer la duración, y un MTTR
supuesto se usa para dimensionar dotación de taller y para prometer
disponibilidad en un contrato.

**Qué haría falta para tenerlos.** Dos marcas de tiempo por intervención que
hoy no se capturan:

| Dato | Para qué |
|---|---|
| Hora de parada y hora de entrega del equipo | MTTR real |
| Horas calendario del período, y horas detenido | Disponibilidad = (tiempo disponible ÷ tiempo total) |

Mientras no se capturen, quien necesite esos dos indicadores debe tomarlos de
su sistema de gestión actual. FixMate no los va a contradecir, porque no los
produce.

### 4.4 Indicadores de TPM — la ronda

| Indicador | Qué mide | Cómo leerlo |
|---|---|---|
| `cumplimiento` | Fracción de rondas completadas | `null` si todavía no hay ninguna ronda. **No es 0 %** |
| `ejecuciones_completas` | Rondas sin ningún punto «sin ver» | Una ronda con un punto no visto **no es completa** |
| `ejecuciones_sospechosas` | Rondas despachadas por debajo del 40 % del presupuesto de tiempo | **Criterio configurable de planta, no normativo.** Es la firma sin ejecución |
| `puntos_nunca_vistos` | Puntos que ninguna ronda pudo ver | No es descuido del operador: es un defecto de la máquina o de la pauta |
| `anomalias_abiertas` | `abierta` + `en_proceso` | |
| `dias_medios_de_cierre` | Promedio de días abierta de las cerradas | `null` sin anomalías cerradas |
| `anomalias_sin_enlazar` | Anomalías que no engancharon con ningún modo de falla | Mide el **techo del catálogo**, no un error del operador |

> [!IMPORTANT]
> `ejecuciones_sospechosas` es el indicador que hay que mirar primero, y no se
> mira solo: una ronda marcada sospechosa **no es prueba de que se firmó**. Es
> una señal para ir a conversar, y el umbral del 40 % es un criterio de su
> planta que puede ajustar.

### 4.5 Indicadores de RCM — el análisis

| Indicador | Qué leer |
|---|---|
| `completitud` | Fracción de análisis con las siete preguntas contestadas. `null` sin ningún análisis |
| `modos_graves` | Con consecuencia de seguridad o ambiental. **Son los que no admiten «operar hasta la falla»** |
| `modos_ocultos` | Fallas que no se notan al ocurrir. Su tratamiento por defecto es **búsqueda de fallas**, porque el riesgo real es la **falla múltiple** |
| `modos_validados` | Con evidencia declarada. Un modo «validado» **sin** evidencia no se puede guardar: es una opinión con sello |
| `modos_sin_criticidad` | Sin evaluar. El método de criticidad es configurable de planta y vive en la oficina |
| `por_estrategia` | Cuántas tareas cayeron en cada estrategia del árbol |

> [!NOTE]
> **Sobre el RPN.** Si viene de una metodología FMEA clásica, note que FixMate
> **no usa el Número de Prioridad de Riesgo**. El RPN es estadísticamente
> indefendible —multiplica escalas ordinales— y el propio manual AIAG-VDA de
> 2019 lo reemplazó por una tabla de prioridad de acción. FixMate sigue esa
> tabla, y si usted carga valores de severidad/frecuencia/detección, los
> muestra con el nombre del método y una advertencia, sin multiplicarlos.

### 4.6 Exportar reportes

| Reporte | Comando | Formato |
|---|---|---|
| Matriz FMEA/FMECA | `fixmate rcm matriz analisis.json -o matriz.csv` | CSV, **30 columnas**, una fila por modo de falla |
| Taxonomía ISO 14224 | `fixmate rcm taxonomia analisis.json --csv` | CSV, una fila por modo con sus nueve niveles |
| Plan de tareas | `fixmate rcm tareas analisis.json` | Texto, con los huecos declarados |
| Indicadores en JSON | `fixmate predecir --flota --json` | JSON |
| Vía API | `GET /tablero` | JSON |

> [!NOTE]
> En la taxonomía, los niveles que FixMate **no modela** (4 planta/unidad,
> 5 sección, 9 parte) salen **vacíos y dichos**, no omitidos. Una flota móvil
> no tiene planta estable y el frente cambia de turno a turno; está escrito en
> el propio módulo para quien llegue a necesitarlos.

---

## 5. Preguntas frecuentes y solución de problemas

### 5.1 Operadores de maquinaria

**La app no abre / se quedó en blanco.**
Ciérrela del todo y vuelva a abrirla. Si sigue, desinstálela y vuelva a
instalarla desde el enlace: la pauta se vuelve a cargar, no se pierde nada —
las rondas ya exportadas están en los archivos que mandó.

**No tengo señal en el socavón.**
No hace falta. La ronda funciona completa sin red; sólo necesitó señal el día
que la instaló. El archivo se manda cuando salga.

**Marqué OK por error en un punto.**
Dentro del mismo punto, el diálogo de la nota tiene **Volver**. Si ya avanzó,
termine la ronda y avise al supervisor: el archivo es el registro y no se
corrige después, a propósito.

**No pude ver un punto. ¿Marco OK para no perjudicar la ronda?**
**No.** Marque **NO PUDE VER** y escriba el motivo. Un «no pude» es un dato
honesto que detecta un defecto de la máquina o de la pauta. Un OK falso
contamina la ronda entera y se arrastra meses.

**Toco «Abrir pauta del equipo» y no pasa nada.**
Si está usando el **`.apk`**, actualícelo: hasta la versión 1.7 inclusive, el
botón no abría el selector de archivos. No era un fallo del teléfono ni de la
pauta — la aplicación no implementaba el selector, así que no abría nada y
tampoco avisaba. Descargue la versión más reciente desde los
[releases](https://github.com/nilthonnn/nefer/releases?q=fixmate-ronda&expanded=true).
En el navegador el botón siempre funcionó.

**Elegí mi Excel y me dice que no es la pauta.**
Correcto: la pauta es un archivo **`.json`** que le pasa mantenimiento, y lo
genera la pantalla **Armar**. El Excel es el historial, y ése va en la app de
diagnóstico, no en la ronda.

**Me pide el nombre y no quiero firmar.**
La ronda necesita responsable porque sin él no se puede discutir después. No es
para culpar a nadie: es para que cuando usted encuentre algo, conste que usted
lo encontró.

### 5.2 Técnicos de mantenimiento

**La consulta no devuelve nada útil.**
Describa la falla como se la contaría a un compañero, con dos o tres síntomas:
«humo negro y pierde fuerza en la subida» recupera mejor que «falla motor». Si
el tablero dio un código, agréguelo con `--dtc`.

**Me devuelve antecedentes de otra máquina.**
Es deliberado cuando no hay de la misma: busca en la familia. Acote con
`--equipo` o `--categoria`.

**La causa aparece en blanco en un modo de falla que tiene código de catálogo.**
No es un hueco: la oficina hereda causa y mecanismo del catálogo. La pantalla
lo distingue de un campo realmente vacío.

**¿Puedo confiar en el procedimiento que me da?**
Confíe en la **cita**, no en el texto. Cada afirmación dice de dónde sale. Y
ninguna precaución del sistema reemplaza al manual OEM ni al bloqueo del
taller.

### 5.3 Administradores y jefes de mantenimiento

**`fixmate tpm ejecutar` dice «la ejecucion necesita responsable» y el archivo
sí lo tiene.**
Ya corregido. El archivo del teléfono es un envoltorio
(`{ejecucion, anomalias, estado}`) y el cargador no lo desenvolvía, por lo que
el error señalaba la causa equivocada. Actualice a la versión actual del
repositorio.

**El análisis dice «5/7 contestadas» y yo las contesté todas.**
Las dos pendientes serán Q6 y Q7: faltan **decisiones de estrategia** por modo.
Tener el esqueleto completo —funciones, fallas, modos, consecuencias— responde
cinco; las otras dos salen de llevar cada modo por el árbol en la pantalla de
Análisis RCM.

**No me deja marcar un modo como «validado».**
Le falta evidencia. Un modo validado sin evidencia es una opinión con sello.
Agregue al menos una referencia con su fuente.

**«Armar» no me deja bajar el archivo.**
Mire el panel fijo de abajo y toque **ver qué falta**. Lo **rojo** detiene el
archivo porque el resto de FixMate lo rechazaría; lo **ámbar** sólo avisa y no
traba nada. Lo más común: una función sin estándar de desempeño.

**¿Por qué me exige el estándar de desempeño?**
Porque una función sin estándar no se puede fallar de forma verificable, y de
ella no sale ningún modo de falla útil. Es el único campo del análisis que se
exige además de las descripciones.

**Puse «oculta» como consecuencia y me lo rechaza.**
«Oculta» no es una consecuencia: es la **primera bifurcación** del análisis. Va
en el campo «¿La falla se nota cuando ocurre?». El mensaje de error se lo
indica.

**Cargué el Excel del taller y salen muy pocos fragmentos.**
El export del sistema del taller trae **seis** tipos de documento, cada uno
con su cabecera repetida: `ORDEN TRABAJO`, `INFORME TECNICO CAMPO`,
`HOJA DE SERVICIO`, `ACTA DE RECEPCION`, `GUIA DE REMISION` y
`CONTROL_EXTRACCIONES`. FixMate lee los seis y dice de cuál salió cada
informe, en `otros_campos.Documento`. Si su export trae un séptimo con otro
rótulo, se descartará en silencio: avísenos con el nombre exacto de la
cabecera y se agrega.

**El historial cargó pero dice «0 casos con causa confirmada».**
Es correcto y es honesto: ese export no trae una columna de causa raíz —en
trece años de historia de una máquina, nadie la escribió—. Lo que sí trae es
**lo que se encontró y lo que se hizo**, y eso se indexa y se recupera con su
cita. El clasificador de causas necesita 12 casos con causa confirmada; esos
se van juntando a medida que el equipo cierra fallas con `fixmate cerrar`,
que sí pide causa.

> [!NOTE]
> Consecuencia práctica: sin causas confirmadas **no hay MTBF** para ese
> equipo, porque `mtbf()` sólo cuenta eventos con causa. Las búsquedas sí
> funcionan desde el primer archivo cargado.

**El MTBF de un equipo no aparece.**
Tiene una sola aparición con causa en el historial. Con una sola no hay
intervalo, hay una fecha.

**El cumplimiento TPM sale vacío y no en 0 %.**
Es correcto: todavía no hay ninguna ronda registrada. `null` significa «no hay
dato», no «lo hicieron mal».

**Las anomalías no enganchan con los modos de falla.**
Tres causas, por frecuencia: (1) el punto de la pauta no declara
`codigo_catalogo`; (2) el código del activo no coincide entre pauta, ronda y
análisis; (3) el análisis no declara ningún modo con ese código. El comando
dice el motivo de cada una que no engancha.

**Cambié una pantalla y lo publicado sigue igual.**
Las pantallas se **generan**. Corra
`python3 .claude/skills/espejo/scripts/espejo.py --regenerar`. Si tocó la app de
diagnóstico, rehaga además el archivo suelto con
`python3 herramientas/empaquetar-fixmate.py`.

**El teléfono se quedó con la versión vieja de una pantalla instalada.**
No debería: el nombre del caché lleva la huella de la página. Si pasa, abra la
pantalla una vez con señal.

**¿Puedo exponer la API en internet?**
**No.** Ver la sección 6.3.

### 5.4 Mensajes de error frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| `la pauta necesita «id» y «activo_codigo»` | Falta el código del activo | Complételo en «Armar» |
| `clase «detectar anomalias» desconocida` | «Detectar anomalías» no es una clase de punto: es lo que pasa cuando un punto sale NOK | Use una de las cinco con criterio verificable |
| `falta el criterio de aceptacion` | Un punto sin criterio no mide nada | Escriba un criterio decidible sin instrumento |
| `el codigo «X» no esta en el catalogo` | Código inventado | Elíjalo de la lista; no se escribe a mano |
| `la fecha «03/04/2026» no esta en formato ISO 8601` | Fecha ambigua: en Lima es 3 de abril, en Houston 4 de marzo | Use `AAAA-MM-DD` |
| `no se puede marcar validado sin evidencia` | — | Agregue una referencia con su fuente |
| `la funcion necesita estandar de desempeño` | — | Agregue el estándar, con número |
| `una orden de trabajo repetida` | Ya existe un informe con esa OT | Use otro código o revise el existente |

---

## 6. Matriz de roles y permisos

> [!WARNING]
> **FixMate no tiene autenticación, ni usuarios, ni roles, ni control de
> acceso.** No hay inicio de sesión, no hay contraseñas, no hay permisos
> configurables, y la API HTTP **no exige credencial alguna**.
>
> La matriz que sigue es una **matriz de responsabilidades operativas**: dice
> quién *debe* hacer cada cosa y con qué herramienta. **No describe un control
> técnico.** Cualquiera que tenga el archivo o la URL puede hacer todo lo que
> esa pantalla hace.

### 6.1 Matriz de responsabilidades operativas

Leyenda: **E** ejecuta · **C** consulta · **—** no le corresponde

| Función | Admin / Jefe de mantenimiento | Técnico en planta | Operador de maquinaria |
|---|---|---|---|
| Indexar historial y manuales (`indexar`) | **E** | — | — |
| Ver estado y calidad del índice (`estado`) | **E** | C | — |
| Consultar una falla (`consultar`, pantalla de diagnóstico) | C | **E** | — |
| Ver precauciones antes de intervenir | C | **E** | — |
| Registrar el cierre de una falla (`cerrar`) | C | **E** | — |
| Recibir lo cerrado en faena (`recibir`) | **E** | — | — |
| Escribir la pauta de ronda («Armar») | **E** | C | — |
| Ejecutar la ronda (Ronda CIL) | — | C | **E** |
| Exportar el archivo de la ronda | — | — | **E** |
| Procesar la ronda (`tpm ejecutar`) | **E** | — | — |
| Escribir el análisis RCM («Armar») | **E** | C | — |
| Contestar el árbol de decisión (pantalla RCM) | **E** | **E** | C |
| Validar el análisis (`rcm analizar`) | **E** | — | — |
| Exportar matriz FMECA (`rcm matriz`) | **E** | C | — |
| Generar el plan de tareas (`rcm tareas`) | **E** | C | — |
| Completar intervalos y límites del OEM | **E** | **E** | — |
| Ver indicadores (`tablero`, `predecir`) | **E** | C | — |
| Listar anomalías abiertas (`tpm pendientes`) | **E** | C | — |
| Levantar la API (`servir`) | **E** | — | — |
| Administrar PostgreSQL (`subir`, `sql`) | **E** | — | — |

### 6.2 Separación real: por superficie y por archivo

Como no hay permisos, la separación efectiva es de otra naturaleza, y conviene
entenderla porque es la que de verdad opera:

| Mecanismo | Cómo funciona | Qué limita de hecho |
|---|---|---|
| **Por superficie** | Cada perfil usa una pantalla distinta, y cada pantalla sólo hace lo suyo | El operador tiene la ronda instalada; no tiene «Armar» ni la línea de comandos |
| **Por archivo** | Lo que viaja son `.json` que alguien mueve a mano | Si no le pasan la pauta, no hay ronda que hacer |
| **Por herramienta** | La validación, la matriz y los indicadores son de línea de comandos | Requiere acceso al servidor o a la máquina de la oficina |
| **Por traza de autoría** | `detectada_por`, `operador`, `facilitador`, `aprobado_por`, `responsable` | No impide nada: **documenta** quién hizo qué |

> [!CAUTION]
> La traza de autoría es **declarativa**: el operador escribe su nombre, no se
> autentica. Sirve para discutir una ronda después, no para probar quién la
> hizo. Si necesita no repudio, hace falta autenticación, y hoy no existe.

### 6.3 Recomendaciones de despliegue seguro

> [!CAUTION]
> **La API HTTP (`fixmate servir`) no tiene autenticación.** Sus rutas
> —`/search-report-rag`, `/informes`, `/prediccion`, `/rcm`, `/tpm/anomalias`,
> `/tablero`— quedan abiertas a cualquiera que alcance el puerto. `/informes`
> **escribe** en el historial.
>
> Mientras no exista control de acceso:
> 1. **No la exponga a internet.** Déjela en `127.0.0.1` o detrás de VPN.
> 2. Si necesita acceso en red, póngala detrás de un proxy inverso que exija
>    autenticación (nginx con *basic auth* o su SSO) y no publique el puerto
>    directamente.
> 3. Trate el índice (`indice-fixmate.json`) como **información del cliente**:
>    lleva dentro su historial de fallas y sus manuales.
> 4. Restrinja por sistema de archivos y por red quién corre la línea de
>    comandos: cualquiera que la corra puede escribir en el historial.

### 6.4 Sobre los datos del cliente

> [!IMPORTANT]
> Los archivos de FixMate pueden contener **nombre del cliente, obra o unidad
> minera, y nombres de técnicos**. El historial que se indexa suele traerlos.
>
> Trátelos con el mismo cuidado que el resto de la documentación del contrato:
> no los suba a repositorios públicos, no los adjunte a tickets de soporte y no
> los mezcle con los datos de ejemplo del repositorio, que son ficticios a
> propósito.

---

## 7. Glosario

| Término | Significado |
|---|---|
| **Activo** | Una máquina de la flota, identificada por el código pintado en ella |
| **Anomalía** | Un hallazgo de la ronda: algo que no cumple el criterio. Tiene estado, severidad y responsable |
| **Catálogo de fallas** | Las 41 entradas con las que FixMate clasifica. Estructura tomada de ISO 14224; **los códigos son propios de FixMate**, no de la norma |
| **CIL** | Limpieza, Inspección y Lubricación. El contenido de la ronda autónoma |
| **Criterio de aceptación** | Lo que decide si un punto está OK. Tiene que decidirse **sin instrumento** |
| **Falla funcional** | Cómo el activo deja de cumplir una función. Pérdida total y parcial son dos fallas distintas |
| **Falla múltiple** | Lo que de verdad se teme en una falla oculta: la protección falló *y* después falla lo que protegía |
| **Falla oculta** | La que no se nota cuando ocurre. Primera bifurcación del análisis RCM |
| **FMECA** | Análisis de modos de falla, efectos y criticidad. La matriz de 30 columnas |
| **Función** | Lo que el activo debe hacer, con el estándar que lo vuelve verificable |
| **ISO 14224** | Norma de recolección e intercambio de datos de confiabilidad. Edición 2016 (3.ª), confirmada 2022 |
| **Jishu Hozen** | Mantenimiento autónomo. El primer pilar de TPM, y lo único de TPM que FixMate cubre |
| **Modo de falla** | Lo que produce la falla funcional. **El nivel donde se decide la tarea** |
| **MTBF** | Tiempo medio entre fallas. En FixMate, días calendario |
| **SAE JA1011** | Criterios de evaluación de procesos RCM. Las siete preguntas. Edición 1999, rev. 2009 |
| **Severidad** | La prioridad de una anomalía: `detiene`, `programable`, `oportunidad` |
| **TPM** | Mantenimiento Productivo Total. **Ocho pilares**; FixMate cubre el primero |

---

### Trazabilidad de este manual

Cada afirmación de este documento se verificó contra el código y la salida real
de los comandos a la fecha indicada en la portada. Las secciones que declaran
una ausencia —3.2 (no hay entidad de orden de trabajo), 3.3 (no hay calendario
ni avisos), 4.3 (no hay MTTR ni disponibilidad), 6 (no hay autenticación ni
roles)— se comprobaron leyendo los módulos correspondientes, no por omisión.

Si una versión posterior agrega alguna de esas funciones, **este manual queda
desactualizado en esa sección y hay que corregirlo ahí**. La fecha de la
portada es lo que dice hasta cuándo se puede confiar en él.
