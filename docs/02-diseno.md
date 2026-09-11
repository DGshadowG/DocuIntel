# 02 — Documento de Diseño

**Proyecto:** DocuIntel — Sistema Inteligente de Gestión y Análisis Documental
**UTS — Desarrollo de Aplicaciones Empresariales — VI semestre**

---

## 1. Arquitectura general

Aplicación web en tres capas + capa de IA desacoplada:

- **Frontend (SPA):** React 18 + TypeScript + Vite + Tailwind. Consume solo
  `/api/v1`. Autenticación por token en `localStorage` con interceptor Axios.
- **Backend (API):** FastAPI. Routers por dominio (auth, users, repositories,
  documents, search, conversations, dashboard, audit-logs), servicios de
  negocio, y worker de pipeline (hilo embebido o proceso aparte).
- **Datos:** SQLAlchemy 2 + Alembic. SQLite en desarrollo, PostgreSQL en el
  perfil de producción (ADR-002). Binarios en almacenamiento de archivos
  (sistema de archivos abstraído; claves UUID), nunca en la BD.
- **IA:** interfaz `AIProvider` con implementaciones `openai`, `ollama` y
  `deterministic` (ADR-005), seleccionada por configuración.

### 1.1 Diagrama de contexto

```mermaid
graph LR
    U[Usuario estandar] -->|HTTPS| FE[SPA DocuIntel]
    A[Administrador] -->|HTTPS| FE
    FE -->|/api/v1 JSON + JWT| BE[API FastAPI]
    BE --> DB[(Base de datos)]
    BE --> FS[(Almacen de archivos)]
    BE -->|clasificar / resumir / extraer / embeddings / RAG| IA[Proveedor de IA<br/>openai - ollama - deterministic]
```

### 1.2 Diagrama de contenedores

```mermaid
graph TB
    subgraph Cliente
        SPA[React SPA<br/>Vite + Tailwind]
    end
    subgraph Servidor
        API[FastAPI /api/v1<br/>auth, repos, docs, search, chat, dashboard, audit]
        WK[Worker de pipeline<br/>hilo embebido o proceso]
        ST[LocalStorage de archivos<br/>claves UUID]
    end
    subgraph Datos
        SQL[(SQLite / PostgreSQL<br/>15 tablas + Alembic)]
    end
    subgraph IA
        P1[OpenAI-compatible]
        P2[Ollama local]
        P3[Deterministic v1]
    end
    SPA -->|JSON + Bearer JWT| API
    API --> SQL
    API --> ST
    API -->|encola jobs| SQL
    WK -->|toma jobs| SQL
    WK --> ST
    WK -->|AIProvider| P1 & P2 & P3
    API -->|embeddings de consulta / respuesta RAG| P1 & P2 & P3
```

### 1.3 Diagrama de componentes (backend)

```mermaid
graph TB
    subgraph api["app/api/v1"]
        AUTH[auth.py] --> DEPS[deps.py<br/>get_current_user / require_admin]
        USERS[users.py] --> DEPS
        REPOS[repositories.py] --> DEPS
        DOCS[documents.py] --> DEPS
        SEARCH[search.py] --> DEPS
        CHAT[chat.py] --> DEPS
        DASH[dashboard.py] --> DEPS
        AUD[audit.py] --> DEPS
    end
    subgraph services["app/services"]
        PERM[permissions.py]
        STO[storage.py]
        EXT[extraction.py]
        CHK[chunking.py]
        PIPE[pipeline.py]
        VEC[vectors.py]
        RAG[rag.py]
        DASHS[dashboard.py]
        AUDS[audit.py]
    end
    subgraph ai["app/ai"]
        FACT[factory.py] --> BASE[base.py AIProvider]
        BASE --> OAI[openai_provider]
        BASE --> OLL[ollama_provider]
        BASE --> DET[deterministic]
        SCH[schemas.py<br/>Pydantic extraccion]
    end
    DOCS --> STO & EXT & PIPE & PERM
    SEARCH --> VEC & FACT & PERM
    CHAT --> RAG & PERM
    RAG --> VEC & FACT
    PIPE --> EXT & CHK & FACT & VEC & SCH
    subgraph worker["app/worker"]
        RUN[runner.py] --> PIPE
    end
```

