"""Load the 30-document synthetic corpus into the demo repository through the
real API (exactly the same path the UI uses), wait for the pipeline to finish
and print a per-document summary.

Requires the backend running (default http://localhost:8000).

Run:  python scripts/load_corpus.py [--base-url URL]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_documents"

MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default=None, help="por defecto usa SEED_ADMIN_EMAIL del .env")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    # Read seed credentials from .env (never hardcoded here)
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    email = args.email or env.get("SEED_ADMIN_EMAIL", "admin@docuintel.co")
    password = args.password or env.get("SEED_ADMIN_PASSWORD", "")
    if not password:
        print("ERROR: no hay contrasena (defina SEED_ADMIN_PASSWORD en .env o use --password)")
        return 1

    api = args.base_url.rstrip("/") + "/api/v1"
    client = httpx.Client(timeout=60)

    # --- login ---------------------------------------------------------------
    resp = client.post(f"{api}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"ERROR login: {resp.status_code} {resp.text}")
        return 1
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[ok] Sesion iniciada como {email}")

    # --- find or create the demo repository ---------------------------------
    repos = client.get(f"{api}/repositories", headers=headers).json()
    repo = next((r for r in repos if r["name"] == "Documentos Corporativos"), None)
    if repo is None:
        repo = client.post(f"{api}/repositories", headers=headers, json={
            "name": "Documentos Corporativos",
            "description": "Repositorio de demostracion con el corpus sintetico de 30 documentos.",
        }).json()
        print("[ok] Repositorio demo creado")
    repo_id = repo["id"]

    # --- skip files already uploaded (idempotent) ----------------------------
    existing = set()
    page = 1
    while True:
        data = client.get(f"{api}/documents", headers=headers,
                          params={"repository_id": repo_id, "page": page, "page_size": 100}).json()
        existing.update(d["original_filename"] for d in data["items"])
        if page >= max(data["pages"], 1):
            break
        page += 1

    gt = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))
    uploaded = 0
    for entry in gt:
        name = entry["filename"]
        if name in existing:
            print(f"[skip] {name} ya existe")
            continue
        path = SAMPLES / name
        ext = name.rsplit(".", 1)[-1]
        files = {"files": (name, path.read_bytes(), MIME[ext])}
        resp = client.post(f"{api}/documents/upload", headers=headers,
                           params={"repository_id": repo_id}, files=files)
        if resp.status_code != 201:
            print(f"[ERROR] {name}: {resp.status_code} {resp.text[:200]}")
            return 1
        uploaded += 1
        print(f"[up] {name}")

    # --- wait for processing -------------------------------------------------
    print(f"[..] {uploaded} documentos cargados; esperando pipeline...")
    deadline = time.time() + 300
    while time.time() < deadline:
        data = client.get(f"{api}/documents", headers=headers,
                          params={"repository_id": repo_id, "page": 1, "page_size": 100}).json()
        by_status = {}
        for d in data["items"]:
            by_status[d["status"]] = by_status.get(d["status"], 0) + 1
        pending = sum(by_status.get(s, 0) for s in ("pending", "queued", "processing"))
        print(f"    estados: {by_status}")
        if pending == 0:
            break
        time.sleep(3)

    # --- final summary -------------------------------------------------------
    stats = client.get(f"{api}/repositories/{repo_id}/stats", headers=headers).json()
    print("\n=== RESUMEN DEL CORPUS CARGADO ===")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    failed = stats["by_status"].get("failed", 0)
    if failed:
        print(f"\nADVERTENCIA: {failed} documentos fallaron")
        return 2
    print("\n[ok] Corpus completo procesado sin fallos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
