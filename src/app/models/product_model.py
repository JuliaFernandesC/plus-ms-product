import uuid
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class SizeModel(Base):
    __tablename__ = "sizes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nome = Column(String(10), nullable=False, unique=True)
    descricao = Column(String(500), nullable=True)
    ativo = Column(Boolean, default=True)

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

    variantes = relationship("VariantModel", back_populates="produto", cascade="all, delete-orphan")

class VariantModel(Base):
    __tablename__ = "variants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    produto_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    tamanho_id = Column(String, ForeignKey("sizes.id"), nullable=False)
    cor = Column(String(50), nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    produto = relationship("ProductModel", back_populates="variantes")
    tamanho = relationship("SizeModel")
