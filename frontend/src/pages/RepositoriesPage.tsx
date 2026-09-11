import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Repository } from "../api/types";
import { useToast } from "../context/ToastContext";
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  formatDate,
} from "../components/ui";

export default function RepositoriesPage() {
  const { notify } = useToast();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState("");
  const [toDelete, setToDelete] = useState<Repository | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .get<Repository[]>("/repositories")
      .then((resp) => setRepos(resp.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    if (name.trim().length < 2) {
      setFormError("El nombre debe tener al menos 2 caracteres");
      return;
    }
    try {
      await api.post("/repositories", { name: name.trim(), description: description.trim() });
      notify("success", "Repositorio creado correctamente");
      setName("");
      setDescription("");
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  }

  async function handleDelete() {
    if (!toDelete) return;
    try {
      await api.delete(`/repositories/${toDelete.id}`);
      notify("success", `Repositorio "${toDelete.name}" eliminado`);
      setToDelete(null);
      load();
    } catch (err) {
      notify("error", errorMessage(err));
      setToDelete(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Repositorios"
        subtitle="Espacios de trabajo que agrupan documentos y controlan el acceso"
        actions={
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {showForm ? "Cancelar" : "Nuevo repositorio"}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="repo-name" className="block text-sm font-medium text-slate-700">
                Nombre *
              </label>
              <input
                id="repo-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={150}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
                placeholder="Ej: Contratos 2025"
              />
            </div>
            <div>
              <label htmlFor="repo-desc" className="block text-sm font-medium text-slate-700">
                Descripción
              </label>
              <input
                id="repo-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={2000}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none"
                placeholder="Opcional"
              />
            </div>
          </div>
          {formError && (
            <p role="alert" className="mt-2 text-sm text-red-600">{formError}</p>
          )}
          <button
            type="submit"
            className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Crear repositorio
          </button>
        </form>
      )}

      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : repos.length === 0 ? (
        <EmptyState
          title="No tiene repositorios todavía"
          hint="Cree su primer repositorio para empezar a cargar documentos"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {repos.map((repo) => (
            <div key={repo.id} className="flex flex-col rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex-1">
                <Link
                  to={`/repositorios/${repo.id}`}
                  className="text-lg font-semibold text-brand-700 hover:underline"
                >
                  {repo.name}
                </Link>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                  {repo.description || "Sin descripción"}
                </p>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
                <span className="text-slate-500">
                  {repo.document_count} documento{repo.document_count === 1 ? "" : "s"}
                </span>
                <span className="text-xs text-slate-400">{formatDate(repo.created_at)}</span>
              </div>
              <div className="mt-2 flex justify-end">
                <button
                  onClick={() => setToDelete(repo)}
                  className="text-sm text-red-600 hover:underline"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Eliminar repositorio"
        message={`Se eliminará "${toDelete?.name}" con sus ${toDelete?.document_count ?? 0} documentos, resultados de IA y conversaciones. Esta acción no se puede deshacer.`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
