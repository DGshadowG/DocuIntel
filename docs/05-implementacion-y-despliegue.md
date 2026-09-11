# 05 — Documento de Implementación y Despliegue

**Proyecto:** DocuIntel — Sistema Inteligente de Gestión y Análisis Documental
**UTS — Desarrollo de Aplicaciones Empresariales — VI semestre**

---

## 1. Arquitectura del ambiente

Dos perfiles soportados:

| | Desarrollo / evaluación local | Producción (contenedores) |
|---|---|---|
| SO | Windows 10/11 (también Linux/macOS) | Cualquier host con Docker |
| BD | SQLite (`database/docuintel.db`) | PostgreSQL 16 (volumen `pgdata`) |
| Archivos | `storage/` local | volumen `storage` |
| Backend | uvicorn :8000 + worker embebido | contenedor `backend` (migra+seed al arrancar) |
| Frontend | Vite dev :5173 (proxy /api) | nginx :8080 (SPA + proxy) |
| IA | deterministic por defecto | configurable (openai/ollama/deterministic) |

Diagrama de despliegue en `docs/02-diseno.md` §11.

## 2. Requisitos de hardware y software

- **Mínimo local:** 2 CPU, 4 GB RAM, 2 GB disco; Python 3.9+, Node 18+.
- **Producción compose:** 2 CPU, 4 GB RAM (8 GB si se usa Ollama local),
  Docker Engine 24+ y Docker Compose v2.
- Navegador moderno (Chrome/Edge/Firefox).

## 3. Variables de entorno

Todas documentadas en `.env.example`. Las críticas:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Firma JWT. **Obligatorio cambiarla**: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Omitida → SQLite; PostgreSQL: `postgresql+psycopg2://user:pass@host:5432/docuintel` |
| `STORAGE_DIR` / `MAX_UPLOAD_MB` | Carpeta de binarios y límite de carga |
| `AI_PROVIDER` | `deterministic` \| `openai` \| `ollama` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AI_CHAT_MODEL`, `AI_EMBEDDING_MODEL` | Solo para `openai` |
| `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL` | Solo para `ollama` |
| `WORKER_EMBEDDED` | `true` (hilo en la API) o `false` (worker aparte) |
| `SEED_ADMIN_EMAIL/PASSWORD`, `SEED_USER_EMAIL/PASSWORD` | Credenciales que crea el seed (cámbielas) |
| `CORS_ORIGINS` | Orígenes permitidos del frontend |

## 4. Instalación local (Windows PowerShell)

```powershell
# 1. Clonar/copiar el proyecto y abrir PowerShell en la raíz
# 2. Instalación completa (venv, deps, migraciones, seed, corpus, npm)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1

# 3. Editar .env: SECRET_KEY nueva y contraseñas de seed propias

# 4. Iniciar (dos ventanas: backend y frontend)
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# 5. (Opcional) cargar el corpus demo de 30 documentos
.\.venv\Scripts\python.exe scripts\load_corpus.py

# Detener
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

Equivalente manual multiplataforma:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
cp .env.example .env                                 # editar SECRET_KEY y seeds
cd backend && alembic upgrade head && python -m app.db.init_db && cd ..
python scripts/generate_corpus.py
cd frontend && npm install && cd ..
# terminal 1:
cd backend && uvicorn app.main:app --port 8000
# terminal 2:
cd frontend && npm run dev
```

## 5. Acceso

| Recurso | URL |
|---------|-----|
| Aplicación web | http://localhost:5173 |
| API | http://localhost:8000/api/v1 |
| Swagger / OpenAPI | http://localhost:8000/api/docs |
| Health check | http://localhost:8000/health |

**Primer administrador (forma segura):** el seed crea el admin con el correo y
la contraseña definidos en `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` de su
`.env` — defina valores propios **antes** de ejecutar `install.ps1`/`init_db`;
no hay credenciales embebidas en el código. Tras el primer ingreso puede crear
más usuarios desde la pantalla "Usuarios".

## 6. Despliegue con Docker (perfil de producción)

> **Transparencia:** la máquina donde se construyó y evaluó este proyecto no
> tiene Docker instalado, por lo que este perfil se entrega definido y
> revisado (Dockerfiles, compose, healthchecks, volúmenes) pero **no fue
> ejecutado en vivo aquí**; su validación en un host con Docker es el único
> paso externo de esta sección.

```bash
# 1. Variables (archivo .env junto al compose)
#    POSTGRES_PASSWORD, SECRET_KEY, SEED_ADMIN_PASSWORD, SEED_USER_PASSWORD
#    y opcionalmente AI_PROVIDER / OPENAI_API_KEY
# 2. Construir y levantar
docker compose up --build -d
# 3. La migración y el seed corren automáticamente al iniciar el backend
# 4. Abrir http://localhost:8080
```

Incluye: healthcheck de PostgreSQL (pg_isready), del backend (/health) y de
nginx; volúmenes persistentes `pgdata` y `storage`; nginx sirve la SPA y
proxya `/api` con `client_max_body_size 25m`.

## 7. Proceso de despliegue de nuevas versiones

1. `git pull` de la versión etiquetada.
2. Local: `pip install -r backend/requirements.txt`, `alembic upgrade head`,
   reiniciar con `stop.ps1`/`start.ps1`.
   Compose: `docker compose up --build -d` (migra al arrancar).
3. Verificar `/health` y una carga de documento de humo.

## 8. Respaldo y recuperación

- **Respaldar:** `scripts\backup.ps1` → `backups/docuintel-backup-<fecha>.zip`
  (BD SQLite + `storage/`). Con PostgreSQL: `pg_dump -Fc docuintel > docuintel.dump`
  + copia del volumen `storage` (documentado en manual técnico §9).
- **Restaurar:** detener la app → `scripts\restore.ps1 -BackupZip backups\...zip`
  (pide confirmación explícita) → iniciar.
- Recomendación operativa: respaldo diario automatizado (Programador de tareas
  de Windows o cron) y retención de 7/30 días.

## 9. Mantenimiento

- Logs JSON del backend por consola (redirigibles a archivo/colector).
- `GET /health` para monitoreo (estado de BD y proveedor configurado).
- Limpieza de huérfanos del storage: los archivos se eliminan junto con el
  documento; si una eliminación de repos falla a mitad, los binarios sin fila
  en BD pueden depurarse comparando `storage/` contra `documents.storage_key`.
- Actualización de dependencias: versiones fijadas en `requirements.txt` y
  `package.json`; CI (GitHub Actions) ejecuta lint de tipos, build y pruebas
  en cada push.

## 10. Evidencias reales de esta sección

- Instalación y arranque locales verificados en Windows 11 (bitácora
  `PROGRESS.md`, comandos exactos).
- Sistema vivo verificado por: `evidence/test-results/load-corpus.txt`
  (30/30 procesados), `e2e-api-results.json` (24 pasos), Playwright 3/3 y las
  11 capturas de `evidence/screenshots/`.
- El perfil Docker queda declarado como **no ejecutado localmente** (sin
  Docker en la máquina) — no se presenta evidencia inventada de ello.
