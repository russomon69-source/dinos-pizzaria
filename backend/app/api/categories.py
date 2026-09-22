from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryOut])
def list_categories(
    active_only: bool = Query(True, description="Filtrar apenas categorias ativas"),
    db: Session = Depends(get_db),
):
    """Listar categorias do cardápio ordenadas por ordem de exibição."""
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)  # noqa: E712
    return query.order_by(Category.order.asc(), Category.name.asc()).all()


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de uma categoria por ID."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )
    return category


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Criar uma nova categoria no cardápio (requer autenticação de administrador)."""
    # Validar unicidade do nome e slug
    existing = (
        db.query(Category)
        .filter((Category.name == category_in.name) | (Category.slug == category_in.slug))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma categoria com este nome ou slug.",
        )

    category = Category(
        name=category_in.name,
        slug=category_in.slug,
        order=category_in.order,
        is_active=category_in.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar dados de uma categoria existente (requer autenticação de administrador)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

    # Validar unicidade caso nome ou slug tenham sido alterados
    if category_in.name is not None and category_in.name != category.name:
        if db.query(Category).filter(Category.name == category_in.name).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com este nome.",
            )
        category.name = category_in.name

    if category_in.slug is not None and category_in.slug != category.slug:
        if db.query(Category).filter(Category.slug == category_in.slug).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com este slug.",
            )
        category.slug = category_in.slug

    if category_in.order is not None:
        category.order = category_in.order

    if category_in.is_active is not None:
        category.is_active = category_in.is_active

    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}/toggle-active", response_model=CategoryOut)
def toggle_category_active(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar status de ativação da categoria (requer autenticação de administrador)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )
    category.is_active = not category.is_active
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir uma categoria e seus produtos vinculados (requer autenticação de administrador)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )
    db.delete(category)
    db.commit()
    return None
