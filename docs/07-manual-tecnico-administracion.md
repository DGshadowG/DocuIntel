# 07 — Manual Técnico y de Administración

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**
Dirigido a administradores del sistema y personal técnico.

---

## 1. Arquitectura (referencia rápida)

SPA React (5173/8080) → API FastAPI `/api/v1` (8000) → SQLite/PostgreSQL +
almacenamiento de archivos + proveedor de IA conmutable. Worker de pipeline en
hilo embebido o proceso aparte. Detalle completo: `docs/02-diseno.md`.

## 2. Dependencias

- Backend: `backend/requirements.txt` (FastAPI, SQLAlchemy 2, Alembic,
  pypdf, python-docx, reportlab, httpx, numpy, PyJWT, bcrypt, Faker).
- Frontend: `frontend/package.json` (React 18, react-router 6, axios,
  Tailwind 3; dev: Vitest, Testing Library, Playwright).
- Sin servicios obligatorios: con configuración por defecto no se requiere
  red externa, BD externa ni broker.

## 3. Configuración

Toda la configuración es por variables de entorno (`.env`); tabla completa en
`docs/05-implementacion-y-despliegue.md` §3 y `.env.example`. Cambios de
configuración requieren reiniciar el backend.

Puntos sensibles:

- `SECRET_KEY`: rotarla invalida todas las sesiones activas (los usuarios
  vuelven a iniciar sesión). Nunca usar el valor de ejemplo.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: por defecto 480 (8 h laborales).
- `CORS_ORIGINS`: incluir exactamente los orígenes del frontend desplegado.

