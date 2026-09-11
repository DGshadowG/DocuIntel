# 01 — Documento de Análisis

**Proyecto:** DocuIntel — Sistema Inteligente de Gestión y Análisis Documental
**Institución:** Unidades Tecnológicas de Santander (UTS)
**Programa:** Tecnología en Desarrollo de Software — VI semestre
**Asignatura:** Desarrollo de Aplicaciones Empresariales
**Docente:** Wilson Castaño Galviz
**Integrantes:** [NOMBRE DEL INTEGRANTE 1], [NOMBRE DEL INTEGRANTE 2]
**Grupo:** [GRUPO]
**Fecha:** Septiembre de 2026

---

## 1. Problema y contexto empresarial

Las organizaciones acumulan carpetas con cientos de archivos heterogéneos
(facturas, contratos, hojas de vida) en PDF, DOCX y TXT. Ese almacenamiento es
**pasivo**: encontrar "el contrato que vence este año" o "la factura del
proveedor X" exige abrir archivos uno por uno; nadie sabe qué contiene el
repositorio ni puede responder preguntas sobre él. El conocimiento existe pero
no es consultable.

## 2. Necesidad y oportunidad

- **Necesidad:** convertir el repositorio pasivo en un sistema que entienda el
  contenido: clasifique, resuma, extraiga datos y responda preguntas con
  evidencia verificable.
- **Oportunidad:** las técnicas de RAG (Retrieval-Augmented Generation),
  embeddings y extracción estructurada permiten construir esa capa de
  inteligencia sobre documentos existentes, sin migrar los archivos ni cambiar
  la forma de trabajar de la empresa.

## 3. Objetivo general

Diseñar, desarrollar, probar, documentar e implementar una aplicación web que
gestione repositorios documentales (PDF, DOCX, TXT) y aplique IA para
transformar información no estructurada en información útil: clasificación,
resumen, extracción de campos, búsqueda semántica y consulta en lenguaje
natural con citas.

## 4. Objetivos específicos

1. Implementar autenticación segura con roles (administrador/usuario) y
   autorización por repositorio (propietario/miembro).
2. Implementar la gestión de repositorios y el ciclo de vida completo de los
   documentos (carga, consulta, descarga, eliminación, estados, reintentos).
3. Construir un pipeline asíncrono de procesamiento: extracción de texto,
   segmentación, clasificación (≥3 categorías), resumen, extracción
   estructurada (≥3 esquemas) y embeddings.
4. Implementar búsqueda textual y semántica respetando permisos.
5. Implementar consulta RAG con historial, citas por documento/página y manejo
   explícito de preguntas sin evidencia.
6. Construir un dashboard con indicadores calculados de la base de datos.
7. Verificar el sistema con un corpus sintético de 30 documentos, pruebas
   automatizadas y evaluación contra ground truth.

## 5. Alcance

**Incluye:** aplicación web SPA + API REST versionada; 3 formatos (PDF, DOCX,
TXT); 3 categorías de clasificación; 3 esquemas de extracción; búsqueda textual
y semántica; chat RAG por repositorio con citas; dashboard; auditoría; gestión
de usuarios (admin); corpus de 30 documentos sintéticos; despliegue local
reproducible con scripts y perfil docker-compose para producción.

## 6. Exclusiones

- OCR de PDF escaneados (los PDF sin capa de texto se marcan como fallidos con
  mensaje claro; queda como trabajo futuro).
- Edición de documentos dentro del sistema (solo gestión y análisis).
- Versionamiento de documentos (un archivo = un registro; re-subir crea otro).
- Notificaciones por correo, SSO/LDAP, firma electrónica.
- Aplicación móvil nativa (la web es responsive).

## 7. Actores

| Actor | Descripción |
|-------|-------------|
| Administrador | Gestiona usuarios, ve todos los repositorios, consulta auditoría |
| Usuario estándar | Crea repositorios propios, es miembro de otros, carga y consulta documentos |
| Worker de procesamiento | Actor de sistema: ejecuta el pipeline de IA sobre los documentos en cola |
| Proveedor de IA | Servicio externo o local que clasifica, resume, extrae y genera embeddings |

