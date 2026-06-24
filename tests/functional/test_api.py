"""
Testes funcionais (integração real) do MS de Produto.

Rodam contra o container Docker de verdade (via fixture
`product_service_container` em conftest.py), batendo HTTP igual um
cliente externo bateria. Não há reset de banco entre testes (o
container sobe uma vez só para toda a sessão), então cada teste usa
nomes/SKUs únicos para não colidir uns com os outros.

O container roda com o JWT_SECRET padrão ("dev-secret", definido em
app/config/settings.py), já que o `docker run` na fixture não passa
nenhuma variável de ambiente. Por isso os tokens aqui são assinados com
esse mesmo segredo, simulando o que o MS Auth emitiria.
"""
import uuid

import requests
from jose import jwt

JWT_SECRET = "dev-secret"
ALGORITHM = "HS256"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _token(role: str = "admin") -> str:
    payload = {"sub": f"{role}@plus.com", "user_id": f"{role}-id", "role": role}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def _auth_headers(role: str = "admin") -> dict:
    return {"Authorization": f"Bearer {_token(role)}"}


def test_health_check(product_service_container):
    # Rota pública, não exige autenticação.
    response = requests.get(product_service_container + "/")

    assert response.status_code == 200
    assert "Product Microservice" in response.json()["message"]


def test_requests_without_token_are_rejected(product_service_container):
    response = requests.get(product_service_container + "/products")
    assert response.status_code == 401


def test_vendedor_cannot_create_product(product_service_container):
    response = requests.post(
        product_service_container + "/products",
        json={"nome": _unique("Produto Vendedor"), "preco": 10.0},
        headers=_auth_headers("vendedor"),
    )
    assert response.status_code == 403


def test_full_product_lifecycle(product_service_container):
    base_url = product_service_container
    admin_headers = _auth_headers("admin")

    # 1. Cria um tamanho
    size_resp = requests.post(
        f"{base_url}/sizes", json={"nome": _unique("T")[:10]}, headers=admin_headers
    )
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
        headers=admin_headers,
    )
    assert product_resp.status_code == 201
    product = product_resp.json()

    # 3. Adiciona uma variante a esse produto
    variant_resp = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Azul", "sku": _unique("SKU")},
        headers=admin_headers,
    )
    assert variant_resp.status_code == 201
    variant = variant_resp.json()
    assert variant["produtoId"] == product["id"]

    # 4. Busca o produto (com token de leitura, papel "vendedor") e confirma
    # que a variante aparece no detalhe
    detail_resp = requests.get(
        f"{base_url}/products/{product['id']}", headers=_auth_headers("vendedor")
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["variantes"]) == 1
    assert detail["variantes"][0]["id"] == variant["id"]

    # 5. Desativa o produto e confirma o soft-delete em cascata
    disable_resp = requests.patch(
        f"{base_url}/products/{product['id']}/disable", headers=admin_headers
    )
    assert disable_resp.status_code == 200

    final_check = requests.get(
        f"{base_url}/products/{product['id']}", headers=admin_headers
    ).json()
    assert final_check["ativo"] is False
    assert final_check["variantes"][0]["ativo"] is False


def test_create_product_without_required_field_returns_422(product_service_container):
    response = requests.post(
        product_service_container + "/products",
        json={"preco": 10.0},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 422


def test_get_nonexistent_product_returns_404(product_service_container):
    response = requests.get(
        product_service_container + "/products/id-inexistente",
        headers=_auth_headers("vendedor"),
    )

    assert response.status_code == 404


def test_duplicate_sku_returns_409(product_service_container):
    base_url = product_service_container
    admin_headers = _auth_headers("admin")
    size = requests.post(
        f"{base_url}/sizes", json={"nome": _unique("T")[:10]}, headers=admin_headers
    ).json()
    product = requests.post(
        f"{base_url}/products",
        json={"nome": _unique("Produto SKU"), "preco": 10.0},
        headers=admin_headers,
    ).json()
    sku = _unique("SKU-DUP")

    first = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Verde", "sku": sku},
        headers=admin_headers,
    )
    assert first.status_code == 201

    second = requests.post(
        f"{base_url}/products/{product['id']}/variants",
        json={"tamanhoId": size["id"], "cor": "Amarelo", "sku": sku},
        headers=admin_headers,
    )
    assert second.status_code == 409


def test_pagination_on_products_list(product_service_container):
    base_url = product_service_container

    response = requests.get(
        f"{base_url}/products",
        params={"page": 1, "pageSize": 1},
        headers=_auth_headers("vendedor"),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 1
    assert body["page"] == 1
    assert body["pageSize"] == 1
