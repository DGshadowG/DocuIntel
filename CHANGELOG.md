# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [1.0.0] — 2026-09-11

### Agregado
- Autenticación JWT con bcrypt, roles admin/usuario y auditoría de acciones.
- CRUD de repositorios con miembros, estadísticas y aislamiento por permisos.
- Carga individual/múltiple de PDF, DOCX y TXT con validación de extensión,
  números mágicos, tamaño y saneamiento de nombres.
- Pipeline documental por etapas (validación → extracción → segmentación →
  clasificación → resumen → extracción estructurada → embeddings → indexación)
  con estados, reintentos (3) y reprocesamiento idempotente.
- Capa de IA desacoplada con tres proveedores: OpenAI-compatible, Ollama y
  determinista offline (usado por pruebas; identificado como `deterministic-v1`).
- Clasificación en 3 categorías (financiero, legal, talento humano) con
  corrección manual que conserva la predicción original.
- Extracción estructurada validada con Pydantic para facturas, contratos y
  hojas de vida.
- Búsqueda textual con resaltado y búsqueda semántica por embeddings (coseno).
- Chat RAG por repositorio con historial, citas (documento/página/fragmento),
  métricas (latencia, fragmentos, modelo) y manejo de "sin evidencia".
- Dashboard con indicadores reales: totales, distribución por categoría/formato/
  estado, tendencia de cargas 14 días, errores recientes, tiempo medio.
- Frontend React+TS completo (12 pantallas) responsive y accesible, en español.
- Corpus sintético reproducible de 30 documentos + ground truth + eval RAG.
- Suites de pruebas: 71 pytest (83% cobertura), 11 Vitest, 3 E2E Playwright,
  flujo E2E por API (24 pasos) y evaluación ground truth (100% clasificación).
- Scripts de operación PowerShell (install/start/stop/backup/restore),
  Dockerfiles + docker-compose (perfil PostgreSQL) y CI GitHub Actions.
- Documentación académica completa (análisis, diseño, desarrollo, pruebas,
  despliegue, manuales, trazabilidad, guion de video y presentación).

### Corregido durante el desarrollo
- DEF-001: `greenlet` sin wheel para Python 3.9/Windows — se fijó 3.1.1.
- DEF-002: `EmailStr` requería `email-validator` — se usa `pydantic[email]`.
- DEF-003: dominios reservados (`.local`) rechazados por el validador de correo
  — seeds y pruebas migrados a `docuintel.co`.
- DEF-004: relaciones `Mapped[list]` sin tipo hacían que SQLAlchemy tratara
  colecciones como escalares — anotadas como `Mapped[List["X"]]`.
- DEF-005: el regex de total de factura coincidía dentro de "Subtotal" — se
  añadió lookbehind negativo.
- DEF-006: la sección IDIOMAS al final de las hojas de vida no se extraía —
  el corte de sección ahora acepta línea en blanco o fin de texto.
