"""Testes unitários do controller de Variantes (/products/{id}/variants e /variants).

Nota: a partir da decisão de modelagem tomada com o professor, "tamanho"
passou a ser tratado como uma categoria (não como um atributo próprio da
Variante) — por isso a Variante aqui só tem `cor` e `sku`.
"""
from tests.unit.conftest import create_product


def test_create_variant_success(client):
    product = create_product(client)

    response = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Vermelho", "sku": "SKU-001"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["cor"] == "Vermelho"
    assert body["sku"] == "SKU-001"
    assert body["produtoId"] == product["id"]
    assert body["ativo"] is True


def test_create_variant_product_not_found_returns_404(client):
    response = client.post(
        "/products/id-que-nao-existe/variants",
        json={"cor": "Azul", "sku": "SKU-404"},
    )

    assert response.status_code == 404


def test_create_variant_duplicate_sku_returns_409(client):
    product = create_product(client)
    client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Verde", "sku": "SKU-DUP"},
    )

    response = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Amarelo", "sku": "SKU-DUP"},
    )

    assert response.status_code == 409


def test_list_variants_by_product(client):
    product = create_product(client)
    client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Preto", "sku": "SKU-LIST-1"},
    )
    client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Branco", "sku": "SKU-LIST-2"},
    )

    response = client.get(f"/products/{product['id']}/variants")

    assert response.status_code == 200
    skus = [v["sku"] for v in response.json()]
    assert skus == ["SKU-LIST-1", "SKU-LIST-2"]


def test_list_variants_by_product_not_found_returns_404(client):
    response = client.get("/products/id-que-nao-existe/variants")

    assert response.status_code == 404


def test_get_variant_by_id_success(client):
    product = create_product(client)
    created = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Rosa", "sku": "SKU-GET"},
    ).json()

    response = client.get(f"/variants/{created['id']}")

    assert response.status_code == 200
    assert response.json()["sku"] == "SKU-GET"


def test_get_variant_by_id_not_found(client):
    response = client.get("/variants/id-que-nao-existe")

    assert response.status_code == 404


def test_update_variant_cor(client):
    product = create_product(client)
    created = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Azul", "sku": "SKU-UPD"},
    ).json()

    response = client.put(f"/variants/{created['id']}", json={"cor": "Roxo"})

    assert response.status_code == 200
    body = response.json()
    assert body["cor"] == "Roxo"
    assert body["sku"] == "SKU-UPD"  # não foi alterado


def test_update_variant_to_existing_sku_returns_409(client):
    product = create_product(client)
    client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Azul", "sku": "SKU-EXISTENTE"},
    )
    created = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Verde", "sku": "SKU-PARA-ATUALIZAR"},
    ).json()

    response = client.put(f"/variants/{created['id']}", json={"sku": "SKU-EXISTENTE"})

    assert response.status_code == 409


def test_update_variant_not_found_returns_404(client):
    response = client.put("/variants/id-que-nao-existe", json={"cor": "Qualquer"})

    assert response.status_code == 404


def test_disable_variant_marks_as_inactive(client):
    product = create_product(client)
    created = client.post(
        f"/products/{product['id']}/variants",
        json={"cor": "Azul", "sku": "SKU-DISABLE"},
    ).json()

    response = client.patch(f"/variants/{created['id']}/disable")

    assert response.status_code == 200
    assert response.json()["message"] == "Variante desativada com sucesso"

    check = client.get(f"/variants/{created['id']}")
    assert check.json()["ativo"] is False


def test_disable_variant_not_found_returns_404(client):
    response = client.patch("/variants/id-que-nao-existe/disable")

    assert response.status_code == 404
