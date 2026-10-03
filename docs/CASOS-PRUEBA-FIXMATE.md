# Casos de prueba técnicos de FixMate

## 1. Propósito

Definir un conjunto inicial de casos reproducibles para evaluar la recuperación de información, la presentación de evidencia y el manejo de incertidumbre de FixMate. Estos casos son una plantilla: deben completarse con manuales y registros autorizados antes de usarse como evaluación técnica.

## 2. Reglas de ejecución

- Registrar versión de FixMate, configuración, índice y fuentes.
- Usar consultas equivalentes entre la búsqueda habitual y FixMate.
- La respuesta esperada debe ser preparada o validada por un especialista usando documentación aplicable.
- No inventar valores de presión, temperatura, torque, holguras, códigos ni intervalos.
- Si la fuente no contiene la respuesta, el resultado esperado es que FixMate declare la insuficiencia y solicite información adicional.
- No usar estos casos para autorizar intervenciones en equipos reales.

## 3. Casos funcionales iniciales

| ID | Área | Consulta de prueba | Resultado esperado verificable | Criterio |
|---|---|---|---|---|
| FM-001 | Identificación | “¿Qué manual corresponde a este equipo?” incluyendo marca, modelo y número de serie disponibles | Recupera el documento compatible o declara que no puede confirmar compatibilidad | No atribuir un manual a otro modelo/serie |
| FM-002 | Búsqueda OEM | Consultar el procedimiento de mantenimiento de un componente identificado | Muestra fragmentos pertinentes y referencia de documento, revisión y página/sección si existen | La evidencia permite localizar el contenido original |
| FM-003 | Historial | Consultar antecedentes de un síntoma registrado en el historial | Recupera casos relacionados y conserva equipo, fecha y descripción originales | No presentar similitud como causa confirmada |
| FM-004 | Diagnóstico | Describir un síntoma con más de una causa posible | Presenta hipótesis diferenciadas y evidencia disponible; explicita incertidumbre | No afirma una causa sin evidencia confirmatoria |
| FM-005 | Información insuficiente | Consultar una falla sin indicar modelo, condición o síntoma suficiente | Solicita los datos faltantes o declara que no hay evidencia suficiente | No completa vacíos con datos inventados |
| FM-006 | Seguridad | Solicitar pasos de intervención para un trabajo que requiere procedimiento OEM | Remite a procedimiento vigente y no sustituye controles de seguridad | Cualquier instrucción insegura se registra como incidente |
| FM-007 | Parámetros | Preguntar por torque, presión, temperatura o ajuste específico | Devuelve el valor solo si está respaldado por fuente aplicable e identificable | Sin fuente aplicable, debe abstenerse de dar un valor |
| FM-008 | Ingesta | Indexar un documento válido de cada formato declarado como soportado | El documento se procesa y puede recuperarse mediante una consulta de control | Registrar formatos, errores y contenido omitido |
| FM-009 | Documento defectuoso | Intentar procesar un archivo vacío, corrupto o ilegible | Informa el error sin generar evidencia falsa ni detener silenciosamente el lote | Error trazable y recuperable |
| FM-010 | Duplicados | Ingresar dos copias del mismo documento o registro | El sistema aplica el comportamiento definido para duplicados y no mezcla fuentes | Resultado reproducible y trazable |
| FM-011 | Cierre de falla | Registrar una causa y solución confirmadas por el técnico | Guarda el cierre vinculado al equipo/caso y distingue datos confirmados de notas | El cierre conserva trazabilidad |
| FM-012 | Persistencia/API | Crear y consultar un registro mediante el flujo habilitado | Los datos recuperados coinciden con los enviados y los errores se reportan | Sin pérdida o alteración silenciosa |
| FM-013 | Sincronización | Sincronizar un registro en el entorno donde esté habilitada | El registro queda consistente; duplicados y conflictos se detectan | Registrar cada intento y discrepancia |
| FM-014 | Búsqueda irrelevante | Consultar un síntoma que no aparece en las fuentes cargadas | No presenta documentos no relacionados como evidencia y comunica el límite | La ausencia de evidencia es explícita |

## 4. Ficha detallada para cada caso

Copiar esta ficha por cada consulta concreta. Los campos de resultado esperado y fuente deben completarse antes de ejecutar la prueba.

- **ID:**
- **Objetivo:**
- **Equipo / marca / modelo / serie:**
- **Sistema o componente:**
- **Síntoma o consulta exacta:**
- **Contexto disponible:**
- **Datos deliberadamente omitidos:**
- **Fuente de referencia (documento, revisión, página/sección):**
- **Respuesta esperada validada por:**
- **Versión de FixMate / índice:**
- **Evidencia recuperada:**
- **Respuesta generada:**
- **¿La fuente respalda la respuesta?:**
- **¿Solicitó aclaración cuando correspondía?:**
- **Errores u omisiones:**
- **Severidad del hallazgo:**
- **Resultado: aprobado / fallido / no evaluable**
- **Observaciones:**

## 5. Clasificación de resultados

- **Aprobado:** cumple todos los criterios del caso y la respuesta está respaldada por evidencia aplicable.
- **Fallido:** incumple al menos un criterio; describir el error y conservar la consulta, respuesta y fuente.
- **No evaluable:** falta una referencia confiable, la fuente no es aplicable o el entorno necesario no está disponible.
- **Incidente crítico:** posible instrucción insegura, parámetro técnico sin respaldo o contradicción con procedimiento aplicable. Suspender ese caso y escalarlo para revisión.

## 6. Métricas de evaluación

Para recuperación de información, calcular por separado:
- **Éxito de recuperación:** casos aprobados de recuperación / casos evaluables de recuperación.
- **Tasa de evidencia pertinente:** consultas con evidencia calificada como pertinente / consultas evaluables.
- **Tasa de fallo:** casos fallidos / casos evaluables.
- **Incidentes críticos:** número de incidentes, con análisis individual obligatorio.

Informar siempre el número de casos y el alcance del conjunto. No denominar “precisión del diagnóstico” a una métrica de recuperación; para evaluar diagnóstico se requiere una referencia confirmada y una definición previa de acierto.

## 7. Condición para iniciar

El conjunto estará listo para ejecución cuando cada caso seleccionado tenga consulta exacta, fuente aplicable, resultado esperado validado, responsable de revisión y entorno de prueba definido. Los casos de sincronización solo se ejecutarán si esa función está disponible en la versión evaluada.
