"""OpenAI-compatible provider (works with OpenAI, Azure-compatible gateways,
Groq, Together, etc. via OPENAI_BASE_URL)."""
import json
import logging
import re
from typing import Dict, List

import httpx

from app.ai.base import AIProvider, AIProviderError
from app.ai import prompts
from app.ai.schemas import ClassificationResult, RagAnswer
from app.core.config import get_settings

logger = logging.getLogger("app.ai.openai")

INSUFFICIENT = "No se encontro evidencia suficiente"


def _extract_json(raw: str) -> dict:
    """Parse the first JSON object found in the model output."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise AIProviderError(f"La respuesta del modelo no contiene JSON: {raw[:200]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIProviderError(f"JSON invalido en respuesta del modelo: {exc}")


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self):
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise AIProviderError(
                "AI_PROVIDER=openai pero OPENAI_API_KEY no esta configurada. "
                "Defina la variable en el archivo .env."
            )
        self._base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        self._chat_model = settings.AI_CHAT_MODEL
        self._embedding_model = settings.AI_EMBEDDING_MODEL
        self._embedding_dim = settings.AI_EMBEDDING_DIM
        self._timeout = settings.AI_TIMEOUT_SECONDS

    # ------------------------------------------------------------ HTTP helpers
    def _chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        payload = {
            "model": self._chat_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/chat/completions",
                json=payload, headers=self._headers, timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Error llamando al proveedor OpenAI: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Respuesta inesperada del proveedor OpenAI: {exc}") from exc

    # ------------------------------------------------------------ operations
    def classify(self, text: str) -> ClassificationResult:
        raw = self._chat(prompts.CLASSIFY_SYSTEM, text[:8000])
        data = _extract_json(raw)
        return ClassificationResult(
            category=str(data.get("category", "otro")),
            confidence=float(data.get("confidence", 0.5)),
        )

    def summarize(self, text: str) -> str:
        return self._chat(prompts.SUMMARY_SYSTEM, text[:12000]).strip()

    def extract(self, text: str, schema_name: str) -> Dict:
        system = prompts.EXTRACT_SYSTEM.get(schema_name)
        if not system:
            raise ValueError(f"Esquema de extraccion desconocido: {schema_name}")
        raw = self._chat(system, text[:12000])
        return _extract_json(raw)

    def embed(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self._embedding_model,
            "input": texts,
            "dimensions": self._embedding_dim,
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/embeddings",
                json=payload, headers=self._headers, timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Error generando embeddings: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Respuesta inesperada de embeddings: {exc}") from exc

    def rag_answer(self, question: str, context_blocks: List[str]) -> RagAnswer:
        answer = self._chat(
            prompts.RAG_SYSTEM, prompts.build_rag_user_prompt(question, context_blocks), temperature=0.1
        ).strip()
        grounded = INSUFFICIENT.lower() not in answer.lower()
        return RagAnswer(answer=answer, grounded=grounded)

    @property
    def chat_model_name(self) -> str:
        return self._chat_model

    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim
