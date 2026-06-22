from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.product_model import SizeModel
from app.dtos.product_dtos import SizeCreateRequest, SizeUpdateRequest, SizeResponse, MessageResponse, ErrorResponse

router = APIRouter(prefix="/sizes", tags=["Tamanhos"])

@router.post("", response_model=SizeResponse, status_code=status.HTTP_201_CREATED)
def create_size(data: SizeCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SizeModel).filter(SizeModel.nome == data.nome).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tamanho com este nome já existe"
        )
    size = SizeModel(
        nome=data.nome,
        descricao=data.descricao,
        ativo=True
    )
    db.add(size)
    db.commit()
    db.refresh(size)
    return SizeResponse.model_validate(size)

@router.get("", response_model=list[SizeResponse])
def list_sizes(ativo: bool = True, db: Session = Depends(get_db)):
    sizes = db.query(SizeModel).filter(SizeModel.ativo == ativo).all()
    return [SizeResponse.model_validate(s) for s in sizes]

@router.get("/{id}", response_model=SizeResponse)
def get_size_by_id(id: str, db: Session = Depends(get_db)):
    size = db.query(SizeModel).filter(SizeModel.id == id).first()
    if not size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tamanho não encontrado"
        )
    return SizeResponse.model_validate(size)

@router.put("/{id}", response_model=SizeResponse)
def update_size(id: str, data: SizeUpdateRequest, db: Session = Depends(get_db)):
    size = db.query(SizeModel).filter(SizeModel.id == id).first()
    if not size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tamanho não encontrado"
        )
    if data.nome is not None:
        existing = db.query(SizeModel).filter(SizeModel.nome == data.nome, SizeModel.id != id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tamanho com este nome já existe"
            )
        size.nome = data.nome
    if data.descricao is not None:
        size.descricao = data.descricao
    db.commit()
    db.refresh(size)
    return SizeResponse.model_validate(size)

@router.patch("/{id}/disable", response_model=MessageResponse)
def disable_size(id: str, db: Session = Depends(get_db)):
    size = db.query(SizeModel).filter(SizeModel.id == id).first()
    if not size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tamanho não encontrado"
        )
    size.ativo = False
    db.commit()
    return MessageResponse(message="Tamanho desativado com sucesso")