## 2. Diagrama de casos de uso

```mermaid
graph LR
    Usuario((Usuario))
    Admin((Administrador))
    Worker((Worker))
    IA((Proveedor IA))

    Usuario --> CU01[CU-01 Iniciar/cerrar sesion]
    Usuario --> CU03[CU-03 Gestionar repositorios y miembros]
    Usuario --> CU04[CU-04 Cargar documentos]
    Usuario --> CU06[CU-06 Consultar documento y resultados IA]
    Usuario --> CU07[CU-07 Corregir categoria]
    Usuario --> CU08[CU-08 Buscar textual/semantica]
    Usuario --> CU09[CU-09 Preguntar RAG]
    Usuario --> CU10[CU-10 Dashboard]
    Usuario --> CU12[CU-12 Reintentar procesamiento]
    Admin --> CU01
    Admin --> CU02[CU-02 Gestionar usuarios]
    Admin --> CU11[CU-11 Auditoria]
    Worker --> CU05[CU-05 Procesar documento]
    CU05 --> IA
    CU08 --> IA
    CU09 --> IA
```

## 3. Diagramas de secuencia

### 3.1 Inicio de sesión

```mermaid
sequenceDiagram
    participant U as SPA
    participant A as API /auth/login
    participant D as BD
    U->>A: POST {email, password}
    A->>D: SELECT user WHERE email
    D-->>A: usuario + password_hash
    A->>A: bcrypt.checkpw
    alt credenciales validas y usuario activo
        A->>D: INSERT audit_log(login)
        A-->>U: 200 {access_token JWT, user}
        U->>U: guarda token, redirige a Dashboard
    else invalidas
        A->>D: INSERT audit_log(login_failed)
        A-->>U: 401 invalid_credentials
    end
```

### 3.2 Carga y procesamiento

```mermaid
sequenceDiagram
    participant U as SPA
    participant A as API /documents/upload
    participant S as Storage
    participant D as BD
    participant W as Worker
    participant P as AIProvider
    U->>A: POST multipart files[] (repo_id)
    A->>A: valida permiso, extension, firma, tamano, nombre
    A->>S: save(bytes) -> clave UUID
    A->>D: INSERT document(pending->queued) + job(queued)
    A-->>U: 201 [{document, job_id}]
    loop sondeo cada 1s
        W->>D: job mas antiguo en cola
        W->>S: read(clave)
        W->>W: extraer texto + chunking
        W->>P: classify / summarize / extract / embed
        P-->>W: resultados validados (Pydantic)
        W->>D: persiste texto, chunks, clasificacion,<br/>resumen, extraccion, embeddings
        W->>D: document=completed, job=completed(duracion)
    end
    U->>A: GET /documents/{id} (poll 2.5s)
    A-->>U: estado + resultados de IA
```

### 3.3 Búsqueda semántica

```mermaid
sequenceDiagram
    participant U as SPA
    participant A as API /search/semantic
    participant P as AIProvider
    participant D as BD
    U->>A: GET ?q=...&filtros
    A->>A: repos accesibles del usuario
    A->>P: embed(pregunta)
    P-->>A: vector consulta
    A->>D: embeddings de chunks (repos permitidos, filtros)
    A->>A: similitud coseno + top-K
    A-->>U: hits {documento, pagina, fragmento, score}
```

### 3.4 Pregunta RAG

