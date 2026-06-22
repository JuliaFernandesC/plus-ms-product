from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import engine, Base
from app.controllers.size_controller import router as size_router
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

@app.get("/")
def root():
    return {"message": "Product Microservice is running !!!"}

# Criar todas as tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)  

# Incluir rotas
app.include_router(product_router)
app.include_router(product_variants_router)
app.include_router(variants_router)
app.include_router(size_router)