## 8. Personas

- **Marcela (48, jefe administrativa):** guarda facturas y contratos; necesita
  encontrar "cuánto se pagó a X" sin abrir 40 PDF. Usa el buscador y el chat.
- **Julián (29, analista de talento humano):** recibe hojas de vida; necesita
  filtrar por habilidades y ver perfiles resumidos. Usa clasificación y
  extracción estructurada.
- **Andrés (35, administrador TI):** crea las cuentas, vigila los errores de
  procesamiento y la auditoría. Usa el panel de usuarios y los logs.

## 9. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema permite iniciar sesión con correo y contraseña y emite un token JWT | Must |
| RF-002 | El sistema permite cerrar sesión y registra el evento en auditoría | Must |
| RF-003 | Existen dos roles: administrador y usuario estándar, con permisos diferenciados | Must |
| RF-004 | El administrador crea, lista, edita y activa/desactiva usuarios | Must |
| RF-005 | Un usuario crea, consulta, edita y elimina (con confirmación) repositorios propios | Must |
| RF-006 | El propietario agrega/quita miembros a un repositorio por correo | Must |
| RF-007 | Solo propietario, miembros o admin acceden a un repositorio y sus documentos | Must |
| RF-008 | El sistema acepta carga individual y múltiple de PDF, DOCX y TXT | Must |
| RF-009 | El sistema rechaza formatos no permitidos validando extensión y firma binaria (números mágicos) | Must |
| RF-010 | El sistema rechaza archivos que exceden el tamaño máximo configurable | Must |
| RF-011 | El sistema sanea nombres de archivo y usa claves de almacenamiento generadas por el servidor (previene path traversal) | Must |
| RF-012 | Cada documento muestra estado: pendiente, en cola, procesando, completado o fallido | Must |
| RF-013 | El pipeline extrae el texto de PDF, DOCX y TXT y detecta documentos vacíos/ilegibles | Must |
| RF-014 | El pipeline segmenta el texto en chunks con solapamiento y mapeo a página | Must |
| RF-015 | El pipeline clasifica cada documento en: financiero, legal, talento_humano u otro | Must |
| RF-016 | El usuario puede corregir la categoría sin perder la predicción original, su confianza y el modelo | Should |
| RF-017 | El pipeline genera un resumen en español por documento | Must |
| RF-018 | El pipeline extrae campos estructurados según esquema: factura, contrato u hoja de vida, validados con Pydantic | Must |
| RF-019 | El pipeline genera embeddings por chunk y los persiste con modelo y dimensión | Must |
| RF-020 | Los documentos fallidos muestran el error técnico y permiten reintento (reprocesamiento idempotente) | Must |
| RF-021 | El usuario descarga el archivo original y consulta el texto extraído | Must |
| RF-022 | El usuario elimina documentos; se limpian archivo físico, texto, chunks, embeddings y resultados | Must |
| RF-023 | La lista de documentos ofrece filtros (repositorio, estado, categoría, formato, nombre) y paginación | Must |
| RF-024 | Búsqueda textual por contenido y metadatos con fragmentos resaltados y ubicación (documento/página) | Must |
| RF-025 | Búsqueda semántica por embeddings con filtros y puntaje de similitud | Must |
| RF-026 | El chat RAG responde preguntas sobre un repositorio usando solo sus documentos, con citas (documento, página, fragmento, similitud) | Must |
| RF-027 | El chat mantiene historial de conversaciones por usuario | Must |
| RF-028 | Cuando no hay evidencia suficiente, el chat lo dice explícitamente y no inventa | Must |
| RF-029 | El chat registra métricas: latencia, número de fragmentos y modelo usado | Should |
| RF-030 | El dashboard muestra totales, distribuciones por categoría/formato/estado, procesados/fallidos, actividad reciente, tendencia de cargas 14 días, errores recientes y tiempo medio de procesamiento | Must |
| RF-031 | El administrador consulta el registro de auditoría con filtro por acción y paginación | Should |
| RF-032 | El proveedor de IA es configurable por variables de entorno (openai/ollama/deterministic) | Must |

