import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ErrorState, PageHeader, Spinner, formatDate } from "../components/ui";

export default function UsersPage() {
  const { user: me } = useAuth();
  const { notify } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "user" });
  const [formError, setFormError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .get<User[]>("/users")
      .then((r) => setUsers(r.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    if (form.password.length < 8) {
      setFormError("La contraseña debe tener al menos 8 caracteres");
      return;
    }
    try {
      await api.post("/users", form);
      notify("success", "Usuario creado");
      setForm({ email: "", full_name: "", password: "", role: "user" });
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  }

  async function toggleActive(u: User) {
    try {
      await api.patch(`/users/${u.id}`, { is_active: !u.is_active });
      notify("success", u.is_active ? "Usuario desactivado" : "Usuario activado");
      load();
    } catch (err) {
      notify("error", errorMessage(err));
    }
  }

  return (
    <div>
      <PageHeader
        title="Usuarios"
        subtitle="Administración de cuentas y roles del sistema"
        actions={
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {showForm ? "Cancelar" : "Nuevo usuario"}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="u-email" className="block text-sm font-medium text-slate-700">Correo *</label>
              <input id="u-email" type="email" required value={form.email}
                     onChange={(e) => setForm({ ...form, email: e.target.value })}
                     className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </div>
            <div>
              <label htmlFor="u-name" className="block text-sm font-medium text-slate-700">Nombre completo *</label>
              <input id="u-name" required minLength={2} value={form.full_name}
                     onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                     className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </div>
            <div>
              <label htmlFor="u-pass" className="block text-sm font-medium text-slate-700">
                Contraseña * (mínimo 8 caracteres)
              </label>
              <input id="u-pass" type="password" required minLength={8} value={form.password}
                     onChange={(e) => setForm({ ...form, password: e.target.value })}
                     className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </div>
            <div>
              <label htmlFor="u-role" className="block text-sm font-medium text-slate-700">Rol</label>
              <select id="u-role" value={form.role}
                      onChange={(e) => setForm({ ...form, role: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
                <option value="user">Usuario estándar</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
          </div>
          {formError && <p role="alert" className="mt-2 text-sm text-red-600">{formError}</p>}
          <button type="submit"
                  className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white">
            Crear usuario
          </button>
        </form>
      )}

      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-2.5 font-medium">Nombre</th>
                <th className="px-4 py-2.5 font-medium">Correo</th>
                <th className="px-4 py-2.5 font-medium">Rol</th>
                <th className="px-4 py-2.5 font-medium">Estado</th>
                <th className="px-4 py-2.5 font-medium">Creado</th>
                <th className="px-4 py-2.5 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-2.5 font-medium text-slate-700">{u.full_name}</td>
                  <td className="px-4 py-2.5 text-slate-500">{u.email}</td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-600"
                    }`}>
                      {u.role === "admin" ? "Administrador" : "Usuario"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                      {u.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-2.5">
                    {u.id !== me?.id && (
                      <button onClick={() => toggleActive(u)}
                              className="text-xs font-medium text-brand-700 hover:underline">
                        {u.is_active ? "Desactivar" : "Activar"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
