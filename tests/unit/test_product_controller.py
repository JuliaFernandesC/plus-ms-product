"""Testes unitários do controller de Produtos (/products).

Nota: "tamanho" foi removido como atributo da Variante (decisão tomada
com o professor — tamanho passou a ser tratado como categoria), então
as variantes aqui só têm `cor` e `sku`.
"""
from tests.unit.conftest import create_product


def test_create_product_success(client):
    response = client.post(
        "/products",
        json={
            "nome": "Vestido Floral",
            "descricao": "Vestido leve de verão",
            "marca": "Plus Co",
            "preco": 149.90,
            "categoriaId": "categoria-1",
            "fornecedorId": "fornecedor-1",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Vestido Floral"
    assert body["preco"] == 149.90
    assert body["ativo"] is True
    assert body["categoriaId"] == "categoria-1"
    assert body["fornecedorId"] == "fornecedor-1"
    assert "id" in body
    assert "criadoEm" in body


def test_create_product_minimo_obrigatorio(client):
    # Só nome e preco são obrigatórios; o resto é opcional.
    response = client.post("/products", json={"nome": "Camiseta Básica", "preco": 49.90})

    assert response.status_code == 201
    body = response.json()
    assert body["marca"] is None
    assert body["categoriaId"] is None


def test_create_product_missing_nome_returns_422(client):
    response = client.post("/products", json={"preco": 10.0})

    assert response.status_code == 422


def test_create_product_negative_preco_returns_422(client):
    response = client.post("/products", json={"nome": "Produto Inválido", "preco": -5.0})

    assert response.status_code == 422


def test_create_product_with_nested_variantes(client):
    response = client.post(
        "/products",
        json={
            "nome": "Calça Jeans",
            "preco": 199.90,
            "variantes": [
                {"cor": "Azul", "sku": "CJ-AZ-M"},
            ],
        },
    )

    assert response.status_code == 201
    # ProductResponse (sem detalhe) não retorna a lista de variantes
    assert "variantes" not in response.json()


def test_create_product_with_duplicate_sku_against_db_in_nested_variante_returns_409(client):
    create_product(
        client,
        nome="Produto Existente",
        variantes=[{"cor": "Preto", "sku": "SKU-JA-EXISTE"}],
    )

    response = client.post(
        "/products",
        json={
            "nome": "Produto Novo",
            "preco": 50.0,
            "variantes": [{"cor": "Branco", "sku": "SKU-JA-EXISTE"}],
        },
    )

    assert response.status_code == 409


def test_create_product_with_duplicate_sku_within_same_payload_returns_409(client):
    response = client.post(
        "/products",
        json={
            "nome": "Produto com SKUs duplicados",
            "preco": 50.0,
            "variantes": [
                {"cor": "Preto", "sku": "SKU-DUPLICADO-NO-PAYLOAD"},
                {"cor": "Branco", "sku": "SKU-DUPLICADO-NO-PAYLOAD"},
            ],
        },
    )

    assert response.status_code == 409
    # Como a validação ocorre antes de qualquer db.add/commit, nenhuma
    # variante (nem o produto) deve ter sido persistida.
    assert client.get("/products/search", params={"nome": "SKUs duplicados"}).json()["totalItems"] == 0


def test_list_products_returns_only_active_by_default(client):
    create_product(client, nome="Produto Ativo")
    inactive = create_product(client, nome="Produto Inativo")
    client.patch(f"/products/{inactive['id']}/disable")

    response = client.get("/products")

    assert response.status_code == 200
    body = response.json()
    nomes = [p["nome"] for p in body["items"]]
    assert "Produto Ativo" in nomes
    assert "Produto Inativo" not in nomes


def test_list_products_pagination_metadata(client):
    for i in range(5):
        create_product(client, nome=f"Produto {i}")

    response = client.get("/products", params={"page": 1, "pageSize": 2})

    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["pageSize"] == 2
    assert body["totalItems"] == 5
    assert body["totalPages"] == 3


def test_get_product_by_id_includes_variantes(client):
    created = create_product(
        client,
        nome="Saia Plissada",
        variantes=[{"cor": "Preto", "sku": "SP-PT-G"}],
    )

    response = client.get(f"/products/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["variantes"]) == 1
    assert body["variantes"][0]["sku"] == "SP-PT-G"


def test_get_product_by_id_not_found(client):
    response = client.get("/products/id-que-nao-existe")

    assert response.status_code == 404


def test_update_product_partial_fields(client):
    created = create_product(client, nome="Blusa Original", preco=99.90)

    response = client.put(
        f"/products/{created['id']}",
        json={"preco": 79.90},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Blusa Original"  # não foi alterado
    assert body["preco"] == 79.90


def test_update_product_not_found_returns_404(client):
    response = client.put("/products/id-que-nao-existe", json={"preco": 10.0})

    assert response.status_code == 404


def test_disable_product_cascades_to_variantes(client):
    created = create_product(
        client,
        nome="Conjunto Praia",
        variantes=[{"cor": "Vermelho", "sku": "CP-VM-P"}],
    )

    response = client.patch(f"/products/{created['id']}/disable")
    assert response.status_code == 200

    detail = client.get(f"/products/{created['id']}").json()
    assert detail["ativo"] is False
    assert all(v["ativo"] is False for v in detail["variantes"])


def test_disable_product_not_found_returns_404(client):
    response = client.patch("/products/id-que-nao-existe/disable")

    assert response.status_code == 404


def test_search_products_by_nome(client):
    # descricao explícita para não colidir com a busca (que também varre descrição)
    create_product(client, nome="Vestido Longo Festa", descricao="Peça para ocasiões especiais")
    create_product(client, nome="Calça Reta", descricao="Peça casual do dia a dia")

    response = client.get("/products/search", params={"nome": "vestido"})

    body = response.json()
    nomes = [p["nome"] for p in body["items"]]
    assert "Vestido Longo Festa" in nomes
    assert "Calça Reta" not in nomes


def test_search_products_by_preco_range(client):
    create_product(client, nome="Produto Barato", preco=50.0)
    create_product(client, nome="Produto Caro", preco=500.0)

    response = client.get("/products/search", params={"precoMin": 100, "precoMax": 1000})

    nomes = [p["nome"] for p in response.json()["items"]]
    assert "Produto Caro" in nomes
    assert "Produto Barato" not in nomes


def test_search_products_by_cor(client):
    create_product(
        client,
        nome="Camisa Listrada",
        variantes=[{"cor": "Branco", "sku": "CL-BR-M"}],
    )
    create_product(
        client,
        nome="Camisa Lisa",
        variantes=[{"cor": "Preto", "sku": "CL-PT-G"}],
    )

    response = client.get("/products/search", params={"cor": "Branco"})
    nomes = [p["nome"] for p in response.json()["items"]]
    assert nomes == ["Camisa Listrada"]


def test_search_products_without_filters_returns_all(client):
    create_product(client, nome="Produto A")
    create_product(client, nome="Produto B")

    response = client.get("/products/search")

    assert response.status_code == 200
    assert response.json()["totalItems"] == 2
