import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "ministack")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "plus")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "plus_secret")
    DB_NAME: str = os.getenv("DB_NAME", "plus_auth") # maps to database name
    PORT: int = int(os.getenv("PORT", 3002))

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