```mermaid
sequenceDiagram
    participant U as SPA
    participant A as API /conversations/{id}/ask
    participant P as AIProvider
    participant D as BD
    U->>A: POST {question}
    A->>D: INSERT message(user)
    A->>P: embed(question)
    A->>D: top-K chunks del repositorio (solo completados)
    alt hay chunks >= umbral de similitud
        A->>A: contexto [Fuente n] archivo (pag. X): texto
        A->>P: rag_answer(question, contexto)
        P-->>A: respuesta citando fuentes
        A->>D: INSERT message(assistant) + citations + metricas
        A-->>U: respuesta + citas (doc, pagina, fragmento, similitud)
    else sin evidencia
        A->>D: INSERT message(grounded=false, sin citas)
        A-->>U: "No se encontro evidencia suficiente..."
    end
```

### 3.5 Reintento después de error

```mermaid
sequenceDiagram
    participant W as Worker
    participant D as BD
    participant U as SPA
    W->>W: etapa X lanza PipelineError
    alt intento < max_attempts (3)
        W->>D: job=queued (reintento), document=queued
        W->>W: proximo ciclo reprocesa desde cero (idempotente)
    else intentos agotados
        W->>D: job=failed, document=failed,<br/>error="[etapa] detalle tecnico"
    end
    U->>U: ve estado Fallido + error tecnico
    U->>D: POST /documents/{id}/reprocess
    D-->>U: 202 nuevo job (limpia derivados y reejecuta)
```

## 4. Modelo entidad-relación

```mermaid
erDiagram
    USERS ||--o{ REPOSITORIES : posee
    USERS ||--o{ REPOSITORY_MEMBERS : participa
    REPOSITORIES ||--o{ REPOSITORY_MEMBERS : tiene
    REPOSITORIES ||--o{ DOCUMENTS : contiene
    USERS ||--o{ DOCUMENTS : carga
    DOCUMENTS ||--|| DOCUMENT_TEXTS : "texto extraido"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "se segmenta en"
    DOCUMENT_CHUNKS ||--|| EMBEDDINGS : "vector"
    DOCUMENTS ||--o{ PROCESSING_JOBS : "procesado por"
    DOCUMENTS ||--|| CLASSIFICATIONS : "clasificado"
    DOCUMENTS ||--|| SUMMARIES : "resumido"
    DOCUMENTS ||--o{ EXTRACTED_FIELDS : "campos por esquema"
    REPOSITORIES ||--o{ CONVERSATIONS : "consultado via"
    USERS ||--o{ CONVERSATIONS : abre
    CONVERSATIONS ||--o{ MESSAGES : contiene
    MESSAGES ||--o{ CITATIONS : cita
    CITATIONS }o--|| DOCUMENTS : referencia
    CITATIONS }o--|| DOCUMENT_CHUNKS : referencia
    USERS ||--o{ AUDIT_LOGS : genera
```

## 5. Diccionario de datos

Claves: PK = primaria, FK = foránea, UQ = única, IX = indexada. Todas las
tablas con FK usan `ON DELETE CASCADE` salvo donde se indica.

**users** — cuentas del sistema
| Columna | Tipo | Restricción | Descripción |
|---|---|---|---|
| id | INTEGER | PK | Identificador |
| email | VARCHAR(255) | UQ, IX | Correo (minúsculas) |
| full_name | VARCHAR(255) | NOT NULL | Nombre completo |
| password_hash | VARCHAR(255) | NOT NULL | Hash bcrypt |
| role | VARCHAR(20) | CHECK admin/user | Rol global |
| is_active | BOOLEAN | NOT NULL | Login habilitado |
| created_at / updated_at | DATETIME | NOT NULL | Auditoría de fila |

**repositories** — espacios de trabajo
| id | INTEGER | PK | |
| name | VARCHAR(150) | NOT NULL | Nombre visible |
| description | TEXT | NOT NULL ('' ) | Descripción |
| owner_id | INTEGER | FK users, IX | Propietario |
| created_at / updated_at | DATETIME | | |

