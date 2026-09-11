"""Pydantic request/response contracts for the versioned API (/api/v1)."""
import datetime as dt
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ pagination
class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------ auth/users
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: dt.datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


# ------------------------------------------------------------------ repositories
class RepositoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(default="", max_length=2000)


class RepositoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)


class RepositoryOut(ORMModel):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: dt.datetime
    updated_at: dt.datetime
    document_count: int = 0
    owner_name: str = ""


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|member)$")


class MemberOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: str


class RepositoryStats(BaseModel):
    document_count: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    by_format: Dict[str, int]
    total_size_bytes: int


# ------------------------------------------------------------------ documents
class ClassificationOut(ORMModel):
    predicted_category: str
    confidence: float
    model: str
    manual_category: Optional[str] = None
    effective_category: str
    corrected_at: Optional[dt.datetime] = None


class SummaryOut(ORMModel):
    content: str
    model: str
    created_at: dt.datetime


class ExtractionOut(ORMModel):
    schema_name: str
    data: Any  # parsed JSON object
    model: str
    created_at: dt.datetime


class DocumentOut(ORMModel):
    id: int
    uuid: str
    repository_id: int
    original_filename: str
    file_type: str
    mime_type: str
    size_bytes: int
    status: str
    error_message: str
    page_count: int
    uploaded_by: int
    uploader_name: str = ""
    category: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime


class DocumentDetail(DocumentOut):
    classification: Optional[ClassificationOut] = None
    summary: Optional[SummaryOut] = None
    extractions: List[ExtractionOut] = Field(default_factory=list)
    chunk_count: int = 0
    text_preview: Optional[str] = None


class CategoryCorrection(BaseModel):
    category: str = Field(pattern="^(financiero|legal|talento_humano|otro)$")


class JobOut(ORMModel):
    id: int
    document_id: int
    job_type: str
    status: str
    stage: str
    attempt: int
    max_attempts: int
    error_message: str
    duration_ms: int
    created_at: dt.datetime
    started_at: Optional[dt.datetime] = None
    finished_at: Optional[dt.datetime] = None


class UploadResult(BaseModel):
    document: DocumentOut
    job_id: int


# ------------------------------------------------------------------ search
class SearchHit(BaseModel):
    document_id: int
    document_name: str
    repository_id: int
    repository_name: str
    file_type: str
    category: Optional[str] = None
    page_number: int
    chunk_id: Optional[int] = None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    mode: str  # text | semantic
    total: int
    page: int
    page_size: int
    hits: List[SearchHit]


# ------------------------------------------------------------------ chat / RAG
class ConversationCreate(BaseModel):
    repository_id: int
    title: Optional[str] = Field(default=None, max_length=200)


class CitationOut(ORMModel):
    id: int
    document_id: int
    chunk_id: int
    snippet: str
    similarity: float
    page_number: int
    document_name: str = ""


class MessageOut(ORMModel):
    id: int
    role: str
    content: str
    model: str
    latency_ms: int
    chunk_count: int
    grounded: bool
    created_at: dt.datetime
    citations: List[CitationOut] = Field(default_factory=list)


class ConversationOut(ORMModel):
    id: int
    repository_id: int
    title: str
    created_at: dt.datetime
    updated_at: dt.datetime


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


# ------------------------------------------------------------------ audit
class AuditLogOut(ORMModel):
    id: int
    user_id: Optional[int] = None
    user_email: str = ""
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    detail: str
    ip_address: str
    created_at: dt.datetime


TokenResponse.model_rebuild()
