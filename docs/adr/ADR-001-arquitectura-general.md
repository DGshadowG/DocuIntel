# ADR-001: Monorepo FastAPI + React con capa de IA desacoplada

- Estado: aceptada (2026-09-10)
- Contexto: el proyecto integrador exige una aplicación web empresarial con
  pipeline de IA documental, ejecutable de forma reproducible en la máquina de
  los estudiantes (Windows 11, Python 3.9, Node 23, **sin Docker**) y evaluable
  por el docente.

## Decisión

Monorepo con `backend/` (FastAPI + SQLAlchemy 2 + Alembic) y `frontend/`
(React 18 + TypeScript + Vite + Tailwind). La lógica de IA vive detrás de una
interfaz `AIProvider` (clasificar, resumir, extraer, embeddings, responder RAG)
seleccionada por variable de entorno.

## Alternativas consideradas

- **Django + templates**: menos separación API/SPA y peor encaje con el
  requisito de API versionada y documentada (OpenAPI nativo en FastAPI).
- **Next.js full-stack**: el equipo domina Python para el pipeline de IA; mezclar
  el pipeline en Node aumentaba el riesgo.

## Consecuencias

- El frontend consume exclusivamente `/api/v1` (contratos tipados en ambos lados).
- Cualquier proveedor de IA nuevo se agrega implementando una clase y un valor
  de `AI_PROVIDER`, sin tocar pipeline ni endpoints.
