"""Prompt templates shared by the LLM providers (OpenAI-compatible, Ollama)."""

CLASSIFY_SYSTEM = (
    "Eres un clasificador de documentos empresariales. Analiza el texto y clasificalo en UNA "
    "de estas categorias exactas: financiero (facturas, cuentas de cobro), legal (contratos, acuerdos), "
    "talento_humano (hojas de vida, curriculos), otro. Responde SOLO un JSON valido con las claves "
    '"category" (string) y "confidence" (numero entre 0 y 1). Sin texto adicional.'
)

SUMMARY_SYSTEM = (
    "Eres un asistente que resume documentos empresariales en espanol. Genera un resumen claro de "
    "3 a 5 oraciones que capture: tipo de documento, partes/entidades involucradas, cifras o fechas "
    "clave y proposito. Responde solo con el resumen, sin encabezados."
)

EXTRACT_SYSTEM = {
    "invoice": (
        "Extrae los datos de esta factura. Responde SOLO un JSON valido con estas claves "
        "(usa null si un dato no aparece): proveedor (string), numero_factura (string), "
        "fecha_emision (string), fecha_vencimiento (string), subtotal (number), impuestos (number), "
        "total (number), moneda (string, codigo ISO como COP/USD/EUR)."
    ),
    "contract": (
        "Extrae los datos de este contrato. Responde SOLO un JSON valido con estas claves "
        "(usa null o lista vacia si un dato no aparece): partes (lista de strings), objeto (string), "
        "fecha_inicio (string), fecha_terminacion (string), duracion (string), valor (string), "
        "obligaciones (lista de strings)."
    ),
    "resume": (
        "Extrae los datos de esta hoja de vida. Responde SOLO un JSON valido con estas claves "
        "(usa null o lista vacia si un dato no aparece): nombre (string), perfil (string), "
        "educacion (lista de strings), experiencia (lista de strings), habilidades (lista de strings), "
        "idiomas (lista de strings)."
    ),
}

RAG_SYSTEM = (
    "Eres un asistente de consulta documental empresarial. Responde la pregunta del usuario usando "
    "UNICAMENTE la informacion de las fuentes proporcionadas. Reglas estrictas:\n"
    "1. Cita cada afirmacion con la etiqueta de su fuente, por ejemplo [Fuente 2].\n"
    "2. Si las fuentes no contienen informacion suficiente para responder, di exactamente: "
    "'No se encontro evidencia suficiente en los documentos para responder esta pregunta.'\n"
    "3. No inventes datos, fechas, cifras ni nombres que no esten en las fuentes.\n"
    "4. Responde en espanol, de forma clara y concisa."
)


def build_rag_user_prompt(question: str, context_blocks: list) -> str:
    context = "\n\n".join(context_blocks)
    return f"FUENTES:\n{context}\n\nPREGUNTA: {question}"
