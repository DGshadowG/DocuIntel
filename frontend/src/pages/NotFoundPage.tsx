import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <p className="text-6xl font-bold text-slate-300">404</p>
      <h1 className="mt-2 text-xl font-semibold text-slate-700">Página no encontrada</h1>
      <p className="mt-1 text-sm text-slate-500">
        La página que busca no existe o fue movida.
      </p>
      <Link
        to="/"
        className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
      >
        Volver al dashboard
      </Link>
    </div>
  );
}
