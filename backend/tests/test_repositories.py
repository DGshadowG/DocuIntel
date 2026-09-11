"""TC-04: repository CRUD + members + stats."""
from tests.conftest import auth


class TestRepositoryCrud:
    def test_tc04_crud_completo(self, client, user_token):
        # Create
        resp = client.post("/api/v1/repositories", headers=auth(user_token),
                           json={"name": "Repositorio CRUD", "description": "Descripcion inicial"})
        assert resp.status_code == 201
        repo = resp.json()
        assert repo["name"] == "Repositorio CRUD"
        assert repo["document_count"] == 0

        # Read
        got = client.get(f"/api/v1/repositories/{repo['id']}", headers=auth(user_token))
        assert got.status_code == 200
        assert got.json()["description"] == "Descripcion inicial"

        # Update
        upd = client.patch(f"/api/v1/repositories/{repo['id']}", headers=auth(user_token),
                           json={"description": "Descripcion editada"})
        assert upd.status_code == 200
        assert upd.json()["description"] == "Descripcion editada"

        # Delete
        assert client.delete(f"/api/v1/repositories/{repo['id']}",
                             headers=auth(user_token)).status_code == 204
        assert client.get(f"/api/v1/repositories/{repo['id']}",
                          headers=auth(user_token)).status_code == 404

    def test_validacion_nombre(self, client, user_token):
        resp = client.post("/api/v1/repositories", headers=auth(user_token),
                           json={"name": "x", "description": ""})
        assert resp.status_code == 422

    def test_miembros(self, client, user_token, other_user_token, make_repo):
        repo = make_repo("Repo con miembros")
        # Add the other user as member
        add = client.post(f"/api/v1/repositories/{repo['id']}/members", headers=auth(user_token),
                          json={"email": "otro@test-docuintel.co", "role": "member"})
        assert add.status_code == 201
        member = add.json()
        # Now the other user has access
        assert client.get(f"/api/v1/repositories/{repo['id']}",
                          headers=auth(other_user_token)).status_code == 200
        # Duplicate is rejected
        dup = client.post(f"/api/v1/repositories/{repo['id']}/members", headers=auth(user_token),
                          json={"email": "otro@test-docuintel.co", "role": "member"})
        assert dup.status_code == 409
        # Member cannot add members (not owner)
        deny = client.post(f"/api/v1/repositories/{repo['id']}/members",
                           headers=auth(other_user_token),
                           json={"email": "admin@test-docuintel.co", "role": "member"})
        assert deny.status_code == 403
        # Remove member -> access revoked
        assert client.delete(f"/api/v1/repositories/{repo['id']}/members/{member['id']}",
                             headers=auth(user_token)).status_code == 204
        assert client.get(f"/api/v1/repositories/{repo['id']}",
                          headers=auth(other_user_token)).status_code == 403

    def test_stats_vacias(self, client, user_token, make_repo):
        repo = make_repo("Repo stats")
        stats = client.get(f"/api/v1/repositories/{repo['id']}/stats", headers=auth(user_token))
        assert stats.status_code == 200
        body = stats.json()
        assert body["document_count"] == 0
        assert body["total_size_bytes"] == 0
