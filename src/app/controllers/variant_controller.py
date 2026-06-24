from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config.security import get_current_user, require_admin
from app.database.connection import get_db
from app.models.product_model import ProductModel, VariantModel
from app.dtos.product_dtos import VariantCreateRequest, VariantUpdateRequest, VariantResponse, MessageResponse

# Definiremos dois roteadores para cobrir as rotas aninhadas em /products e as rotas raiz em /variants
product_variants_router = APIRouter(prefix="/products", tags=["Variantes"])
variants_router = APIRouter(prefix="/variants", tags=["Variantes"])

@product_variants_router.post("/{productId}/variants", response_model=VariantResponse, status_code=status.HTTP_201_CREATED)
def create_variant(
    productId: str,
    data: VariantCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    # Verifica se o produto existe
    product = db.query(ProductModel).filter(ProductModel.id == productId).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
        
    # Verifica se SKU já existe
    existing_sku = db.query(VariantModel).filter(VariantModel.sku == data.sku).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU já cadastrado para outra variante"
        )

    variant = VariantModel(
        produto_id=productId,
        cor=data.cor,
        sku=data.sku,
        ativo=True
    )
    db.add(variant)

    try:
        db.commit()
    except IntegrityError:
        # Defesa contra corrida entre a checagem acima e o commit (ex.: duas
        # requisições concorrentes criando o mesmo SKU).
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU já cadastrado para outra variante"
        )

    db.refresh(variant)
    return VariantResponse.model_validate(variant)

@product_variants_router.get("/{productId}/variants", response_model=list[VariantResponse])
def list_variants_by_product(
    productId: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    product = db.query(ProductModel).filter(ProductModel.id == productId).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    return [VariantResponse.model_validate(v) for v in product.variantes]

@variants_router.get("/{id}", response_model=VariantResponse)
def get_variant_by_id(
    id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )
    return VariantResponse.model_validate(variant)

@variants_router.put("/{id}", response_model=VariantResponse)
def update_variant(
    id: str,
    data: VariantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )

    if data.cor is not None:
        variant.cor = data.cor

    if data.sku is not None:
        existing_sku = db.query(VariantModel).filter(VariantModel.sku == data.sku, VariantModel.id != id).first()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SKU já cadastrado para outra variante"
            )
        variant.sku = data.sku

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU já cadastrado para outra variante"
        )

    db.refresh(variant)
    return VariantResponse.model_validate(variant)

@variants_router.patch("/{id}/disable", response_model=MessageResponse)
def disable_variant(
    id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )
    variant.ativo = False
    db.commit()
    return MessageResponse(message="Variante desativada com sucesso")
