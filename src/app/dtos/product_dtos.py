from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==============================================================
# BASE DTO CONFIG (COMPATIBILITY PYDANTIC V1 & V2)
# ==============================================================
class BaseDTO(BaseModel):
    # from_attributes: permite construir o DTO a partir de objetos ORM
    #   (acessando atributos, não chaves de dict).
    # populate_by_name: permite que os DTOs de Request aceitem tanto o nome
    #   "pythonico" do campo quanto seu alias (ex.: tamanhoId), sem afetar
    #   os DTOs de Response (que não recebem dados externos via alias).
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ==============================================================
# VARIANTES DTOs
# ==============================================================
class VariantCreateNestedRequest(BaseDTO):
    cor: str = Field(..., max_length=50)
    sku: str = Field(..., max_length=50)

class VariantCreateRequest(BaseDTO):
    cor: str = Field(..., max_length=50)
    sku: str = Field(..., max_length=50)

class VariantUpdateRequest(BaseDTO):
    cor: Optional[str] = Field(None, max_length=50)
    sku: Optional[str] = Field(None, max_length=50)

class VariantResponse(BaseDTO):
    id: str
    produtoId: str = Field(..., validation_alias="produto_id")
    cor: str
    sku: str
    ativo: bool
    criadoEm: Optional[datetime] = Field(None, validation_alias="criado_em")
    atualizadoEm: Optional[datetime] = Field(None, validation_alias="atualizado_em")

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
    categoriaId: Optional[str] = Field(None, validation_alias="categoria_id")
    fornecedorId: Optional[str] = Field(None, validation_alias="fornecedor_id")
    criadoEm: datetime = Field(..., validation_alias="criado_em")
    atualizadoEm: datetime = Field(..., validation_alias="atualizado_em")

# Detalhes do Produto contendo variantes
class ProductDetailResponse(ProductResponse):
    variantes: List[VariantResponse] = []

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
