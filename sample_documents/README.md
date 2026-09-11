# Corpus sintético de prueba — 30 documentos

Corpus de demostración y evaluación del Sistema Inteligente de Gestión y
Análisis Documental.

## Contenido

| Tipo | Cantidad | Formatos |
|------|----------|----------|
| Facturas (`factura_01..10`) | 10 | 4 PDF, 3 DOCX, 3 TXT |
| Contratos (`contrato_01..10`) | 10 | 4 PDF, 3 DOCX, 3 TXT |
| Hojas de vida (`hoja_de_vida_01..10`) | 10 | 4 PDF, 3 DOCX, 3 TXT |

Total: 30 documentos — 12 PDF, 9 DOCX, 9 TXT.

Variaciones incluidas deliberadamente: longitudes distintas, monedas COP/USD/EUR,
formato de fecha corto y largo, factura sin fecha de vencimiento
(`factura_08`), contrato sin valor explícito (`contrato_07`), contratista
persona natural, 1–5 ítems por factura, 1–3 experiencias por hoja de vida.

## Archivos auxiliares

- `ground_truth.json` — categoría esperada y campos esperados por documento
  (usado por las pruebas y `scripts/evaluate_ground_truth.py`).
- `rag_eval.json` — preguntas de evaluación RAG con respuesta/fuente esperada,
  incluida una pregunta sin respuesta en el corpus (debe producir "sin
  evidencia suficiente").

## Reproducibilidad

Generado por `scripts/generate_corpus.py` con Faker (`es_CO`) y semilla fija 42.
Ejecutar el script regenera exactamente el mismo corpus.

## Licencia y origen de los datos

**Todos los datos son ficticios.** Nombres de personas, empresas, NIT,
direcciones, correos, cifras y fechas fueron generados por software
(biblioteca Faker) y no corresponden a personas ni organizaciones reales.
Cualquier coincidencia es fortuita. El corpus se entrega únicamente con fines
académicos dentro de este proyecto y puede reutilizarse libremente citando el
proyecto.
