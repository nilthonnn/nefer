# Revisión inicial de pruebas de FixMate

## Alcance y limitación

Revisión estática de los nombres y contenidos de pruebas existentes en `tests/` y de los módulos principales de FixMate en la rama `main`. Esta revisión no ejecuta el código, no confirma que las pruebas pasen y no sustituye una revisión completa de implementación.

## Cobertura automatizada ya existente

| Área | Suite existente | Cobertura visible en las pruebas |
|---|---|---|
| Ingesta | `tests/test_fixmate_ingesta.py` | Historial JSON/Excel, actas, manuales, códigos, torques, metadatos, archivos no válidos y reindexación |
| Lectura documental | `tests/test_fixmate_documentos.py` | PDF, DOCX, XLSX, encabezados, fechas, archivos inválidos y PDF escaneado sin capa de texto |
| Índice y búsqueda | `tests/test_fixmate_indice.py` | Búsqueda léxica/vectorial, filtros, preferencias, umbral, orden estable, duplicados, persistencia y reindexación incremental |
| Motor diagnóstico | `tests/test_fixmate_motor.py` | Consulta vacía, falta de evidencia, citas de origen, causas, pasos, torques, incertidumbre y serialización |
| API | `tests/test_fixmate_api.py` | Salud, consulta, errores HTTP, validación de entrada, registro de fallas y predicción |
| Aprendizaje | `tests/test_fixmate_aprendizaje.py` | Suite específica del clasificador/aprendizaje |
| Cierre | `tests/test_fixmate_cierre.py` | Suite específica de cierre de fallas |
| Seguridad | `tests/test_fixmate_seguridad.py` | Suite específica de controles de seguridad |
| Persistencia PostgreSQL | `tests/test_fixmate_pg.py` | Suite específica del almacén PostgreSQL |

## Hallazgos de la revisión estática

1. El repositorio ya cuenta con pruebas unitarias específicas para ingesta, documentos, índice, motor y API. Conviene ampliarlas solo cuando se identifique un comportamiento no cubierto, en lugar de duplicar casos existentes.
2. La suite del motor incluye pruebas explícitas para no inventar torques ni pasos y para distinguir evidencia débil. Esas pruebas protegen comportamientos importantes, pero no prueban por sí solas la exactitud con manuales reales de cada fabricante.
3. Las pruebas de documentos generan varios archivos de prueba y contemplan fallos de lectura. La compatibilidad real debe seguir comprobándose con documentos representativos autorizados de campo.
4. Las pruebas de índice incluyen casos de búsqueda y reindexación. Para evaluar calidad de recuperación con datos reales hace falta un conjunto de consultas etiquetadas y relevancia revisada por especialistas.
5. La presencia de un archivo de prueba no demuestra que se ejecute en CI ni que pase en el entorno actual. El resultado debe registrarse con el comando, versión, dependencias y salida.

## Ejecución local recomendada

Desde la raíz del repositorio, en un entorno con dependencias de desarrollo instaladas:

```bash
python -m pytest tests/test_fixmate_documentos.py tests/test_fixmate_ingesta.py -q
python -m pytest tests/test_fixmate_indice.py tests/test_fixmate_motor.py -q
python -m pytest tests/test_fixmate_api.py -q
python -m pytest tests/test_fixmate_aprendizaje.py tests/test_fixmate_cierre.py tests/test_fixmate_seguridad.py tests/test_fixmate_pg.py -q
python -m pytest -q
```

Si alguna suite requiere servicios externos, credenciales o dependencias opcionales, registrar el motivo del salto o fallo; no marcarlo como aprobado.

## Siguiente ciclo técnico

1. Ejecutar primero las suites existentes y guardar la salida completa.
2. Corregir fallos reproducibles antes de añadir funciones.
3. Comparar cada caso de `docs/CASOS-PRUEBA-FIXMATE.md` con las pruebas existentes.
4. Añadir una prueba automatizada únicamente cuando falte cobertura de un comportamiento concreto, con datos sintéticos seguros y resultado esperado explícito.
5. Complementar las pruebas unitarias con evaluación de recuperación usando consultas y documentos OEM autorizados, revisados por un especialista.

## Estado

- Revisión estática de suites: realizada a nivel de archivos y nombres de pruebas.
- Ejecución de pytest: pendiente.
- Evaluación con manuales OEM y casos reales: pendiente.
- Validación de campo: pendiente.
