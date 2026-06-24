import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "ministack")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "plus")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "plus_secret")
    DB_NAME: str = os.getenv("DB_NAME", "plus_product") # maps to database name
    PORT: int = int(os.getenv("PORT", 3002))

    # Segredo compartilhado com o MS Auth para validar a assinatura dos JWTs.
    # Precisa ser IDÊNTICO ao JWT_SECRET configurado no plus-ms-auth, senão
    # nenhum token emitido por ele será aceito aqui.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret")

    # URL base do MS de Categorias, usada para validar categoriaId antes de
    # criar/atualizar um produto. Se não for configurada, a validação
    # cross-service é simplesmente pulada (fail-open) — ver ADR.md, seção de
    # trade-offs, para a justificativa dessa escolha.
    CATEGORIA_SERVICE_URL: str = os.getenv("CATEGORIA_SERVICE_URL", "")
    CATEGORIA_SERVICE_TIMEOUT_SECONDS: float = float(os.getenv("CATEGORIA_SERVICE_TIMEOUT_SECONDS", "3"))

    # URL base do MS de Fornecedores, usada para validar fornecedorId antes de
    # criar/atualizar um produto. Mesmo padrão de fail-open do MS de
    # Categorias — ver app/clients/supplier_client.py e ADR.md.
    SUPPLIER_SERVICE_URL: str = os.getenv("SUPPLIER_SERVICE_URL", "")
    SUPPLIER_SERVICE_TIMEOUT_SECONDS: float = float(os.getenv("SUPPLIER_SERVICE_TIMEOUT_SECONDS", "3"))

    @property
    def DATABASE_URL(self) -> str:
        # Usa SQLite por padrão no local para poder testar o Swagger imediatamente sem Docker.
        # Se for explicitamente configurado no .env, usa PostgreSQL.
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
        if os.getenv("DB_HOST") and os.getenv("DB_HOST") != "localhost":
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return "sqlite:///./products.db"

settings = Settings()
