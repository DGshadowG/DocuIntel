"""Typed schemas for structured extraction, validated with Pydantic.

Any provider output (LLM JSON or rule-based) must pass through these models
before persistence, so malformed AI output can never corrupt the database.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("financiero", "legal", "talento_humano", "otro")
SCHEMA_BY_CATEGORY = {
    "financiero": "invoice",
    "legal": "contract",
    "talento_humano": "resume",
}


class ClassificationResult(BaseModel):
    category: str = Field(description="financiero | legal | talento_humano | otro")
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in CATEGORIES:
            return "otro"
        return v


class InvoiceExtraction(BaseModel):
    proveedor: Optional[str] = None
    numero_factura: Optional[str] = None
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    subtotal: Optional[float] = None
    impuestos: Optional[float] = None
    total: Optional[float] = None
    moneda: Optional[str] = None


class ContractExtraction(BaseModel):
    partes: List[str] = Field(default_factory=list)
    objeto: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_terminacion: Optional[str] = None
    duracion: Optional[str] = None
    valor: Optional[str] = None
    obligaciones: List[str] = Field(default_factory=list)


class ResumeExtraction(BaseModel):
    nombre: Optional[str] = None
    perfil: Optional[str] = None
    educacion: List[str] = Field(default_factory=list)
    experiencia: List[str] = Field(default_factory=list)
    habilidades: List[str] = Field(default_factory=list)
    idiomas: List[str] = Field(default_factory=list)


EXTRACTION_MODELS = {
    "invoice": InvoiceExtraction,
    "contract": ContractExtraction,
    "resume": ResumeExtraction,
}


class RagAnswer(BaseModel):
    answer: str
    grounded: bool = True
