"""TC-05..10, TC-22, TC-24: uploads, validation, security, delete, retry."""
import io

from tests.conftest import auth, run_pending_jobs, sample_file


def upload(client, token, repo_id, filename, content, mime="application/octet-stream"):
    return client.post(
        f"/api/v1/documents/upload?repository_id={repo_id}",
        headers=auth(token),
        files=[("files", (filename, io.BytesIO(content), mime))],
    )


class TestUploadFormats:
    def test_tc05_carga_pdf(self, client, user_token, make_repo):
        repo = make_repo("Repo PDF")
        resp = upload(client, user_token, repo["id"], "factura_01.pdf",
                      sample_file("factura_01.pdf"), "application/pdf")
        assert resp.status_code == 201, resp.text
        result = resp.json()[0]
        assert result["document"]["file_type"] == "pdf"
        assert result["document"]["status"] == "queued"
        assert result["job_id"] > 0

    def test_tc06_carga_docx(self, client, user_token, make_repo):
        repo = make_repo("Repo DOCX")
        resp = upload(client, user_token, repo["id"], "contrato_05.docx",
                      sample_file("contrato_05.docx"))
        assert resp.status_code == 201, resp.text
        assert resp.json()[0]["document"]["file_type"] == "docx"

    def test_tc07_carga_txt(self, client, user_token, make_repo):
        repo = make_repo("Repo TXT")
        resp = upload(client, user_token, repo["id"], "hoja_de_vida_08.txt",
                      sample_file("hoja_de_vida_08.txt"), "text/plain")
        assert resp.status_code == 201, resp.text
        assert resp.json()[0]["document"]["file_type"] == "txt"

    def test_carga_multiple(self, client, user_token, make_repo):
        repo = make_repo("Repo multiple")
        resp = client.post(
            f"/api/v1/documents/upload?repository_id={repo['id']}",
            headers=auth(user_token),
            files=[
                ("files", ("factura_02.pdf", io.BytesIO(sample_file("factura_02.pdf")), "application/pdf")),
                ("files", ("contrato_08.txt", io.BytesIO(sample_file("contrato_08.txt")), "text/plain")),
            ],
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 2


class TestUploadValidation:
    def test_tc08_formato_no_permitido(self, client, user_token, make_repo):
        repo = make_repo("Repo formatos")
        resp = upload(client, user_token, repo["id"], "script.exe", b"MZ\x90\x00binario")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_format"

    def test_tc08b_extension_pdf_contenido_falso(self, client, user_token, make_repo):
        repo = make_repo("Repo firmas")
        resp = upload(client, user_token, repo["id"], "falso.pdf", b"esto no es un pdf real")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_content"

    def test_tc09_archivo_demasiado_grande(self, client, user_token, make_repo):
        repo = make_repo("Repo limite")
        big = b"A" * (6 * 1024 * 1024)  # MAX_UPLOAD_MB=5 in tests
        resp = upload(client, user_token, repo["id"], "grande.txt", big, "text/plain")
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "file_too_large"

    def test_archivo_vacio(self, client, user_token, make_repo):
        repo = make_repo("Repo vacio")
        resp = upload(client, user_token, repo["id"], "vacio.txt", b"")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "empty_file"

    def test_tc10_path_traversal_neutralizado(self, client, user_token, make_repo, db_session):
        from app.models import Document

        repo = make_repo("Repo traversal")
        evil_name = "..\\..\\..\\windows\\system32\\config\\sam.txt"
        resp = upload(client, user_token, repo["id"], evil_name,
                      b"contenido inofensivo de prueba", "text/plain")
        assert resp.status_code == 201
        doc = resp.json()[0]["document"]
        # Stored name contains no path separators; storage key is a server UUID
        assert "/" not in doc["original_filename"] and "\\" not in doc["original_filename"]
        row = db_session.query(Document).filter(Document.id == doc["id"]).first()
        db_session.refresh(row)
        assert "/" not in row.storage_key and "\\" not in row.storage_key
        assert ".." not in row.storage_key

    def test_carga_en_repo_ajeno_denegada(self, client, user_token, other_user_token, make_repo):
        repo = make_repo("Repo carga ajena")
        resp = upload(client, other_user_token, repo["id"], "intruso.txt",
                      b"texto de intruso", "text/plain")
        assert resp.status_code == 403


class TestDocumentLifecycle:
    def test_tc22_eliminacion_y_limpieza(self, client, user_token, make_repo, db_session):
        from app.models import Document, DocumentChunk, DocumentText, Embedding
        from app.services.storage import get_storage

        repo = make_repo("Repo limpieza")
        resp = upload(client, user_token, repo["id"], "factura_08.txt",
                      sample_file("factura_08.txt"), "text/plain")
        doc_id = resp.json()[0]["document"]["id"]
        run_pending_jobs()

        row = db_session.query(Document).get(doc_id)
        db_session.refresh(row)
        storage_key = row.storage_key
        chunk_ids = [c.id for c in db_session.query(DocumentChunk).filter_by(document_id=doc_id)]
        assert chunk_ids, "el pipeline debio crear chunks"
        assert get_storage().exists(storage_key)

        assert client.delete(f"/api/v1/documents/{doc_id}",
                             headers=auth(user_token)).status_code == 204

        db_session.expire_all()
        assert db_session.query(Document).get(doc_id) is None
        assert db_session.query(DocumentText).filter_by(document_id=doc_id).count() == 0
        assert db_session.query(DocumentChunk).filter_by(document_id=doc_id).count() == 0
        assert db_session.query(Embedding).filter(Embedding.chunk_id.in_(chunk_ids)).count() == 0
        assert not get_storage().exists(storage_key)

    def test_tc24_reintento_procesamiento(self, client, user_token, make_repo):
        repo = make_repo("Repo reintento")
        resp = upload(client, user_token, repo["id"], "contrato_09.txt",
                      sample_file("contrato_09.txt"), "text/plain")
        doc_id = resp.json()[0]["document"]["id"]
        run_pending_jobs()
        detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth(user_token)).json()
        assert detail["status"] == "completed"

        # Reprocess: enqueues a new job and completes again (idempotent)
        rep = client.post(f"/api/v1/documents/{doc_id}/reprocess", headers=auth(user_token))
        assert rep.status_code == 202
        run_pending_jobs()
        jobs = client.get(f"/api/v1/documents/{doc_id}/jobs", headers=auth(user_token)).json()
        assert len(jobs) == 2
        assert all(j["status"] == "completed" for j in jobs)
        detail2 = client.get(f"/api/v1/documents/{doc_id}", headers=auth(user_token)).json()
        assert detail2["status"] == "completed"
        assert detail2["chunk_count"] == detail["chunk_count"]

    def test_descarga(self, client, user_token, make_repo):
        repo = make_repo("Repo descarga")
        original = sample_file("hoja_de_vida_09.txt")
        resp = upload(client, user_token, repo["id"], "hoja_de_vida_09.txt", original, "text/plain")
        doc_id = resp.json()[0]["document"]["id"]
        down = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth(user_token))
        assert down.status_code == 200
        assert down.content == original
        assert "attachment" in down.headers["content-disposition"]

    def test_listado_filtros_paginacion(self, client, user_token, make_repo):
        repo = make_repo("Repo filtros")
        for name in ("factura_09.txt", "factura_10.txt", "contrato_10.txt"):
            upload(client, user_token, repo["id"], name, sample_file(name), "text/plain")
        run_pending_jobs()
        page = client.get(
            f"/api/v1/documents?repository_id={repo['id']}&page=1&page_size=2",
            headers=auth(user_token),
        ).json()
        assert page["total"] == 3
        assert len(page["items"]) == 2
        assert page["pages"] == 2
        filtered = client.get(
            f"/api/v1/documents?repository_id={repo['id']}&search=contrato",
            headers=auth(user_token),
        ).json()
        assert filtered["total"] == 1
        by_status = client.get(
            f"/api/v1/documents?repository_id={repo['id']}&status=completed",
            headers=auth(user_token),
        ).json()
        assert by_status["total"] == 3