**repository_members** — membresías
| id | INTEGER | PK | |
| repository_id | INTEGER | FK, IX | |
| user_id | INTEGER | FK, IX | |
| role | VARCHAR(20) | CHECK owner/member | Rol en el repositorio |
| (repository_id, user_id) | | UQ | Sin duplicados |

**documents** — metadatos de archivos
| id | INTEGER | PK | |
| uuid | VARCHAR(36) | UQ, IX | Identificador externo |
| repository_id | INTEGER | FK, IX | |
| uploaded_by | INTEGER | FK users, IX | |
| original_filename | VARCHAR(255) | NOT NULL | Nombre saneado |
| storage_key | VARCHAR(255) | UQ | Clave UUID en el almacén |
| file_type | VARCHAR(10) | CHECK pdf/docx/txt | |
| mime_type | VARCHAR(100) | NOT NULL | |
| size_bytes | INTEGER | NOT NULL | |
| status | VARCHAR(20) | CHECK 5 estados, IX | pending/queued/processing/completed/failed |
| error_message | TEXT | '' | Último error técnico |
| page_count | INTEGER | 0 | Páginas detectadas |

**document_texts** — texto completo extraído (1:1)
| document_id | INTEGER | FK UQ | | content TEXT | char_count INTEGER |

**document_chunks** — fragmentos indexables
| id | PK | | document_id | FK, IX | | chunk_index | INTEGER, UQ con doc |
| content | TEXT | | page_number | INTEGER | | start_char / end_char | INTEGER |

**embeddings** — vectores por chunk (1:1)
| chunk_id | FK UQ | | model | VARCHAR(100) | | dim | INTEGER | | vector | BLOB float32 |

**processing_jobs** — cola y trazabilidad del pipeline
| id | PK | | document_id | FK, IX | | job_type | 'full_pipeline' |
| status | CHECK queued/running/completed/failed, IX | | stage | etapa actual/fallida |
| attempt / max_attempts | INTEGER | | error_message | TEXT |
| started_at / finished_at | DATETIME NULL | | duration_ms | INTEGER |

**classifications** — categoría por documento (1:1)
| document_id | FK UQ | | predicted_category | VARCHAR(30) | | confidence | FLOAT |
| model | VARCHAR(100) | | manual_category | VARCHAR(30) NULL | corrección |
| corrected_by | FK users ON DELETE SET NULL | | corrected_at | DATETIME NULL |

**summaries** — resumen por documento (1:1)
| document_id | FK UQ | | content | TEXT | | model | VARCHAR(100) |

**extracted_fields** — datos estructurados por esquema
| document_id | FK, IX | | schema_name | invoice/contract/resume, UQ con doc |
| data | TEXT JSON validado | | model | VARCHAR(100) |

**conversations / messages / citations** — chat RAG
| conversations: id PK, repository_id FK IX, user_id FK IX, title |
| messages: id PK, conversation_id FK IX, role CHECK user/assistant, content, model, latency_ms, chunk_count, grounded BOOL |
| citations: id PK, message_id FK IX, document_id FK, chunk_id FK, snippet, similarity FLOAT, page_number |

**audit_logs** — auditoría
| id PK | user_id FK SET NULL, IX | action VARCHAR(60) | entity_type/entity_id |
| detail TEXT | ip_address VARCHAR(45) | created_at DATETIME IX |

## 6. Diseño de la API

Prefijo `/api/v1`, JSON, Bearer JWT. Contratos completos en Swagger
(`/api/docs`) y colección `docs/api-collection.postman.json`.

| Recurso | Endpoints |
|---------|-----------|
| Auth | POST /auth/login, POST /auth/logout, GET /auth/me |
| Usuarios (admin) | GET/POST /users, PATCH /users/{id} |
| Repositorios | GET/POST /repositories, GET/PATCH/DELETE /repositories/{id}, GET .../stats, GET/POST .../members, DELETE .../members/{id} |
| Documentos | POST /documents/upload?repository_id, GET /documents (filtros+paginación), GET/DELETE /documents/{id}, GET .../content, GET .../download, POST .../reprocess, GET .../jobs, PATCH .../category |
| Búsqueda | GET /search/text, GET /search/semantic |
| RAG | GET/POST /conversations, GET/DELETE /conversations/{id}, POST .../ask |
| Dashboard | GET /dashboard |
| Auditoría (admin) | GET /audit-logs |
| Salud | GET /health (sin auth) |

