"""Testes unitários do controller de Tamanhos (/sizes)."""


def test_create_size_success(client):
    response = client.post("/sizes", json={"nome": "GG", "descricao": "Busto 110-118cm"})

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "GG"
    assert body["descricao"] == "Busto 110-118cm"
    assert body["ativo"] is True
    assert "id" in body


def test_create_size_without_descricao_is_optional(client):
    response = client.post("/sizes", json={"nome": "P"})

    assert response.status_code == 201
    assert response.json()["descricao"] is None


def test_create_size_missing_nome_returns_422(client):
    response = client.post("/sizes", json={"descricao": "Sem nome"})

    assert response.status_code == 422


def test_create_size_duplicate_name_returns_409(client):
    client.post("/sizes", json={"nome": "M"})
    response = client.post("/sizes", json={"nome": "M"})

    assert response.status_code == 409


def test_list_sizes_returns_only_active_by_default(client):
    client.post("/sizes", json={"nome": "P"})
    created = client.post("/sizes", json={"nome": "G"}).json()
    client.patch(f"/sizes/{created['id']}/disable")

    response = client.get("/sizes")

    assert response.status_code == 200
    nomes = [s["nome"] for s in response.json()]
    assert "P" in nomes
    assert "G" not in nomes


def test_list_sizes_can_filter_inactive(client):
    created = client.post("/sizes", json={"nome": "EG"}).json()
    client.patch(f"/sizes/{created['id']}/disable")

    response = client.get("/sizes", params={"ativo": False})

    nomes = [s["nome"] for s in response.json()]
    assert "EG" in nomes


def test_get_size_by_id_success(client):
    created = client.post("/sizes", json={"nome": "PP"}).json()

    response = client.get(f"/sizes/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_size_by_id_not_found(client):
    response = client.get("/sizes/id-que-nao-existe")

    assert response.status_code == 404


def test_update_size_changes_nome_and_descricao(client):
    created = client.post("/sizes", json={"nome": "U1"}).json()

    response = client.put(
        f"/sizes/{created['id']}",
        json={"nome": "U1-Novo", "descricao": "Nova descrição"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "U1-Novo"
    assert body["descricao"] == "Nova descrição"


def test_update_size_not_found_returns_404(client):
    response = client.put("/sizes/id-que-nao-existe", json={"nome": "Qualquer"})

    assert response.status_code == 404


def test_update_size_to_existing_name_returns_409(client):
    client.post("/sizes", json={"nome": "Existente"})
    created = client.post("/sizes", json={"nome": "ParaAtu"}).json()

    response = client.put(f"/sizes/{created['id']}", json={"nome": "Existente"})

    assert response.status_code == 409


def test_update_size_keeping_same_name_does_not_conflict(client):
    created = client.post("/sizes", json={"nome": "MesmoNome"}).json()

    response = client.put(
        f"/sizes/{created['id']}",
        json={"nome": "MesmoNome", "descricao": "Atualizando só a descrição"},
    )

    assert response.status_code == 200


def test_disable_size_marks_as_inactive(client):
    created = client.post("/sizes", json={"nome": "Desativar"}).json()

    response = client.patch(f"/sizes/{created['id']}/disable")

    assert response.status_code == 200
    assert response.json()["message"] == "Tamanho desativado com sucesso"

    check = client.get(f"/sizes/{created['id']}")
    assert check.json()["ativo"] is False


def test_disable_size_not_found_returns_404(client):
    response = client.patch("/sizes/id-que-nao-existe/disable")

    assert response.status_code == 404
