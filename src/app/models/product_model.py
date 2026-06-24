import uuid
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class ProductModel(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(String(2000), nullable=True)
    marca = Column(String(100), nullable=True)
    preco = Column(Float, nullable=False)
    categoria_id = Column(String, nullable=True)
    fornecedor_id = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())




