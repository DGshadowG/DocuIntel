# ADR-004: Cola de trabajos en base de datos con worker embebido

- Estado: aceptada (2026-09-10)
- Contexto: el pipeline documental debe ejecutarse de forma asíncrona (la carga
  responde 201 de inmediato y el procesamiento continúa). La recomendación era
  Celery/RQ + Redis, pero no hay Redis disponible en el entorno objetivo.

## Decisión

Tabla `processing_jobs` como cola (estados queued/running/completed/failed,
intentos, etapa, duración) y un worker que la sondea:

- **Embebido** (`WORKER_EMBEDDED=true`, por defecto): hilo daemon dentro del
  proceso de la API — cero infraestructura.
- **Independiente**: `python -m app.worker.runner` como proceso aparte para
  producción, escalable por separado.

## Por qué no Celery/Redis

- Requeriría instalar y operar Redis en una máquina donde no existe.
- La cola en BD es transaccional con el resto de los datos: un job nunca queda
  huérfano de su documento y el estado que muestra la UI es siempre consistente.
- El volumen (decenas de documentos por carga) no justifica un broker dedicado.

## Consecuencias

- Reintentos: al fallar, el job vuelve a `queued` hasta `max_attempts` (3);
  el error técnico por etapa queda registrado en el job y el documento.
- Con múltiples réplicas de API en producción se recomienda el worker
  independiente y `WORKER_EMBEDDED=false` (documentado en el manual técnico).
