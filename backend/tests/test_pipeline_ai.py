"""TC-11..16, TC-23: extraction, classification, summary, structured data,
AI provider failure handling, ground-truth evaluation."""
import io
import json

import pytest

from tests.conftest import SAMPLES_DIR, auth, run_pending_jobs, sample_file


def upload_and_process(client, token, repo_id, filename):
    resp = client.post(
        f"/api/v1/documents/upload?repository_id={repo_id}",
        headers=auth(token),
        files=[("files", (filename, io.BytesIO(sample_file(filename)), "application/octet-stream"))],
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()[0]["document"]["id"]
    run_pending_jobs()
    detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth(token))
    return detail.json()


class TestExtractionPipeline:
    def test_tc11_extraccion_texto_pdf_docx_txt(self, client, user_token, make_repo):
        repo = make_repo("Repo extraccion")
        for name in ("factura_01.pdf", "contrato_05.docx", "hoja_de_vida_08.txt"):
            detail = upload_and_process(client, user_token, repo["id"], name)
            assert detail["status"] == "completed", f"{name}: {detail['error_message']}"
            content = client.get(f"/api/v1/documents/{detail['id']}/content",
                                 headers=auth(user_token)).json()
            assert content["char_count"] > 100, name
            assert detail["chunk_count"] >= 1, name

    def test_documento_ilegible_falla_con_error(self, client, user_token, make_repo):
        repo = make_repo("Repo ilegible")
        # Valid PDF signature but corrupt body -> extraction stage must fail
        corrupt = b"%PDF-1.4\n" + b"\x00basura" * 50
        resp = client.post(
            f"/api/v1/documents/upload?repository_id={repo['id']}",
            headers=auth(user_token),
            files=[("files", ("corrupto.pdf", io.BytesIO(corrupt), "application/pdf"))],
        )
        assert resp.status_code == 201
        doc_id = resp.json()[0]["document"]["id"]
        run_pending_jobs()
        detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth(user_token)).json()
        assert detail["status"] == "failed"
        assert detail["error_message"] != ""
        jobs = client.get(f"/api/v1/documents/{doc_id}/jobs", headers=auth(user_token)).json()
        assert jobs[0]["status"] == "failed"
        assert jobs[0]["attempt"] == jobs[0]["max_attempts"]  # retries were consumed


