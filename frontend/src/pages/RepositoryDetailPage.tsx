import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Doc, Member, Page, Repository, RepositoryStats, UploadResult } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  CategoryBadge,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  Spinner,
  StatusBadge,
  formatBytes,
  formatDate,
} from "../components/ui";

const ACTIVE_STATUSES = new Set(["pending", "queued", "processing"]);

export default function RepositoryDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { notify } = useToast();

  const [repo, setRepo] = useState<Repository | null>(null);
  const [stats, setStats] = useState<RepositoryStats | null>(null);
  const [docs, setDocs] = useState<Page<Doc> | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [memberEmail, setMemberEmail] = useState("");
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  const loadDocs = useCallback(() => {
    return api
      .get<Page<Doc>>(`/documents`, { params: { repository_id: id, page, page_size: 10 } })
      .then((resp) => {
        setDocs(resp.data);
        return resp.data;
      });
  }, [id, page]);

  const loadAll = useCallback(() => {
    setLoading(true);
    setError("");
    Promise.all([
      api.get<Repository>(`/repositories/${id}`),
      api.get<RepositoryStats>(`/repositories/${id}/stats`),
      api.get<Member[]>(`/repositories/${id}/members`),
      loadDocs(),
    ])
      .then(([r, s, m]) => {
        setRepo(r.data);
        setStats(s.data);
        setMembers(m.data);
        setEditName(r.data.name);
        setEditDesc(r.data.description);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [id, loadDocs]);

  useEffect(loadAll, [loadAll]);

  // Poll while any document is still processing so states update live
  useEffect(() => {
    if (!docs?.items.some((d) => ACTIVE_STATUSES.has(d.status))) return;
    pollRef.current = window.setTimeout(() => {
      loadDocs().catch(() => undefined);
      api.get<RepositoryStats>(`/repositories/${id}/stats`).then((s) => setStats(s.data)).catch(() => undefined);
    }, 2500);
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current);
    };
  }, [docs, id, loadDocs]);

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    setUploading(true);
    try {
      const resp = await api.post<UploadResult[]>(
        `/documents/upload?repository_id=${id}`,
        form,
      );
      notify("success", `${resp.data.length} documento(s) cargado(s); el procesamiento inició`);
      await loadDocs();
    } catch (err) {
      notify("error", errorMessage(err));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleDeleteRepo() {
    try {
      await api.delete(`/repositories/${id}`);
      notify("success", "Repositorio eliminado");
      navigate("/repositorios");
    } catch (err) {
      notify("error", errorMessage(err));
      setDeleteOpen(false);
    }
  }

  async function handleAddMember(e: FormEvent) {
    e.preventDefault();
    if (!memberEmail.trim()) return;
    try {
      await api.post(`/repositories/${id}/members`, { email: memberEmail.trim(), role: "member" });
      notify("success", "Miembro agregado");
      setMemberEmail("");
      const m = await api.get<Member[]>(`/repositories/${id}/members`);
      setMembers(m.data);
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  async function handleRemoveMember(memberId: number) {
    try {
      await api.delete(`/repositories/${id}/members/${memberId}`);
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
      notify("success", "Miembro removido");
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault();
    try {
      const resp = await api.patch<Repository>(`/repositories/${id}`, {
        name: editName.trim(),
        description: editDesc.trim(),
      });
      setRepo(resp.data);
      setEditing(false);
      notify("success", "Repositorio actualizado");
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={loadAll} />;
  if (!repo) return null;

  const isOwnerOrAdmin = user?.role === "admin" || user?.id === repo.owner_id;

  return (
    <div>
      <PageHeader
        title={repo.name}
        subtitle={repo.description || "Sin descripción"}
        actions={
          isOwnerOrAdmin ? (
            <>
              <button
                onClick={() => setEditing(!editing)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Editar
              </button>
              <button
                onClick={() => setDeleteOpen(true)}
                className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
              >
                Eliminar
              </button>
            </>
          ) : undefined
        }
      />

      {editing && (
        <form onSubmit={handleSaveEdit} className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="edit-name" className="block text-sm font-medium text-slate-700">Nombre</label>
              <input id="edit-name" value={editName} onChange={(e) => setEditName(e.target.value)}
                     className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </div>
            <div>
              <label htmlFor="edit-desc" className="block text-sm font-medium text-slate-700">Descripción</label>
              <input id="edit-desc" value={editDesc} onChange={(e) => setEditDesc(e.target.value)}
                     className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </div>
          </div>
          <button type="submit" className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white">
            Guardar cambios
          </button>
        </form>
      )}

      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Documentos</p>
            <p className="text-2xl font-bold text-slate-800">{stats.document_count}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Completados</p>
            <p className="text-2xl font-bold text-green-600">{stats.by_status.completed ?? 0}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Fallidos</p>
            <p className="text-2xl font-bold text-red-600">{stats.by_status.failed ?? 0}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">Tamaño total</p>
            <p className="text-2xl font-bold text-slate-800">{formatBytes(stats.total_size_bytes)}</p>
          </div>
        </div>
      )}

      <div className="mb-6 rounded-xl border-2 border-dashed border-brand-200 bg-brand-50/50 p-6 text-center">
        <p className="font-medium text-slate-700">Cargar documentos (PDF, DOCX o TXT)</p>
        <p className="mt-1 text-sm text-slate-500">Puede seleccionar varios archivos a la vez — máximo 20 MB por archivo</p>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => handleUpload(e.target.files)}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className={`mt-3 inline-block cursor-pointer rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 ${uploading ? "pointer-events-none opacity-60" : ""}`}
        >
          {uploading ? "Cargando..." : "Seleccionar archivos"}
        </label>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold text-slate-700">Documentos</h2>
          {!docs || docs.items.length === 0 ? (
            <EmptyState title="Sin documentos" hint="Cargue archivos con el botón de arriba" />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Archivo</th>
                    <th className="px-4 py-2.5 font-medium">Categoría</th>
                    <th className="px-4 py-2.5 font-medium">Estado</th>
                    <th className="px-4 py-2.5 font-medium">Tamaño</th>
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
                      <td className="px-4 py-2.5"><CategoryBadge category={d.category} /></td>
                      <td className="px-4 py-2.5"><StatusBadge status={d.status} /></td>
                      <td className="px-4 py-2.5 text-slate-500">{formatBytes(d.size_bytes)}</td>
                      <td className="px-4 py-2.5 text-slate-500">{formatDate(d.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {docs && <Pagination page={docs.page} pages={docs.pages} onChange={setPage} />}
        </div>

        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-700">Miembros</h2>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <ul className="divide-y divide-slate-100">
              {members.map((m) => (
                <li key={m.id} className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{m.full_name}</p>
                    <p className="text-xs text-slate-400">{m.email} · {m.role === "owner" ? "Propietario" : "Miembro"}</p>
                  </div>
                  {isOwnerOrAdmin && m.role !== "owner" && (
                    <button
                      onClick={() => handleRemoveMember(m.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Quitar
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {isOwnerOrAdmin && (
              <form onSubmit={handleAddMember} className="mt-3 flex gap-2">
                <input
                  type="email"
                  value={memberEmail}
                  onChange={(e) => setMemberEmail(e.target.value)}
                  placeholder="correo@empresa.com"
                  aria-label="Correo del nuevo miembro"
                  className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
                <button type="submit" className="shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white">
                  Agregar
                </button>
              </form>
            )}
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="mb-2 font-semibold text-slate-700">Consultar con IA</h3>
            <p className="text-sm text-slate-500">
              Haga preguntas en lenguaje natural sobre los documentos de este repositorio.
            </p>
            <Link
              to={`/chat?repositorio=${repo.id}`}
              className="mt-3 inline-block rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Abrir consulta IA
            </Link>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Eliminar repositorio"
        message={`Se eliminará "${repo.name}" con todos sus documentos y resultados. Esta acción no se puede deshacer.`}
        onConfirm={handleDeleteRepo}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  );
}
