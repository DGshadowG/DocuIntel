import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Category, DocDetail, Job } from "../api/types";
import { useToast } from "../context/ToastContext";
import {
  CATEGORY_LABELS,
  CategoryBadge,
  ConfirmDialog,
  ErrorState,
  PageHeader,
  Spinner,
  StatusBadge,
  formatBytes,
  formatDate,
} from "../components/ui";

const SCHEMA_TITLES: Record<string, string> = {
  invoice: "Datos de la factura",
  contract: "Datos del contrato",
  resume: "Datos de la hoja de vida",
};

const FIELD_LABELS: Record<string, string> = {
  proveedor: "Proveedor",
  numero_factura: "Número de factura",
  fecha_emision: "Fecha de emisión",
  fecha_vencimiento: "Fecha de vencimiento",
  subtotal: "Subtotal",
  impuestos: "Impuestos",
  total: "Total",
  moneda: "Moneda",
  partes: "Partes",
  objeto: "Objeto",
  fecha_inicio: "Fecha de inicio",
  fecha_terminacion: "Fecha de terminación",
  duracion: "Duración",
  valor: "Valor",
  obligaciones: "Obligaciones relevantes",
  nombre: "Nombre",
  perfil: "Perfil",
  educacion: "Educación",
  experiencia: "Experiencia",
  habilidades: "Habilidades",
  idiomas: "Idiomas",
};

