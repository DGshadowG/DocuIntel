# DocuIntel — Sistema Inteligente de Gestión y Análisis Documental

Proyecto Integrador — Desarrollo de Aplicaciones Empresariales, VI semestre
Unidades Tecnológicas de Santander (UTS) — Tecnología en Desarrollo de Software
Docente: Wilson Castaño Galviz

DocuIntel convierte repositorios de archivos (PDF, DOCX, TXT) en información
consultable: extrae el texto, lo clasifica, lo resume, extrae campos
estructurados, genera embeddings y permite búsqueda textual/semántica y
preguntas en lenguaje natural (RAG) con citas verificables.

## Flujo real implementado

```
archivo → validación → almacenamiento → extracción de texto → segmentación
→ clasificación IA → resumen IA → extracción estructurada → embeddings
→ indexación → búsqueda → consulta RAG → respuesta con fuentes
```

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python) + SQLAlchemy 2 + Alembic |
| Base de datos | SQLite (desarrollo) / PostgreSQL (perfil producción) |
| Worker | Cola transaccional en BD + hilo embebido (o proceso aparte) |
| IA | Capa desacoplada: OpenAI-compatible, Ollama local o proveedor determinista offline |
| Pruebas | pytest (71), Vitest (11), Playwright E2E (3) |
| Autenticación | JWT + bcrypt, control de roles y membresías |

## Inicio rápido (Windows PowerShell)

Requisitos: Python 3.9+, Node 18+.

```powershell
# 1. Instalar todo (venv, dependencias, migraciones, seed, corpus)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1

# 2. Revisar .env (cambie SECRET_KEY y contraseñas de seed)

# 3. Iniciar backend + frontend
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# 4. (Opcional) Cargar el corpus demo de 30 documentos
.\.venv\Scripts\python.exe scripts\load_corpus.py
```

- Aplicación: **http://localhost:5173**
- API / Swagger: **http://localhost:8000/api/docs**
- Credenciales iniciales: definidas por `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`
  en su `.env` (cámbielas antes de usar el sistema con datos reales).

Para detener: `powershell -ExecutionPolicy Bypass -File scripts\stop.ps1`

## Proveedor de IA

Se configura con `AI_PROVIDER` en `.env`:

- `deterministic` (por defecto): reglas + embeddings hash 384d. 100% offline,
  reproducible; usado por las pruebas automatizadas. El nombre del modelo
  (`deterministic-v1`) se persiste y se muestra en la UI — nunca se hace pasar
  por un LLM.
- `openai`: cualquier API compatible (OpenAI, Groq, Together…). Requiere
  `OPENAI_API_KEY`.
- `ollama`: modelos locales (`llama3.1` + `nomic-embed-text` por defecto).

Detalles completos en `docs/03-desarrollo-documento-tecnico.md` §IA.

## Estructura

```
backend/          API FastAPI, modelos, pipeline, capa IA, worker, pruebas
frontend/         SPA React + TS (pruebas Vitest y E2E Playwright)
database/         Base SQLite de desarrollo (generada; no versionada)
scripts/          install/start/stop/backup/restore + corpus + E2E + evaluación
sample_documents/ Corpus sintético de 30 documentos + ground truth + eval RAG
docs/             Documentación académica (análisis, diseño, pruebas, manuales…)
evidence/         Resultados reales de pruebas y capturas de pantalla
docker-compose.yml  Perfil de despliegue con PostgreSQL (documentado)
```

## Pruebas

```powershell
# Backend (71 pruebas, cobertura 83%)
cd backend; ..\.venv\Scripts\python.exe -m pytest --cov=app

# Frontend (11 pruebas)
cd frontend; npm test

# E2E navegador real (requiere backend+frontend arriba y corpus cargado)
cd frontend; npx playwright test

# Flujo E2E por API + evaluación contra ground truth (backend arriba)
.\.venv\Scripts\python.exe scripts\e2e_flow.py
.\.venv\Scripts\python.exe scripts\evaluate_ground_truth.py
```

Resultados reales en `evidence/test-results/` y capturas en `evidence/screenshots/`.

## Documentación

| Documento | Archivo |
|-----------|---------|
| Análisis | `docs/01-analisis.md` |
| Diseño | `docs/02-diseno.md` |
| Desarrollo / doc. técnico | `docs/03-desarrollo-documento-tecnico.md` |
| Plan y evidencias de pruebas | `docs/04-plan-y-evidencias-de-pruebas.md` |
| Implementación y despliegue | `docs/05-implementacion-y-despliegue.md` |
| Manual de usuario | `docs/06-manual-de-usuario.md` |
| Manual técnico / administración | `docs/07-manual-tecnico-administracion.md` |
| Matriz de trazabilidad | `docs/08-matriz-trazabilidad.md` |
| Guion del video (≤5 min) | `docs/12-guion-video.md` |
| Presentación (12 diapositivas) | `docs/13-presentacion.md` |
| Decisiones de arquitectura | `docs/adr/` |
| Bitácora del proyecto | `PROGRESS.md` |

## Seguridad

Contraseñas con bcrypt, JWT firmado, autorización por propietario/miembro,
validación de extensión + números mágicos, nombres de archivo saneados y claves
de almacenamiento UUID (sin path traversal), límite de tamaño configurable,
CORS restringido, errores sin stack traces al usuario, auditoría de acciones.
Ningún secreto se versiona: todo vive en `.env` (ver `.env.example`).

## Datos

Los 30 documentos de `sample_documents/` son **completamente ficticios**
(generados con Faker con semilla fija). No contienen datos de personas reales.
