"""Evaluate classification and structured extraction of the loaded corpus
against sample_documents/ground_truth.json, using the live API.

Writes evidence/test-results/ground-truth-eval.json with per-document detail
and aggregate metrics.

Run (backend up, corpus loaded):  python scripts/evaluate_ground_truth.py
"""
import datetime as dt
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_documents"
EVIDENCE = ROOT / "evidence" / "test-results"


def approx(a, b, tol=0.01):
    if a is None or b is None:
        return a == b
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def main() -> int:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()

    api = "http://localhost:8000/api/v1"
    client = httpx.Client(timeout=60)
    token = client.post(f"{api}/auth/login", json={
        "email": env["SEED_ADMIN_EMAIL"], "password": env["SEED_ADMIN_PASSWORD"],
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    repos = client.get(f"{api}/repositories", headers=headers).json()
    repo = next(r for r in repos if r["name"] == "Documentos Corporativos")

    docs = {}
    page = 1
    while True:
        data = client.get(f"{api}/documents", headers=headers, params={
            "repository_id": repo["id"], "page": page, "page_size": 100}).json()
        for d in data["items"]:
            docs[d["original_filename"]] = d["id"]
        if page >= max(data["pages"], 1):
            break
        page += 1

    gt = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))
    per_doc = []
    cls_correct = 0
    field_total = 0
    field_correct = 0

    for entry in gt:
        name = entry["filename"]
        if name not in docs:
            per_doc.append({"filename": name, "error": "no cargado"})
            continue
        detail = client.get(f"{api}/documents/{docs[name]}", headers=headers).json()
        predicted = detail["classification"]["predicted_category"] if detail["classification"] else None
        cls_ok = predicted == entry["category"]
        cls_correct += int(cls_ok)

        extraction = {e["schema_name"]: e["data"] for e in detail["extractions"]}
        schema = {"financiero": "invoice", "legal": "contract", "talento_humano": "resume"}[entry["category"]]
        data = extraction.get(schema, {})
        field_results = {}
        expected_fields = entry["fields"]

        if schema == "invoice":
            checks = {
                "numero_factura": data.get("numero_factura") == expected_fields["numero_factura"],
                "subtotal": approx(data.get("subtotal"), expected_fields["subtotal"]),
                "impuestos": approx(data.get("impuestos"), expected_fields["impuestos"]),
                "total": approx(data.get("total"), expected_fields["total"]),
                "moneda": data.get("moneda") == expected_fields["moneda"],
            }
        elif schema == "contract":
            checks = {
                "fecha_inicio": data.get("fecha_inicio") == expected_fields["fecha_inicio"],
                "fecha_terminacion": data.get("fecha_terminacion") == expected_fields["fecha_terminacion"],
                "duracion": data.get("duracion") == expected_fields["duracion"],
                "obligaciones": len(data.get("obligaciones", [])) >= expected_fields["num_obligaciones_min"],
            }
        else:  # resume
            checks = {
                "nombre": data.get("nombre") == expected_fields["nombre"],
                "educacion": len(data.get("educacion", [])) >= 1,
                "experiencia": len(data.get("experiencia", [])) >= 1,
                "habilidades": len(data.get("habilidades", [])) >= 3,
            }

        for field, ok in checks.items():
            field_results[field] = bool(ok)
            field_total += 1
            field_correct += int(ok)

        per_doc.append({
            "filename": name,
            "format": entry["format"],
            "expected_category": entry["category"],
            "predicted_category": predicted,
            "classification_ok": cls_ok,
            "confidence": detail["classification"]["confidence"] if detail["classification"] else None,
            "fields": field_results,
        })

    n = len([e for e in gt])
    summary = {
        "executed_at": dt.datetime.now().isoformat(),
        "documents_evaluated": n,
        "classification_accuracy": round(cls_correct / n, 4),
        "classification_correct": cls_correct,
        "field_accuracy": round(field_correct / field_total, 4) if field_total else None,
        "fields_correct": field_correct,
        "fields_total": field_total,
        "detail": per_doc,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "ground-truth-eval.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Clasificacion: {cls_correct}/{n} ({summary['classification_accuracy']:.0%})")
    print(f"Campos extraidos: {field_correct}/{field_total} ({summary['field_accuracy']:.0%})")
    fails = [d for d in per_doc if not d.get("classification_ok", True)
             or not all(d.get("fields", {}).values())]
    if fails:
        print("\nDocumentos con diferencias:")
        for f in fails:
            bad_fields = [k for k, v in f.get("fields", {}).items() if not v]
            print(f"  - {f['filename']}: "
                  + ("clasificacion incorrecta " if not f.get("classification_ok", True) else "")
                  + (f"campos: {bad_fields}" if bad_fields else ""))
    print("\nEvidencia: evidence/test-results/ground-truth-eval.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
