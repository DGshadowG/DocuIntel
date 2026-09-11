"""Admin user management endpoints."""
from tests.conftest import auth


class TestUserAdmin:
    def test_listar_usuarios(self, client, admin_token):
        resp = client.get("/api/v1/users", headers=auth(admin_token))
        assert resp.status_code == 200
        assert any(u["email"] == "admin@test-docuintel.co" for u in resp.json())

    def test_crear_actualizar_usuario(self, client, admin_token):
        resp = client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "nuevo@test-docuintel.co", "full_name": "Usuario Nuevo",
            "password": "ClaveNueva123!", "role": "user",
        })
        assert resp.status_code == 201
        user = resp.json()
        assert user["role"] == "user"

        # Duplicate email rejected
        dup = client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "nuevo@test-docuintel.co", "full_name": "Duplicado",
            "password": "ClaveNueva123!", "role": "user",
        })
        assert dup.status_code == 409

        # New user can log in
        login = client.post("/api/v1/auth/login",
                            json={"email": "nuevo@test-docuintel.co", "password": "ClaveNueva123!"})
        assert login.status_code == 200

        # Update: deactivate -> login denied
        upd = client.patch(f"/api/v1/users/{user['id']}", headers=auth(admin_token),
                           json={"is_active": False})
        assert upd.status_code == 200
        assert upd.json()["is_active"] is False
        login2 = client.post("/api/v1/auth/login",
                             json={"email": "nuevo@test-docuintel.co", "password": "ClaveNueva123!"})
        assert login2.status_code == 403

    def test_password_corta_rechazada(self, client, admin_token):
        resp = client.post("/api/v1/users", headers=auth(admin_token), json={
            "email": "corta@test-docuintel.co", "full_name": "Clave Corta",
            "password": "corta", "role": "user",
        })
        assert resp.status_code == 422

    def test_admin_no_puede_autodesactivarse(self, client, admin_token):
        me = client.get("/api/v1/auth/me", headers=auth(admin_token)).json()
        resp = client.patch(f"/api/v1/users/{me['id']}", headers=auth(admin_token),
                            json={"is_active": False})
        assert resp.status_code == 400
