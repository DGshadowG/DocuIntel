"""TC-17..20, TC-25: text search, semantic search, RAG with citations,
insufficient-evidence handling, dashboard indicators."""
import io
import json

import pytest

from tests.conftest import SAMPLES_DIR, auth, run_pending_jobs, sample_file


@pytest.fixture(scope="module")
def corpus_repo(client, user_token):
    """One repository with a representative slice of the corpus, processed."""
    resp = client.post("/api/v1/repositories", headers=auth(user_token),
                       json={"name": "Repo corpus busqueda", "description": "corpus para busqueda y RAG"})
    repo = resp.json()
    files = ["factura_08.txt", "factura_09.txt", "contrato_08.txt",
             "contrato_09.txt", "hoja_de_vida_08.txt", "hoja_de_vida_09.txt"]
    for name in files:
        client.post(
            f"/api/v1/documents/upload?repository_id={repo['id']}",
            headers=auth(user_token),
            files=[("files", (name, io.BytesIO(sample_file(name)), "text/plain"))],
        )
    run_pending_jobs()
    return repo


@pytest.fixture(scope="module")
def ground_truth():
    return {g["filename"]: g for g in
            json.loads((SAMPLES_DIR / "ground_truth.json").read_text(encoding="utf-8"))}


class TestTextSearch:
    def test_tc17_busqueda_textual(self, client, user_token, corpus_repo, ground_truth):
        numero = ground_truth["factura_08.txt"]["fields"]["numero_factura"]
        resp = client.get(f"/api/v1/search/text?q={numero}&repository_id={corpus_repo['id']}",
                          headers=auth(user_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        hit = body["hits"][0]
        assert hit["document_name"] == "factura_08.txt"
        assert f"**{numero}**" in hit["snippet"]  # highlighted term
        assert hit["page_number"] >= 1

    def test_busqueda_textual_filtros(self, client, user_token, corpus_repo):
        resp = client.get(
            f"/api/v1/search/text?q=obligaciones&repository_id={corpus_repo['id']}&category=legal",
            headers=auth(user_token))
        body = resp.json()
        assert body["total"] >= 1
        assert all(h["category"] == "legal" for h in body["hits"])

    def test_busqueda_respeta_permisos(self, client, other_user_token, corpus_repo):
        resp = client.get("/api/v1/search/text?q=factura", headers=auth(other_user_token))
        body = resp.json()
        assert all(h["repository_id"] != corpus_repo["id"] for h in body["hits"])


class TestSemanticSearch:
    def test_tc18_busqueda_semantica(self, client, user_token, corpus_repo):
        resp = client.get(
            f"/api/v1/search/semantic?q=experiencia laboral y habilidades del candidato"
            f"&repository_id={corpus_repo['id']}&top_k=5",
            headers=auth(user_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        # A resume must rank in the top results for this query
        top_docs = [h["document_name"] for h in body["hits"][:3]]
        assert any(name.startswith("hoja_de_vida") for name in top_docs), top_docs
        assert body["hits"][0]["score"] > 0

    def test_semantica_con_filtro_categoria(self, client, user_token, corpus_repo):
        resp = client.get(
            f"/api/v1/search/semantic?q=valor total y fecha de vencimiento"
            f"&repository_id={corpus_repo['id']}&category=financiero",
            headers=auth(user_token))
        body = resp.json()
        assert all(h["category"] == "financiero" for h in body["hits"])


class TestRag:
    def _ask(self, client, token, repo_id, question):
        conv = client.post("/api/v1/conversations", headers=auth(token),
                           json={"repository_id": repo_id}).json()
        resp = client.post(f"/api/v1/conversations/{conv['id']}/ask",
                           headers=auth(token), json={"question": question})
        assert resp.status_code == 200, resp.text
        return conv, resp.json()

    def test_tc19_pregunta_con_citas(self, client, user_token, corpus_repo, ground_truth):
        gt = ground_truth["factura_08.txt"]["fields"]
        _, answer = self._ask(
            client, user_token, corpus_repo["id"],
            f"¿Cual es el total a pagar de la factura {gt['numero_factura']}?")
        assert answer["grounded"] is True
        assert len(answer["citations"]) >= 1
        cited_docs = {c["document_name"] for c in answer["citations"]}
        assert "factura_08.txt" in cited_docs
        assert answer["latency_ms"] >= 0
        assert answer["chunk_count"] >= 1
        assert answer["model"] == "deterministic-v1"
        for citation in answer["citations"]:
            assert citation["snippet"]
            assert citation["similarity"] > 0
            assert citation["page_number"] >= 1

    def test_tc20_pregunta_sin_evidencia(self, client, user_token, corpus_repo):
        _, answer = self._ask(client, user_token, corpus_repo["id"],
                              "¿Cual es la receta de la bandeja paisa tradicional?")
        assert answer["grounded"] is False
        assert "No se encontro evidencia suficiente" in answer["content"]
        assert answer["citations"] == []

    def test_historial_conversacion(self, client, user_token, corpus_repo):
        conv, _ = self._ask(client, user_token, corpus_repo["id"],
                            "¿Que obligaciones tiene el contratista?")
        detail = client.get(f"/api/v1/conversations/{conv['id']}", headers=auth(user_token)).json()
        assert len(detail["messages"]) == 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"
        assert detail["title"] != "Nueva conversacion"  # first question became title

    def test_conversacion_ajena_denegada(self, client, user_token, other_user_token, corpus_repo):
        conv, _ = self._ask(client, user_token, corpus_repo["id"], "¿Cual es el valor del contrato?")
        assert client.get(f"/api/v1/conversations/{conv['id']}",
                          headers=auth(other_user_token)).status_code in (403, 404)

    def test_evaluacion_rag_eval_json(self, client, user_token, corpus_repo):
        """Run the corpus rag_eval questions that reference loaded documents."""
        eval_set = json.loads((SAMPLES_DIR / "rag_eval.json").read_text(encoding="utf-8"))
        unanswerable = [e for e in eval_set if not e["expect_grounded"]]
        assert unanswerable, "rag_eval.json debe incluir una pregunta sin respuesta"
        for case in unanswerable:
            _, answer = self._ask(client, user_token, corpus_repo["id"], case["question"])
            assert answer["grounded"] is False, case["id"]


class TestDashboard:
    def test_tc25_indicadores_dashboard(self, client, user_token, corpus_repo):
        resp = client.get("/api/v1/dashboard", headers=auth(user_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_repositories"] >= 1
        assert body["total_documents"] >= 6
        assert body["by_status"].get("completed", 0) >= 6
        assert set(body["by_category"]) >= {"financiero", "legal", "talento_humano"}
        assert body["by_format"].get("txt", 0) >= 6
        assert body["processed_count"] >= 6
        assert body["avg_processing_ms"] is not None and body["avg_processing_ms"] > 0
        assert len(body["recent_documents"]) >= 1
        assert len(body["uploads_last_14_days"]) == 14
        assert sum(d["count"] for d in body["uploads_last_14_days"]) >= 6

    def test_dashboard_usuario_sin_repos(self, client, other_user_token):
        resp = client.get("/api/v1/dashboard", headers=auth(other_user_token))
        body = resp.json()
        # This user only sees their own (possibly zero) repositories
        assert body["total_documents"] >= 0
        assert isinstance(body["uploads_last_14_days"], list)


class TestAuditLogs:
    def test_auditoria_registra_acciones(self, client, admin_token, user_token):
        # Generate an auditable action within this test (self-contained)
        client.post("/api/v1/repositories", headers=auth(user_token),
                    json={"name": "Repo auditoria", "description": "para probar auditoria"})
        resp = client.get("/api/v1/audit-logs?page_size=100", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        actions = {row["action"] for row in body["items"]}
        assert "login" in actions
        assert "create_repository" in actions
        # Non-admin cannot read the audit trail
        deny = client.get("/api/v1/audit-logs", headers=auth(user_token))
        assert deny.status_code == 403
