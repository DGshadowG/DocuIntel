# 13 — Presentación y Sustentación

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**
12 diapositivas con notas para el presentador y preguntas probables del jurado.

---

## Diapositiva 1 — Portada

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**
Unidades Tecnológicas de Santander · Tecnología en Desarrollo de Software · VI semestre
Desarrollo de Aplicaciones Empresariales · Docente: Wilson Castaño Galviz
Integrantes: [NOMBRE DEL INTEGRANTE 1] · [NOMBRE DEL INTEGRANTE 2] · Grupo [GRUPO] · Septiembre 2026

*Notas:* presentarse; una frase: "convertimos una carpeta de archivos en un
sistema que responde preguntas con evidencia".

## Diapositiva 2 — Problema

- Las empresas acumulan cientos de PDF, DOCX y TXT en carpetas pasivas.
- Encontrar "el contrato que vence este año" = abrir archivos uno a uno.
- El conocimiento existe pero **no es consultable** ni gobernable.

*Notas:* anclar con el ejemplo de la persona administrativa (persona "Marcela"
del análisis). Pregunta orientadora del proyecto.

## Diapositiva 3 — Objetivos y alcance

- **General:** app web que gestiona documentos y aplica IA para volverlos información útil.
- **Específicos:** seguridad por roles y membresías · gestión documental completa · pipeline IA (clasificar/resumir/extraer/embeddings) · búsqueda textual y semántica · RAG con citas · dashboard · verificación con corpus de 30 docs.
- **Exclusiones honestas:** OCR de escaneados, versionamiento, SSO, móvil nativa.

*Notas:* el alcance mínimo del enunciado está cubierto al 100%; las
exclusiones están documentadas desde el análisis.

## Diapositiva 4 — Requisitos

- 32 requisitos funcionales (RF-001..032) y 12 no funcionales, numerados y verificables.
- 11 historias de usuario con criterios de aceptación · 12 casos de uso especificados.
- Priorización MoSCoW: todos los Must y Should entregados.

*Notas:* mostrar 2 ejemplos concretos (RF-009 validación por firma binaria,
RF-028 "sin evidencia suficiente") para evidenciar que son verificables.

## Diapositiva 5 — Arquitectura

(insertar diagrama de contenedores de `docs/02-diseno.md` §1.2)

- SPA React+TS ↔ API FastAPI `/api/v1` (JWT) ↔ SQLite/PostgreSQL + storage de archivos.
- Worker asíncrono con cola transaccional en BD (sin Redis: ADR-004).
- Capa IA desacoplada: OpenAI-compatible · Ollama local · determinista offline (ADR-005).

*Notas:* justificar con el contexto real: la máquina objetivo no tiene
Docker/Redis; las decisiones están en 5 ADRs, no improvisadas.

## Diapositiva 6 — Modelo de datos

(insertar ER de `docs/02-diseno.md` §4)

- 15 tablas: usuarios/membresías, documentos y derivados (texto, chunks,
  embeddings), jobs, resultados IA (clasificación, resumen, extracción),
  chat (conversaciones/mensajes/citas), auditoría.
- Migraciones Alembic versionadas · FKs con cascada · seed idempotente.

*Notas:* subrayar que los binarios NO van en la BD (clave UUID en storage) y
que las citas RAG referencian chunk y documento reales.

## Diapositiva 7 — Pipeline de IA

archivo → validación (firma+tamaño+nombre) → storage → extracción de texto →
chunks (1200/200, página) → clasificación → resumen → extracción estructurada
(Pydantic) → embeddings (coseno) → índice → búsqueda/RAG

- Estados y errores por etapa · 3 reintentos · reprocesamiento idempotente.
- RAG: top-K con umbral de evidencia, contexto etiquetado [Fuente n], citas con página y similitud.

*Notas:* esta diapositiva responde el "requisito central de IA" del enunciado:
no es un CRUD con botón IA; cada etapa persiste resultados verificables.

## Diapositiva 8 — Funcionalidades (demo)

- 12 pantallas en español, responsive: login, dashboard, repositorios(+detalle),
  documentos(+detalle), buscar, consulta IA, usuarios, auditoría, 404.
- Corrección manual de categoría conservando la predicción.
- Búsqueda textual resaltada y semántica con score.
- Chat con historial, citas clicables y aviso de "sin evidencia".

*Notas:* aquí va la demo en vivo (o video). Ruta: login → repo → carga →
resultado IA → búsqueda ×2 → 3 preguntas RAG + 1 sin evidencia → dashboard.

## Diapositiva 9 — Seguridad

- bcrypt + JWT firmado · roles y membresías en cada consulta.
- Validación real de archivos (extensión + números mágicos) · anti path-traversal (nombres saneados + claves UUID).
- CORS restringido · errores sin stack trace (correlation id) · auditoría completa · cero secretos en el repositorio.

*Notas:* mencionar las pruebas de seguridad ejecutadas (bypass, escalamiento
horizontal/vertical, traversal, contenido falsificado).

## Diapositiva 10 — Pruebas y resultados

- **71** pytest (**83%** cobertura) · **11** Vitest · **3** E2E Playwright · **24** pasos E2E por API.
- Ground truth: clasificación **30/30 (100%)** · extracción **130/130 campos (100%)** · corpus 30/30 procesado sin fallos.
- 7 defectos encontrados → 7 corregidos con regresión (DEF-001..007).
- Evidencias reales en `evidence/` (salidas + 11 capturas).