## 10. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Contraseñas cifradas con bcrypt (nunca en texto plano) |
| RNF-002 | Autenticación stateless con JWT firmado (HS256) y expiración configurable |
| RNF-003 | CORS restringido a orígenes configurados |
| RNF-004 | Errores HTTP consistentes `{error:{code,message,correlation_id}}`; sin stack traces al usuario |
| RNF-005 | Logs estructurados JSON con identificador de correlación por petición |
| RNF-006 | Ningún secreto versionado; configuración por `.env` (con `.env.example`) |
| RNF-007 | Arranque reproducible: script de instalación + migraciones versionadas + seed idempotente |
| RNF-008 | La interfaz es responsive (escritorio y móvil), en español, con contraste y navegación por teclado adecuados |
| RNF-009 | Las pruebas automatizadas son repetibles y no dependen de servicios externos (proveedor determinista) |
| RNF-010 | El pipeline es asíncrono: la carga responde de inmediato y el procesamiento continúa en segundo plano |
| RNF-011 | Reintentos controlados (máx. 3) con registro del error por etapa |
| RNF-012 | La API está versionada (`/api/v1`) y documentada con OpenAPI/Swagger |

## 11. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Todo repositorio tiene exactamente un propietario; el propietario no puede ser removido de los miembros |
| RN-002 | Un usuario solo ve repositorios donde es propietario o miembro; el admin ve todos |
| RN-003 | Solo propietario o admin editan/eliminan un repositorio o gestionan miembros |
| RN-004 | Formatos permitidos: PDF, DOCX, TXT; tamaño máximo por archivo configurable (20 MB por defecto) |
| RN-005 | Categorías válidas: financiero, legal, talento_humano, otro; el esquema de extracción se elige por la categoría predicha |
| RN-006 | La corrección manual de categoría prevalece sobre la predicción, pero la predicción, confianza y modelo se conservan |
| RN-007 | Un documento con job activo (en cola/procesando) no admite otro reproceso simultáneo |
| RN-008 | Las respuestas RAG solo usan fragmentos de repositorios accesibles al usuario; sin evidencia suficiente no se responde contenido |
| RN-009 | Eliminar un documento o repositorio elimina en cascada sus derivados (texto, chunks, embeddings, resultados, conversaciones del repositorio) |
| RN-010 | Un administrador no puede desactivar su propia cuenta |

## 12. Historias de usuario (con criterios de aceptación)

**HU-001 — Iniciar sesión.** Como usuario quiero autenticarme con correo y
contraseña para acceder a mis repositorios.
*CA1:* credenciales válidas → token y redirección al dashboard. *CA2:*
credenciales inválidas → mensaje "Correo o contraseña incorrectos" sin revelar
cuál falló. *CA3:* usuario inactivo → acceso denegado (403).

**HU-002 — Crear repositorio.** Como usuario quiero crear repositorios para
organizar mis documentos.
*CA1:* nombre ≥2 caracteres → repositorio creado y visible en mi lista.
*CA2:* quedo registrado como propietario y miembro owner. *CA3:* otro usuario
no lo ve ni accede (403).

**HU-003 — Cargar documentos.** Como usuario quiero cargar uno o varios
archivos PDF/DOCX/TXT para que el sistema los procese.
*CA1:* carga válida → 201, documento "en cola" y job creado. *CA2:* `.exe` →
400 formato no permitido. *CA3:* archivo >20 MB → 413. *CA4:* PDF falso (firma
incorrecta) → 400. *CA5:* el estado progresa hasta "completado" sin intervención.

**HU-004 — Ver resultados de IA.** Como usuario quiero ver la categoría,
resumen y datos extraídos de cada documento.
*CA1:* documento completado muestra categoría con confianza y modelo. *CA2:*
resumen en español visible. *CA3:* según categoría, veo los campos del esquema
(factura/contrato/hoja de vida) con "No detectado" cuando falte un campo.

