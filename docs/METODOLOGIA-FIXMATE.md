# Metodología de trabajo de FixMate

## 1. Propósito

Establecer una forma de trabajo ligera y verificable para evolucionar FixMate desde una herramienta de apoyo al diagnóstico hasta un producto validado en campo. Las metodologías se aplican de forma complementaria; no implican crear procesos burocráticos.

## 2. Enfoque metodológico

| Metodología | Uso en FixMate | Entregable o evidencia |
|---|---|---|
| Scrum + Kanban | Planificar y visualizar el trabajo por ciclos cortos y limitar tareas en curso | Backlog priorizado, tablero y revisión por ciclo |
| CRISP-DM | Gestionar el ciclo de vida de los datos y de los componentes de IA | Dataset documentado, evaluación y registro de versiones |
| RCM | Estructurar el conocimiento de mantenimiento y las relaciones entre fallas, causas y tareas | Taxonomía técnica y fichas de diagnóstico trazables |
| TDD | Desarrollar cambios con pruebas automatizadas desde el inicio | Pruebas reproducibles y regresión controlada |
| Lean Startup | Validar el problema, el uso y el valor del producto con usuarios reales | Hipótesis, piloto, métricas y decisiones |
| ISO/IEC 25010 | Usar características de calidad como guía de aceptación | Criterios de calidad y evidencias de prueba |

## 3. Aplicación práctica

### 3.1 Scrum + Kanban: organización del trabajo

- Mantener un backlog único, ordenado por valor para el técnico y riesgo.
- Trabajar en ciclos de una o dos semanas, según capacidad real.
- Cada tarea debe tener alcance, responsable y criterio de aceptación.
- Visualizar el flujo con estados: Pendiente, En curso, En revisión y Terminado.
- Limitar el trabajo simultáneo para evitar iniciar más de lo que se puede terminar.
- Al cierre del ciclo, revisar el incremento y registrar bloqueos y próximos pasos.

Criterio de terminado: código revisado, pruebas pertinentes ejecutadas, documentación actualizada cuando corresponda y comportamiento comprobable. No marcar como terminado solo porque compila.

### 3.2 CRISP-DM: ciclo de vida de datos e IA

Aplicar las seis fases a cada mejora relevante del diagnóstico:

1. Comprensión del negocio: definir qué decisión o tarea del técnico se quiere apoyar.
2. Comprensión de los datos: identificar fuentes, cobertura, calidad y vacíos.
3. Preparación: normalizar marcas, modelos, sistemas, síntomas, códigos, causas y soluciones; conservar la procedencia.
4. Modelado: ajustar búsqueda léxica/híbrida, embeddings o clasificación solo cuando exista una necesidad medible.
5. Evaluación: usar casos etiquetados y métricas adecuadas; separar datos de desarrollo y evaluación para reducir fuga de información.
6. Despliegue: versionar el índice/modelo y monitorear resultados, errores y cambios de datos.

Para cada evaluación, registrar conjunto de prueba, fecha, versión, métricas, errores observados y limitaciones. No presentar una muestra pequeña como validación industrial.

### 3.3 RCM: estructura del conocimiento técnico

Usar RCM como marco de dominio, no como generador automático de instrucciones. Para cada familia de equipos y sistema, documentar cuando la fuente lo permita:

- Función y falla funcional.
- Modo de falla y mecanismo, si se conoce.
- Efectos y consecuencias.
- Síntomas y comprobaciones seguras.
- Acción recomendada y condición de aplicación.
- Fuente técnica (fabricante, documento, revisión y página/sección).

Distinguir explícitamente entre causa confirmada, causa probable y dato desconocido. Las recomendaciones deben respetar el manual OEM y los procedimientos de seguridad aplicables. Si la evidencia es insuficiente o las fuentes discrepan, indicarlo y solicitar verificación técnica.

### 3.4 TDD: control de cambios

Para nuevas funciones y correcciones:

1. Definir el comportamiento esperado mediante una prueba.
2. Ejecutar la prueba y comprobar que detecta el caso pendiente.
3. Implementar el cambio mínimo.
4. Ejecutar la prueba específica y la suite de regresión pertinente.
5. Refactorizar y revisar el cambio.

Priorizar pruebas de parsers e ingesta, búsqueda y ranking, clasificación, persistencia, API y sincronización. Incluir casos límite: documentos vacíos o corruptos, datos incompletos, duplicados y errores de almacenamiento. Registrar las pruebas omitidas y su motivo.

