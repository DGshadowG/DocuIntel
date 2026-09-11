import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { SearchResponse } from "../api/types";
import {
  CategoryBadge,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
} from "../components/ui";

/** Render **term** highlights produced by the backend as <mark>. */
function Snippet({ text }: { text: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return (
    <p className="text-sm text-slate-600">
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded bg-yellow-100 px-0.5 font-medium">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"text" | "semantic">("text");
  const [category, setCategory] = useState("");
  const [fileType, setFileType] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function handleSearch(e?: FormEvent, page = 1) {
    e?.preventDefault();
    if (query.trim().length < 2) {
      setError("Escriba al menos 2 caracteres");
      return;
    }
    setLoading(true);
    setError("");
    setSearched(true);
    const params: Record<string, string | number> = { q: query.trim() };
    if (category) params.category = category;
    if (fileType) params.file_type = fileType;
    if (mode === "text") {
      params.page = page;
      params.page_size = 10;
    } else {
      params.top_k = 10;
    }
    try {
      const resp = await api.get<SearchResponse>(`/search/${mode === "text" ? "text" : "semantic"}`, { params });
      setResults(resp.data);
    } catch (err) {
      setError(errorMessage(err));
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Buscar"
        subtitle="Búsqueda textual exacta o semántica por significado, sobre el contenido de sus documentos"
      />
      <form onSubmit={handleSearch} className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ej: valor total del contrato de servicios..."
            aria-label="Texto a buscar"
            className="min-w-64 flex-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-brand-600 px-5 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            Buscar
          </button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <fieldset className="flex gap-1 rounded-lg bg-slate-100 p-1" aria-label="Modo de búsqueda">
            <button
              type="button"
              onClick={() => setMode("text")}
              className={`rounded-md px-3 py-1 text-sm font-medium ${mode === "text" ? "bg-white text-brand-700 shadow-sm" : "text-slate-600"}`}
            >
              Textual
            </button>
            <button
              type="button"
              onClick={() => setMode("semantic")}
              className={`rounded-md px-3 py-1 text-sm font-medium ${mode === "semantic" ? "bg-white text-brand-700 shadow-sm" : "text-slate-600"}`}
            >
              Semántica (IA)
            </button>
          </fieldset>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
                  aria-label="Filtrar por categoría"
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm">
            <option value="">Todas las categorías</option>
            <option value="financiero">Financiero</option>
            <option value="legal">Legal</option>
            <option value="talento_humano">Talento humano</option>
            <option value="otro">Otro</option>
          </select>
          <select value={fileType} onChange={(e) => setFileType(e.target.value)}
                  aria-label="Filtrar por formato"
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm">
            <option value="">Todos los formatos</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="txt">TXT</option>
          </select>
        </div>
      </form>

      <div className="mt-6">
        {loading ? (
          <Spinner label="Buscando..." />
        ) : error ? (
          <ErrorState message={error} />
        ) : !searched ? (
          <EmptyState
            title="Escriba una consulta para empezar"
            hint="La búsqueda semántica encuentra contenido por significado aunque no coincidan las palabras exactas"
          />
        ) : !results || results.hits.length === 0 ? (
          <EmptyState title="Sin resultados" hint="Intente con otros términos o cambie el modo de búsqueda" />
        ) : (
          <>
            <p className="mb-3 text-sm text-slate-500">
              {results.total} resultado{results.total === 1 ? "" : "s"} ·{" "}
              {results.mode === "text" ? "búsqueda textual" : "búsqueda semántica"}
            </p>
            <ul className="space-y-3">
              {results.hits.map((hit, i) => (
                <li key={`${hit.document_id}-${hit.chunk_id ?? i}`}
                    className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Link to={`/documentos/${hit.document_id}`}
                          className="font-medium text-brand-700 hover:underline">
                      {hit.document_name}
                    </Link>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <CategoryBadge category={hit.category} />
                      <span>{hit.repository_name}</span>
                      <span>pág. {hit.page_number}</span>
                      <span>
                        {results.mode === "semantic"
                          ? `similitud ${(hit.score * 100).toFixed(0)}%`
                          : `${hit.score} coincidencia(s)`}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <Snippet text={hit.snippet} />
                  </div>
                </li>
              ))}
            </ul>
            {results.mode === "text" && results.total > results.page_size && (
              <div className="mt-4 flex justify-center gap-2">
                <button
                  disabled={results.page <= 1}
                  onClick={() => handleSearch(undefined, results.page - 1)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  disabled={results.page * results.page_size >= results.total}
                  onClick={() => handleSearch(undefined, results.page + 1)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-40"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
