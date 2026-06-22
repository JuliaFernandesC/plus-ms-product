"""
Testes funcionais (integração real) do MS de Produto.

Rodam contra o container Docker de verdade (via fixture
`product_service_container` em conftest.py), batendo HTTP igual um
cliente externo bateria. Não há reset de banco entre testes (o
container sobe uma vez só para toda a sessão), então cada teste usa
nomes/SKUs únicos para não colidir uns com os outros.
"""
import uuid

import requests


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_health_check(product_service_container):
    response = requests.get(product_service_container + "/")

    assert response.status_code == 200
    assert "Product Microservice" in response.json()["message"]


def test_full_product_lifecycle(product_service_container):
    base_url = product_service_container

    # 1. Cria um tamanho
    size_resp = requests.post(f"{base_url}/sizes", json={"nome": _unique("T")[:10]})
    assert size_resp.status_code == 201
    size = size_resp.json()

    # 2. Cria um produto
    product_resp = requests.post(
        f"{base_url}/products",
        json={
            "nome": _unique("Produto Funcional"),
            "preco": 129.90,
            "marca": "Plus Co",
        },
    )
    assert product_resp.status_code == 201
    product = product_resp.json()

    # 3. Adiciona uma variante a esse produto
    variant_resp = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Azul", "sku": _unique("SKU")},
    )
    assert variant_resp.status_code == 201
    variant = variant_resp.json()
    assert variant["produtoId"] == product["id"]

    # 4. Busca o produto e confirma que a variante aparece no detalhe
    detail_resp = requests.get(f"{base_url}/products/{product['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["variantes"]) == 1
    assert detail["variantes"][0]["id"] == variant["id"]

    # 5. Desativa o produto e confirma o soft-delete em cascata
    disable_resp = requests.patch(f"{base_url}/products/{product['id']}/disable")
    assert disable_resp.status_code == 200

    final_check = requests.get(f"{base_url}/products/{product['id']}").json()
    assert final_check["ativo"] is False
    assert final_check["variantes"][0]["ativo"] is False


def test_create_product_without_required_field_returns_422(product_service_container):
    response = requests.post(product_service_container + "/products", json={"preco": 10.0})

    assert response.status_code == 422


def test_get_nonexistent_product_returns_404(product_service_container):
    response = requests.get(product_service_container + "/products/id-inexistente")

    assert response.status_code == 404


def test_duplicate_sku_returns_409(product_service_container):
    base_url = product_service_container
    size = requests.post(f"{base_url}/sizes", json={"nome": _unique("T")[:10]}).json()
    product = requests.post(
        f"{base_url}/products", json={"nome": _unique("Produto SKU"), "preco": 10.0}
    ).json()
    sku = _unique("SKU-DUP")

    first = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Verde", "sku": sku},
    )
    assert first.status_code == 201

    second = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Amarelo", "sku": sku},
    )
    assert second.status_code == 409


def test_pagination_on_products_list(product_service_container):
    base_url = product_service_container

    response = requests.get(f"{base_url}/products", params={"page": 1, "pageSize": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 1
    assert body["page"] == 1
    assert body["pageSize"] == 1