class TestClassification:
    def test_tc12_clasificacion_tres_categorias(self, client, user_token, make_repo):
        repo = make_repo("Repo clasificacion")
        cases = [
            ("factura_08.txt", "financiero"),
            ("contrato_08.txt", "legal"),
            ("hoja_de_vida_08.txt", "talento_humano"),
        ]
        for name, expected in cases:
            detail = upload_and_process(client, user_token, repo["id"], name)
            assert detail["classification"] is not None, name
            assert detail["classification"]["predicted_category"] == expected, name
            assert 0 <= detail["classification"]["confidence"] <= 1
            assert detail["classification"]["model"] == "deterministic-v1"

    def test_correccion_manual_conserva_prediccion(self, client, user_token, make_repo):
        repo = make_repo("Repo correccion")
        detail = upload_and_process(client, user_token, repo["id"], "factura_09.txt")
        original = detail["classification"]["predicted_category"]
        resp = client.patch(f"/api/v1/documents/{detail['id']}/category",
                            headers=auth(user_token), json={"category": "otro"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["predicted_category"] == original      # prediction preserved
        assert body["manual_category"] == "otro"
        assert body["effective_category"] == "otro"
        assert body["corrected_at"] is not None


class TestSummary:
    def test_tc13_resumen(self, client, user_token, make_repo):
        repo = make_repo("Repo resumen")
        detail = upload_and_process(client, user_token, repo["id"], "contrato_09.txt")
        assert detail["summary"] is not None
        assert len(detail["summary"]["content"]) > 50
        assert detail["summary"]["model"] == "deterministic-v1"


class TestStructuredExtraction:
    @pytest.fixture(scope="class")
    def ground_truth(self):
        return {g["filename"]: g for g in
                json.loads((SAMPLES_DIR / "ground_truth.json").read_text(encoding="utf-8"))}

    def test_tc14_extraccion_factura(self, client, user_token, make_repo, ground_truth):
        repo = make_repo("Repo ext factura")
        detail = upload_and_process(client, user_token, repo["id"], "factura_08.txt")
        extractions = {e["schema_name"]: e for e in detail["extractions"]}
        assert "invoice" in extractions
        data = extractions["invoice"]["data"]
        gt = ground_truth["factura_08.txt"]["fields"]
        assert data["numero_factura"] == gt["numero_factura"]
        assert data["total"] == pytest.approx(gt["total"], rel=0.01)
        assert data["subtotal"] == pytest.approx(gt["subtotal"], rel=0.01)
        assert data["moneda"] == gt["moneda"]

    def test_tc15_extraccion_contrato(self, client, user_token, make_repo, ground_truth):
        repo = make_repo("Repo ext contrato")
        detail = upload_and_process(client, user_token, repo["id"], "contrato_08.txt")
        extractions = {e["schema_name"]: e for e in detail["extractions"]}
        assert "contract" in extractions
        data = extractions["contract"]["data"]
        gt = ground_truth["contrato_08.txt"]["fields"]
        assert data["fecha_inicio"] == gt["fecha_inicio"]
        assert data["fecha_terminacion"] == gt["fecha_terminacion"]
        assert data["duracion"] == gt["duracion"]
        assert len(data["obligaciones"]) >= gt["num_obligaciones_min"]

    def test_tc16_extraccion_hoja_de_vida(self, client, user_token, make_repo, ground_truth):
        repo = make_repo("Repo ext hv")
        detail = upload_and_process(client, user_token, repo["id"], "hoja_de_vida_08.txt")
        extractions = {e["schema_name"]: e for e in detail["extractions"]}
        assert "resume" in extractions
        data = extractions["resume"]["data"]
        gt = ground_truth["hoja_de_vida_08.txt"]["fields"]
        assert data["nombre"] == gt["nombre"]
        assert len(data["habilidades"]) >= 3
        assert len(data["experiencia"]) >= 1
        assert len(data["idiomas"]) == len(gt["idiomas"])


class TestGroundTruthEvaluation:
    def test_evaluacion_clasificacion_corpus_txt(self, client, user_token, make_repo):
        """Classify every TXT document in the corpus and require >=80% accuracy
        against ground truth (TXT avoids PDF re-extraction noise in this test)."""
        gt = {g["filename"]: g for g in
              json.loads((SAMPLES_DIR / "ground_truth.json").read_text(encoding="utf-8"))}
        txt_files = [name for name in gt if name.endswith(".txt")]
        assert len(txt_files) == 9
        repo = make_repo("Repo eval corpus")
        correct = 0
        for name in txt_files:
            detail = upload_and_process(client, user_token, repo["id"], name)
            assert detail["status"] == "completed", f"{name}: {detail['error_message']}"
            if detail["classification"]["predicted_category"] == gt[name]["category"]:
                correct += 1
        accuracy = correct / len(txt_files)
        assert accuracy >= 0.8, f"Precision de clasificacion {accuracy:.0%} por debajo del 80%"


class TestAIProviderFailure:
    def test_tc23_fallo_proveedor_ia(self, client, user_token, make_repo, monkeypatch):
        """If the AI provider raises, the job retries and finally fails with the
        technical error recorded — the API never returns a fake success."""
        from app.ai.base import AIProviderError
        from app.ai.deterministic import DeterministicProvider

        def broken_classify(self, text):
            raise AIProviderError("simulacion: servicio de IA no disponible")

        monkeypatch.setattr(DeterministicProvider, "classify", broken_classify)
        repo = make_repo("Repo fallo IA")
        resp = client.post(
            f"/api/v1/documents/upload?repository_id={repo['id']}",
            headers=auth(user_token),
            files=[("files", ("factura_10.txt", io.BytesIO(sample_file("factura_10.txt")), "text/plain"))],
        )
        doc_id = resp.json()[0]["document"]["id"]
        run_pending_jobs()
        detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth(user_token)).json()
        assert detail["status"] == "failed"
        assert "IA" in detail["error_message"] or "proveedor" in detail["error_message"].lower()
        jobs = client.get(f"/api/v1/documents/{doc_id}/jobs", headers=auth(user_token)).json()
        assert jobs[0]["attempt"] == jobs[0]["max_attempts"]
        assert jobs[0]["stage"] == "classification"

        # Recovery: provider works again -> reprocess succeeds (TC-24 complement)
        monkeypatch.undo()
        client.post(f"/api/v1/documents/{doc_id}/reprocess", headers=auth(user_token))
        run_pending_jobs()
        detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth(user_token)).json()
        assert detail["status"] == "completed"
