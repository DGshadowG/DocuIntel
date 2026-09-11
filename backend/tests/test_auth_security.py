"""TC-01..03, TC-21: authentication, authorization and user isolation."""
from tests.conftest import auth


class TestLogin:
    def test_tc01_login_valido(self, client, admin_token):
        resp = client.post("/api/v1/auth/login",
                           json={"email": "admin@test-docuintel.co", "password": "AdminTest123!"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["user"]["email"] == "admin@test-docuintel.co"
        assert body["user"]["role"] == "admin"

    def test_tc02_login_invalido(self, client, admin_token):
        resp = client.post("/api/v1/auth/login",
                           json={"email": "admin@test-docuintel.co", "password": "clave-incorrecta"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "invalid_credentials"

    def test_tc02b_login_usuario_inexistente(self, client):
        resp = client.post("/api/v1/auth/login",
                           json={"email": "nadie@test-docuintel.co", "password": "loquesea123"})
        assert resp.status_code == 401

    def test_login_payload_invalido(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "no-es-correo", "password": ""})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

    def test_me_y_logout(self, client, user_token):
        me = client.get("/api/v1/auth/me", headers=auth(user_token))
        assert me.status_code == 200
        assert me.json()["email"] == "user@test-docuintel.co"
        out = client.post("/api/v1/auth/logout", headers=auth(user_token))
        assert out.status_code == 200


class TestAccessControl:
    def test_tc03_acceso_sin_token(self, client):
        for path in ("/api/v1/repositories", "/api/v1/documents", "/api/v1/dashboard"):
            resp = client.get(path)
            assert resp.status_code == 401, path

    def test_tc03b_token_invalido(self, client):
        resp = client.get("/api/v1/repositories", headers=auth("token-falso"))
        assert resp.status_code == 401

    def test_tc03c_usuario_normal_no_admin(self, client, user_token):
        resp = client.get("/api/v1/users", headers=auth(user_token))
        assert resp.status_code == 403
        resp = client.get("/api/v1/audit-logs", headers=auth(user_token))
        assert resp.status_code == 403

    def test_tc21_aislamiento_entre_usuarios(self, client, user_token, other_user_token, make_repo):
        repo = make_repo("Repo privado de user")
        # The other user cannot see, read, edit or delete it
        listado = client.get("/api/v1/repositories", headers=auth(other_user_token)).json()
        assert repo["id"] not in [r["id"] for r in listado]
        assert client.get(f"/api/v1/repositories/{repo['id']}",
                          headers=auth(other_user_token)).status_code == 403
        assert client.patch(f"/api/v1/repositories/{repo['id']}",
                            headers=auth(other_user_token),
                            json={"name": "hackeado"}).status_code == 403
        assert client.delete(f"/api/v1/repositories/{repo['id']}",
                             headers=auth(other_user_token)).status_code == 403

    def test_tc21b_admin_ve_todo(self, client, admin_token, make_repo):
        repo = make_repo("Repo visible para admin")
        resp = client.get(f"/api/v1/repositories/{repo['id']}", headers=auth(admin_token))
        assert resp.status_code == 200


class TestPasswordHashing:
    def test_contrasenas_cifradas_bcrypt(self, db_session, admin_token):
        from app.models import User
        user = db_session.query(User).filter(User.email == "admin@test-docuintel.co").first()
        assert user.password_hash.startswith("$2b$")
        assert "AdminTest123!" not in user.password_hash

    def test_verify_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("MiClave123!")
        assert verify_password("MiClave123!", hashed)
        assert not verify_password("otra-clave", hashed)
        assert not verify_password("MiClave123!", "hash-corrupto")