### 3.5 Lean Startup: validación con usuarios

Realizar un piloto acotado con técnicos y un conjunto definido de equipos/documentos. Antes de empezar, establecer línea base y criterios de éxito acordados con el cliente.

Hipótesis iniciales para validar:
- El técnico encuentra antecedentes relevantes más rápido que con el proceso actual.
- El cierre estructurado mejora la trazabilidad de causa y solución.
- La respuesta presenta evidencia suficiente para apoyar la inspección, sin reemplazar el criterio técnico.

Medir, como mínimo:
- Tiempo desde la consulta hasta encontrar evidencia útil.
- Tiempo para registrar el cierre.
- Porcentaje de consultas con evidencia técnica pertinente.
- Correcciones o rechazos de recomendaciones.
- Errores y duplicados de sincronización, si aplica.
- Uso recurrente por técnico.

Los objetivos numéricos deben fijarse después de medir la línea base; no asumir ahorros ni mejoras antes del piloto. Revisar semanalmente los hallazgos y decidir continuar, modificar o descartar cada hipótesis.

### 3.6 ISO/IEC 25010: calidad del producto

Usar el modelo como lista de verificación adaptada al alcance de FixMate:

| Característica | Criterio práctico |
|---|---|
| Adecuación funcional | Los flujos principales resuelven los casos de uso definidos |
| Eficiencia de desempeño | Medir tiempos de búsqueda, respuesta e ingesta con un conjunto representativo |
| Compatibilidad | Verificar los entornos y formatos que FixMate declara soportar |
| Usabilidad | Observar si un técnico completa consulta y cierre sin ayuda excesiva |
| Fiabilidad | Probar recuperación ante errores y persistencia de registros |
| Seguridad | Revisar autenticación, autorización, exposición de datos y secretos |
| Mantenibilidad | Mantener módulos comprensibles, pruebas y revisiones de código |
| Portabilidad | Verificar instalación, configuración y operación en los entornos objetivo |

La conformidad con esta guía no equivale a certificación ISO. Los controles de seguridad, multiempresa y operación comercial requieren una revisión específica antes de ofrecer el sistema a clientes.

## 4. Orden de implementación recomendado

### Etapa 1 — Estabilizar el flujo principal
- Priorizar consulta, visualización de evidencia y cierre de falla.
- Definir criterios de aceptación para cada flujo.
- Mantener pruebas de regresión para los módulos existentes.

### Etapa 2 — Mejorar la calidad del conocimiento y la búsqueda
- Normalizar campos de equipo y falla.
- Registrar procedencia de los fragmentos recuperados.
- Evaluar relevancia con casos etiquetados y revisar errores.

### Etapa 3 — Ejecutar un piloto
- Seleccionar usuarios, equipos, fuentes y duración.
- Medir línea base y resultados con el mismo procedimiento.
- Documentar limitaciones, incidentes y comentarios de usuarios.

### Etapa 4 — Preparar operación y comercialización
- Revisar permisos, separación de datos, copias de seguridad, auditoría y recuperación.
- Definir soporte, actualización de índices y costos de operación.
- Ampliar solo cuando el piloto aporte evidencia suficiente.

## 5. Reglas de decisión

- No añadir IA avanzada si una regla simple o una mejora de datos resuelve el problema.
- No presentar una causa probable como confirmada.
- No mostrar una recomendación técnica sin conservar su fuente y contexto, cuando estén disponibles.
- No declarar una mejora de precisión, disponibilidad o ahorro sin medición reproducible.
- No desplegar cambios que afecten datos o seguridad sin pruebas y revisión.
- Priorizar los problemas que bloquean el uso real sobre las funciones atractivas pero no validadas.

## 6. Plantilla mínima para cada tarea

- Problema del usuario:
- Resultado esperado:
- Alcance y exclusiones:
- Datos o módulos afectados:
- Criterios de aceptación:
- Pruebas requeridas:
- Riesgos de seguridad o de uso técnico:
- Evidencia de validación:
- Estado y decisión:

## 7. Resultado esperado

Este marco busca que cada ciclo de FixMate produzca una mejora verificable: una función útil, datos mejor preparados, diagnósticos más trazables o mayor confiabilidad. La calidad y el valor comercial se deben demostrar mediante pruebas y pilotos, no solo por la cantidad de funcionalidades desarrolladas.
