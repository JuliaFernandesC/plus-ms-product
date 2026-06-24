"""
Testes unitários focados na integração com o MS Auth (JWT) e RBAC, além da
validação cross-service do categoriaId contra o MS de Categorias.

Diferente dos demais arquivos em tests/unit, aqui usamos o TestClient SEM
o override padrão de `get_current_user` (que os outros arquivos usam via
a fixture `client` em conftest.py) sempre que o objetivo é validar o
comportamento real do dependency (HTTPBearer + decodificação do JWT).
"""
import os

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config.security import ALGORITHM, get_bearer_token, get_current_user
from app.config.settings import settings
from app.database.connection import Base, get_db
from main import app
from tests.unit.conftest import (
    FAKE_ADMIN_PAYLOAD,
    TestingSessionLocal,
    engine,
)


def _make_token(role: str = "admin", **extra_claims) -> str:
    """Gera um JWT real, assinado com o mesmo segredo usado pelo MS de
    Produto (settings.JWT_SECRET), simulando um token emitido pelo MS Auth.
    """
    payload = {"sub": "user@plus.com", "user_id": "user-1", "role": role, **extra_claims}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


@pytest.fixture()
def raw_client():
    """Cliente de teste SEM nenhum override de autenticação — exercita o
    `get_current_user`/`require_admin` reais (HTTPBearer + verify_token),
    só com o banco substituído pelo de testes.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


# ----------------------------------------------------------------------
# 1. Nenhuma rota deve responder sem autenticação
# ----------------------------------------------------------------------
def test_list_products_without_token_returns_401(raw_client):
    response = raw_client.get("/products")
    assert response.status_code == 401


def test_create_product_without_token_returns_401(raw_client):
    response = raw_client.post("/products", json={"nome": "X", "preco": 10.0})
    assert response.status_code == 401


def test_request_with_invalid_token_returns_401(raw_client):
    response = raw_client.get(
        "/products", headers={"Authorization": "Bearer token-invalido-e-mal-formado"}
    )
    assert response.status_code == 401


# ----------------------------------------------------------------------
# 2. RBAC: leitura é permitida a qualquer papel autenticado; escrita é
#    restrita a admin.
# ----------------------------------------------------------------------
def test_vendedor_can_read_products(raw_client):
    token = _make_token(role="vendedor")
    response = raw_client.get("/products", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_vendedor_cannot_create_product_returns_403(raw_client):
    token = _make_token(role="vendedor")
    response = raw_client.post(
        "/products",
        json={"nome": "Produto Vendedor", "preco": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_create_product(raw_client):
    token = _make_token(role="admin")
    response = raw_client.post(
        "/products",
        json={"nome": "Produto Admin", "preco": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_user_without_role_claim_cannot_create_product(raw_client):
    # Token válido (assinatura correta), mas sem a claim "role" — não deve
    # ser tratado como admin por omissão.
    token = _make_token(role="vendedor")
    payload_without_role = {"sub": "user@plus.com", "user_id": "user-1"}
    token = jwt.encode(payload_without_role, settings.JWT_SECRET, algorithm=ALGORITHM)

    response = raw_client.post(
        "/products",
        json={"nome": "Sem Role", "preco": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ----------------------------------------------------------------------
# 3. Validação cross-service de categoriaId (fail-open quando o serviço de
#    Categorias não está configurado/disponível; bloqueante quando o
#    serviço confirma que a categoria não existe).
# ----------------------------------------------------------------------
def test_create_product_with_categoria_id_when_service_not_configured(client):
    """Sem CATEGORIA_SERVICE_URL configurada (padrão), a criação do produto
    não deve ser bloqueada por causa do categoriaId — a validação é
    simplesmente pulada (fail-open)."""
    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "categoriaId": "1"}
    )
    assert response.status_code == 201


def test_create_product_blocked_when_categoria_service_confirms_not_found(client, monkeypatch):
    monkeypatch.setattr(settings, "CATEGORIA_SERVICE_URL", "http://fake-categorias:9999")

    class FakeResponse:
        status_code = 404

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    import app.clients.categoria_client as categoria_client_module
    monkeypatch.setattr(categoria_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "categoriaId": "999"}
    )
    assert response.status_code == 400


def test_create_product_allowed_when_categoria_service_confirms_exists(client, monkeypatch):
    monkeypatch.setattr(settings, "CATEGORIA_SERVICE_URL", "http://fake-categorias:9999")

    class FakeResponse:
        status_code = 200

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    import app.clients.categoria_client as categoria_client_module
    monkeypatch.setattr(categoria_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "categoriaId": "1"}
    )
    assert response.status_code == 201


def test_create_product_fails_open_when_categoria_service_unreachable(client, monkeypatch):
    monkeypatch.setattr(settings, "CATEGORIA_SERVICE_URL", "http://fake-categorias:9999")

    import httpx as httpx_module

    def fake_get(url, headers=None, timeout=None):
        raise httpx_module.ConnectTimeout("timeout simulado")

    import app.clients.categoria_client as categoria_client_module
    monkeypatch.setattr(categoria_client_module.httpx, "get", fake_get)

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "categoriaId": "1"}
    )
    # Serviço indisponível -> fail-open: não bloqueia a criação do produto.
    assert response.status_code == 201


def test_create_product_with_non_numeric_categoria_id_returns_400(client, monkeypatch):
    monkeypatch.setattr(settings, "CATEGORIA_SERVICE_URL", "http://fake-categorias:9999")

    response = client.post(
        "/products", json={"nome": "Vestido", "preco": 10.0, "categoriaId": "categoria-abc"}
    )
    assert response.status_code == 400
