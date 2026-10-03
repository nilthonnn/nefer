# Matriz de ejecución del piloto FixMate

## 1. Propósito

Convertir los casos de prueba definidos en `docs/CASOS-PRUEBA-FIXMATE.md` en una matriz operativa para un piloto controlado. Esta matriz es una plantilla de ejecución: no contiene resultados inventados y debe completarse con fuentes OEM e historial autorizados.

## 2. Condiciones previas

Antes de ejecutar el piloto registrar:

- Versión/commit de FixMate:
- Versión del índice:
- Fecha de inicio:
- Fecha de término:
- Responsable:
- Técnicos participantes (usar códigos):
- Equipos/familias incluidos:
- Fuentes autorizadas:
- Línea base del proceso actual:
- Criterios de aceptación acordados:
- Funciones fuera de alcance:

## 3. Matriz de casos

| ID | Caso | Datos mínimos | Fuente de referencia | Resultado esperado | Evidencia registrada | Resultado |
|---|---|---|---|---|---|---|
| FM-001 | Identificación de manual | Marca, modelo, serie | Manual aplicable | Identifica o declara incompatibilidad | Pendiente | No evaluado |
| FM-002 | Búsqueda OEM | Equipo + componente + consulta | Manual/revisión/página | Recupera evidencia localizable | Pendiente | No evaluado |
| FM-003 | Historial | Síntoma + equipo | Historial autorizado | Recupera antecedentes sin convertir similitud en causa | Pendiente | No evaluado |
| FM-004 | Diagnóstico con varias causas | Síntoma + contexto | OEM + historial | Separa hipótesis y evidencia | Pendiente | No evaluado |
| FM-005 | Información insuficiente | Consulta deliberadamente incompleta | N/A | Solicita datos o declara insuficiencia | Pendiente | No evaluado |
| FM-006 | Seguridad | Trabajo sujeto a procedimiento | OEM/procedimiento de seguridad | Remite a procedimiento y no sustituye controles | Pendiente | No evaluado |
| FM-007 | Parámetros técnicos | Torque/presión/temperatura/ajuste | Fuente OEM aplicable | Solo entrega valor respaldado | Pendiente | No evaluado |
| FM-008 | Ingesta | Documento de formato soportado | Documento autorizado | Procesa y permite recuperación | Pendiente | No evaluado |
| FM-009 | Documento defectuoso | Archivo vacío/corrupto/ilegible | Archivo de prueba | Reporta error de forma trazable | Pendiente | No evaluado |
| FM-010 | Duplicados | Copias del mismo documento/registro | Mismo origen | Aplica regla definida y conserva trazabilidad | Pendiente | No evaluado |
| FM-011 | Cierre de falla | Causa y solución confirmadas | Registro validado | Guarda cierre vinculado al caso | Pendiente | No evaluado |
| FM-012 | Persistencia/API | Registro válido | API/almacén habilitado | Recupera lo enviado sin alteración silenciosa | Pendiente | No evaluado |
| FM-013 | Sincronización | Registro en entorno habilitado | Servidor/dispositivo | Detecta conflictos/duplicados | Pendiente | No evaluado |
| FM-014 | Búsqueda irrelevante | Síntoma fuera de las fuentes | Índice de prueba | Declara ausencia y no inventa evidencia | Pendiente | No evaluado |

## 4. Registro por caso

Para cada caso evaluable completar:

- ID:
- Fecha:
- Versión de FixMate:
- Código del técnico:
- Equipo/familia:
- Marca/modelo/serie:
- Síntoma y contexto:
- Consulta exacta:
- Fuente de referencia:
- Resultado de referencia validado por especialista:
- Tiempo con método habitual:
- Tiempo con FixMate:
- Evidencia recuperada:
- Pertinencia: pertinente / parcial / irrelevante / insuficiente
- Hipótesis mostradas:
- Validación técnica:
- Correcciones o rechazos:
- Incidente crítico: sí / no
- Error de ingesta/sincronización:
- Observaciones:
- Revisor:
- Resultado: aprobado / fallido / no evaluable

## 5. Reglas de evaluación

1. Un caso no se considera evaluable sin una fuente o referencia técnica aplicable cuando la métrica requiera comparar contra una respuesta conocida.
2. No registrar como “precisión” una coincidencia no validada.
3. Un parámetro técnico sin fuente aplicable se considera un hallazgo crítico para revisión.
4. Una instrucción potencialmente insegura suspende el caso y requiere revisión.
5. Separar resultados por familia de equipo, tipo de consulta y fuente.
6. Conservar consulta, respuesta, evidencia y versión para permitir reproducción.
7. No afirmar ahorros, reducción de fallas o mejora de disponibilidad a partir de este piloto sin diseño y datos que lo permitan.

## 6. Resumen de resultados

| Indicador | Fórmula/registro | Resultado |
|---|---|---|
| Casos evaluables | Conteo | Pendiente |
| Casos aprobados | Aprobados / evaluables | Pendiente |
| Tasa de evidencia pertinente | Consultas con evidencia pertinente / consultas evaluables | Pendiente |
| Tasa de fallo | Casos fallidos / casos evaluables | Pendiente |
| Incidentes críticos | Conteo y revisión individual | Pendiente |
| Tiempo habitual | Mediana + rango | Pendiente |
| Tiempo con FixMate | Mediana + rango | Pendiente |
| Correcciones/rechazos | Conteo | Pendiente |
| Errores de ingesta | Conteo | Pendiente |
| Errores de sincronización | Conteo | Pendiente |
| Uso recurrente | Participantes/sesiones | Pendiente |

## 7. Decisión del piloto

Comparar los resultados únicamente contra los criterios de aceptación definidos antes de la ejecución.

- Continuar:
- Ajustar y repetir:
- Detener/restringir:
- Principales defectos:
- Limitaciones:
- Acciones siguientes:
- Responsable:
- Fecha:

## 8. Estado actual

Esta matriz queda preparada para ejecución. No contiene resultados de campo, por lo que ningún indicador debe interpretarse como validado hasta completar el piloto.
