import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.clients import categoria_client
from app.config.security import get_bearer_token, get_current_user, require_admin
from app.database.connection import get_db
from app.models.product_model import ProductModel, VariantModel
from app.dtos.product_dtos import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductDetailResponse,
    PaginatedProductResponse,
    MessageResponse
)

router = APIRouter(prefix="/products", tags=["Produtos"])


def _validate_categoria_id(categoria_id: str | None, bearer_token: str | None) -> None:
    """Valida cross-service o categoriaId informado, se houver.

    Levanta 400 apenas quando o MS de Categorias CONFIRMA que a categoria
    não existe (ou quando o formato do id é inválido). Se a validação não
    puder ser concluída (serviço não configurado/indisponível), a operação
    segue normalmente — ver app/clients/categoria_client.py e ADR.md.
    """
    if not categoria_id:
        return

    exists = categoria_client.categoria_exists(categoria_id, bearer_token=bearer_token)
    if exists is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="categoriaId não corresponde a uma categoria existente"
        )


def _validate_variantes_payload(db: Session, variantes) -> None:
    """Replica, na criação de produto com variantes aninhadas, as mesmas
    validações já existentes na rota dedicada de variantes
    (POST /products/{id}/variants): SKU não pode estar duplicado — nem
    contra o banco, nem dentro do próprio payload.
    """
    if not variantes:
        return

    skus_no_payload = set()
    for v in variantes:
        if v.sku in skus_no_payload:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SKU '{v.sku}' duplicado dentro da mesma requisição"
            )
        skus_no_payload.add(v.sku)

        existing_sku = db.query(VariantModel).filter(VariantModel.sku == v.sku).first()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SKU '{v.sku}' já cadastrado para outra variante"
            )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_categoria_id(data.categoriaId, bearer_token)
    _validate_variantes_payload(db, data.variantes)

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
                cor=v.cor,
                sku=v.sku,
                ativo=True
            )
            db.add(variant)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito de integridade ao salvar o produto (ex.: SKU duplicado por uma requisição concorrente)."
        )

    db.refresh(product)
    return ProductResponse.model_validate(product)

@router.get("", response_model=PaginatedProductResponse)
def list_products(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    ativo: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
    marca: str = Query(None),
    precoMin: float = Query(None),
    precoMax: float = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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

    # Filtros por Variántes (Cor)
    if cor:
        query = query.join(ProductModel.variantes)
        query = query.filter(VariantModel.cor.ilike(f"%{cor}%"))

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
def get_product_by_id(
    id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    return ProductDetailResponse.model_validate(product)

@router.put("/{id}", response_model=ProductResponse)
def update_product(
    id: str,
    data: ProductUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
    bearer_token: str = Depends(get_bearer_token),
):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )

    if data.categoriaId is not None:
        _validate_categoria_id(data.categoriaId, bearer_token)

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

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito de integridade ao atualizar o produto."
        )

    db.refresh(product)
    return ProductResponse.model_validate(product)

@router.patch("/{id}/disable", response_model=MessageResponse)
def disable_product(
    id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
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
