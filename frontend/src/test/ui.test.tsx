import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  CategoryBadge,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Pagination,
  StatusBadge,
  formatBytes,
} from "../components/ui";

describe("StatusBadge", () => {
  it("muestra las etiquetas en español para cada estado", () => {
    const { rerender } = render(<StatusBadge status="completed" />);
    expect(screen.getByText("Completado")).toBeInTheDocument();
    rerender(<StatusBadge status="failed" />);
    expect(screen.getByText("Fallido")).toBeInTheDocument();
    rerender(<StatusBadge status="processing" />);
    expect(screen.getByText("Procesando")).toBeInTheDocument();
    rerender(<StatusBadge status="queued" />);
    expect(screen.getByText("En cola")).toBeInTheDocument();
  });
});

describe("CategoryBadge", () => {
  it("muestra la categoría legible", () => {
    render(<CategoryBadge category="financiero" />);
    expect(screen.getByText("Financiero / Facturas")).toBeInTheDocument();
  });

  it("muestra 'Sin clasificar' cuando no hay categoría", () => {
    render(<CategoryBadge category={null} />);
    expect(screen.getByText("Sin clasificar")).toBeInTheDocument();
  });
});

describe("ConfirmDialog", () => {
  it("solo se muestra cuando open=true y ejecuta las acciones", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { rerender } = render(
      <ConfirmDialog open={false} title="Eliminar" message="¿Seguro?"
                     onConfirm={onConfirm} onCancel={onCancel} />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    rerender(
      <ConfirmDialog open={true} title="Eliminar" message="¿Seguro?"
                     onConfirm={onConfirm} onCancel={onCancel} />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});

describe("Pagination", () => {
  it("no renderiza nada con una sola página", () => {
    const { container } = render(<Pagination page={1} pages={1} onChange={() => undefined} />);
    expect(container.innerHTML).toBe("");
  });

  it("deshabilita Anterior en la primera página y navega con Siguiente", async () => {
    const onChange = vi.fn();
    render(<Pagination page={1} pages={3} onChange={onChange} />);
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(onChange).toHaveBeenCalledWith(2);
  });
});

describe("estados de la interfaz", () => {
  it("EmptyState muestra título y pista", () => {
    render(<EmptyState title="Sin documentos" hint="Cargue archivos" />);
    expect(screen.getByText("Sin documentos")).toBeInTheDocument();
    expect(screen.getByText("Cargue archivos")).toBeInTheDocument();
  });

  it("ErrorState muestra el mensaje y permite reintentar", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Fallo de red" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Fallo de red");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("formatBytes", () => {
  it("formatea bytes, KB y MB", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
