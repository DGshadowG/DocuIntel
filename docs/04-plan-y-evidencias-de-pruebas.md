# 04 — Plan y Evidencias de Pruebas

**Proyecto:** DocuIntel — Sistema Inteligente de Gestión y Análisis Documental
**UTS — Desarrollo de Aplicaciones Empresariales — VI semestre**
**Fecha de ejecución de las evidencias:** 2026-09-11

---

## 1. Alcance

Se prueba el sistema completo: autenticación y autorización, gestión de
repositorios y documentos, validaciones de carga y seguridad, pipeline de IA
(extracción, clasificación, resumen, extracción estructurada, embeddings),
búsqueda textual y semántica, consulta RAG con citas, dashboard, auditoría,
manejo de errores y el flujo E2E por interfaz real.

## 2. Estrategia

| Nivel | Herramienta | Cantidad | Entorno |
|-------|------------|----------|---------|
| Unitarias (chunking, vectores, saneamiento, proveedor IA, esquemas, JWT) | pytest | 15 | BD SQLite temporal por sesión |
| Integración/API (endpoints reales con TestClient) | pytest | 56 | Ídem + storage temporal |
| Frontend (componentes y login) | Vitest + Testing Library | 11 | jsdom |
| E2E interfaz real (navegador) | Playwright + Chromium | 3 | Backend+frontend vivos |
| E2E por API (flujo de negocio completo) | script `e2e_flow.py` | 24 pasos | Sistema vivo |
| Evaluación IA vs ground truth | script `evaluate_ground_truth.py` | 30 docs / 130 campos | Sistema vivo |

Reglas: pruebas repetibles (BD y storage aislados, proveedor de IA
determinista con semillas fijas), sin dependencia de servicios externos, y
ninguna prueba se declara aprobada sin ejecución real (salidas guardadas en
`evidence/test-results/`).

## 3. Ambiente de pruebas

Windows 11, Python 3.9.13 (venv), Node 23.9.0, SQLite temporal por sesión de
pytest, `AI_PROVIDER=deterministic`, `MAX_UPLOAD_MB=5` (pruebas), corpus
sintético generado con semilla 42.

## 4. Datos de prueba

- Corpus `sample_documents/`: 30 documentos (10 facturas, 10 contratos, 10
  hojas de vida; 12 PDF / 9 DOCX / 9 TXT) + `ground_truth.json` + `rag_eval.json`.