**HU-005 — Corregir categoría.** Como usuario quiero corregir una categoría mal
predicha sin perder la predicción original.
*CA1:* al corregir, la categoría efectiva cambia. *CA2:* la UI muestra "IA
predijo: X" tras la corrección. *CA3:* la predicción/confianza originales
permanecen en la base de datos.

**HU-006 — Buscar.** Como usuario quiero buscar por texto o por significado.
*CA1:* búsqueda textual resalta el término y muestra documento/página. *CA2:*
búsqueda semántica ordena por similitud y encuentra contenido sin coincidencia
literal. *CA3:* nunca aparecen resultados de repositorios ajenos.

**HU-007 — Preguntar a los documentos.** Como usuario quiero hacer preguntas en
lenguaje natural sobre un repositorio.
*CA1:* la respuesta cita fuentes (documento, página, fragmento, similitud).
*CA2:* pregunta sin soporte documental → "No se encontró evidencia suficiente"
sin citas. *CA3:* el historial de la conversación se conserva. *CA4:* se
registran latencia, fragmentos y modelo.

**HU-008 — Reintentar procesamiento.** Como usuario quiero reintentar un
documento fallido.
*CA1:* documento fallido muestra el error técnico. *CA2:* "Reprocesar" crea un
nuevo job y limpia resultados previos (idempotente). *CA3:* si el proveedor de
IA falla, el job reintenta hasta 3 veces y luego marca fallido.

**HU-009 — Dashboard.** Como usuario quiero un panel con indicadores de mis
repositorios.
*CA1:* totales y distribuciones coinciden con los datos reales. *CA2:* muestra
estados de carga/vacío/error. *CA3:* la tendencia cubre 14 días.

**HU-010 — Administrar usuarios.** Como administrador quiero crear y gestionar
cuentas.
*CA1:* creo usuarios con rol. *CA2:* correo duplicado → 409. *CA3:* desactivar
impide login. *CA4:* no puedo desactivarme a mí mismo.

**HU-011 — Auditoría.** Como administrador quiero ver quién hizo qué.
*CA1:* login, cargas, eliminaciones y preguntas quedan registradas con fecha,
usuario e IP. *CA2:* un usuario estándar recibe 403 al intentar verla.

## 13. Casos de uso

Diagrama en `docs/02-diseno.md` §4. Listado:

| CU | Nombre | Actores |
|----|--------|---------|
| CU-01 | Iniciar/cerrar sesión | Admin, Usuario |
| CU-02 | Gestionar usuarios | Admin |
| CU-03 | Gestionar repositorios y miembros | Usuario, Admin |
| CU-04 | Cargar documentos | Usuario, Admin |
| CU-05 | Procesar documento (pipeline IA) | Worker, Proveedor IA |
| CU-06 | Consultar documento y resultados de IA | Usuario, Admin |
| CU-07 | Corregir categoría | Usuario, Admin |
| CU-08 | Buscar (textual/semántica) | Usuario, Admin |
| CU-09 | Preguntar (RAG) | Usuario, Admin |
| CU-10 | Consultar dashboard | Usuario, Admin |
| CU-11 | Consultar auditoría | Admin |
| CU-12 | Reintentar procesamiento | Usuario, Admin |

### Especificación de casos de uso principales

**CU-04 — Cargar documentos.**
*Precondición:* sesión activa; permiso de escritura en el repositorio.
*Flujo principal:* 1) el usuario selecciona 1–20 archivos; 2) el sistema valida
extensión, firma binaria, tamaño y nombre; 3) guarda el binario con clave UUID;
4) crea el registro del documento (estado pendiente→en cola) y un job; 5)
responde 201 con documento y job.
*Flujos alternos:* A1 formato inválido → 400 `invalid_format`; A2 contenido no
coincide con la extensión → 400 `invalid_content`; A3 tamaño excedido → 413;
A4 archivo vacío → 400; A5 sin permiso → 403.
*Postcondición:* documento en cola visible en la UI con su estado.

