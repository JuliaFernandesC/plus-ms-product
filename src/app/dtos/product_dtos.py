from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==============================================================
# BASE DTO CONFIG (COMPATIBILITY PYDANTIC V1 & V2)
# ==============================================================
class BaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ==============================================================
# TAMANHOS DTOs
# ==============================================================
class SizeCreateRequest(BaseDTO):
    nome: str = Field(..., max_length=10, example="GG")
    descricao: Optional[str] = Field(None, max_length=500, example="Tamanho GG — Busto 110-118cm, Cintura 96-104cm")

class SizeUpdateRequest(BaseDTO):
    nome: Optional[str] = Field(None, max_length=10)
    descricao: Optional[str] = Field(None, max_length=500)

class SizeResponse(BaseDTO):
    id: str
    nome: str
    descricao: Optional[str] = None
    ativo: bool

# ==============================================================
# VARIANTES DTOs
# ==============================================================
class VariantCreateNestedRequest(BaseDTO):
    tamanhoId: str = Field(..., alias="tamanhoId")
    cor: str = Field(..., max_length=50)
    sku: str = Field(..., max_length=50)

class VariantCreateRequest(BaseDTO):
    tamanhoId: str = Field(..., alias="tamanhoId")
    cor: str = Field(..., max_length=50)
    sku: str = Field(..., max_length=50)

class VariantUpdateRequest(BaseDTO):
    tamanhoId: Optional[str] = Field(None, alias="tamanhoId")
    cor: Optional[str] = Field(None, max_length=50)
    sku: Optional[str] = Field(None, max_length=50)

class VariantResponse(BaseDTO):
    id: str
    produtoId: str = Field(..., alias="produtoId")
    tamanhoId: str = Field(..., alias="tamanhoId")
    tamanho: Optional[SizeResponse] = None
    cor: str
    sku: str
    ativo: bool
    criadoEm: Optional[datetime] = Field(None, alias="criadoEm")
    atualizadoEm: Optional[datetime] = Field(None, alias="atualizadoEm")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, "produto_id"):
            size_dto = SizeResponse.model_validate(obj.tamanho) if hasattr(obj, "tamanho") and obj.tamanho else None
            return cls(
                id=obj.id,
                produtoId=obj.produto_id,
                tamanhoId=obj.tamanho_id,
                tamanho=size_dto,
                cor=obj.cor,
                sku=obj.sku,
                ativo=obj.ativo,
                criadoEm=obj.criado_em,
                atualizadoEm=obj.atualizado_em
            )
        return super().model_validate(obj, **kwargs)

# ==============================================================
# PRODUTOS DTOs
# ==============================================================
class ProductCreateRequest(BaseDTO):
    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, max_length=2000)
    marca: Optional[str] = Field(None, max_length=100)
    preco: float = Field(..., ge=0.0)
    categoriaId: Optional[str] = Field(None, alias="categoriaId")
    fornecedorId: Optional[str] = Field(None, alias="fornecedorId")
    variantes: Optional[List[VariantCreateNestedRequest]] = None

class ProductUpdateRequest(BaseDTO):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, max_length=2000)
    marca: Optional[str] = Field(None, max_length=100)
    preco: Optional[float] = Field(None, ge=0.0)
    categoriaId: Optional[str] = Field(None, alias="categoriaId")
    fornecedorId: Optional[str] = Field(None, alias="fornecedorId")

class ProductResponse(BaseDTO):
    id: str
    nome: str
    descricao: Optional[str] = None
    marca: Optional[str] = None
    preco: float
    ativo: bool
    categoriaId: Optional[str] = Field(None, alias="categoriaId")
    fornecedorId: Optional[str] = Field(None, alias="fornecedorId")
    criadoEm: datetime = Field(..., alias="criadoEm")
    atualizadoEm: datetime = Field(..., alias="atualizadoEm")

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, "categoria_id"):
            return cls(
                id=obj.id,
                nome=obj.nome,
                descricao=obj.descricao,
                marca=obj.marca,
                preco=obj.preco,
                ativo=obj.ativo,
                categoriaId=obj.categoria_id,
                fornecedorId=obj.fornecedor_id,
                criadoEm=obj.criado_em,
                atualizadoEm=obj.atualizado_em
            )
        return super().model_validate(obj, **kwargs)

# Detalhes do Produto contendo variantes
class ProductDetailResponse(ProductResponse):
    variantes: List[VariantResponse] = []

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, "categoria_id"):
            vars_dto = [VariantResponse.model_validate(v) for v in obj.variantes]
            return cls(
                id=obj.id,
                nome=obj.nome,
                descricao=obj.descricao,
                marca=obj.marca,
                preco=obj.preco,
                ativo=obj.ativo,
                categoriaId=obj.categoria_id,
                fornecedorId=obj.fornecedor_id,
                criadoEm=obj.criado_em,
                atualizadoEm=obj.atualizado_em,
                variantes=vars_dto
            )
        return super().model_validate(obj, **kwargs)

class PaginatedProductResponse(BaseDTO):
    items: List[ProductDetailResponse]
    page: int
    pageSize: int = Field(..., alias="pageSize")
    totalItems: int = Field(..., alias="totalItems")
    totalPages: int = Field(..., alias="totalPages")

# ==============================================================
# RESPOSTAS GENÉRICAS
# ==============================================================
class MessageResponse(BaseDTO):
    message: str

class ErrorResponse(BaseDTO):
    error: str
    statusCode: int = Field(..., alias="statusCode")
