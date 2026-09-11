import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { DashboardData } from "../api/types";
import {
  CATEGORY_LABELS,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  StatusBadge,
  formatDate,
} from "../components/ui";
import type { Category } from "../api/types";

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent ?? "text-slate-800"}`}>{value}</p>
    </div>
  );
}

function DistBar({ data, labels }: { data: Record<string, number>; labels?: Record<string, string> }) {
  const entries = Object.entries(data);
  const total = entries.reduce((acc, [, v]) => acc + v, 0);
  if (!total) return <p className="text-sm text-slate-400">Sin datos todavía</p>;
  return (
    <ul className="space-y-2">
      {entries
        .sort((a, b) => b[1] - a[1])
        .map(([key, value]) => (
          <li key={key}>
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">{labels?.[key] ?? key.toUpperCase()}</span>
              <span className="font-medium text-slate-800">{value}</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-brand-500"
                style={{ width: `${Math.round((value / total) * 100)}%` }}
              />
            </div>
          </li>
        ))}
    </ul>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .get<DashboardData>("/dashboard")
      .then((resp) => setData(resp.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  if (loading) return <Spinner label="Cargando indicadores..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return null;

  const maxUpload = Math.max(1, ...data.uploads_last_14_days.map((d) => d.count));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Indicadores calculados sobre los repositorios a los que tiene acceso"
      />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Repositorios" value={data.total_repositories} />
        <StatCard label="Documentos" value={data.total_documents} />
        <StatCard label="Procesados" value={data.processed_count} accent="text-green-600" />
        <StatCard label="Fallidos" value={data.failed_count} accent={data.failed_count ? "text-red-600" : undefined} />
        <StatCard
          label="Tiempo medio de proceso"
          value={data.avg_processing_ms != null ? `${(data.avg_processing_ms / 1000).toFixed(1)} s` : "—"}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-700">Por categoría</h2>
          <DistBar data={data.by_category} labels={CATEGORY_LABELS as Record<Category, string>} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-700">Por formato</h2>
          <DistBar data={data.by_format} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-700">Por estado</h2>
          <DistBar
            data={data.by_status}
            labels={{
              pending: "Pendiente", queued: "En cola", processing: "Procesando",
              completed: "Completado", failed: "Fallido",
            }}
          />
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-3 font-semibold text-slate-700">Cargas de los últimos 14 días</h2>
        <div className="flex h-28 items-end gap-1" role="img" aria-label="Tendencia de cargas de documentos">
          {data.uploads_last_14_days.map((d) => (
            <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
              <span className="text-xs text-slate-500">{d.count > 0 ? d.count : ""}</span>
              <div
                className={`w-full rounded-t ${d.count ? "bg-brand-500" : "bg-slate-100"}`}
                style={{ height: `${Math.max(4, (d.count / maxUpload) * 80)}px` }}
                title={`${d.date}: ${d.count} documentos`}
              />
              <span className="text-[10px] text-slate-400">{d.date.slice(8)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-700">Actividad reciente</h2>
          {data.recent_documents.length === 0 ? (
            <EmptyState title="Sin documentos aún" hint="Cargue documentos desde un repositorio" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_documents.map((d) => (
                <li key={d.id} className="flex items-center justify-between py-2">
                  <Link to={`/documentos/${d.id}`} className="truncate text-sm text-brand-700 hover:underline">
                    {d.filename}
                  </Link>
                  <div className="ml-2 flex shrink-0 items-center gap-2">
                    <StatusBadge status={d.status} />
                    <span className="text-xs text-slate-400">{formatDate(d.created_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-700">Errores recientes</h2>
          {data.recent_errors.length === 0 ? (
            <EmptyState title="Sin errores de procesamiento" hint="Todo funciona correctamente" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_errors.map((d) => (
                <li key={d.id} className="py-2">
                  <Link to={`/documentos/${d.id}`} className="text-sm font-medium text-red-700 hover:underline">
                    {d.filename}
                  </Link>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{d.error_message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
