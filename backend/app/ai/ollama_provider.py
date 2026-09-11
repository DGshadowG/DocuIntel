"""Ollama local provider (no API key, runs models locally)."""
import json
import logging
import re
from typing import Dict, List

import httpx

from app.ai.base import AIProvider, AIProviderError
from app.ai import prompts
from app.ai.schemas import ClassificationResult, RagAnswer
from app.core.config import get_settings

logger = logging.getLogger("app.ai.ollama")

INSUFFICIENT = "No se encontro evidencia suficiente"


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self):
        settings = get_settings()
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._chat_model = settings.OLLAMA_CHAT_MODEL
        self._embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._embedding_dim = 768  # nomic-embed-text; adjusted on first call

    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self._chat_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.0},
        }
        try:
            resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Error llamando a Ollama: {exc}") from exc
        except KeyError as exc:
            raise AIProviderError(f"Respuesta inesperada de Ollama: {exc}") from exc

    @staticmethod
    def _extract_json(raw: str) -> dict:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise AIProviderError(f"La respuesta del modelo no contiene JSON: {raw[:200]}")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"JSON invalido en respuesta del modelo: {exc}")

    def classify(self, text: str) -> ClassificationResult:
        data = self._extract_json(self._chat(prompts.CLASSIFY_SYSTEM, text[:8000]))
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
        return self._extract_json(self._chat(system, text[:12000]))

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            try:
                resp = httpx.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._embedding_model, "prompt": text},
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                vector = resp.json()["embedding"]
            except httpx.HTTPError as exc:
                raise AIProviderError(f"Error generando embeddings con Ollama: {exc}") from exc
            except KeyError as exc:
                raise AIProviderError(f"Respuesta inesperada de embeddings de Ollama: {exc}") from exc
            self._embedding_dim = len(vector)
            vectors.append(vector)
        return vectors

    def rag_answer(self, question: str, context_blocks: List[str]) -> RagAnswer:
        answer = self._chat(
            prompts.RAG_SYSTEM, prompts.build_rag_user_prompt(question, context_blocks)
        ).strip()
        grounded = INSUFFICIENT.lower() not in answer.lower()
        return RagAnswer(answer=answer, grounded=grounded)

    @property
    def chat_model_name(self) -> str:
        return f"ollama/{self._chat_model}"

    @property
    def embedding_model_name(self) -> str:
        return f"ollama/{self._embedding_model}"

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim
