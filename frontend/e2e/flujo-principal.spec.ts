import { expect, test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * TC-26 (UI): main end-to-end journey through the real interface.
 * Login -> dashboard -> repository -> upload TXT -> processing -> document
 * detail with AI results -> search -> RAG chat with citations -> logout.
 * Saves real screenshots to evidence/screenshots/.
 *
 * Credentials come from environment variables (E2E_EMAIL / E2E_PASSWORD) or
 * the repository .env seed values — never hardcoded here.
 */

const ROOT = path.resolve(__dirname, "..", "..");
const SHOTS = path.join(ROOT, "evidence", "screenshots");

function seedCredentials(): { email: string; password: string } {
  if (process.env.E2E_EMAIL && process.env.E2E_PASSWORD) {
    return { email: process.env.E2E_EMAIL, password: process.env.E2E_PASSWORD };
  }
  const env = fs.readFileSync(path.join(ROOT, ".env"), "utf-8");
  const get = (key: string) =>
    env.split(/\r?\n/).find((l) => l.startsWith(`${key}=`))?.split("=")[1]?.trim() ?? "";
  return { email: get("SEED_ADMIN_EMAIL"), password: get("SEED_ADMIN_PASSWORD") };
}

test.beforeAll(() => {
  fs.mkdirSync(SHOTS, { recursive: true });
});

test("flujo principal completo con evidencias", async ({ page }) => {
  const { email, password } = seedCredentials();

  // ---- 1. Login -----------------------------------------------------------
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "DocuIntel" })).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "01-login.png") });

  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  // ---- 2. Dashboard -------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Por categoría")).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "02-dashboard.png"), fullPage: true });

  // ---- 3. Repositories ----------------------------------------------------
  await page.getByRole("link", { name: "Repositorios" }).first().click();
  await expect(page.getByRole("heading", { name: "Repositorios" })).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "03-repositorios.png") });

  await page.getByRole("link", { name: "Documentos Corporativos" }).click();
  await expect(page.getByText("Cargar documentos (PDF, DOCX o TXT)")).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "04-repositorio-detalle.png"), fullPage: true });

  // ---- 4. Upload a new TXT document and watch it process ------------------
  const uniqueContent = [
    "ACTA DE REUNION E2E",
    "Fecha de emision: 05/09/2026",
    "FACTURA DE VENTA No: FV-E2E-777",
    "Proveedor: Pruebas Automatizadas SAS",
    "Subtotal: $1.000.000",
    "IVA (19%): $190.000",
    "Total a pagar: $1.190.000",
    "Moneda: COP",
    "Documento generado por la prueba E2E de interfaz.",
  ].join("\n");
  await page.locator("#file-upload").setInputFiles({
    name: "factura_e2e.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(uniqueContent, "utf-8"),
  });
  await expect(page.getByText("documento(s) cargado(s)", { exact: false })).toBeVisible();

  // The poller refreshes states; wait until our file shows Completado
  const row = page.getByRole("row", { name: /factura_e2e\.txt/ }).first();
  await expect(row.getByText("Completado")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(SHOTS, "05-carga-procesada.png"), fullPage: true });

  // ---- 5. Document detail with AI results ---------------------------------
  await row.getByRole("link", { name: "factura_e2e.txt" }).click();
  await expect(page.getByText("Resumen generado por IA")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Datos de la factura")).toBeVisible();
  await expect(page.getByText("FV-E2E-777", { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "06-documento-detalle.png"), fullPage: true });

  // ---- 6. Text search -----------------------------------------------------
  await page.getByRole("link", { name: "Buscar" }).first().click();
  await page.getByLabel("Texto a buscar").fill("FV-E2E-777");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByRole("link", { name: "factura_e2e.txt" })).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "07-busqueda-textual.png"), fullPage: true });

  // ---- 7. Semantic search -------------------------------------------------
  await page.getByRole("button", { name: "Semántica (IA)" }).click();
  await page.getByLabel("Texto a buscar").fill("hoja de vida con experiencia en desarrollo de software");
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByText("búsqueda semántica")).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "08-busqueda-semantica.png"), fullPage: true });

  // ---- 8. RAG chat with citations -----------------------------------------
  await page.getByRole("link", { name: "Consulta IA" }).first().click();
  await page.getByLabel("Pregunta sobre los documentos").fill(
    "¿Cual es el total a pagar de la factura FV-E2E-777?",
  );
  await page.getByRole("button", { name: "Preguntar" }).click();
  await expect(page.getByText("Fuentes citadas:")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(SHOTS, "09-chat-rag-citas.png"), fullPage: true });

  // Unanswerable question -> explicit "no evidence" behavior
  await page.getByLabel("Pregunta sobre los documentos").fill(
    "¿Cual es la receta de la bandeja paisa tradicional?",
  );
  await page.getByRole("button", { name: "Preguntar" }).click();
  await expect(
    page.getByText("Sin evidencia suficiente en los documentos", { exact: false }).first(),
  ).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(SHOTS, "10-chat-sin-evidencia.png"), fullPage: true });

  // ---- 9. Cleanup the E2E document and logout -----------------------------
  await page.getByRole("link", { name: "Documentos" }).first().click();
  await page.getByLabel("Buscar por nombre de archivo").fill("factura_e2e");
  await page.getByRole("link", { name: "factura_e2e.txt" }).click();
  await page.getByRole("button", { name: "Eliminar" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Eliminar" }).click();

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByRole("heading", { name: "DocuIntel" })).toBeVisible();
});

test("acceso denegado sin sesion", async ({ page }) => {
  await page.goto("/repositorios");
  // Route guard redirects to login
  await expect(page.getByRole("heading", { name: "DocuIntel" })).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("pagina 404", async ({ page }) => {
  const { email, password } = seedCredentials();
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.goto("/ruta-que-no-existe");
  await expect(page.getByText("404")).toBeVisible();
  await expect(page.getByText("Página no encontrada")).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "11-pagina-404.png") });
});
