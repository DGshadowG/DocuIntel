"""Abstract AI provider contract.

Every provider (OpenAI-compatible, Ollama, deterministic) implements the same
operations so the pipeline and RAG service stay provider-agnostic. Selection
happens in `factory.get_provider()` from the AI_PROVIDER env variable.
"""
import abc
from typing import Dict, List

from app.ai.schemas import ClassificationResult, RagAnswer


class AIProviderError(Exception):
    """Raised when a provider call fails (network, auth, malformed output)."""


class AIProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def classify(self, text: str) -> ClassificationResult:
        """Classify a document into financiero | legal | talento_humano | otro."""

    @abc.abstractmethod
    def summarize(self, text: str) -> str:
        """Return a short Spanish summary of the document."""

    @abc.abstractmethod
    def extract(self, text: str, schema_name: str) -> Dict:
        """Extract structured fields for schema invoice | contract | resume.

        Must return a dict validated against the corresponding Pydantic model.
        """

    @abc.abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return one embedding vector per input text."""

    @abc.abstractmethod
    def rag_answer(self, question: str, context_blocks: List[str]) -> RagAnswer:
        """Answer a question using ONLY the given context blocks, citing sources."""

    @property
    @abc.abstractmethod
    def chat_model_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def embedding_model_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def embedding_dim(self) -> int: ...