Formato de error uniforme:

```json
{ "error": { "code": "forbidden", "message": "No tiene acceso a este repositorio",
             "correlation_id": "ab12cd34ef56" } }
```

Códigos usados: 200/201/202/204, 400 (validación de negocio), 401, 403, 404,
409 (conflicto), 413 (tamaño), 422 (validación de esquema), 503 (IA no
disponible), 500 (con correlation_id, sin detalles internos).

## 7. Flujo documental

```mermaid
flowchart LR
    A[Archivo] --> B[Validacion<br/>ext + firma + tamano + nombre]
    B --> C[Almacenamiento<br/>clave UUID]
    C --> D[Extraccion de texto<br/>pypdf / python-docx / decode]
    D --> E[Normalizacion + Segmentacion<br/>1200 chars, solape 200, pagina]
    E --> F[Clasificacion IA<br/>financiero/legal/talento_humano/otro]
    F --> G[Resumen IA]
    G --> H[Extraccion estructurada<br/>Pydantic: invoice/contract/resume]
    H --> I[Embeddings por chunk<br/>float32 + modelo + dim]
    I --> J[Indexado / Completado]
    J --> K[Busqueda textual y semantica]
    J --> L[Consulta RAG con citas]
```

## 8. Diseño de la integración con IA

| Aspecto | Valor |
|---------|-------|
| Contrato | `AIProvider`: classify, summarize, extract, embed, rag_answer |
| Proveedor por defecto | `deterministic` (offline, reproducible, visible como `deterministic-v1`) |
| Proveedor LLM | OpenAI-compatible — chat `gpt-4o-mini`, embeddings `text-embedding-3-small` |
| Proveedor local | Ollama — `llama3.1` + `nomic-embed-text` (768d) |
| Dimensión vector | 384 (openai con `dimensions`/deterministic), 768 (ollama); guardada por embedding |
| Chunking | 1200 caracteres, solapamiento 200, corte preferente en párrafo/oración, mapeo a página |
| Métrica | Similitud coseno |
| Top-K | 6 (RAG), 10 (búsqueda), configurables |
| Umbral de evidencia | RAG_MIN_SIMILARITY=0.15 → debajo: "sin evidencia suficiente" |
| Contexto RAG | Bloques `[Fuente n] archivo (pág. X): texto`, respuesta obligada a citar |
| Reducción de alucinación | Solo contexto recuperado, instrucción estricta, umbral, frase estándar de no-evidencia, citas verificables en UI |
| Registro | Latencia, nº fragmentos y modelo por respuesta; errores de proveedor en logs sin secretos |
| Privacidad | Con proveedor externo, los textos salen al servicio configurado — documentado en manual técnico; alternativa local (Ollama) y offline (deterministic) |
| Justificación | ADR-005 |

## 9. Diseño de interfaz (wireframes implementados)

Las 12 pantallas siguen un patrón común: encabezado con navegación,
contenido en tarjetas, estados de carga/vacío/error, confirmaciones para
acciones destructivas y notificaciones tipo toast. Wireframes textuales:

