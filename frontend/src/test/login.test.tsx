import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", () => ({
  api: {
    get: vi.fn().mockRejectedValue(new Error("no session")),
    post: vi.fn(),
  },
  getToken: vi.fn().mockReturnValue(null),
  setToken: vi.fn(),
  errorMessage: vi.fn().mockReturnValue("Correo o contrasena incorrectos"),
}));

import { api } from "../api/client";
import { AuthProvider } from "../context/AuthContext";
import LoginPage from "../pages/LoginPage";

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("valida campos vacíos sin llamar a la API", async () => {
    renderLogin();
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ingrese su correo y contraseña");
    expect(api.post).not.toHaveBeenCalled();
  });

  it("envía credenciales y muestra el error del backend si falla", async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error("401"));
    renderLogin();
    await userEvent.type(screen.getByLabelText("Correo electrónico"), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "clave-mala");
    await userEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "admin@empresa.com",
        password: "clave-mala",
      });
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contrasena incorrectos");
  });
});
