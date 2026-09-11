# PROGRESS — Sistema Inteligente de Gestión y Análisis Documental

Bitácora real de construcción del proyecto. Última actualización: 2026-09-11.

## Estado general: COMPLETO ✅

- [x] Diagnóstico inicial del repositorio y entorno
- [x] Arquitectura definida (5 ADRs) y estructura monorepo
- [x] Backend FastAPI: API v1 completa (38 rutas), 15 tablas, pipeline IA, worker
- [x] Capa de IA desacoplada (openai | ollama | deterministic)
- [x] Migraciones Alembic aplicadas + seed reproducible e idempotente
- [x] Corpus de 30 documentos generado, cargado y procesado (30/30 completados)
- [x] Pruebas backend: **71/71 pytest, cobertura 83%**
- [x] Frontend React+TS+Vite+Tailwind: 12 pantallas, build limpio con TS estricto
- [x] Pruebas frontend: **11/11 Vitest**
- [x] E2E navegador real: **3/3 Playwright + 11 capturas reales**
- [x] E2E por API: **24/24 pasos** (`scripts/e2e_flow.py`)
- [x] Evaluación ground truth: **clasificación 30/30 (100%), campos 130/130 (100%)**
- [x] Scripts de operación (install/start/stop/backup/restore .ps1)
- [x] Dockerfiles + docker-compose (perfil PostgreSQL, declarado no ejecutado localmente)
- [x] CI GitHub Actions (backend + frontend)
- [x] 13 entregables de documentación (docs/ + README + CHANGELOG + este archivo)
- [x] Auditoría final (TODO/FIXME/secretos/mocks: limpia)

## Diagnóstico inicial (2026-09-10/11)

- Repositorio vacío salvo `tmp/pdfs/integrador_review/` (brief del docente en
  5 PNG, leído completo) y `.atl/` (registro de skills, ignorado).
- Entorno: Windows 11, Python 3.9.13, Node 23.9.0, npm 10.9.2, git 2.48.1.
  **Docker NO disponible.** Red a PyPI/npm OK.

## Decisiones técnicas (formalizadas en docs/adr/)

1. **ADR-001** Monorepo FastAPI + React, capa IA desacoplada por interfaz.
2. **ADR-002** SQLite por defecto, PostgreSQL como perfil producción
   (`DATABASE_URL` conmuta; Alembic batch mode).
3. **ADR-003** Embeddings BLOB float32 + coseno NumPy en proceso; ruta pgvector
   documentada con plan de migración.
4. **ADR-004** Cola de jobs en BD + worker embebido (hilo) o standalone; sin
   Redis/Celery (no disponible y no necesario a esta escala).
5. **ADR-005** Tres proveedores IA (openai/ollama/deterministic); el
   determinista es honesto (modelo `deterministic-v1` visible siempre) y las
   pruebas lo usan por reproducibilidad.

## Comandos ejecutados (reproducibles)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.db.init_db
..\.venv\Scripts\python.exe -m pytest --cov=app          # 71 passed, 83%
cd ..
.venv\Scripts\python.exe scripts\generate_corpus.py       # 30 docs + GT + eval
cd frontend
npm install; npm run build; npm test                      # build OK, 11 passed
npx playwright install chromium
# con backend (uvicorn :8000) y frontend (vite :5173) vivos:
npx playwright test                                       # 3 passed + capturas
cd ..
.venv\Scripts\python.exe scripts\load_corpus.py           # 30/30 completed
.venv\Scripts\python.exe scripts\e2e_flow.py              # 24/24 pasos OK
.venv\Scripts\python.exe scripts\evaluate_ground_truth.py # 100% / 100%
```

## Defectos encontrados y corregidos (todos cerrados, con regresión)

| ID | Descripción | Corrección |
|----|-------------|------------|
| DEF-001 | pip fallaba compilando greenlet (sin wheel Py3.9/win) | fijar `greenlet==3.1.1` |
| DEF-002 | `EmailStr` requería email-validator | `pydantic[email]==2.9.2` |
| DEF-003 | Validador de email rechaza TLD reservados (`.local`) → login seed 422 | dominios `docuintel.co`/`test-docuintel.co` |
| DEF-004 | `Mapped[list]` sin tipo → SQLAlchemy trató colecciones como escalares (500 en detalle de documento) | `Mapped[List["X"]]` en las 8 colecciones |
| DEF-005 | Regex de total de factura coincidía dentro de "Subtotal" | lookbehind `(?<![a-zA-Z])total` |
| DEF-006 | Sección IDIOMAS al final de la hoja de vida no se extraía | corte de sección acepta línea en blanco o fin |
| DEF-007 | Playwright strict-mode: localizadores ambiguos + residuo de corrida fallida | `exact:true`/`.first()` + limpieza |
| DEF-008 | Vitest recogía la spec de Playwright | `include/exclude` en vite.config.ts |

## Evidencias reales

- `evidence/test-results/pytest-backend.txt` (71 passed + cobertura por módulo)
- `evidence/test-results/coverage.xml`
- `evidence/test-results/vitest-frontend.txt` (11 passed)
- `evidence/test-results/playwright-e2e.txt` (3 passed)
- `evidence/test-results/e2e-api-results.json` + `e2e-api-log.txt` (24 pasos)
- `evidence/test-results/load-corpus.txt` (30/30 completed, 10/10/10 categorías)
- `evidence/test-results/ground-truth-eval.json` + `.txt` (100% / 100%)
- `evidence/screenshots/01..11-*.png` (11 capturas reales del flujo E2E)

## Pendientes reales / pasos externos

1. **Activar un LLM real**: definir `OPENAI_API_KEY` (o instalar Ollama) y
   cambiar `AI_PROVIDER` — la integración está implementada y probada
   contractualmente; no se pudo ejercer en vivo sin credencial.
2. **Validar docker-compose en un host con Docker** — definido y revisado, no
   ejecutado aquí (sin Docker en la máquina).
3. **Grabar el video** siguiendo `docs/12-guion-video.md` (el guion existe; el
   video no se afirma como grabado).
4. **Datos académicos**: reemplazar los marcadores `[NOMBRE DEL INTEGRANTE]` y
   `[GRUPO]` en `docs/01-analisis.md` y `docs/13-presentacion.md`.

## Riesgos residuales

- Calidad generativa (resumen/RAG) en modo determinista es extractiva; con LLM
  real mejora sin cambios de código (mismo pipeline, misma evaluación).
- SQLite limita concurrencia de escritura; producción usa PostgreSQL (compose).