function FieldValue({ value }: { value: unknown }) {
  if (value == null || (Array.isArray(value) && value.length === 0)) {
    return <span className="text-slate-400">No detectado</span>;
  }
  if (Array.isArray(value)) {
    return (
      <ul className="list-inside list-disc space-y-0.5">
        {value.map((v, i) => (
          <li key={i}>{String(v)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "number") {
    return <span>{value.toLocaleString("es-CO")}</span>;
  }
  return <span>{String(value)}</span>;
}

const ACTIVE = new Set(["pending", "queued", "processing"]);

export default function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [showText, setShowText] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const pollRef = useRef<number | null>(null);

  const load = useCallback(() => {
    setError("");
    return Promise.all([
      api.get<DocDetail>(`/documents/${id}`),
      api.get<Job[]>(`/documents/${id}/jobs`),
    ])
      .then(([d, j]) => {
        setDoc(d.data);
        setJobs(j.data);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    if (!doc || !ACTIVE.has(doc.status)) return;
    pollRef.current = window.setTimeout(load, 2500);
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current);
    };
  }, [doc, load]);

  async function handleDownload() {
    try {
      const resp = await api.get(`/documents/${id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(resp.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc?.original_filename ?? "documento";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  async function handleReprocess() {
    try {
      await api.post(`/documents/${id}/reprocess`);
      notify("info", "Reprocesamiento en cola");
      load();
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  async function handleDelete() {
    try {
      await api.delete(`/documents/${id}`);
      notify("success", "Documento eliminado");
      navigate(-1);
    } catch (err) {
      notify("error", errorMessage(err));
      setDeleteOpen(false);
    }
  }

  async function handleCorrectCategory(category: Category) {
    try {
      await api.patch(`/documents/${id}/category`, { category });
      notify("success", "Categoría corregida");
      setCorrecting(false);
      load();
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!doc) return null;

  return (
    <div>
      <PageHeader
        title={doc.original_filename}
        subtitle={`Repositorio: `}
        actions={
          <>
            <button onClick={handleDownload}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              Descargar
            </button>
            <button onClick={handleReprocess}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              Reprocesar
            </button>
            <button onClick={() => setDeleteOpen(true)}
                    className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
              Eliminar
            </button>
          </>
        }
      />
      <p className="-mt-4 mb-6 text-sm text-slate-500">
        <Link to={`/repositorios/${doc.repository_id}`} className="text-brand-700 hover:underline">
          Ver repositorio
        </Link>
      </p>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Estado</p>
          <div className="mt-1"><StatusBadge status={doc.status} /></div>
          {doc.status === "failed" && doc.error_message && (
            <p className="mt-2 text-xs text-red-600">{doc.error_message}</p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Categoría</p>
          <div className="mt-1"><CategoryBadge category={doc.classification?.effective_category ?? null} /></div>
          {doc.classification && (
            <p className="mt-1 text-xs text-slate-400">
              Confianza: {(doc.classification.confidence * 100).toFixed(0)}% · Modelo: {doc.classification.model}
            </p>
          )}
          {doc.classification?.manual_category && (
            <p className="mt-1 text-xs text-amber-600">
              Corregida manualmente (IA predijo: {CATEGORY_LABELS[doc.classification.predicted_category]})
            </p>
          )}
          {doc.classification && (
            <button onClick={() => setCorrecting(!correcting)}
                    className="mt-2 text-xs font-medium text-brand-700 hover:underline">
              Corregir categoría
            </button>
          )}
          {correcting && (
            <div className="mt-2 flex flex-col gap-1">
              {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
                <button key={c} onClick={() => handleCorrectCategory(c)}
                        className="rounded border border-slate-200 px-2 py-1 text-left text-xs hover:bg-slate-50">
                  {CATEGORY_LABELS[c]}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Archivo</p>
          <p className="mt-1 text-sm text-slate-700">
            {doc.file_type.toUpperCase()} · {formatBytes(doc.size_bytes)} · {doc.page_count} pág.
          </p>
          <p className="mt-1 text-xs text-slate-400">{doc.chunk_count} fragmentos indexados</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Cargado por</p>
          <p className="mt-1 text-sm text-slate-700">{doc.uploader_name}</p>
          <p className="mt-1 text-xs text-slate-400">{formatDate(doc.created_at)}</p>
        </div>
      </div>

      {doc.summary && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-700">Resumen generado por IA</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{doc.summary.content}</p>
          <p className="mt-2 text-xs text-slate-400">Modelo: {doc.summary.model}</p>
        </div>
      )}

      {doc.extractions.map((ext) => (
        <div key={ext.schema_name} className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-700">
            {SCHEMA_TITLES[ext.schema_name] ?? "Datos estructurados"}
          </h2>
          <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm md:grid-cols-2">
            {Object.entries(ext.data).map(([key, value]) => (
              <div key={key} className="flex flex-col">
                <dt className="font-medium text-slate-500">{FIELD_LABELS[key] ?? key}</dt>
                <dd className="text-slate-700"><FieldValue value={value} /></dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-slate-400">Modelo: {ext.model}</p>
        </div>
      ))}

      {doc.text_preview && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-700">Texto extraído</h2>
            <button onClick={() => setShowText(!showText)}
                    className="text-sm font-medium text-brand-700 hover:underline">
              {showText ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          {showText && (
            <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
              {doc.text_preview}
            </pre>
          )}
        </div>
      )}

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold text-slate-700">Historial de procesamiento</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1.5 pr-4 font-medium">Estado</th>
                <th className="py-1.5 pr-4 font-medium">Etapa</th>
                <th className="py-1.5 pr-4 font-medium">Intentos</th>
                <th className="py-1.5 pr-4 font-medium">Duración</th>
                <th className="py-1.5 pr-4 font-medium">Inicio</th>
                <th className="py-1.5 font-medium">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td className="py-2 pr-4">
                    <StatusBadge status={j.status === "running" ? "processing" : j.status === "queued" ? "queued" : j.status} />
                  </td>
                  <td className="py-2 pr-4 text-slate-600">{j.stage || "—"}</td>
                  <td className="py-2 pr-4 text-slate-600">{j.attempt}/{j.max_attempts}</td>
                  <td className="py-2 pr-4 text-slate-600">{j.duration_ms ? `${(j.duration_ms / 1000).toFixed(1)} s` : "—"}</td>
                  <td className="py-2 pr-4 text-slate-600">{formatDate(j.started_at)}</td>
                  <td className="py-2 text-xs text-red-600">{j.error_message || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Eliminar documento"
        message={`Se eliminará "${doc.original_filename}" junto con su texto, fragmentos, embeddings y resultados de IA.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  );
}
