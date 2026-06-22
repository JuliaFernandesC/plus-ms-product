"""
Configuração compartilhada dos testes UNITÁRIOS do MS de Produto.

Os testes aqui NÃO sobem servidor nem container: usam o TestClient do
FastAPI (chama o app diretamente em memória) e um banco SQLite em
memória no lugar do Postgres/Ministack real. Isso é o que permite
esses testes rodarem direto no pipe, sem precisar de Docker.
"""
import os

# Garante que, ao importar `main` (que cria as tabelas no banco "de
# produção" assim que o módulo é carregado), isso aconteça contra um
# banco em memória descartável — nunca contra o products.db real ou
# um Postgres/Ministack de verdade.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.connection import Base, get_db
from main import app

# Engine separada, exclusiva dos testes. StaticPool garante que todas as
# "conexões" do SQLAlchemy reutilizem a mesma conexão sqlite em memória
# (sem isso, cada conexão nova veria um banco em memória vazio diferente).
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    """Cria um banco zerado antes de cada teste e destrói depois."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """Cliente HTTP de teste com o banco de teste injetado no lugar do real."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Helpers reutilizados por vários arquivos de teste
# ----------------------------------------------------------------------
def create_size(client, nome="M", descricao="Tamanho M"):
    """Cria um tamanho via API e devolve o JSON criado (id incluso)."""
    response = client.post("/sizes", json={"nome": nome, "descricao": descricao})
    assert response.status_code == 201
    return response.json()


def create_product(client, **overrides):
    """Cria um produto via API com valores padrão sobrescrevíveis."""
    payload = {
        "nome": "Vestido Floral",
        "descricao": "Vestido leve de verão",
        "marca": "Plus Co",
        "preco": 149.90,
        "categoriaId": "categoria-1",
        "fornecedorId": "fornecedor-1",
    }
    payload.update(overrides)
    response = client.post("/products", json=payload)
    assert response.status_code == 201
    return response.json()
