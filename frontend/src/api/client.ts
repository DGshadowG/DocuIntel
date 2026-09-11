import axios, { AxiosError } from "axios";
import type { ApiError } from "./types";

const TOKEN_KEY = "docuintel_token";

export const api = axios.create({ baseURL: "/api/v1" });

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/auth/login")) {
      setToken(null);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a user-readable Spanish message from any API error. */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as ApiError | undefined;
    if (body?.error?.message) {
      const details = body.error.details
        ?.map((d) => `${d.campo}: ${d.detalle}`)
        .join("; ");
      return details ? `${body.error.message} (${details})` : body.error.message;
    }
    if (err.code === "ERR_NETWORK") return "No se pudo conectar con el servidor";
  }
  return "Ocurrió un error inesperado";
}
