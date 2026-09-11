# 03 — Documento de Desarrollo / Documento Técnico

**Proyecto:** DocuIntel — Sistema Inteligente de Gestión y Análisis Documental
**UTS — Desarrollo de Aplicaciones Empresariales — VI semestre**

---

## 1. Entorno de desarrollo

| Componente | Versión usada |
|------------|---------------|
| SO | Windows 11 Home (10.0.26200) |
| Python | 3.9.13 (venv en `.venv/`) |
| Node.js / npm | 23.9.0 / 10.9.2 |
| Git | 2.48.1 |
| Editor recomendado | VS Code |
| Docker | **No disponible** en la máquina de desarrollo (ver ADR-002/004) |

## 2. Configuración del proyecto

1. `python -m venv .venv` y `pip install -r backend/requirements-dev.txt`.
2. `npm install` en `frontend/`.
3. Copiar `.env.example` → `.env`; todas las variables están comentadas allí
   (secreto JWT, BD, almacenamiento, worker, proveedor IA, RAG, seeds).
4. `alembic upgrade head` (migraciones) y `python -m app.db.init_db` (seed).
5. `python scripts/generate_corpus.py` (corpus de 30 documentos).

Todo lo anterior lo automatiza `scripts/install.ps1`.

## 3. Estructura del código fuente

```
backend/
  app/
    core/        config (pydantic-settings), security (bcrypt+JWT),
                 logging (JSON + correlation id), errors (handler global)
    db/          base declarativa, sesión/engine, seed (init_db)
    models/      entities.py — 15 tablas SQLAlchemy 2 tipadas
    schemas/     api.py — contratos Pydantic de entrada/salida
    api/         deps.py (auth), v1/ — 8 routers de dominio
    services/    storage, extraction, chunking, pipeline, vectors,
                 rag, permissions, dashboard, audit
    ai/          base (AIProvider), prompts, openai_provider,
                 ollama_provider, deterministic, schemas, factory
    worker/      runner.py — cola en BD, hilo embebido o proceso
  alembic/       migraciones versionadas (autogenerate + batch mode)
  tests/         71 pruebas pytest (unitarias, integración, API, seguridad)
frontend/
  src/api/       client.ts (axios + interceptores), types.ts (contratos)
  src/context/   AuthContext, ToastContext
  src/components/ Layout, ErrorBoundary, ui.tsx (badges, dialogo, paginación…)
  src/pages/     Login, Dashboard, Repositories(+Detail), Documents(+Detail),
                 Search, Chat, Users, Audit, NotFound
  src/test/      11 pruebas Vitest + Testing Library
  e2e/           3 pruebas Playwright con capturas reales
scripts/         install/start/stop/backup/restore (.ps1),
                 generate_corpus, load_corpus, e2e_flow, evaluate_ground_truth (.py)
```

## 4. Convenciones

- Código, identificadores y comentarios en inglés; textos de UI y mensajes al
  usuario en español; valores de dominio como códigos cortos (`financiero`,
  `completed`) traducidos en la UI.
- Backend: tipado con `Mapped[...]`/Pydantic v2; errores de negocio con
  `AppError(status, code, message)`; servicios sin dependencia de FastAPI.
- Frontend: TypeScript estricto; contratos de `types.ts` espejo de
  `schemas/api.py`; componentes de presentación en `ui.tsx`.
- Commits convencionales (`feat:`, `fix:`, `docs:`, `test:`).

## 5. Implementación del backend

- **Autenticación** (`api/v1/auth.py`, `core/security.py`): login verifica
  bcrypt y emite JWT con `sub` (id) y `role`; `get_current_user` valida token,
  existencia y estado activo en cada petición.
- **Repositorios** (`api/v1/repositories.py` + `services/permissions.py`):
  `accessible_repository_ids()` resuelve el ámbito del usuario una vez y toda
  lectura (documentos, búsqueda, RAG, dashboard) se filtra por él.
- **Documentos** (`api/v1/documents.py`): carga multipart (1–20 archivos),
  validación en `services/extraction.py` (extensión + firma + tamaño +
  saneamiento), persistencia vía `services/storage.py` y encolado en
  `services/pipeline.enqueue_document()`. Descarga con `filename*` RFC 5987.
- **Pipeline** (`services/pipeline.py`): etapas con actualización de `stage`
  en el job; `_clear_derived()` borra texto/chunks/embeddings/resultados antes
  de reprocesar (idempotencia); fallo → reintento hasta 3, luego documento
  fallido con `[etapa] error`.
- **Worker** (`worker/runner.py`): sondeo de la cola (1 s); embebido como hilo
  daemon del proceso API (`WORKER_EMBEDDED=true`) o standalone
  (`python -m app.worker.runner`).
- **Búsqueda** (`api/v1/search.py`): textual con ILIKE por término sobre chunks
  y nombres, mejor chunk por documento, resaltado `**término**`; semántica con
  embedding de la consulta + coseno (`services/vectors.py`).
- **RAG** (`services/rag.py`): descrito en diseño §8; persiste ambos mensajes,
  citas y métricas en una transacción.
