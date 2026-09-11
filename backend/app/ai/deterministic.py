"""Deterministic (rule-based) AI provider.

Fully offline and reproducible. Used for automated tests and as documented
fallback when no LLM credentials exist. It is NOT a silent mock: the provider
name is persisted with every result ("deterministic-v1") and shown in the UI.

Techniques:
- Classification: weighted keyword scoring per category with margin confidence.
- Summary: extractive — frequency-scored sentences returned in document order.
- Extraction: regex + section heuristics tuned for Spanish business documents.
- Embeddings: 384-dim signed feature hashing over normalized tokens
  (log-scaled TF, L2 normalized) -> real cosine similarity search.
- RAG: extractive answer built from the sentences most similar to the question.
"""
import hashlib
import math
import re
import unicodedata
from typing import Dict, List

from app.ai.base import AIProvider
from app.ai.schemas import ClassificationResult, RagAnswer

EMBEDDING_DIM = 384

STOPWORDS = set(
    """a al algo ante antes como con contra cual cuando de del desde donde dos e el ella ellas ellos en entre era
    es esa ese eso esta este esto fue ha han hasta hay la las le les lo los mas me mi mientras muy no nos o os otra
    otro para pero por que se ser si sin sobre son su sus te tiene tienen todo tras tu un una uno unos y ya""".split()
)

CATEGORY_KEYWORDS = {
    "financiero": {
        "factura": 5, "subtotal": 4, "iva": 4, "impuesto": 3, "impuestos": 3, "total a pagar": 5,
        "proveedor": 3, "vencimiento": 3, "pago": 2, "valor unitario": 4, "cantidad": 1, "nit": 2,
        "cufe": 4, "moneda": 2, "cop": 1, "usd": 1, "descuento": 2, "cobro": 2, "emision": 2,
    },
    "legal": {
        "contrato": 5, "clausula": 5, "las partes": 4, "contratante": 5, "contratista": 5,
        "obligaciones": 4, "objeto del contrato": 5, "terminacion": 3, "vigencia": 3, "acuerdo": 2,
        "arrendamiento": 4, "arrendador": 4, "arrendatario": 4, "confidencialidad": 3, "incumplimiento": 3,
        "juridica": 2, "suscribe": 2, "celebrado": 3, "duracion": 2,
    },
    "talento_humano": {
        "hoja de vida": 6, "curriculum": 5, "perfil profesional": 5, "experiencia laboral": 5,
        "educacion": 3, "formacion academica": 5, "habilidades": 4, "idiomas": 3, "referencias": 2,
        "aspiracion salarial": 4, "certificaciones": 2, "logros": 2, "cargo": 2, "egresado": 2,
        "tecnologo": 2, "ingeniero": 1, "estudios": 2,
    },
}


