"""Unit tests: chunking, vectors, sanitization, deterministic provider, schemas."""
import pytest


class TestChunking:
    def test_chunks_con_solapamiento(self, test_env):
        from app.services.chunking import chunk_text
        text = "Parrafo de prueba con contenido util. " * 200  # ~7600 chars
        chunks = chunk_text(text, [(1, 0)], chunk_size=1000, overlap=200)
        assert len(chunks) >= 7
        for i, c in enumerate(chunks):
            assert c["index"] == i
            assert 0 < len(c["content"]) <= 1100
        # Overlap: consecutive chunks share content
        assert chunks[1]["start_char"] < chunks[0]["end_char"]

    def test_mapeo_de_paginas(self, test_env):
        from app.services.chunking import chunk_text
        text = ("A" * 500) + "\n\n" + ("B" * 500)
        offsets = [(1, 0), (2, 501)]
        chunks = chunk_text(text, offsets, chunk_size=400, overlap=50)
        assert chunks[0]["page_number"] == 1
        assert chunks[-1]["page_number"] == 2

    def test_texto_corto_un_chunk(self, test_env):
        from app.services.chunking import chunk_text
        chunks = chunk_text("Texto corto.", [(1, 0)])
        assert len(chunks) == 1


class TestVectors:
    def test_serializacion_ida_y_vuelta(self, test_env):
        from app.services import vectors
        original = [0.1, -0.5, 0.9, 0.0]
        recovered = vectors.from_bytes(vectors.to_bytes(original))
        assert list(recovered) == pytest.approx(original, abs=1e-6)

    def test_similitud_coseno(self, test_env):
        import numpy as np
        from app.services.vectors import cosine_similarity
        a = np.array([1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, np.array([1.0, 0.0], dtype=np.float32)) == pytest.approx(1.0)
        assert cosine_similarity(a, np.array([0.0, 1.0], dtype=np.float32)) == pytest.approx(0.0)
        assert cosine_similarity(a, np.array([-1.0, 0.0], dtype=np.float32)) == pytest.approx(-1.0)
        assert cosine_similarity(a, np.zeros(2, dtype=np.float32)) == 0.0


class TestSanitization:
    def test_sanitize_filename(self, test_env):
        from app.services.extraction import sanitize_filename
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("..\\..\\windows\\sam.txt") == "sam.txt"
        assert "/" not in sanitize_filename("a/b/c/archivo final.pdf")
        assert sanitize_filename("") == "documento"
        assert len(sanitize_filename("x" * 500)) <= 200

    def test_storage_confina_claves(self, test_env, tmp_path):
        from app.services.storage import LocalStorage
        storage = LocalStorage(str(tmp_path / "store"))
        with pytest.raises(ValueError):
            storage._path("../fuera.txt")
        key = storage.save(b"contenido", "txt")
        assert storage.read(key) == b"contenido"
        storage.delete(key)
        assert not storage.exists(key)


class TestDeterministicProvider:
    @pytest.fixture()
    def provider(self, test_env):
        from app.ai.deterministic import DeterministicProvider
        return DeterministicProvider()

    def test_embeddings_deterministas_y_normalizados(self, provider):
        import math
        v1 = provider.embed(["contrato de arrendamiento entre las partes"])[0]
        v2 = provider.embed(["contrato de arrendamiento entre las partes"])[0]
        assert v1 == v2  # reproducible
        assert len(v1) == 384
        assert math.sqrt(sum(x * x for x in v1)) == pytest.approx(1.0, abs=1e-5)

    def test_embeddings_similitud_relativa(self, provider):
        import numpy as np
        from app.services.vectors import cosine_similarity
        base = np.array(provider.embed(["factura de venta con subtotal e IVA"])[0], dtype=np.float32)
        similar = np.array(provider.embed(["factura con IVA y subtotal por pagar"])[0], dtype=np.float32)
        distinct = np.array(provider.embed(["hoja de vida con experiencia laboral"])[0], dtype=np.float32)
        assert cosine_similarity(base, similar) > cosine_similarity(base, distinct)

    def test_clasificacion_categorias(self, provider):
        assert provider.classify("FACTURA DE VENTA No 123 Subtotal: $100 IVA: $19 Total a pagar: $119").category == "financiero"
        assert provider.classify("CONTRATO entre el contratante y el contratista. PRIMERA - OBJETO DEL CONTRATO").category == "legal"
        assert provider.classify("HOJA DE VIDA Perfil profesional EXPERIENCIA LABORAL EDUCACION HABILIDADES").category == "talento_humano"
        result = provider.classify("texto sin relacion con nada especifico xyz")
        assert result.category == "otro"

    def test_resumen_no_vacio(self, provider):
        text = ("El contrato establece las obligaciones de las partes. " * 5 +
                "El valor total es de cien millones de pesos. " * 3)
        summary = provider.summarize(text)
        assert len(summary) > 30

    def test_extraccion_montos_formato_colombiano(self, provider):
        data = provider.extract(
            "FACTURA DE VENTA No: FV-2024-001\nSubtotal: $1.234.567\nIVA (19%): $234.568\n"
            "Total a pagar: $1.469.135\nMoneda: COP\n", "invoice")
        assert data["subtotal"] == 1234567
        assert data["total"] == 1469135
        assert data["moneda"] == "COP"
        assert data["numero_factura"] == "FV-2024-001"


class TestExtractionSchemas:
    def test_esquemas_validan_y_normalizan(self, test_env):
        from app.ai.schemas import ClassificationResult, InvoiceExtraction
        # Unknown category degrades to 'otro' instead of crashing
        assert ClassificationResult(category="INVALIDA", confidence=0.9).category == "otro"
        with pytest.raises(Exception):
            ClassificationResult(category="financiero", confidence=1.7)
        inv = InvoiceExtraction(proveedor="ACME", total=100.5)
        assert inv.numero_factura is None
        assert inv.total == 100.5

    def test_jwt_expirado_rechazado(self, test_env):
        from app.core.security import create_access_token, decode_token
        token = create_access_token("1", "user", expires_minutes=-5)
        assert decode_token(token) is None
        valid = create_access_token("1", "user")
        payload = decode_token(valid)
        assert payload["sub"] == "1"
        assert decode_token(valid + "x") is None  # tampered
