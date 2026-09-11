# ADR-005: Tres proveedores de IA con contrato único y determinista de respaldo

- Estado: aceptada (2026-09-10)
- Contexto: el sistema necesita IA real (clasificación, resumen, extracción,
  embeddings, RAG), pero el entorno de desarrollo/evaluación no tiene API key
  ni GPU garantizadas, y las pruebas automatizadas deben ser reproducibles.

## Decisión

Interfaz `AIProvider` con tres implementaciones seleccionables por `AI_PROVIDER`:

1. **openai** — API compatible con OpenAI (`/chat/completions`, `/embeddings`),
   sirve para OpenAI, Groq, Together, gateways corporativos. Modelos por defecto:
   `gpt-4o-mini` (chat) y `text-embedding-3-small` a 384 dimensiones.
2. **ollama** — modelos locales (`llama3.1`, `nomic-embed-text` 768d) sin API key.
3. **deterministic** — reglas en español + embeddings por feature hashing con
   signo (384d, TF logarítmico, normalizados L2) + resumen extractivo + RAG
   extractivo con umbral de evidencia.

Reglas de honestidad:
- El proveedor activo y el nombre del modelo se **persisten con cada resultado**
  y se muestran en la UI (`deterministic-v1` nunca se disfraza de LLM).
- Las pruebas automatizadas usan siempre `deterministic` (reproducible).
- Si el proveedor real falla, el job falla con el error registrado y permite
  reintento — jamás se degrada silenciosamente al determinista.

## Embeddings para español

- `text-embedding-3-small` es multilingüe y rinde bien en español; 384d
  (parámetro `dimensions`) equilibra calidad y almacenamiento.
- Alternativa local: `nomic-embed-text` (768d) vía Ollama.
- El determinista comparte pipeline y métrica (coseno), lo que permite validar
  todo el flujo sin red.

## Consecuencias

- Único paso externo para activar un LLM real: definir `OPENAI_API_KEY` (o
  instalar Ollama) y cambiar `AI_PROVIDER`. Nada más cambia.
- La dimensión del vector se guarda por embedding; cambiar de modelo requiere
  reprocesar (documentado en manual técnico).
