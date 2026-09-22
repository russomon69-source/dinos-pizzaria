from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=List[ReviewOut])
def list_published_reviews(
    limit: int = Query(20, ge=1, le=50, description="Número máximo de avaliações a retornar"),
    db: Session = Depends(get_db),
):
    """Listar avaliações e depoimentos de clientes publicados no site."""
    return (
        db.query(Review)
        .filter(Review.is_published == True)  # noqa: E712
        .order_by(Review.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/admin-list", response_model=List[ReviewOut])
def list_reviews_admin(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Listar todas as avaliações no painel administrativo."""
    return db.query(Review).order_by(Review.id.desc()).all()


@router.get("/{review_id}", response_model=ReviewOut)
def get_review_admin(
    review_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Obter detalhes de uma avaliação por ID."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")
    return review


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Cadastrar nova avaliação ou depoimento no sistema (requer admin)."""
    review = Review(
        customer_name=payload.customer_name.strip(),
        rating=payload.rating,
        comment=payload.comment.strip(),
        is_published=payload.is_published,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar avaliação existente (requer admin)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")

    if payload.customer_name is not None:
        review.customer_name = payload.customer_name.strip()
    if payload.rating is not None:
        review.rating = payload.rating
    if payload.comment is not None:
        review.comment = payload.comment.strip()
    if payload.is_published is not None:
        review.is_published = payload.is_published

    db.commit()
    db.refresh(review)
    return review


@router.patch("/{review_id}/toggle-published", response_model=ReviewOut)
def toggle_review_published(
    review_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar visibilidade pública da avaliação (requer admin)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")
    review.is_published = not review.is_published
    db.commit()
    db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir avaliação (requer admin)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")
    db.delete(review)
    db.commit()
    return None