```
LOGIN                          DASHBOARD
+----------------------+       +------------------------------------------+
|      [DI] DocuIntel  |       | KPIs: repos | docs | procesados | fallidos|
|  Correo [_________]  |       | [Categoria][Formato][Estado] (barras)    |
|  Clave  [_________]  |       | [Tendencia 14 dias  ▂▄▆█▄▂]              |
|  [ Iniciar sesion ]  |       | [Actividad reciente] [Errores recientes] |
+----------------------+       +------------------------------------------+

REPOSITORIO (detalle)          DOCUMENTO (detalle)
+---------------------------+  +----------------------------------------+
| Nombre  [Editar][Eliminar]|  | archivo.pdf [Descargar][Reproc][Elim]  |
| KPIs: docs/compl/fall/MB  |  | Estado | Categoria(conf/modelo) | Info |
| [ Zona de carga drag&drop]|  | [Resumen IA]                           |
| Tabla docs + estados      |  | [Datos extraidos por esquema]          |
| Miembros | Consultar IA   |  | [Texto extraido] [Historial de jobs]   |
+---------------------------+  +----------------------------------------+

BUSCAR                         CHAT RAG
+---------------------------+  +----------------------------------------+
| [q________] [Buscar]      |  | Repo [v] [Nueva conv] | burbujas chat  |
| (Textual|Semantica) filtros|  | Historial            | respuesta +     |
| Resultados con resaltado  |  |                      | Fuentes citadas |
| doc/pagina/score          |  | [pregunta__________][Preguntar]        |
+---------------------------+  +----------------------------------------+
```

Capturas reales de la implementación en `evidence/screenshots/`.

## 10. Diseño de seguridad

- **Autenticación:** JWT HS256 firmado con `SECRET_KEY` (env), expiración
  configurable; bcrypt (12 rondas) para contraseñas.
- **Autorización:** dependencia `get_current_user` en toda ruta de negocio;
  `require_admin` para usuarios/auditoría; `permissions.py` centraliza la regla
  propietario/miembro/admin; toda consulta se filtra por repositorios accesibles.
- **Carga de archivos:** lista blanca de extensiones + verificación de firma
  binaria (%PDF-, PK\x03\x04, decodificación de texto), límite de tamaño,
  saneamiento del nombre (solo base name + caracteres seguros) y clave de
  almacenamiento UUID generada por el servidor → el nombre del usuario jamás
  toca una ruta.
- **Errores:** cuerpo uniforme con `correlation_id`; detalles técnicos solo en
  logs JSON del servidor.
- **CORS:** solo orígenes configurados; métodos y cabeceras explícitos.
- **Auditoría:** login (ok/fallido), logout, CRUD de repositorios/miembros,
  cargas, descargas, eliminaciones, reprocesos, correcciones, preguntas RAG y
  gestión de usuarios, con usuario, entidad, detalle e IP.
- **Secretos:** exclusivamente en `.env` (no versionado); el seed toma las
  credenciales iniciales del entorno.

## 11. Diagrama de despliegue

```mermaid
graph TB
    subgraph "Desarrollo (Windows, sin Docker)"
        DEV1[uvicorn :8000<br/>API + worker embebido] --> DEV2[(SQLite<br/>database/docuintel.db)]
        DEV1 --> DEV3[(storage/ local)]
        DEV4[Vite dev :5173] -->|proxy /api| DEV1
    end
    subgraph "Produccion (docker-compose)"
        N[nginx :8080<br/>SPA estatica + proxy /api] --> B[backend :8000<br/>migraciones + seed + API + worker]
        B --> PG[(PostgreSQL 16<br/>volumen pgdata)]
        B --> VOL[(volumen storage)]
    end
```

El perfil de producción está definido y documentado; la máquina de desarrollo
no tiene Docker, por lo que su validación en vivo queda como paso externo
(declarado en `docs/05-implementacion-y-despliegue.md`).

## 12. Decisiones tecnológicas

Resumen (detalle y alternativas en `docs/adr/`):

| Decisión | ADR |
|----------|-----|
| Monorepo FastAPI + React, IA desacoplada | ADR-001 |
| SQLite default + PostgreSQL producción | ADR-002 |
| Vectores BLOB + coseno NumPy (ruta pgvector) | ADR-003 |
| Cola en BD + worker embebido/independiente | ADR-004 |
| 3 proveedores IA, determinista honesto para pruebas | ADR-005 |
