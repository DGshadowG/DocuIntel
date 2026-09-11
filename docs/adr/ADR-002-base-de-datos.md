# ADR-002: SQLite por defecto con ruta de migración a PostgreSQL

- Estado: aceptada (2026-09-10)
- Contexto: la máquina de desarrollo/evaluación no tiene Docker ni PostgreSQL
  instalados. El requisito pedía preferiblemente PostgreSQL + pgvector.

## Decisión

`DATABASE_URL` conmutable: SQLite (archivo `database/docuintel.db`) por defecto
para desarrollo y evaluación local; PostgreSQL 16 en el perfil docker-compose
para producción. SQLAlchemy 2 + Alembic con `render_as_batch` para que las
migraciones funcionen en ambos motores. WAL + foreign_keys activados en SQLite.

## Alternativas consideradas

- **Exigir PostgreSQL local**: rompía el criterio "la aplicación inicia desde
  cero siguiendo el README" en la máquina objetivo.
- **Solo SQLite**: insuficiente para un despliegue empresarial real; por eso el
  perfil compose usa PostgreSQL.

## Consecuencias

- El arranque local no necesita servicios externos.
- Los tipos usados (Integer, String, Text, LargeBinary, DateTime, Float) son
  portables entre ambos motores; las pruebas corren igual en CI (Linux).
