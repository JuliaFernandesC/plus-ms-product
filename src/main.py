from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.database.connection import engine, Base
from app.controllers.product_controller import router as product_router
from app.controllers.variant_controller import product_variants_router, variants_router
from app.models.product_model import *

# Arquivo principal do microsserviço de Produtos e Grades
app = FastAPI(
    title="Plus Gestão — Microsserviço de Produto",
    description="API do microsserviço de Produto do sistema Plus Gestão (vestuário plus size).",
    version="1.0.0"
)

# Configurar CORS (permite requisições do frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rede de segurança contra IntegrityError não tratado em algum ponto do
# código (ex.: uma corrida entre duas requisições concorrentes que passe
# pelas validações manuais nos controllers mas colida no commit). Sem isso,
# o SQLAlchemy/driver do banco propagaria uma exceção crua e o FastAPI
# devolveria um 500 sem nenhum detalhe útil para o cliente da API.
@app.exception_handler(IntegrityError)
def handle_integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Conflito de integridade de dados (registro duplicado ou referência inválida)."},
    )


@app.get("/")
def root():
    return {"message": "Product Microservice is running !!!"}

# Criar todas as tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)  

# Incluir rotas
app.include_router(product_router)
app.include_router(product_variants_router)
app.include_router(variants_router)
