import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import { Spinner } from "./components/ui";
import AuditPage from "./pages/AuditPage";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import DocumentDetailPage from "./pages/DocumentDetailPage";
import DocumentsPage from "./pages/DocumentsPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RepositoriesPage from "./pages/RepositoriesPage";
import RepositoryDetailPage from "./pages/RepositoryDetailPage";
import SearchPage from "./pages/SearchPage";
import UsersPage from "./pages/UsersPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Verificando sesión..." />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/repositorios" element={<RepositoriesPage />} />
        <Route path="/repositorios/:id" element={<RepositoryDetailPage />} />
        <Route path="/documentos" element={<DocumentsPage />} />
        <Route path="/documentos/:id" element={<DocumentDetailPage />} />
        <Route path="/buscar" element={<SearchPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route
          path="/usuarios"
          element={
            <RequireAdmin>
              <UsersPage />
            </RequireAdmin>
          }
        />
        <Route
          path="/auditoria"
          element={
            <RequireAdmin>
              <AuditPage />
            </RequireAdmin>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
