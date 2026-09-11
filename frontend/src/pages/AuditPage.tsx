import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { AuditLog, Page } from "../api/types";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  Spinner,
  formatDate,
} from "../components/ui";

const ACTION_LABELS: Record<string, string> = {
  login: "Inicio de sesión",
  login_failed: "Inicio de sesión fallido",
  logout: "Cierre de sesión",
  create_repository: "Creación de repositorio",
  update_repository: "Edición de repositorio",
  delete_repository: "Eliminación de repositorio",
  add_member: "Miembro agregado",
  remove_member: "Miembro removido",
  upload_document: "Carga de documento",
  download_document: "Descarga de documento",
  delete_document: "Eliminación de documento",
  reprocess_document: "Reprocesamiento",
  correct_category: "Corrección de categoría",
  rag_question: "Pregunta RAG",
  create_user: "Creación de usuario",
  update_user: "Edición de usuario",
};

export default function AuditPage() {
  const [logs, setLogs] = useState<Page<AuditLog> | null>(null);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const params: Record<string, string | number> = { page, page_size: 25 };
    if (action) params.action = action;
    api
      .get<Page<AuditLog>>("/audit-logs", { params })
      .then((r) => setLogs(r.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, action]);

  useEffect(load, [load]);

  return (
    <div>
      <PageHeader
        title="Auditoría"
        subtitle="Registro de acciones de los usuarios sobre el sistema (solo administradores)"
      />
      <div className="mb-4">
        <select
          value={action}
          onChange={(e) => { setPage(1); setAction(e.target.value); }}
          aria-label="Filtrar por acción"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todas las acciones</option>
          {Object.entries(ACTION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !logs || logs.items.length === 0 ? (
        <EmptyState title="Sin registros de auditoría" />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Fecha</th>
                  <th className="px-4 py-2.5 font-medium">Usuario</th>
                  <th className="px-4 py-2.5 font-medium">Acción</th>
                  <th className="px-4 py-2.5 font-medium">Detalle</th>
                  <th className="px-4 py-2.5 font-medium">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.items.map((log) => (
                  <tr key={log.id}>
                    <td className="whitespace-nowrap px-4 py-2 text-slate-500">{formatDate(log.created_at)}</td>
                    <td className="px-4 py-2 text-slate-600">{log.user_email || "—"}</td>
                    <td className="px-4 py-2 font-medium text-slate-700">
                      {ACTION_LABELS[log.action] ?? log.action}
                    </td>
                    <td className="max-w-xs truncate px-4 py-2 text-slate-500">{log.detail || "—"}</td>
                    <td className="px-4 py-2 text-slate-400">{log.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={logs.page} pages={logs.pages} onChange={setPage} />
        </>
      )}
    </div>
  );
}
