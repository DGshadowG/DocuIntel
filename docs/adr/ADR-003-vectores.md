# ADR-003: Embeddings en BLOB float32 + búsqueda coseno en proceso (NumPy)

- Estado: aceptada (2026-09-10)
- Contexto: la búsqueda semántica y el RAG requieren almacenar y comparar
  vectores. pgvector no está disponible (sin PostgreSQL local, ver ADR-002).

## Decisión

Cada chunk guarda su embedding como bytes float32 en la tabla `embeddings`
(columna `LargeBinary`, con modelo y dimensión). La búsqueda carga los vectores
del ámbito permitido (repositorios accesibles + filtros) y calcula similitud
coseno con NumPy en memoria.

## Números que la justifican

El corpus objetivo (30 documentos) produce ~40-80 chunks de 384 dimensiones.
Un escaneo brute-force de incluso 10 000 chunks × 384d son ~15 MB y <10 ms en
NumPy — órdenes de magnitud por debajo del umbral donde un índice ANN aporta.

## Ruta de migración (documentada, no especulativa)

Con PostgreSQL: crear columna `vector(384)` con pgvector, migrar los BLOB con
un script de una pasada y reemplazar `semantic_search()` por una consulta
`ORDER BY embedding <=> :query LIMIT :k`. La interfaz de `vectors.py` no cambia.

## Consecuencias

- Cero infraestructura adicional; los embeddings viajan en el backup estándar.
- Vectores de dimensión distinta (cambio de modelo) se ignoran en la búsqueda
  en lugar de romperla; reprocesar regenera todo.
