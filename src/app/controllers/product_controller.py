import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.product_model import ProductModel, VariantModel, SizeModel
from app.dtos.product_dtos import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductDetailResponse,
    PaginatedProductResponse,
    MessageResponse
)

router = APIRouter(prefix="/products", tags=["Produtos"])

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreateRequest, db: Session = Depends(get_db)):
    product = ProductModel(
        nome=data.nome,
        descricao=data.descricao,
        marca=data.marca,
        preco=data.preco,
        categoria_id=data.categoriaId,
        fornecedor_id=data.fornecedorId,
        ativo=True
    )
    db.add(product)
    
    if data.variantes:
        for v in data.variantes:
            variant = VariantModel(
                produto=product,
                tamanho_id=v.tamanhoId,
                cor=v.cor,
                sku=v.sku,
                ativo=True
            )
            db.add(variant)

    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)

@router.get("", response_model=PaginatedProductResponse)
def list_products(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    ativo: bool = Query(True),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * pageSize
    query = db.query(ProductModel).filter(ProductModel.ativo == ativo)
    total_items = query.count()
    products = query.offset(offset).limit(pageSize).all()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0

    return PaginatedProductResponse(
        items=[ProductDetailResponse.model_validate(p) for p in products],
        page=page,
        pageSize=pageSize,
        totalItems=total_items,
        totalPages=total_pages
    )

@router.get("/search", response_model=PaginatedProductResponse)
def search_products(
    nome: str = Query(None),
    categoriaId: str = Query(None),
    fornecedorId: str = Query(None),
    cor: str = Query(None),
    tamanho: str = Query(None),
    marca: str = Query(None),
    precoMin: float = Query(None),
    precoMax: float = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * pageSize
    query = db.query(ProductModel)

    # Filtros textuais
    if nome:
        query = query.filter(
            (ProductModel.nome.ilike(f"%{nome}%")) | (ProductModel.descricao.ilike(f"%{nome}%"))
        )
    if marca:
        query = query.filter(ProductModel.marca.ilike(f"%{marca}%"))
    
    # Filtros por chaves estrangeiras
    if categoriaId:
        query = query.filter(ProductModel.categoria_id == categoriaId)
    if fornecedorId:
        query = query.filter(ProductModel.fornecedor_id == fornecedorId)
        
    # Faixa de preço
    if precoMin is not None:
        query = query.filter(ProductModel.preco >= precoMin)
    if precoMax is not None:
        query = query.filter(ProductModel.preco <= precoMax)

    # Filtros por Variantes (Cor/Tamanho)
    if cor or tamanho:
        query = query.join(ProductModel.variantes)
        if cor:
            query = query.filter(VariantModel.cor.ilike(f"%{cor}%"))
        if tamanho:
            query = query.join(VariantModel.tamanho).filter(SizeModel.nome.ilike(f"%{tamanho}%"))

    # Remover duplicatas que podem vir do join
    query = query.distinct()
    
    total_items = query.count()
    products = query.offset(offset).limit(pageSize).all()
    total_pages = math.ceil(total_items / pageSize) if total_items > 0 else 0

    return PaginatedProductResponse(
        items=[ProductDetailResponse.model_validate(p) for p in products],
        page=page,
        pageSize=pageSize,
        totalItems=total_items,
        totalPages=total_pages
    )

@router.get("/{id}", response_model=ProductDetailResponse)
def get_product_by_id(id: str, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    return ProductDetailResponse.model_validate(product)

@router.put("/{id}", response_model=ProductResponse)
def update_product(id: str, data: ProductUpdateRequest, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    
    if data.nome is not None:
        product.nome = data.nome
    if data.descricao is not None:
        product.descricao = data.descricao
    if data.marca is not None:
        product.marca = data.marca
    if data.preco is not None:
        product.preco = data.preco
    if data.categoriaId is not None:
        product.categoria_id = data.categoriaId
    if data.fornecedorId is not None:
        product.fornecedor_id = data.fornecedorId

    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)

@router.patch("/{id}/disable", response_model=MessageResponse)
def disable_product(id: str, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    
    # Soft delete do produto e desativação em cascata das suas variantes
    product.ativo = False
    for v in product.variantes:
        v.ativo = False

    db.commit()
    return MessageResponse(message="Produto desativado com sucesso")
