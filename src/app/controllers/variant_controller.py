from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.product_model import ProductModel, VariantModel, SizeModel
from app.dtos.product_dtos import VariantCreateRequest, VariantUpdateRequest, VariantResponse, MessageResponse

# Definiremos dois roteadores para cobrir as rotas aninhadas em /products e as rotas raiz em /variants
product_variants_router = APIRouter(prefix="/products", tags=["Variantes"])
variants_router = APIRouter(prefix="/variants", tags=["Variantes"])

@product_variants_router.post("/{productId}/variants", response_model=VariantResponse, status_code=status.HTTP_201_CREATED)
def create_variant(productId: str, data: VariantCreateRequest, db: Session = Depends(get_db)):
    # Verifica se o produto existe
    product = db.query(ProductModel).filter(ProductModel.id == productId).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    
    # Verifica se o tamanho existe
    size = db.query(SizeModel).filter(SizeModel.id == data.tamanhoId).first()
    if not size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tamanho inválido ou não cadastrado"
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
        tamanho_id=data.tamanhoId,
        cor=data.cor,
        sku=data.sku,
        ativo=True
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return VariantResponse.model_validate(variant)

@product_variants_router.get("/{productId}/variants", response_model=list[VariantResponse])
def list_variants_by_product(productId: str, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == productId).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    return [VariantResponse.model_validate(v) for v in product.variantes]

@variants_router.get("/{id}", response_model=VariantResponse)
def get_variant_by_id(id: str, db: Session = Depends(get_db)):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )
    return VariantResponse.model_validate(variant)

@variants_router.put("/{id}", response_model=VariantResponse)
def update_variant(id: str, data: VariantUpdateRequest, db: Session = Depends(get_db)):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )

    if data.tamanhoId is not None:
        size = db.query(SizeModel).filter(SizeModel.id == data.tamanhoId).first()
        if not size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tamanho inválido ou não cadastrado"
            )
        variant.tamanho_id = data.tamanhoId

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

    db.commit()
    db.refresh(variant)
    return VariantResponse.model_validate(variant)

@variants_router.patch("/{id}/disable", response_model=MessageResponse)
def disable_variant(id: str, db: Session = Depends(get_db)):
    variant = db.query(VariantModel).filter(VariantModel.id == id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante não encontrada"
        )
    variant.ativo = False
    db.commit()
    return MessageResponse(message="Variante desativada com sucesso")
