# 08 — Matriz de Trazabilidad

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**

Cadena completa: problema → objetivo → requisito → historia → caso de uso →
componente → endpoint → pantalla → código → prueba → evidencia → estado.

Convenciones: O1..O7 = objetivos específicos (`docs/01-analisis.md` §4);
HU/CU ídem §12–13; pruebas en `backend/tests/` salvo indicación; evidencias en
`evidence/`. Estado ✅ = implementado con prueba ejecutada y aprobada.

## Matriz principal (requisitos funcionales)

| RF | Historia / CU | Componente y código | Endpoint | Pantalla | Prueba | Evidencia | Estado |
|----|--------------|--------------------|----------|----------|--------|-----------|--------|
| RF-001 Login JWT | HU-001 / CU-01 | `api/v1/auth.py`, `core/security.py` | POST /auth/login | Login | TC-01/02 test_auth_security.py; login.test.tsx | pytest-backend.txt; vitest-frontend.txt; 01-login.png | ✅ |
| RF-002 Logout auditado | HU-001 / CU-01 | `auth.py` + `services/audit.py` | POST /auth/logout | Menú superior | test_me_y_logout; E2E UI logout | pytest-backend.txt; playwright-e2e.txt | ✅ |
| RF-003 Roles admin/usuario | HU-010 / CU-02 | `api/deps.py` (require_admin), modelo User.role | — (transversal) | todas | TC-03c; test_users_admin.py | pytest-backend.txt | ✅ |
| RF-004 CRUD usuarios (admin) | HU-010 / CU-02 | `api/v1/users.py` | GET/POST /users, PATCH /users/{id} | Usuarios | test_users_admin.py (4 casos) | pytest-backend.txt | ✅ |
| RF-005 CRUD repositorios | HU-002 / CU-03 | `api/v1/repositories.py` | /repositories* | Repositorios (+detalle) | TC-04 test_repositories.py | pytest-backend.txt; 03-repositorios.png | ✅ |
| RF-006 Miembros | HU-002 / CU-03 | `repositories.py` + RepositoryMember | /repositories/{id}/members* | Detalle repositorio | test_miembros | pytest-backend.txt | ✅ |
| RF-007 Autorización por repositorio | HU-002 / CU-03 | `services/permissions.py` | — (transversal) | todas | TC-21, búsqueda/conversación ajenas | pytest-backend.txt | ✅ |
| RF-008 Carga múltiple 3 formatos | HU-003 / CU-04 | `api/v1/documents.py` upload | POST /documents/upload | Detalle repositorio | TC-05/06/07 + carga múltiple | pytest-backend.txt; e2e-api-results.json | ✅ |
| RF-009 Validación extensión+firma | HU-003 / CU-04 | `services/extraction.py` detect_file_type | ídem | ídem | TC-08, tc08b | pytest-backend.txt | ✅ |
| RF-010 Límite de tamaño | HU-003 / CU-04 | `config.MAX_UPLOAD_MB` + upload | ídem | ídem | TC-09 | pytest-backend.txt | ✅ |
| RF-011 Anti path-traversal | HU-003 / CU-04 | sanitize_filename + LocalStorage._path | ídem | — | TC-10 + test_units sanitización/storage | pytest-backend.txt | ✅ |
| RF-012 Estados del documento | HU-003 / CU-04-05 | Document.status + jobs | GET /documents* | Tablas + detalle | TC-05 (queued), TC-11 (completed), corrupto (failed) | pytest-backend.txt; 05-carga-procesada.png | ✅ |
| RF-013 Extracción de texto + ilegibles | HU-003 / CU-05 | `services/extraction.py` extract_text | pipeline | Detalle documento | TC-11; test_documento_ilegible | pytest-backend.txt | ✅ |
| RF-014 Chunking con página | — / CU-05 | `services/chunking.py` | pipeline | — | test_units chunking (3 casos) | pytest-backend.txt | ✅ |
| RF-015 Clasificación 3 categorías | HU-004 / CU-05 | AIProvider.classify + pipeline | pipeline | Detalle documento | TC-12; eval corpus ≥80% | pytest-backend.txt; ground-truth-eval.json (30/30) | ✅ |
| RF-016 Corrección manual | HU-005 / CU-07 | Classification.manual_category | PATCH /documents/{id}/category | Detalle documento | test_correccion_manual | pytest-backend.txt | ✅ |
| RF-017 Resumen | HU-004 / CU-05 | AIProvider.summarize + Summary | pipeline | Detalle documento | TC-13 | pytest-backend.txt; 06-documento-detalle.png | ✅ |
| RF-018 Extracción estructurada validada | HU-004 / CU-05 | AIProvider.extract + ai/schemas.py + ExtractedField | pipeline | Detalle documento | TC-14/15/16 | pytest-backend.txt; ground-truth-eval.json (130/130) | ✅ |
| RF-019 Embeddings persistidos | — / CU-05 | AIProvider.embed + Embedding + vectors.py | pipeline | — | test_units embeddings; TC-18 | pytest-backend.txt | ✅ |
| RF-020 Error + reintento | HU-008 / CU-12 | pipeline execute_job (attempts) | POST /documents/{id}/reprocess, GET .../jobs | Detalle documento | TC-23, TC-24 | pytest-backend.txt | ✅ |
| RF-021 Descarga + texto extraído | HU-004 / CU-06 | documents.py download/content | GET .../download, .../content | Detalle documento | test_descarga; TC-11 | pytest-backend.txt | ✅ |
| RF-022 Eliminación con limpieza | HU-003 / CU-06 | cascadas + storage.delete | DELETE /documents/{id} | Detalle documento | TC-22 | pytest-backend.txt | ✅ |
| RF-023 Filtros y paginación | HU-004 / CU-06 | documents.py list | GET /documents | Documentos | test_listado_filtros_paginacion | pytest-backend.txt | ✅ |
| RF-024 Búsqueda textual | HU-006 / CU-08 | `api/v1/search.py` text_search | GET /search/text | Buscar | TC-17 + filtros + permisos | pytest-backend.txt; 07-busqueda-textual.png | ✅ |
| RF-025 Búsqueda semántica | HU-006 / CU-08 | search.py + vectors.semantic_search | GET /search/semantic | Buscar | TC-18 + filtro categoría | pytest-backend.txt; 08-busqueda-semantica.png | ✅ |
| RF-026 RAG con citas | HU-007 / CU-09 | `services/rag.py` + Citation | POST /conversations/{id}/ask | Consulta IA | TC-19; e2e_flow (3 preguntas) | pytest-backend.txt; e2e-api-results.json; 09-chat-rag-citas.png | ✅ |
| RF-027 Historial conversaciones | HU-007 / CU-09 | Conversation/Message | GET /conversations* | Consulta IA | test_historial_conversacion | pytest-backend.txt | ✅ |
| RF-028 Sin evidencia explícito | HU-007 / CU-09 | rag.py umbral + RagAnswer.grounded | ídem | Consulta IA | TC-20; rag_eval.json | pytest-backend.txt; 10-chat-sin-evidencia.png | ✅ |
| RF-029 Métricas RAG | HU-007 / CU-09 | Message.latency_ms/chunk_count/model | ídem | Consulta IA (pie de respuesta) | TC-19 asserts de métricas | pytest-backend.txt | ✅ |
| RF-030 Dashboard real | HU-009 / CU-10 | `services/dashboard.py` | GET /dashboard | Dashboard | TC-25 | pytest-backend.txt; 02-dashboard.png | ✅ |
| RF-031 Auditoría visible | HU-011 / CU-11 | `api/v1/audit.py` + audit_logs | GET /audit-logs | Auditoría | test_auditoria (registro + 403) | pytest-backend.txt | ✅ |
| RF-032 Proveedor IA configurable | — / CU-05 | `ai/factory.py` + config | — (transversal) | — (modelo visible en UI) | suites completas con deterministic; TC-23 (fallo proveedor) | pytest-backend.txt | ✅ |