**CU-05 — Procesar documento.**
*Precondición:* job en cola.
*Flujo principal:* 1) el worker toma el job más antiguo; 2) valida el archivo
físico; 3) extrae texto (por formato); 4) segmenta en chunks con página; 5)
clasifica; 6) resume; 7) extrae campos según categoría y valida con esquema;
8) genera embeddings; 9) marca completado con duración.
*Flujos alternos:* cualquier etapa falla → job vuelve a cola (hasta 3 intentos);
al agotar intentos → documento fallido con `[etapa] error` registrado.
*Postcondición:* resultados persistidos o error explicable; nunca un "éxito" vacío.

**CU-09 — Preguntar (RAG).**
*Precondición:* conversación en un repositorio accesible.
*Flujo principal:* 1) el usuario pregunta; 2) el sistema genera el embedding de
la pregunta; 3) recupera top-K chunks del repositorio (solo completados) por
similitud coseno; 4) filtra por umbral mínimo; 5) construye contexto etiquetado
[Fuente n] con documento y página; 6) el proveedor responde solo con ese
contexto; 7) se persisten mensaje, citas y métricas.
*Flujo alterno:* sin chunks sobre el umbral → respuesta fija "No se encontró
evidencia suficiente…", `grounded=false`, sin citas.

## 14. Priorización MoSCoW

- **Must:** RF-001..015, RF-017..028, RF-030, RF-032, RNF-001..012 (núcleo evaluable).
- **Should:** RF-016 (corrección manual), RF-029 (métricas RAG), RF-031 (auditoría visible).
- **Could:** OCR de escaneados, exportar resultados a CSV, notificaciones.
- **Won't (esta entrega):** versionamiento documental, SSO, móvil nativa.

Todos los Must y Should quedaron implementados; los Could/Won't están en
exclusiones y trabajo futuro.

## 15. Matriz inicial de trazabilidad

La matriz completa (requisito → historia → caso de uso → componente → endpoint
→ pantalla → código → prueba → evidencia → estado) está en
`docs/08-matriz-trazabilidad.md`. Resumen inicial problema→objetivo:

| Problema | Objetivo | Requisitos |
|----------|----------|-----------|
| Repositorio pasivo, sin control de acceso | O1 (seguridad) | RF-001..007, RNF-001..003 |
| Archivos ingobernables | O2 (gestión documental) | RF-008..012, RF-020..023 |
| Contenido no comprendido | O3 (pipeline IA) | RF-013..019, RF-032 |
| Información no encontrable | O4 (búsqueda) | RF-024..025 |
| Preguntas sin respuesta | O5 (RAG) | RF-026..029 |
| Sin visibilidad gerencial | O6 (dashboard) | RF-030..031 |
| Sin garantía de calidad | O7 (verificación) | RNF-007, RNF-009 + plan de pruebas |

## 16. Análisis de riesgos

| Riesgo | Prob. | Impacto | Mitigación | Responsable |
|--------|-------|---------|-----------|-------------|
| No disponer de API key de IA en la sustentación | Alta | Alto | Proveedor determinista offline totalmente funcional y honesto (modelo visible); cambio a LLM real = 1 variable | Equipo backend |
| PDF escaneados sin texto | Media | Medio | Detección explícita y estado fallido con mensaje claro; OCR documentado como trabajo futuro | Equipo backend |
| Entorno sin Docker/PostgreSQL/Redis | Alta (confirmado) | Medio | SQLite + worker embebido por defecto; compose PostgreSQL como perfil producción (ADR-002/004) | DevOps |
| Alucinaciones del LLM en RAG | Media | Alto | Contexto etiquetado, instrucción de citar, umbral de similitud, respuesta explícita "sin evidencia", citas verificables en UI | IA |
| Fuga de secretos al repositorio | Baja | Alto | `.env` fuera de git, `.env.example` sin valores reales, auditoría final de secretos | Todo el equipo |
| Datos personales reales en el corpus | Baja | Alto | Corpus 100% sintético con Faker y semilla fija; nota de licencia | QA |
| Pérdida de datos por eliminación accidental | Media | Medio | Confirmaciones en UI, scripts de backup/restore | DevOps |