def normalize(text: str) -> str:
    """Lowercase and strip accents for robust Spanish matching."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9ñ]+", normalize(text)) if len(t) > 1 and t not in STOPWORDS]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


class DeterministicProvider(AIProvider):
    name = "deterministic"

    # ------------------------------------------------------------ classification
    def classify(self, text: str) -> ClassificationResult:
        norm = normalize(text)
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for kw, weight in keywords.items():
                score += weight * norm.count(kw)
            scores[category] = score
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_cat, best_score = ranked[0]
        second_score = ranked[1][1]
        if best_score == 0:
            return ClassificationResult(category="otro", confidence=0.3)
        margin = (best_score - second_score) / best_score
        confidence = round(min(0.99, 0.5 + 0.5 * margin), 2)
        return ClassificationResult(category=best_cat, confidence=confidence)

    # ------------------------------------------------------------ summary
    def summarize(self, text: str) -> str:
        sentences = split_sentences(text)
        if not sentences:
            return "El documento no contiene texto suficiente para generar un resumen."
        freq: Dict[str, int] = {}
        for token in tokenize(text):
            freq[token] = freq.get(token, 0) + 1
        scored = []
        for idx, sentence in enumerate(sentences):
            tokens = tokenize(sentence)
            if not tokens:
                continue
            score = sum(freq.get(t, 0) for t in tokens) / math.sqrt(len(tokens))
            # Slight boost for early sentences (title/lead effect)
            score *= 1.15 if idx < 3 else 1.0
            scored.append((idx, score, sentence))
        top = sorted(scored, key=lambda x: x[1], reverse=True)[:4]
        ordered = [s for _, _, s in sorted(top, key=lambda x: x[0])]
        summary = " ".join(ordered)
        return summary[:1200]

    # ------------------------------------------------------------ extraction
    def extract(self, text: str, schema_name: str) -> Dict:
        if schema_name == "invoice":
            return self._extract_invoice(text)
        if schema_name == "contract":
            return self._extract_contract(text)
        if schema_name == "resume":
            return self._extract_resume(text)
        raise ValueError(f"Esquema de extraccion desconocido: {schema_name}")

    @staticmethod
    def _find(pattern: str, text: str, flags=re.IGNORECASE):
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else None

    @staticmethod
    def _to_amount(raw) -> float:
        if raw is None:
            return None
        raw = raw.strip().replace(" ", "")
        # Handle Colombian format 1.234.567,89 and plain 1234567.89
        if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", raw):
            raw = raw.replace(".", "").replace(",", ".")
        elif re.match(r"^\d+(,\d{3})+(\.\d+)?$", raw):
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
        try:
            return round(float(raw), 2)
        except ValueError:
            return None

    def _extract_invoice(self, text: str) -> Dict:
        amount = r"\$?\s*([\d.,]+)"
        moneda = self._find(r"moneda[:\s]+([A-Z]{3})", text)
        if not moneda:
            norm = normalize(text)
            for code in ("cop", "usd", "eur"):
                if re.search(rf"\b{code}\b", norm):
                    moneda = code.upper()
                    break
        return {
            "proveedor": self._find(r"(?:proveedor|raz[oó]n social|emisor)[:\s]+(.+)", text),
            "numero_factura": self._find(r"factura(?:\s+de\s+venta)?\s*(?:electr[oó]nica)?\s*(?:n[oº°.]*|#|num(?:ero)?[.:]?)\s*[:\s]*([A-Z0-9-]+)", text),
            "fecha_emision": self._find(r"fecha\s+de\s+emisi[oó]n[:\s]+(.+)", text),
            "fecha_vencimiento": self._find(r"fecha\s+de\s+vencimiento[:\s]+(.+)", text),
            "subtotal": self._to_amount(self._find(rf"subtotal[:\s]+{amount}", text)),
            "impuestos": self._to_amount(self._find(rf"(?:iva|impuestos?)(?:\s*\(?\d+%\)?)?[:\s]+{amount}", text)),
            # (?<![a-z]) prevents matching the "total" inside "Subtotal"
            "total": self._to_amount(self._find(rf"(?<![a-zA-Z])total(?:\s+a\s+pagar)?[:\s]+{amount}", text)),
            "moneda": moneda,
        }

    def _extract_contract(self, text: str) -> Dict:
        partes = []
        m = re.search(r"entre\s+(.+?)\s*,?\s*(?:identificad|con\s+NIT|quien)", text, re.IGNORECASE | re.DOTALL)
        parties_block = re.findall(
            r"(?:contratante|contratista|arrendador|arrendatario|empleador|trabajador)[:\s]+([^\n,;]+)",
            text, re.IGNORECASE,
        )
        for p in parties_block:
            p = p.strip().rstrip(".")
            if p and p not in partes:
                partes.append(p)
        if not partes and m:
            partes.append(m.group(1).strip()[:120])
        obligaciones = []
        oblig_section = re.search(
            r"obligaciones[^\n]*\n((?:\s*[-•a-z)0-9.]+\s+[^\n]+\n?)+)", text, re.IGNORECASE
        )
        if oblig_section:
            for line in oblig_section.group(1).splitlines():
                clean = re.sub(r"^\s*[-•]?\s*[a-z0-9]{0,2}[).]?\s*", "", line).strip()
                if len(clean) > 15:
                    obligaciones.append(clean)
        def clean(value):
            return value.rstrip(" .") if value else value

        return {
            "partes": partes[:6],
            "objeto": clean(self._find(r"objeto(?:\s+del\s+contrato)?[:\s]+([^\n]+)", text)),
            "fecha_inicio": clean(self._find(r"fecha\s+de\s+inicio[:\s]+([^\n]+)", text)),
            "fecha_terminacion": clean(self._find(r"fecha\s+de\s+terminaci[oó]n[:\s]+([^\n]+)", text)),
            "duracion": clean(self._find(r"duraci[oó]n[:\s]+([^\n]+)", text)),
            "valor": clean(self._find(r"valor(?:\s+total)?(?:\s+del\s+contrato)?[:\s]+([^\n]+)", text)),
            "obligaciones": obligaciones[:8],
        }

    def _extract_resume(self, text: str) -> Dict:
        def section(names: List[str]) -> List[str]:
            pattern = "|".join(names)
            # Section ends at the next ALL-CAPS header, a blank line, or end of text
            m = re.search(
                rf"(?:{pattern})[:\s]*\n((?:[^\n]+\n?)+?)(?=\n\s*(?:[A-ZÁÉÍÓÚ][A-ZÁÉÍÓÚ\s]{{3,}}\n)|\n\s*\n|\Z)",
                text,
            )
            if not m:
                return []
            items = []
            for line in m.group(1).splitlines():
                clean = line.strip().lstrip("-•* ").strip()
                if len(clean) > 3:
                    items.append(clean)
            return items[:8]

        nombre = self._find(r"(?:nombre|candidat[oa])[:\s]+([^\n]+)", text)
        if not nombre:
            first_lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
            for ln in first_lines[:4]:
                if re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}$", ln):
                    nombre = ln
                    break
        perfil = self._find(r"perfil(?:\s+profesional)?[:\s]*\n?([^\n]+(?:\n[a-záéíóúñ][^\n]+)*)", text)
        idiomas_raw = section(["IDIOMAS"])
        return {
            "nombre": nombre,
            "perfil": (perfil or "").strip()[:600] or None,
            "educacion": section(["EDUCACI[OÓ]N", "FORMACI[OÓ]N ACAD[EÉ]MICA", "ESTUDIOS"]),
            "experiencia": section(["EXPERIENCIA(?:\\s+LABORAL|\\s+PROFESIONAL)?"]),
            "habilidades": section(["HABILIDADES", "COMPETENCIAS"]),
            "idiomas": idiomas_raw,
        }

    # ------------------------------------------------------------ embeddings
    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    @staticmethod
    def _embed_one(text: str) -> List[float]:
        vec = [0.0] * EMBEDDING_DIM
        counts: Dict[str, int] = {}
        for token in tokenize(text):
            counts[token] = counts.get(token, 0) + 1
        for token, count in counts.items():
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    # ------------------------------------------------------------ RAG
    def rag_answer(self, question: str, context_blocks: List[str]) -> RagAnswer:
        if not context_blocks:
            return RagAnswer(
                answer="No se encontro evidencia suficiente en los documentos para responder esta pregunta.",
                grounded=False,
            )
        q_tokens = set(tokenize(question))
        candidates = []
        for block in context_blocks:
            # Block format: "[Fuente N] Documento (pag. X):\ntext"
            header_match = re.match(r"(\[Fuente \d+\][^\n]*)\n(.*)", block, re.DOTALL)
            header = header_match.group(1) if header_match else ""
            body = header_match.group(2) if header_match else block
            for sentence in split_sentences(body):
                s_tokens = set(tokenize(sentence))
                if not s_tokens:
                    continue
                overlap = len(q_tokens & s_tokens) / math.sqrt(len(s_tokens))
                if overlap > 0:
                    candidates.append((overlap, sentence, header))
        candidates.sort(key=lambda x: x[0], reverse=True)
        strong = [c for c in candidates if c[0] >= 0.45][:4]
        if not strong:
            return RagAnswer(
                answer="No se encontro evidencia suficiente en los documentos para responder esta pregunta.",
                grounded=False,
            )
        seen_sources = []
        lines = []
        for _, sentence, header in strong:
            source_tag = header.split("]")[0] + "]" if "]" in header else ""
            lines.append(f"{sentence} {source_tag}".strip())
            if source_tag and source_tag not in seen_sources:
                seen_sources.append(source_tag)
        answer = "Segun los documentos consultados: " + " ".join(lines)
        return RagAnswer(answer=answer[:2500], grounded=True)

    # ------------------------------------------------------------ metadata
    @property
    def chat_model_name(self) -> str:
        return "deterministic-v1"

    @property
    def embedding_model_name(self) -> str:
        return "hash-embed-384-v1"

    @property
    def embedding_dim(self) -> int:
        return EMBEDDING_DIM
