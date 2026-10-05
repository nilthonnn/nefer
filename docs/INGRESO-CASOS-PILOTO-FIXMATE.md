# Ingreso de casos reales — Piloto FixMate

## Objetivo

Definir el paquete mínimo de información necesario para ejecutar un caso real del piloto de FixMate sin inventar datos, perder trazabilidad ni confundir una recomendación probabilística con una validación técnica.

Este documento complementa:
- `docs/PILOTO-FIXMATE.md`
- `docs/CASOS-PRUEBA-FIXMATE.md`
- `docs/MATRIZ-PILOTO-FIXMATE.md`

## 1. Paquete mínimo por caso

Antes de ejecutar una consulta real se debe disponer, como mínimo, de:

| Campo | Requerido | Descripción |
|---|---|---|
| ID del caso | Sí | Identificador único del caso |
| Equipo | Sí | Código interno o identificación del activo |
| Marca/modelo | Sí | Identificación técnica disponible |
| Fecha/hora | Sí | Momento del reporte o intervención |
| Horómetro | Si existe | Lectura disponible al momento del caso |
| Síntoma reportado | Sí | Descripción literal del operador/técnico |
| Condición observada | Sí | Evidencia disponible antes del diagnóstico |
| Historial relacionado | Si existe | Reparaciones o fallas anteriores |
| Documentación autorizada | Sí | Manual/OEM, historial u otra fuente autorizada |
| Fuente de cada dato | Sí | Archivo, registro, documento, página o ID |
| Validador técnico | Sí para cierre | Especialista que revisa el resultado |

Si un campo no está disponible, debe registrarse como **No disponible** y no completarse por inferencia.

## 2. Evidencia y trazabilidad

Para cada evidencia utilizada por FixMate registrar:

- nombre de archivo o fuente;
- versión/fecha cuando exista;
- página, sección, hoja o registro;
- identificador del registro histórico cuando exista;
- fragmento o referencia suficiente para localizar nuevamente la evidencia.

La salida debe permitir responder: **¿de dónde salió esta recomendación?**

## 3. Resultado de FixMate

Registrar por separado:

1. causas posibles;
2. pasos de diagnóstico sugeridos;
3. herramientas/repuestos sugeridos;
4. parámetros técnicos encontrados;
5. precedentes históricos relacionados;
6. nivel de confianza;
7. advertencias o información faltante.

No registrar como hecho una causa que FixMate solamente presenta como posibilidad.

## 4. Validación del especialista

El especialista debe clasificar el resultado como:

- **Pertinente:** útil y técnicamente aceptable para el caso.
- **Parcial:** contiene información útil, pero requiere corrección o complemento.
- **Incorrecto:** la recomendación no es técnicamente aceptable.
- **Sin evidencia suficiente:** las fuentes disponibles no permiten sustentar una recomendación.

Registrar además:
- corrección realizada;
- motivo de la corrección;
- fuente técnica utilizada;
- si el caso debe incorporarse como aprendizaje.

## 5. Seguridad

Ninguna recomendación de FixMate sustituye:
- procedimientos de bloqueo/etiquetado;
- permisos de trabajo;
- procedimientos de seguridad del sitio;
- manual OEM;
- criterios del especialista responsable.

Si existe conflicto entre una salida de FixMate y una fuente OEM/procedimiento vigente, debe prevalecer la fuente autorizada y registrarse el conflicto.

## 6. Medición del caso

Registrar, cuando sea posible:

- tiempo para encontrar evidencia útil sin FixMate;
- tiempo con FixMate;
- tiempo para registrar/cerrar el caso;
- cantidad de evidencias pertinentes;
- cantidad de recomendaciones corregidas;
- errores de ingestión;
- errores de sincronización;
- observaciones del técnico.

No calcular ahorros económicos ni afirmar reducción de fallas a partir de un caso aislado.

## 7. Registro resumido

```
ID caso:
Equipo:
Marca/modelo:
Fecha/hora:
Horómetro:
Síntoma:
Condición observada:
Historial relacionado:
Fuentes utilizadas:

Resultado FixMate:
- Causas posibles:
- Pasos:
- Herramientas/repuestos:
- Parámetros:
- Evidencia histórica:
- Confianza:
- Advertencias:

Validación especialista:
- Clasificación:
- Correcciones:
- Fuente de validación:
- Observaciones:

Medición:
- Tiempo sin FixMate:
- Tiempo con FixMate:
- Tiempo de registro/cierre:
- Evidencias pertinentes:
- Recomendaciones corregidas:
- Error de ingestión:
- Error de sincronización:

Decisión del caso:
[ ] Aceptado
[ ] Aceptado con correcciones
[ ] Rechazado
[ ] Sin evidencia suficiente
```

## 8. Regla de oro del piloto

**Si no existe evidencia, se registra la ausencia de evidencia. No se inventa.**

El objetivo del piloto es medir el comportamiento real de FixMate y descubrir dónde funciona, dónde requiere corrección y dónde no debe utilizarse.
