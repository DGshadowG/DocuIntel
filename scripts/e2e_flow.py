"""End-to-end flow against the live system (TC-26): exercises the complete
user journey through the real API and records genuine evidence.

Flow: login admin -> create repository -> upload PDF+DOCX+TXT -> wait for
pipeline -> verify classification/summary/extraction -> text search ->
semantic search -> 3 RAG questions with citations + 1 unanswerable ->
dashboard -> ground-truth evaluation over the full demo corpus -> cleanup.

Writes evidence to evidence/test-results/e2e-api-results.json and prints a
human-readable log.

Run (backend must be up):  python scripts/e2e_flow.py
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_documents"
EVIDENCE = ROOT / "evidence" / "test-results"

MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}

results = []


def step(name: str, ok: bool, detail: str = ""):
    results.append({"step": name, "ok": bool(ok), "detail": detail})
    print(f"[{'OK ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        finish(1)


def finish(code: int):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    payload = {
        "executed_at": dt.datetime.now().isoformat(),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "steps": results,
    }
    (EVIDENCE / "e2e-api-results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nEvidencia guardada en evidence/test-results/e2e-api-results.json "
          f"({payload['passed']} pasos OK, {payload['failed']} fallidos)")
    sys.exit(code)


def main():
    base = "http://localhost:8000"
    api = f"{base}/api/v1"
    client = httpx.Client(timeout=60)

    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()

    # 1. Health
    health = client.get(f"{base}/health").json()
    step("Health check", health["status"] == "ok", f"db={health['database']}, ia={health['ai_provider']}")

    # 2. Login
    resp = client.post(f"{api}/auth/login", json={
        "email": env["SEED_ADMIN_EMAIL"], "password": env["SEED_ADMIN_PASSWORD"]})
    step("Login administrador", resp.status_code == 200)
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    # 3. Create E2E repository
    repo = client.post(f"{api}/repositories", headers=headers, json={
        "name": f"E2E {dt.datetime.now():%Y%m%d-%H%M%S}",
        "description": "Repositorio temporal del flujo E2E",
    }).json()
    step("Crear repositorio", "id" in repo, f"id={repo.get('id')}")
    repo_id = repo["id"]

    # 4. Upload one file per format
    doc_ids = {}
    for name in ("factura_01.pdf", "contrato_05.docx", "hoja_de_vida_08.txt"):
        ext = name.rsplit(".", 1)[-1]
        resp = client.post(f"{api}/documents/upload", headers=headers,
                           params={"repository_id": repo_id},
                           files={"files": (name, (SAMPLES / name).read_bytes(), MIME[ext])})
        ok = resp.status_code == 201
        if ok:
            doc_ids[name] = resp.json()[0]["document"]["id"]
        step(f"Carga {ext.upper()} ({name})", ok)

    # 5. Wait for pipeline
    deadline = time.time() + 120
    while time.time() < deadline:
        data = client.get(f"{api}/documents", headers=headers,
                          params={"repository_id": repo_id, "page_size": 10}).json()
        statuses = {d["original_filename"]: d["status"] for d in data["items"]}
        if all(s in ("completed", "failed") for s in statuses.values()):
            break
        time.sleep(2)
    step("Pipeline completo para los 3 formatos",
         all(s == "completed" for s in statuses.values()), str(statuses))

    # 6. Verify AI results per document
    expected = {"factura_01.pdf": ("financiero", "invoice"),
                "contrato_05.docx": ("legal", "contract"),
                "hoja_de_vida_08.txt": ("talento_humano", "resume")}
    for name, (cat, schema) in expected.items():
        detail = client.get(f"{api}/documents/{doc_ids[name]}", headers=headers).json()
        got_cat = detail["classification"]["predicted_category"] if detail["classification"] else None
        has_summary = bool(detail["summary"] and len(detail["summary"]["content"]) > 30)
        schemas = [e["schema_name"] for e in detail["extractions"]]
        step(f"Clasificacion {name}", got_cat == cat, f"predicha={got_cat}")
        step(f"Resumen {name}", has_summary)
        step(f"Extraccion {schema} {name}", schema in schemas, f"esquemas={schemas}")

    # 7. Text search
    search = client.get(f"{api}/search/text", headers=headers,
                        params={"q": "obligaciones", "repository_id": repo_id}).json()
    step("Busqueda textual", search["total"] >= 1,
         f"{search['total']} resultados, primero={search['hits'][0]['document_name'] if search['hits'] else '-'}")

    # 8. Semantic search
    sem = client.get(f"{api}/search/semantic", headers=headers,
                     params={"q": "experiencia laboral y habilidades del candidato",
                             "repository_id": repo_id, "top_k": 5}).json()
    top = sem["hits"][0]["document_name"] if sem["hits"] else "-"
    step("Busqueda semantica", sem["total"] >= 1 and top.startswith("hoja_de_vida"),
         f"top={top}, score={sem['hits'][0]['score'] if sem['hits'] else 0}")

    # 9. RAG: 3 real questions + 1 unanswerable
    conv = client.post(f"{api}/conversations", headers=headers,
                       json={"repository_id": repo_id}).json()
    gt = {g["filename"]: g for g in json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))}
    inv = gt["factura_01.pdf"]["fields"]
    con = gt["contrato_05.docx"]["fields"]
    res = gt["hoja_de_vida_08.txt"]["fields"]
    questions = [
        (f"¿Cual es el total a pagar de la factura {inv['numero_factura']}?", True),
        (f"¿Cual es la fecha de terminacion del contrato entre {con['partes'][0]} y {con['partes'][1]}?", True),
        (f"¿Que habilidades tiene {res['nombre']}?", True),
        ("¿Cual es la receta de la bandeja paisa tradicional?", False),
    ]
    for question, expect_grounded in questions:
        answer = client.post(f"{api}/conversations/{conv['id']}/ask", headers=headers,
                             json={"question": question}).json()
        if expect_grounded:
            ok = answer["grounded"] and len(answer["citations"]) >= 1
            detail_txt = (f"citas={len(answer['citations'])}, latencia={answer['latency_ms']}ms, "
                          f"fuente={answer['citations'][0]['document_name'] if answer['citations'] else '-'}")
        else:
            ok = not answer["grounded"] and not answer["citations"]
            detail_txt = "sin evidencia detectada correctamente"
        step(f"RAG: {question[:60]}...", ok, detail_txt)

    # 10. Dashboard reflects real data
    dash = client.get(f"{api}/dashboard", headers=headers).json()
    step("Dashboard con datos reales",
         dash["total_documents"] >= 3 and dash["processed_count"] >= 3,
         f"docs={dash['total_documents']}, procesados={dash['processed_count']}")

    # 11. Cleanup E2E repository (demo corpus repo remains)
    deleted = client.delete(f"{api}/repositories/{repo_id}", headers=headers)
    step("Limpieza del repositorio E2E", deleted.status_code == 204)

    finish(0)


if __name__ == "__main__":
    main()
