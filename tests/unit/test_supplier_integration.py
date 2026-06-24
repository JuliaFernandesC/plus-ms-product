"""
Testes unitários da validação cross-service de fornecedorId (mesma lógica
de fail-open/bloqueio aplicada à Categoria, em test_auth_integration.py,
agora para o MS de Fornecedores).
"""
from app.config.settings import settings


def test_create_product_with_fornecedor_id_when_service_not_configured(client):
    """Sem SUPPLIER_SERVICE_URL configurada (padrão), a criação do produto
    não deve ser bloqueada por causa do fornecedorId — validação pulada
    (fail-open)."""
    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "fornecedorId": "fornecedor-1"}
    )
    assert response.status_code == 201


def test_create_product_blocked_when_supplier_service_confirms_not_found(client, monkeypatch):
    monkeypatch.setattr(settings, "SUPPLIER_SERVICE_URL", "http://fake-supplier:9999")

    class FakeResponse:
        status_code = 404

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    import app.clients.supplier_client as supplier_client_module
    monkeypatch.setattr(supplier_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "fornecedorId": "fornecedor-inexistente"}
    )
    assert response.status_code == 400


def test_create_product_allowed_when_supplier_service_confirms_exists(client, monkeypatch):
    monkeypatch.setattr(settings, "SUPPLIER_SERVICE_URL", "http://fake-supplier:9999")

    class FakeResponse:
        status_code = 200

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    import app.clients.supplier_client as supplier_client_module
    monkeypatch.setattr(supplier_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "fornecedorId": "fornecedor-1"}
    )
    assert response.status_code == 201


def test_create_product_fails_open_when_supplier_service_unreachable(client, monkeypatch):
    monkeypatch.setattr(settings, "SUPPLIER_SERVICE_URL", "http://fake-supplier:9999")

    import httpx as httpx_module

    def fake_get(url, headers=None, timeout=None):
        raise httpx_module.ConnectTimeout("timeout simulado")

    import app.clients.supplier_client as supplier_client_module
    monkeypatch.setattr(supplier_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "fornecedorId": "fornecedor-1"}
    )
    # Serviço indisponível -> fail-open: não bloqueia a criação do produto.
    assert response.status_code == 201


def test_update_product_blocked_when_supplier_service_confirms_not_found(client, monkeypatch):
    create_response = client.post("/products", json={"nome": "Produto Base", "preco": 10.0})
    product_id = create_response.json()["id"]

    monkeypatch.setattr(settings, "SUPPLIER_SERVICE_URL", "http://fake-supplier:9999")

    class FakeResponse:
        status_code = 404

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    import app.clients.supplier_client as supplier_client_module
    monkeypatch.setattr(supplier_client_module.httpx, "get", fake_get)

    response = client.put(
        f"/products/{product_id}", json={"fornecedorId": "fornecedor-inexistente"}
    )
    assert response.status_code == 400