- Archivos adversarios generados en las pruebas: `.exe`, PDF con firma falsa,
  PDF corrupto, TXT vacío, archivo de 6 MB, nombre con `..\..\`.

## 5. Casos de prueba y resultados

Convención: los TC-01..26 del enunciado se mapean a pruebas automatizadas; la
columna "Prueba" indica archivo::caso. **Resultado obtenido: los 71 casos de
pytest, 11 de Vitest y 3 de Playwright pasaron** (evidencias §7).

| TC | Caso | Prueba automatizada | Resultado esperado | Obtenido | Estado |
|----|------|--------------------|--------------------|----------|--------|
| 01 | Login válido | test_auth_security.py::test_tc01 | 200 + JWT + usuario | Igual | ✅ |
| 02 | Login inválido | ::test_tc02, ::test_tc02b | 401 `invalid_credentials` | Igual | ✅ |
| 03 | Acceso no autorizado | ::test_tc03, tc03b, tc03c | 401 sin token / 403 sin rol | Igual | ✅ |
| 04 | CRUD repositorio | test_repositories.py::test_tc04 | crear/leer/editar/eliminar + 404 final | Igual | ✅ |
| 05 | Carga PDF | test_documents_upload.py::test_tc05 | 201, tipo pdf, job creado | Igual | ✅ |
| 06 | Carga DOCX | ::test_tc06 | 201, tipo docx | Igual | ✅ |
| 07 | Carga TXT | ::test_tc07 | 201, tipo txt | Igual | ✅ |
| 08 | Formato no permitido | ::test_tc08, tc08b | 400 `invalid_format` / `invalid_content` (firma) | Igual | ✅ |
| 09 | Archivo demasiado grande | ::test_tc09 | 413 `file_too_large` | Igual | ✅ |
| 10 | Path traversal | ::test_tc10 + test_units (sanitize/storage) | nombre saneado, clave UUID sin `..` | Igual | ✅ |
| 11 | Extracción de texto | test_pipeline_ai.py::test_tc11 | texto >100 chars y chunks para pdf/docx/txt | Igual | ✅ |
| 12 | Clasificación 3 categorías | ::test_tc12 | financiero/legal/talento_humano correctas | Igual | ✅ |
| 13 | Resumen | ::test_tc13 | resumen >50 chars con modelo registrado | Igual | ✅ |
| 14 | Extracción factura | ::test_tc14 | número, subtotal, impuestos, total, moneda = ground truth | Igual | ✅ |
| 15 | Extracción contrato | ::test_tc15 | fechas, duración, ≥3 obligaciones = ground truth | Igual | ✅ |
| 16 | Extracción hoja de vida | ::test_tc16 | nombre, habilidades, experiencia, idiomas = ground truth | Igual | ✅ |
| 17 | Búsqueda textual | test_search_rag_dashboard.py::test_tc17 | hit correcto con término resaltado y página | Igual | ✅ |
| 18 | Búsqueda semántica | ::test_tc18 | hoja de vida en top-3 para consulta de perfil | Igual | ✅ |
| 19 | RAG con cita | ::test_tc19 | grounded, ≥1 cita del documento correcto, métricas | Igual | ✅ |
| 20 | RAG sin evidencia | ::test_tc20 | grounded=false, frase estándar, 0 citas | Igual | ✅ |
| 21 | Aislamiento entre usuarios | test_auth_security.py::test_tc21 (+búsqueda/conversación ajenas) | 403 en ver/editar/eliminar; sin fugas en listados | Igual | ✅ |
| 22 | Eliminación y limpieza | test_documents_upload.py::test_tc22 | borra doc + texto + chunks + embeddings + archivo físico | Igual | ✅ |
| 23 | Fallo proveedor IA | test_pipeline_ai.py::test_tc23 | 3 intentos, fallido con etapa y error; recuperación al reprocesar | Igual | ✅ |
| 24 | Reintento procesamiento | ::test_tc24 | reproceso idéntico e idempotente (2 jobs completados) | Igual | ✅ |
| 25 | Indicadores dashboard | ::test_tc25 | totales, distribuciones, tendencia 14 días, tiempo medio reales | Igual | ✅ |
| 26 | Flujo E2E principal | Playwright `flujo-principal.spec.ts` + `scripts/e2e_flow.py` | recorrido completo con capturas / 24 pasos API | 3/3 y 24/24 | ✅ |

Casos adicionales más allá de los 26 (también ejecutados y aprobados):
payload de login inválido (422), usuario inexistente, logout+me, validación de
nombre de repositorio, gestión de miembros (agregar/duplicado/denegado/quitar),
estadísticas vacías, carga múltiple, archivo vacío, carga en repo ajeno (403),
descarga byte a byte, filtros+paginación de documentos, PDF corrupto → fallo
con reintentos consumidos, corrección manual de categoría conservando
predicción, precisión de clasificación ≥80% en corpus TXT, filtros en ambas
búsquedas, permisos en búsqueda, historial de conversación, conversación ajena
denegada, dashboard sin repos, auditoría (registro + 403 no admin), CRUD de
usuarios admin (duplicado, contraseña corta, autodesactivación prohibida),
unitarias de chunking/vectores/sanitización/embeddings/JWT expirado-alterado.

## 6. Pruebas de seguridad ejecutadas

1. Bypass de autenticación (sin token, token falso, token expirado, token
   alterado) → 401 en todos los casos.
2. Escalamiento horizontal (usuario B sobre recursos de A: repositorio,
   documento vía búsqueda, conversación) → 403/aislado.
3. Escalamiento vertical (usuario estándar a /users, /audit-logs) → 403.
4. Path traversal en nombre de archivo y en claves de storage → neutralizado
   (saneamiento + confinamiento de rutas verificado unitariamente).
5. Contenido falsificado (extensión pdf con bytes arbitrarios) → 400 por firma.
6. Contraseñas: hash bcrypt verificado en BD; nunca en texto plano.

## 7. Evidencias reales

| Evidencia | Archivo |
|-----------|---------|
| Salida completa pytest (71 passed) + cobertura por módulo | `evidence/test-results/pytest-backend.txt` |
| Cobertura XML | `evidence/test-results/coverage.xml` |
| Salida Vitest (11 passed) | `evidence/test-results/vitest-frontend.txt` |
| Salida Playwright (3 passed) | `evidence/test-results/playwright-e2e.txt` |
| Flujo E2E por API, 24 pasos con detalle | `evidence/test-results/e2e-api-results.json` y `e2e-api-log.txt` |
| Carga real del corpus (30/30 completados) | `evidence/test-results/load-corpus.txt` |
| Evaluación vs ground truth | `evidence/test-results/ground-truth-eval.json` y `.txt` |
| Capturas reales del flujo E2E (11 pantallas) | `evidence/screenshots/01..11-*.png` |

## 8. Métricas

- **Pruebas backend:** 71/71 aprobadas — cobertura de líneas **83%**
  (`app/` completo; los módulos de proveedor LLM openai/ollama no se cubren en
  pruebas porque requieren servicios externos — decisión documentada §9).
- **Pruebas frontend:** 11/11 aprobadas. **E2E:** 3/3 UI + 24/24 pasos API.
- **Clasificación vs ground truth:** 30/30 = **100%** (corpus sintético,
  proveedor determinista).
- **Extracción vs ground truth:** 130/130 campos = **100%**.
- **RAG:** 3/3 preguntas con cita correcta al documento fuente; 1/1 pregunta
  sin evidencia manejada correctamente (sin alucinación).
- **Procesamiento del corpus:** 30/30 completados, 0 fallidos.

## 9. Registro de defectos

| ID | Descripción | Severidad | Reproducción | Causa | Corrección | Prueba de regresión | Estado |
|----|-------------|-----------|--------------|-------|-----------|--------------------|--------|
| DEF-001 | `pip install` fallaba compilando greenlet | Alta (bloqueo de instalación) | instalar requirements en Py3.9/Win | SQLAlchemy arrastraba greenlet sin wheel para 3.9 | fijar `greenlet==3.1.1` | instalación reproducible en install.ps1 + CI | Cerrado |
| DEF-002 | Import de la app fallaba por `EmailStr` | Alta | `import app.main` | faltaba extra `email` de pydantic | `pydantic[email]==2.9.2` | arranque probado en todas las suites | Cerrado |
| DEF-003 | Login de seed fallaba con 422 | Alta | login con `admin@docuintel.local` | email-validator rechaza TLD reservados (`.local`) | dominios `docuintel.co` / `test-docuintel.co` en seed y pruebas | TC-01 | Cerrado |
| DEF-004 | GET /documents/{id} devolvía 500 tras procesar | Alta | subir doc y abrir detalle | relaciones `Mapped[list]` sin tipo → SQLAlchemy las trató como escalares | anotar `Mapped[List["X"]]` en las 8 colecciones | TC-11..16 y detalle en E2E | Cerrado |
| DEF-005 | Total de factura extraído = subtotal | Media | extraer factura con "Subtotal" | regex `total` coincidía dentro de "Subtotal" | lookbehind negativo `(?<![a-zA-Z])total` | test_extraccion_montos + TC-14 | Cerrado |
| DEF-006 | Idiomas no extraídos en hojas de vida | Media | extraer hv con IDIOMAS al final | el corte de sección exigía otro encabezado en mayúsculas o fin estricto | aceptar línea en blanco o fin de texto | TC-16 | Cerrado |
| DEF-007 | E2E Playwright: localizadores ambiguos (strict mode) | Baja | correr E2E dos veces | texto duplicado (resumen+campo) y residuo de corrida fallida | `exact:true` / `.first()` + limpieza del dato E2E | suite Playwright 3/3 | Cerrado |

## 10. Matriz requisito–prueba

Incluida como columnas "Prueba" y "Evidencia" de la matriz completa en
`docs/08-matriz-trazabilidad.md` (RF-001..032 → TC/archivo de prueba →
evidencia). Ningún requisito quedó sin al menos una prueba ejecutada.

## 11. Conclusiones

- Las 26 pruebas mínimas exigidas y 60+ casos adicionales se ejecutaron con
  resultados reales y reproducibles; no hay casos declarados sin ejecución.
- Los 7 defectos encontrados durante el desarrollo fueron corregidos y cuentan
  con prueba de regresión; ninguno quedó abierto.
- La evaluación contra ground truth valida el pipeline completo de IA
  (clasificación y extracción al 100% sobre el corpus sintético con el
  proveedor determinista); la calidad con LLM real depende del proveedor
  configurado y queda cubierta por la misma batería de evaluación
  (`scripts/evaluate_ground_truth.py`), reejecutable tras cambiar `AI_PROVIDER`.
