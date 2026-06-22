## revisar
def test_create_size_success(client):
    response = client.post("/sizes", json={"nome": "GG", "descricao": "Busto 110-118cm"})

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "GG"
    assert body["ativo"] is True


def test_create_size_duplicate_name_returns_conflict(client):
    client.post("/sizes", json={"nome": "M"})
    response = client.post("/sizes", json={"nome": "M"})

    assert response.status_code == 409


def test_list_sizes_only_returns_active(client):
    client.post("/sizes", json={"nome": "P"})
    created = client.post("/sizes", json={"nome": "G"}).json()
    client.patch(f"/sizes/{created['id']}/disable")

    response = client.get("/sizes")

    assert response.status_code == 200
    nomes = [s["nome"] for s in response.json()]
    assert "P" in nomes
    assert "G" not in nomes


def test_get_size_by_id_not_found(client):
    response = client.get("/sizes/id-que-nao-existe")
    assert response.status_code == 404