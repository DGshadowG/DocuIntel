# 12 — Guion del Video de Demostración (máx. 5:00)

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**

> Preparación previa a grabar: sistema iniciado (`scripts\start.ps1`), corpus
> de 30 documentos cargado (`scripts\load_corpus.py`), sesión cerrada, un
> archivo `factura_demo.txt` listo en el escritorio (puede generarse copiando
> `sample_documents/factura_08.txt`). Resolución 1920×1080, zoom del navegador
> 100%. Este guion está cronometrado por bloques; el tiempo total es 5:00.

| Tiempo | Narración (texto del narrador) | Pantalla | Acción exacta |
|--------|-------------------------------|----------|---------------|
| 0:00–0:20 | "Las empresas acumulan carpetas con cientos de facturas, contratos y hojas de vida imposibles de consultar. DocuIntel convierte ese archivo muerto en un sistema que clasifica, resume, extrae datos y responde preguntas con evidencia. Veámoslo funcionando." | Portada con logo + carpeta de archivos → transición al login | Mostrar diapositiva 2 s, cambiar a http://localhost:5173 |
| 0:20–0:45 | "La arquitectura: un frontend React, una API FastAPI con quince tablas y un pipeline asíncrono, y una capa de IA intercambiable: OpenAI, Ollama local o un motor determinista para pruebas. Los vectores se comparan por similitud coseno y todo queda auditado." | Diagrama de contenedores del documento de diseño | Mostrar `docs/02-diseno.md` §1.2 renderizado |
| 0:45–1:20 | "Ingresamos como administrador. El sistema usa JWT y contraseñas bcrypt. Este es el repositorio 'Documentos Corporativos' con treinta documentos ya procesados: diez facturas, diez contratos y diez hojas de vida en PDF, DOCX y TXT. Cada usuario ve solo sus repositorios; los permisos son por propietario y miembros." | Login → Repositorios → detalle del repositorio | Iniciar sesión con el admin del seed; abrir Repositorios; abrir "Documentos Corporativos"; señalar KPIs y miembros |
| 1:20–2:10 | "Cargamos un documento nuevo. El sistema valida formato real por firma binaria y tamaño, lo guarda con clave segura y lo procesa: extrae el texto, lo segmenta, lo clasifica, lo resume, extrae los campos y genera embeddings. Vean el estado pasar de 'En cola' a 'Completado' en vivo." | Zona de carga del repositorio → tabla de documentos | Cargar `factura_demo.txt`; esperar el cambio de estado (se actualiza solo); abrir el documento |
| 2:10–2:45 | "Aquí está el resultado: categoría 'Financiero' con su confianza y el modelo usado, un resumen del contenido, y los datos estructurados de la factura: proveedor, número, fechas, subtotal, impuestos, total y moneda — validados con esquemas tipados. Si la IA se equivocara, la categoría se corrige manualmente sin perder la predicción original." | Detalle del documento | Recorrer con el cursor: clasificación → resumen → datos extraídos; abrir el menú "Corregir categoría" sin confirmar |
| 2:45–3:25 | "Dos búsquedas. La textual encuentra coincidencias exactas y las resalta con documento y página. La semántica busca por significado: pido 'personas con experiencia en desarrollo de software' y me trae hojas de vida de programadores aunque no usen esas palabras, ordenadas por similitud." | Buscar (modo textual, luego semántico) | Textual: buscar el número de una factura del corpus; cambiar a Semántica: escribir la consulta de perfiles y mostrar los scores |
| 3:25–4:05 | "Y la consulta en lenguaje natural. Primera pregunta: el total de una factura concreta — responde con el valor y cita la fuente con página y fragmento. Segunda: la fecha de terminación de un contrato — cita el contrato exacto. Tercera: las habilidades de una candidata — cita su hoja de vida. Y si pregunto algo que no está en los documentos, el sistema lo admite: 'no se encontró evidencia suficiente'. Sin inventos." | Consulta IA | Hacer las 3 preguntas preparadas del corpus (ver nota) y la de la bandeja paisa; señalar las citas y el aviso de sin evidencia |
| 4:05–4:25 | "El dashboard sale de la base de datos real: treinta y un documentos, distribución por categoría, formato y estado, tendencia de cargas y errores recientes con su causa." | Dashboard | Recorrer tarjetas, barras y tendencia |
| 4:25–4:45 | "Calidad verificada: 71 pruebas de backend con 83% de cobertura, 11 de frontend, E2E con navegador real, y evaluación contra ground truth: clasificación y extracción al cien por ciento sobre el corpus. Todas las evidencias están en el repositorio." | Terminal con `pytest` finalizando + carpeta evidence/ | Mostrar `evidence/test-results/pytest-backend.txt` (final) y las capturas |
| 4:45–5:00 | "El despliegue es reproducible: un script instala, migra y siembra; docker-compose entrega el perfil de producción con PostgreSQL. DocuIntel: de una carpeta de archivos a respuestas con evidencia. Gracias." | README (inicio rápido) → diapositiva de cierre | Mostrar README; cerrar con portada |

**Preguntas RAG preparadas (datos del corpus real):** tomar de
`sample_documents/rag_eval.json` las tres primeras (total de la factura
FV-2024-100, fecha de terminación del contrato de contrato_01, habilidades de
la persona de hoja_de_vida_01) — así narración y datos coinciden siempre.

## Plan alternativo ante fallos

| Riesgo en vivo | Plan B |
|----------------|--------|
| El procesamiento tarda más de lo esperado en cámara | El corpus ya está procesado: usar un documento existente y mostrar el historial de jobs (duración real) en lugar de la carga en vivo |
| Falla el proveedor de IA configurado | Grabar con `AI_PROVIDER=deterministic` (offline, mismo flujo y citas) |
| El navegador/SO se congela | Tener las 11 capturas de `evidence/screenshots/` como respaldo para narrar sobre imágenes |
| Se corta la toma | El guion está por bloques independientes: regrabar solo el bloque afectado |

> **Nota:** este es el guion para grabar el video; el video en sí no se
> incluye en el repositorio y debe grabarse siguiendo este documento.