## 4. Migraciones de base de datos

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head     # aplicar
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "cambio"  # crear
..\.venv\Scripts\python.exe -m alembic downgrade -1     # revertir una
..\.venv\Scripts\python.exe -m alembic history          # historial
```

Las migraciones usan `render_as_batch` (compatibles con SQLite y PostgreSQL).
En el contenedor de producción `alembic upgrade head` corre automáticamente al
arrancar.

## 5. Gestión de usuarios

- **Primer admin:** lo crea el seed (`python -m app.db.init_db`) con
  `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` del `.env`. El seed es idempotente:
  si el usuario existe, no lo duplica ni cambia su contraseña.
- **Siguientes usuarios:** pantalla **Usuarios** (UI) o `POST /api/v1/users`.
- **Restablecer contraseña de un usuario:** `PATCH /api/v1/users/{id}` con
  `{"password": "NuevaClave123"}` (como admin, vía Swagger o Postman).
- **Bloquear acceso:** desactivar el usuario (no se elimina; conserva
  auditoría y propiedad de repositorios).
- Regla de protección: un admin no puede desactivar su propia cuenta.

## 6. Worker de procesamiento

- Modo por defecto: hilo dentro de la API (`WORKER_EMBEDDED=true`).
- Modo dedicado: `WORKER_EMBEDDED=false` en la API y ejecutar
  `python -m app.worker.runner` como servicio aparte (recomendado con varias
  réplicas de API).
- Cola: tabla `processing_jobs`. Un job fallido reintenta solo (máx. 3);
  los fallidos definitivos se relanzan desde la UI ("Reprocesar") o con
  `POST /api/v1/documents/{id}/reprocess`.
- Diagnóstico: columna `stage` indica la etapa exacta del fallo;
  `error_message` el detalle técnico; `duration_ms` el tiempo por intento.

## 7. Proveedor de IA

| Modo | Activación | Notas |
|------|-----------|-------|
| deterministic | `AI_PROVIDER=deterministic` | Offline, reproducible; modelo `deterministic-v1` visible en resultados |
| openai | `AI_PROVIDER=openai` + `OPENAI_API_KEY` | Compatible con OpenAI/Groq/Together vía `OPENAI_BASE_URL`; modelos en `AI_CHAT_MODEL`/`AI_EMBEDDING_MODEL` |
| ollama | `AI_PROVIDER=ollama` + Ollama corriendo | `ollama pull llama3.1 && ollama pull nomic-embed-text` |

**Importante al cambiar de proveedor/modelo de embeddings:** los vectores
almacenados tienen la dimensión del modelo anterior; la búsqueda semántica
ignora vectores de dimensión distinta. Reprocese los documentos (botón
Reprocesar o re-carga) para regenerar embeddings homogéneos.

**Privacidad:** con `openai`, el texto de los documentos y las preguntas se
envían al servicio configurado. Para datos sensibles use `ollama` (local) o
`deterministic` (sin red). Esta decisión es del administrador.

## 8. Logs y monitoreo

- Logs del backend: JSON por stdout con `correlation_id`, evento, latencia y
  código de estado. Redirigir a archivo: `uvicorn ... >> logs/api.log 2>&1`.
- Ante un reporte de error de un usuario, pida la hora y busque el
  `correlation_id` devuelto en la respuesta de error para ubicar el stack
  completo en el log.
- Monitoreo: `GET /health` (estado de BD y proveedor); en compose, los tres
  contenedores traen healthcheck.
- Auditoría funcional: pantalla **Auditoría** o `GET /api/v1/audit-logs`.

## 9. Respaldo y restauración

- SQLite (por defecto): `scripts\backup.ps1` y
  `scripts\restore.ps1 -BackupZip <zip>` (BD + storage; restore pide
  confirmación y requiere la app detenida).
- PostgreSQL (compose):
  ```bash
  docker compose exec db pg_dump -U docuintel -Fc docuintel > docuintel.dump
  docker run --rm -v proyecto_storage:/data -v $PWD:/backup alpine tar czf /backup/storage.tgz /data
  # restaurar
  docker compose exec -T db pg_restore -U docuintel -d docuintel --clean < docuintel.dump
  ```

## 10. Solución de problemas (técnico)

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `/health` → `degraded` | BD inaccesible/bloqueada | Verificar archivo SQLite o servicio PostgreSQL; revisar `DATABASE_URL` |
| Todos los documentos quedan "En cola" | Worker no corre | Confirmar `WORKER_EMBEDDED=true` o proceso worker activo; revisar logs |
| Fallos en etapa `classification`/`embeddings` con `openai` | API key inválida/agotada o sin red | Probar la key; los jobs se reprocesan al corregir |
| 503 `ai_unavailable` en búsqueda semántica/chat | Proveedor caído | Igual que arriba; la búsqueda textual sigue operativa |
| Búsqueda semántica sin resultados tras cambiar modelo | Dimensión de vectores mezclada | Reprocesar documentos (ver §7) |
| 401 constantes tras redesplegar | `SECRET_KEY` cambió | Es esperado: sesiones invalidadas |
| `database is locked` (SQLite) con mucha concurrencia | Límite del motor | Migrar a PostgreSQL (perfil compose) |
| CORS bloqueado en el navegador | Origen no listado | Añadir el origen exacto a `CORS_ORIGINS` |

## 11. Actualización del sistema

1. Respaldar (§9). 2. Obtener la nueva versión. 3. Instalar dependencias
   nuevas (`pip install -r ...`, `npm install`). 4. `alembic upgrade head`.
5. Reiniciar. 6. Verificar `/health` y una carga de humo.
CI (`.github/workflows/ci.yml`) valida pruebas y build en cada push.

## 12. Seguridad operativa

- Rote `SECRET_KEY` y contraseñas seed al pasar a producción; use HTTPS por
  reverse proxy (nginx/caddy) delante del backend.
- Revise periódicamente la auditoría (logins fallidos repetidos).
- Mantenga `MAX_UPLOAD_MB` acorde a su capacidad de disco.
- Los respaldos contienen datos de negocio: guárdelos cifrados y con acceso
  restringido.

## 13. Mantenimiento periódico sugerido

| Frecuencia | Tarea |
|-----------|-------|
| Diario | Respaldo automatizado; revisar errores recientes del dashboard |
| Semanal | Revisar auditoría y jobs fallidos; espacio en disco de `storage/` |
| Mensual | Actualizar dependencias con CI en verde; probar una restauración |
| Al cambiar modelo IA | Reprocesar corpus y re-ejecutar `scripts/evaluate_ground_truth.py` |
