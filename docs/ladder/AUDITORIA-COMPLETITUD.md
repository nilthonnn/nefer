# Auditoría de completitud de LadderLab

Revisión, pedido por pedido, de todo lo solicitado para LadderLab desde el
primer mensaje: qué se entregó, cómo se comprobó y qué queda pendiente. Se
verificó contra el estado actual del repositorio, de las descargas y de GitHub,
no contra la memoria de lo hecho.

Fecha: 20 de noviembre de 2026. Rama `ccr-2f7a751b-yz17rd`, pull request #47.

- [1. Resumen](#1-resumen)
- [2. Pedido por pedido](#2-pedido-por-pedido)
- [3. Inventario de la app](#3-inventario-de-la-app)
- [4. Entregables y su estado](#4-entregables-y-su-estado)
- [5. Lo que esta auditoría encontró y corrigió](#5-lo-que-esta-auditoría-encontró-y-corrigió)
- [6. Lo que queda pendiente](#6-lo-que-queda-pendiente)

---

## 1. Resumen

| | |
|---|---|
| Pedidos revisados | 13 |
| Completos | **12** |
| Completo con una condición externa | 1: la dirección web depende de fusionar el PR #47 |
| Lecciones / retos | **32 / 28**; todas con teoría, ejemplo y cuestionario |
| Retos que pasan con su solución, con ciclos exactos e irregulares | **28 / 28** |
| Retos cuyo programa inicial no pasa | **28 / 28** |
| Retos con guía «¿Cómo se resuelve?» escrita a mano | **28 / 28** (antes de esta auditoría eran 18) |
| Defectos encontrados y corregidos en esta revisión | 5 (sección 5) |

---

## 2. Pedido por pedido

| # | Pedido | Entregado | Evidencia | Estado |
|---|---|---|---|---|
| 1 | App para aprender Ladder de Siemens TIA Portal, de básico a avanzado | 32 lecciones en 6 niveles, PLC simulado con ciclo de scan, editor LAD, retos autocorregidos, referencia de instrucciones | Inventario (sección 3) | ✅ |
| 2 | Tomar lo mejor de las mejores apps y enfocarla en grupos electrógenos y minería (Quellaveco), con ejercicios de sincronismo de grupos en paralelo y TTA grupo‑red | Ruta «Mina: energía y planta»; gamificación (XP, rangos, racha, 14 insignias); modelos de planta con HMI. Retos de sincronismo con sincronoscopio, reparto de carga, arranque por demanda, TTA y tablero TTA | Retos `sincronismo`, `reparto`, `demanda`, `tta`, `tta3_*` | ✅ |
| 3 | Auditoría funcional según normas internacionales | `AUDITORIA-FUNCIONAL.md`: IEC 61131‑3, IEEE 1547/C50.13, NFPA 110, IEC 60947‑6‑1, ISO 13850, EN 620, WCAG 2.2 y otras | Documento y sus pruebas | ✅ |
| 4 | Corregir las no conformidades y entregar demo descargable con manual de uso | No conformidades cerradas; manual HTML y PDF (29 páginas); `LadderLab-demo.zip` | `descargas/` | ✅ |
| 5 | Abrir el pull request | PR #47 abierto y fusionable | GitHub | ✅ |
| 6 | Enlace de descarga | Enlaces del .zip, del PDF y del archivo único | Descargas verificadas byte a byte | ✅ |
| 7 | «No lo puedo abrir en Android»: auditoría de funcionalidad, operatividad, descargas e instalación | Causa encontrada (`content://`); APK, archivo único y botón «Instalar». `AUDITORIA-ANDROID.md` | 15 pruebas en emulación de Android | ✅ |
| 8 | «No se pudo descargar en mi celular» | Servidor verificado (200, tipo APK, adjunto); el APK enviado en el chat; código QR; instrucciones para Chrome y Play Protect | Descarga con agente Android | ✅ (sin confirmación desde un teléfono real) |
| 9 | Versión para PC con Windows | Instalador `LadderLab-Setup.exe`, probado instalando, abriendo con Edge y desinstalando en Windows | Flujo `windows-ladderlab.yml` en verde | ✅ |
| 10 | Copiar la integración de la imagen (fajas, sensores, cilindro) para aprender, con retos, y mejorar la app | Nivel «Proyectos integradores»: línea de transferencia con modelo de planta y 4 retos; corrector con ciclos irregulares | 21 pruebas | ✅ |
| 11 | Adaptar a Quellaveco (TTA, automatización, sincronismo de grupos de mina) y crear la opción «cómo resolver el reto» con explicación y teoría | Bloque estándar de motor de mina; recuadro «⛏ En la mina» en las 10 lecciones de la ruta; botón «💡 ¿Cómo se resuelve?» con estrategia, teoría y la solución paso a paso en todos los retos | 26 pruebas | ✅ |
| 12 | Un modelo del tablero de la foto, de básico a avanzado | Nivel «Tablero de transferencia»: LED de estado (básico), mando manual con llave Local/Remoto (intermedio) y transferencia automática con 3 interruptores (avanzado) | Retos `tta3_*` | ✅ |
| 13 | Enlaces del APK y del instalador | APK v5 e instalador v3, compilados desde la última versión y enviados | Releases `ladderlab-v5` y `ladderlab-windows-v3` | ✅ |
| — | Dirección web pública | `nilthonnn.github.io/nefer/ladder/` | Depende de fusionar el PR y de GitHub Pages | ⏳ |

---

## 3. Inventario de la app

| Nivel | Lecciones | Retos | Con modelo de planta |
|---|---:|---:|---:|
| Básico | 6 | 4 | — |
| Intermedio | 5 | 5 | — |
| Avanzado | 4 | 2 | — |
| Proyectos integradores | 4 | 4 | 4 |
| Tablero de transferencia | 3 | 3 | 2 |
| Mina: energía y planta | 10 | 10 | 10 |
| **Total** | **32** | **28** | **16** |

La lección de luces del tablero usa el HMI sin modelo: las señales las mueve el
alumno.

Se comprobó automáticamente, para todo el inventario:
- ninguna lección sin teoría, ejemplo o cuestionario;
- ningún reto que falle con su solución (en los dos modos de ciclo) o que pase con su programa inicial;
- ninguna lección de la ruta de mina sin recuadro «En la mina» ni sin el aviso de escenario de ejemplo;
- ninguna nota de la guía que apunte a un segmento inexistente.

---

## 4. Entregables y su estado

| Entregable | Versión | Estado |
|---|---|---|
| APK Android | `ladderlab-v5` (2,7 MB) | Compilado desde la última versión, contenido verificado, sin permiso de INTERNET |
| Instalador Windows | `ladderlab-windows-v3` (4,1 MB) | Instalado, abierto con Edge (32 lecciones y 28 retos correctos) y desinstalado en la integración |
| App en un archivo | `descargas/LadderLab.html` | Generada desde la app; probada sola, sin archivos al lado |
| Demo `.zip` | `descargas/LadderLab-demo.zip` | Reproducible byte a byte; trae el archivo único y el LEEME con instrucciones para Android y Windows |
| Manual | HTML y PDF | 15 secciones; capturas renovadas en esta auditoría |
| Auditorías | funcional, Android y esta | Las dos primeras quedan como registro de su fecha; esta las pone al día |
| Pruebas | 4 archivos `tests/test_ladder_*.py` | 107 pruebas más 5 de esta auditoría, todas aprobadas |

---

## 5. Lo que esta auditoría encontró y corrigió

### C1 · Mayor · Elementos ocultos que se veían

`.btn` fijaba `display` y pisaba el atributo `hidden`. Por eso «⤓ Instalar en
este equipo» se veía aunque el navegador no permitiera instalar (y no hacía
nada), y «+ Segmento» se veía fuera del modo edición. Lo reveló una captura
del manual.

**Corrección:** `[hidden]{display:none !important}`. La prueba
`test_lo_oculto_no_se_ve` revisa cinco pantallas.

### C2 · Menor · Diez retos solo con la explicación automática

Los retos de los niveles básico, intermedio y avanzado no tenían estrategia ni
teoría escritas a mano.

**Corrección:** ahora los 28 retos las tienen.

### C3 · Menor · Nombres viejos de la ruta

La insignia «Jefe de turno eléctrico» y la tarjeta de la ruta seguían diciendo
«Grupos y minería».

**Corrección:** ahora dicen «la mina: energía y planta», y la portada menciona
el tablero de transferencia.

### C4 · Menor · Capturas del manual desactualizadas

La pantalla de inicio mostraba 24 lecciones y el botón de instalar.

**Corrección:** las 13 capturas se rehicieron y el PDF se regeneró.

### C5 · Menor · Descripción del PR desactualizada

La descripción del PR #47 no mencionaba el APK, el instalador de Windows, los
proyectos, el tablero, la ruta de mina ni la guía.

**Corrección:** se actualizó.

---

## 6. Lo que queda pendiente

1. **Fusionar el PR #47.** Hasta entonces la dirección web no existe, y el APK
   y el instalador salen como *prepublicación*. Es una decisión del dueño del
   repositorio.
2. **Firma propia del APK.** El repositorio no tiene los secretos `ANDROID_*`.
   Cada versión nueva del APK exige desinstalar la anterior, y con ella se
   pierde el progreso. `herramientas/crear-llave-android.sh` genera la llave.
3. **Pruebas en equipos físicos.** Todo se probó en emulación (Android) y en
   una máquina Windows de la integración. Falta instalarlo en un celular y una
   PC reales y recorrer una lección y un reto.
4. **Datos reales de Quellaveco y del tablero.** Los escenarios de mina son de
   ejemplo y el tablero se modeló desde la foto de su frente. Para replicar
   equipos reales hacen falta sus planos y su lógica de control.
5. **Pendientes técnicos de la auditoría funcional:**
   - qué valor deja TIA en OUT al desbordar un Int;
   - validar el simulador contra S7‑PLCSIM;
   - simular una F‑CPU, que queda fuera del alcance.
