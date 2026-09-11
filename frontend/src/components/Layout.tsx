import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", adminOnly: false },
  { to: "/repositorios", label: "Repositorios", adminOnly: false },
  { to: "/documentos", label: "Documentos", adminOnly: false },
  { to: "/buscar", label: "Buscar", adminOnly: false },
  { to: "/chat", label: "Consulta IA", adminOnly: false },
  { to: "/usuarios", label: "Usuarios", adminOnly: true },
  { to: "/auditoria", label: "Auditoría", adminOnly: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const items = NAV_ITEMS.filter((i) => !i.adminOnly || user?.role === "admin");

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              className="rounded p-1.5 text-slate-600 hover:bg-slate-100 md:hidden"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Abrir menú"
              aria-expanded={menuOpen}
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <NavLink to="/" className="flex items-center gap-2">
              <span className="rounded-lg bg-brand-600 px-2 py-1 text-sm font-bold text-white">DI</span>
              <span className="hidden text-lg font-semibold text-slate-800 sm:block">DocuIntel</span>
            </NavLink>
            <nav className="ml-6 hidden gap-1 md:flex" aria-label="Navegación principal">
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm font-medium ${
                      isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-700">{user?.full_name}</p>
              <p className="text-xs text-slate-400">
                {user?.role === "admin" ? "Administrador" : "Usuario"}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav className="border-t border-slate-100 px-4 py-2 md:hidden" aria-label="Navegación móvil">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