- **Dashboard** (`services/dashboard.py`): agregados SQL (`GROUP BY`) +
  tendencia de 14 días; todo dentro del ámbito de permisos.
- **Errores y logs** (`core/errors.py`, `core/logging.py`): handler global,
  cuerpo uniforme, `X-Correlation-Id` de vuelta al cliente, logs JSON.

## 6. Implementación del frontend

- **Sesión:** `AuthContext` restaura al usuario con `GET /auth/me` al montar;
  interceptor añade el Bearer y ante 401 limpia el token y redirige a login.
- **Rutas protegidas:** `RequireAuth` y `RequireAdmin` en `App.tsx`; 404 dentro
  del layout autenticado.
- **Estados vivos:** las páginas de repositorio y documento hacen polling cada
  2,5 s mientras existan documentos pendientes/en cola/procesando, así el
  usuario ve el avance del pipeline sin recargar.
- **UX:** confirmaciones (`ConfirmDialog`) para eliminar, toasts accesibles
  (`aria-live`), estados de carga/vacío/error en cada página, tablas con
  paginación, textos reales en español.

## 7. Base de datos y almacenamiento

- Modelo de 15 tablas (diseño §4–5); migración inicial `81a49e3686fd` generada
  con autogenerate y aplicada con Alembic (batch mode para SQLite).
- SQLite con WAL y `foreign_keys=ON`; cambio a PostgreSQL solo con
  `DATABASE_URL` (probado el mismo esquema por compatibilidad de tipos).
- Binarios en `storage/` con clave `uuid4().hex.ext`; la BD solo guarda la
  clave. Adaptador S3/MinIO definido por interfaz (`Storage`) como extensión.

## 8. Capa de IA (clasificación, resumen, extracción, embeddings, RAG)

Contrato y proveedores según ADR-005. Puntos de implementación:

- **Prompts** (`ai/prompts.py`): en español, con instrucción de responder solo
  JSON (clasificación/extracción) y reglas estrictas de cita para RAG.
- **Validación:** toda salida de extracción pasa por los modelos Pydantic de
  `ai/schemas.py` antes de persistirse; JSON malformado → etapa fallida con
  error registrado (nunca datos corruptos).
- **Deterministic v1** (`ai/deterministic.py`): clasificador por puntaje de
  palabras clave con confianza por margen; resumen extractivo por frecuencia;
  extracción por regex/secciones (formatos de monto colombianos incluidos);
  embeddings por feature hashing con signo (384d, TF log, L2); RAG extractivo
  con umbral. Es un motor real y reproducible — se identifica siempre como
  `deterministic-v1` en BD y UI.
- **Fallos de proveedor:** `AIProviderError` → la etapa falla, el job reintenta
  y el error queda visible; el endpoint de búsqueda semántica/chat devuelve 503
  `ai_unavailable` si el proveedor no responde.

## 9. Manejo de errores

- Backend: `AppError` (negocio), `RequestValidationError` (422 con campos),
  `Exception` (500 genérico + log con stack). Todos devuelven `correlation_id`.
- Pipeline: error por etapa en `processing_jobs.stage/error_message` y, al
  agotar reintentos, en `documents.error_message`.
- Frontend: `errorMessage()` traduce cualquier fallo de red/API a un mensaje
  legible; `ErrorBoundary` captura errores de render con pantalla de recarga.

## 10. Seguridad de credenciales

- `.env` en `.gitignore`; `.env.example` sin valores reales.
- `SECRET_KEY` y contraseñas seed solo por entorno; el README indica generarla
  con `secrets.token_hex(32)`.
- La API key de IA nunca se loguea ni viaja al frontend.

## 11. Control de versiones

Repositorio Git local con rama `main` y commits convencionales por hito
(estructura, backend, corpus, pruebas, frontend, e2e, docs). El historial
refleja la bitácora de `PROGRESS.md`.

## 12. Bitácora real de desarrollo

Mantenida en `PROGRESS.md` (trabajo realizado, comandos, defectos DEF-001..006
con causa y corrección, riesgos y pendientes). Los defectos también están
resumidos en `CHANGELOG.md`.

## 13. Instalación y ejecución

Ver README (inicio rápido) y `docs/05-implementacion-y-despliegue.md`
(procedimiento completo, perfiles y despliegue con Docker).

## 14. Limitaciones conocidas

1. **PDF escaneados:** sin OCR; se marcan fallidos con mensaje explícito.
2. **Proveedor determinista:** su calidad de resumen/RAG es extractiva, no
   generativa; es el modo de evaluación offline. Con `AI_PROVIDER=openai` u
   `ollama` el mismo pipeline usa un LLM real (paso externo: credencial/modelo).
3. **Búsqueda semántica:** escaneo en memoria adecuado hasta ~10⁴ chunks
   (ADR-003); corpus mayores requieren la ruta pgvector documentada.
4. **SQLite:** concurrencia de escritura limitada; producción usa PostgreSQL.
5. **JWT sin lista de revocación:** el logout es del lado del cliente (se
   registra en auditoría); mitigable con expiración corta.
