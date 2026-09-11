import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Doc, Page, Repository } from "../api/types";
import {
  CategoryBadge,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  Spinner,
  StatusBadge,
  formatBytes,
  formatDate,
} from "../components/ui";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Page<Doc> | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    repository_id: "",
    status: "",
    category: "",
    file_type: "",
    search: "",
  });

  useEffect(() => {
    api.get<Repository[]>("/repositories").then((r) => setRepos(r.data)).catch(() => undefined);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const params: Record<string, string | number> = { page, page_size: 12 };
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params[k] = v;
    });
    api
      .get<Page<Doc>>("/documents", { params })
      .then((resp) => setDocs(resp.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, filters]);

  useEffect(load, [load]);

  function setFilter(key: keyof typeof filters, value: string) {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  const selectCls =
    "rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

  return (
    <div>
      <PageHeader title="Documentos" subtitle="Todos los documentos de sus repositorios" />

      <div className="mb-4 flex flex-wrap gap-2">
        <input
          value={filters.search}
          onChange={(e) => setFilter("search", e.target.value)}
          placeholder="Buscar por nombre..."
          aria-label="Buscar por nombre de archivo"
          className={`${selectCls} w-52`}
        />
        <select aria-label="Filtrar por repositorio" value={filters.repository_id}
                onChange={(e) => setFilter("repository_id", e.target.value)} className={selectCls}>
          <option value="">Todos los repositorios</option>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select aria-label="Filtrar por estado" value={filters.status}
                onChange={(e) => setFilter("status", e.target.value)} className={selectCls}>
          <option value="">Todos los estados</option>
          <option value="pending">Pendiente</option>
          <option value="queued">En cola</option>
          <option value="processing">Procesando</option>
          <option value="completed">Completado</option>
          <option value="failed">Fallido</option>
        </select>
        <select aria-label="Filtrar por categoría" value={filters.category}
                onChange={(e) => setFilter("category", e.target.value)} className={selectCls}>
          <option value="">Todas las categorías</option>
          <option value="financiero">Financiero / Facturas</option>
          <option value="legal">Legal / Contratos</option>
          <option value="talento_humano">Talento humano / Hojas de vida</option>
          <option value="otro">Otro</option>
        </select>
        <select aria-label="Filtrar por formato" value={filters.file_type}
                onChange={(e) => setFilter("file_type", e.target.value)} className={selectCls}>
          <option value="">Todos los formatos</option>
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
          <option value="txt">TXT</option>
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !docs || docs.items.length === 0 ? (
        <EmptyState title="No hay documentos que coincidan" hint="Ajuste los filtros o cargue documentos desde un repositorio" />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Archivo</th>
                  <th className="px-4 py-2.5 font-medium">Tipo</th>
                  <th className="px-4 py-2.5 font-medium">Categoría</th>
                  <th className="px-4 py-2.5 font-medium">Estado</th>
                  <th className="px-4 py-2.5 font-medium">Tamaño</th>
                  <th className="px-4 py-2.5 font-medium">Propietario</th>
                  <th className="px-4 py-2.5 font-medium">Fecha</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docs.items.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5">
                      <Link to={`/documentos/${d.id}`} className="font-medium text-brand-700 hover:underline">
                        {d.original_filename}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 uppercase text-slate-500">{d.file_type}</td>
                    <td className="px-4 py-2.5"><CategoryBadge category={d.category} /></td>
                    <td className="px-4 py-2.5"><StatusBadge status={d.status} /></td>
                    <td className="px-4 py-2.5 text-slate-500">{formatBytes(d.size_bytes)}</td>
                    <td className="px-4 py-2.5 text-slate-500">{d.uploader_name}</td>
                    <td className="px-4 py-2.5 text-slate-500">{formatDate(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={docs.page} pages={docs.pages} onChange={setPage} />
        </>
      )}
    </div>
  );
}