## Requisitos no funcionales

| RNF | Implementación | Prueba/verificación | Evidencia | Estado |
|-----|----------------|--------------------|-----------|--------|
| RNF-001 bcrypt | core/security.py | test_contrasenas_cifradas, test_verify_password | pytest-backend.txt | ✅ |
| RNF-002 JWT firmado/expirable | core/security.py | test_jwt_expirado_rechazado (expirado + alterado) | pytest-backend.txt | ✅ |
| RNF-003 CORS restringido | main.py CORSMiddleware | revisión de configuración + orígenes explícitos | main.py:52 | ✅ |
| RNF-004 Errores consistentes | core/errors.py | asserts de `error.code` en 20+ pruebas | pytest-backend.txt | ✅ |
| RNF-005 Logs JSON + correlation id | core/logging.py + middleware | visible en salidas de prueba; header X-Correlation-Id | pytest-backend.txt (líneas JSON) | ✅ |
| RNF-006 Sin secretos versionados | .env ignorado, .env.example | auditoría final §15 del enunciado (grep) | PROGRESS.md auditoría | ✅ |
| RNF-007 Arranque reproducible | install.ps1 + Alembic + seed idempotente | instalación real documentada; CI | load-corpus.txt; ci.yml | ✅ |
| RNF-008 UI responsive/accesible es | Tailwind + aria-* + labels | pruebas Vitest de componentes; revisión capturas | vitest-frontend.txt; screenshots | ✅ |
| RNF-009 Pruebas repetibles | conftest aislado + deterministic | 2+ ejecuciones completas idénticas | pytest-backend.txt | ✅ |
| RNF-010 Pipeline asíncrono | cola processing_jobs + worker | TC-05 (201 inmediato) + polling E2E | e2e-api-results.json | ✅ |
| RNF-011 Reintentos (3) | execute_job attempts | TC-23 | pytest-backend.txt | ✅ |
| RNF-012 API versionada + OpenAPI | prefijo /api/v1 + /api/docs | E2E health/docs; colección Postman | e2e-api-results.json; api-collection.postman.json | ✅ |

## Trazabilidad problema → objetivo → entrega

| Problema (análisis §1) | Objetivo | RFs | Estado global |
|---|---|---|---|
| Acceso sin control | O1 | RF-001..007 | ✅ completo |
| Archivos ingobernables | O2 | RF-008..012, 020..023 | ✅ completo |
| Contenido no comprendido | O3 | RF-013..019, 032 | ✅ completo |
| Información no encontrable | O4 | RF-024..025 | ✅ completo |
| Preguntas sin respuesta | O5 | RF-026..029 | ✅ completo |
| Sin visibilidad | O6 | RF-030..031 | ✅ completo |
| Sin garantía de calidad | O7 | RNF-007/009 + plan de pruebas | ✅ completo |

**Nota de honestidad:** RF-032 incluye la integración real con LLM
(openai/ollama) implementada y configurada por entorno; su ejercicio en vivo
requiere una credencial o instalación de Ollama (único paso externo, declarado
en `docs/05` §6 y `PROGRESS.md`). Todo lo demás está verificado con
ejecuciones reales referenciadas arriba.
