// API contract types mirrored from backend/app/schemas/api.py

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Repository {
  id: number;
  name: string;
  description: string;
  owner_id: number;
  owner_name: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface RepositoryStats {
  document_count: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_format: Record<string, number>;
  total_size_bytes: number;
}

export interface Member {
  id: number;
  user_id: number;
  email: string;
  full_name: string;
  role: string;
}

export type DocStatus = "pending" | "queued" | "processing" | "completed" | "failed";
export type Category = "financiero" | "legal" | "talento_humano" | "otro";

export interface Doc {
  id: number;
  uuid: string;
  repository_id: number;
  original_filename: string;
  file_type: "pdf" | "docx" | "txt";
  mime_type: string;
  size_bytes: number;
  status: DocStatus;
  error_message: string;
  page_count: number;
  uploaded_by: number;
  uploader_name: string;
  category: Category | null;
  created_at: string;
  updated_at: string;
}

export interface Classification {
  predicted_category: Category;
  confidence: number;
  model: string;
  manual_category: Category | null;
  effective_category: Category;
  corrected_at: string | null;
}

export interface Summary {
  content: string;
  model: string;
  created_at: string;
}

export interface Extraction {
  schema_name: "invoice" | "contract" | "resume";
  data: Record<string, unknown>;
  model: string;
  created_at: string;
}

export interface DocDetail extends Doc {
  classification: Classification | null;
  summary: Summary | null;
  extractions: Extraction[];
  chunk_count: number;
  text_preview: string | null;
}

export interface Job {
  id: number;
  document_id: number;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  attempt: number;
  max_attempts: number;
  error_message: string;
  duration_ms: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface UploadResult {
  document: Doc;
  job_id: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SearchHit {
  document_id: number;
  document_name: string;
  repository_id: number;
  repository_name: string;
  file_type: string;
  category: Category | null;
  page_number: number;
  chunk_id: number | null;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  mode: "text" | "semantic";
  total: number;
  page: number;
  page_size: number;
  hits: SearchHit[];
}

export interface Citation {
  id: number;
  document_id: number;
  chunk_id: number;
  snippet: string;
  similarity: number;
  page_number: number;
  document_name: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  model: string;
  latency_ms: number;
  chunk_count: number;
  grounded: boolean;
  created_at: string;
  citations: Citation[];
}

export interface Conversation {
  id: number;
  repository_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface DashboardData {
  total_repositories: number;
  total_documents: number;
  by_category: Record<string, number>;
  by_format: Record<string, number>;
  by_status: Record<string, number>;
  processed_count: number;
  failed_count: number;
  avg_processing_ms: number | null;
  recent_documents: {
    id: number;
    filename: string;
    status: DocStatus;
    file_type: string;
    created_at: string;
  }[];
  recent_errors: {
    id: number;
    filename: string;
    error_message: string;
    updated_at: string;
  }[];
  uploads_last_14_days: { date: string; count: number }[];
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  user_email: string;
  action: string;
  entity_type: string;
  entity_id: number | null;
  detail: string;
  ip_address: string;
  created_at: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    correlation_id: string;
    details?: { campo: string; detalle: string }[];
  };
}