*Notas:* insistir: ninguna prueba declarada sin ejecución; mostrar
`ground-truth-eval.json` si piden detalle.

## Diapositiva 11 — Despliegue

- Local reproducible: `install.ps1` → `start.ps1` (venv, migraciones, seed, corpus).
- Producción: docker-compose (PostgreSQL + backend con migración automática + nginx), healthchecks y volúmenes. *Declarado: no ejecutado en la máquina de desarrollo por ausencia de Docker.*
- CI en GitHub Actions: pruebas backend + typecheck/build/pruebas frontend.
- Backup/restore con scripts dedicados.

*Notas:* la transparencia sobre Docker suma credibilidad: todo lo demás tiene
evidencia de ejecución real.

## Diapositiva 12 — Conclusiones y trabajo futuro

- Ciclo completo demostrado: análisis → diseño → desarrollo → pruebas → implementación, con trazabilidad requisito→código→prueba→evidencia.
- La IA es verificable: resultados citados, modelo visible, evaluación contra ground truth.
- **Futuro:** OCR para escaneados, pgvector a escala, re-ranking del RAG, versionamiento documental, SSO.

*Notas:* cerrar con la pregunta orientadora respondida: la carpeta ahora
"comprende, organiza, busca y responde".

---

## Preguntas probables del jurado (con respuesta técnica)

1. **¿Por qué SQLite si el enunciado sugería PostgreSQL+pgvector?**
   Por reproducibilidad: la máquina objetivo no tiene Docker ni PostgreSQL.
   `DATABASE_URL` conmuta a PostgreSQL sin cambiar código (mismo esquema vía
   Alembic batch mode) y el compose de producción ya lo usa. Los vectores en
   BLOB + coseno NumPy resuelven este corpus en <10 ms; la ruta pgvector está
   escrita en ADR-003 con el plan de migración.

2. **¿Su IA es "de verdad" si usan un proveedor determinista?**
   La capa de IA tiene tres proveedores intercambiables; openai y ollama son
   integraciones LLM reales completas (prompts, JSON validado, embeddings).
   El determinista es un motor NLP clásico (keywords ponderadas, resumen
   extractivo, regex de extracción, feature-hashing embeddings) que existe
   para pruebas reproducibles y demos offline — y siempre se identifica como
   `deterministic-v1` en BD y UI. Activar un LLM real es una variable de
   entorno.

3. **¿Cómo evitan alucinaciones en el RAG?**
   Recuperación con umbral mínimo de similitud; contexto etiquetado por
   fuente; instrucción estricta de citar y de responder la frase estándar si
   no hay soporte; persistimos las citas (documento, página, fragmento,
   similitud) para que el usuario verifique; probado con TC-19/20 y
   `rag_eval.json` (pregunta imposible → sin evidencia, cero citas).

4. **¿Qué pasa si el proveedor de IA se cae a mitad de un procesamiento?**
   La etapa lanza `AIProviderError`, el job vuelve a cola hasta 3 intentos y
   luego queda fallido con `[etapa] error` visible; el usuario reprocesa
   cuando el servicio vuelve. Probado con TC-23 (inyección de fallo y
   recuperación).

5. **¿Cómo garantizan el aislamiento entre usuarios?**
   `permissions.py` centraliza la regla propietario/miembro/admin y TODA
   lectura (documentos, búsqueda, RAG, dashboard) se filtra por los
   repositorios accesibles resueltos server-side. Probado con TC-21 y casos de
   fuga en búsqueda y conversaciones.

6. **¿Por qué el pipeline reprocesa desde cero en vez de reanudar la etapa fallida?**
   Idempotencia simple y verificable: `_clear_derived()` borra derivados y
   reconstruye, evitando estados híbridos (chunks de una versión, embeddings
   de otra). El costo es bajo (segundos por documento) frente al riesgo de
   inconsistencia.

7. **¿Cómo validan que la extracción no corrompa datos?**
   Toda salida del proveedor pasa por esquemas Pydantic
   (InvoiceExtraction/ContractExtraction/ResumeExtraction) antes de
   persistirse; JSON inválido = etapa fallida registrada, nunca datos basura.
   Además se evalúa contra `ground_truth.json` (130/130 campos).

8. **¿Qué harían distinto a escala (10⁶ documentos)?**
   PostgreSQL+pgvector con índice HNSW (ADR-003), worker dedicado escalado
   horizontalmente (ADR-004), storage S3/MinIO (interfaz ya definida),
   colas por prioridad y re-ranking del RAG con cross-encoder.

9. **¿Cómo protegen las credenciales y datos sensibles?**
   Secretos solo en `.env` (no versionado, con `.env.example`); bcrypt;
   auditoría de acciones con IP; con proveedor externo los textos salen al
   servicio configurado — documentado, con alternativas local/offline para
   datos sensibles.

10. **¿Qué evidencia tienen de que todo lo anterior es cierto?**
    Salidas reales en `evidence/test-results/` (pytest, vitest, playwright,
    E2E API 24 pasos, carga del corpus, ground truth 100%) y 11 capturas
    reales del sistema en `evidence/screenshots/`; la matriz de trazabilidad
    enlaza cada requisito con su prueba y su evidencia.
