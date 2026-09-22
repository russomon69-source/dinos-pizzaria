from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductOut])
def list_products(
    category_id: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
    is_promo: Optional[bool] = Query(None, description="Filtrar produtos em promoção"),
    is_featured: Optional[bool] = Query(None, description="Filtrar produtos em destaque"),
    active_only: bool = Query(True, description="Filtrar apenas produtos ativos"),
    db: Session = Depends(get_db),
):
    """Listar produtos ativos do cardápio com suporte a filtros por categoria e promoção."""
    query = db.query(Product).options(joinedload(Product.category))
    if active_only:
        query = query.filter(Product.is_active == True)  # noqa: E712
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if is_promo is not None:
        query = query.filter(Product.is_promo == is_promo)
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)

    return query.order_by(Product.title.asc()).all()


@router.get("/featured", response_model=List[ProductOut])
def list_featured_products(db: Session = Depends(get_db)):
    """Listar produtos ativos marcados como Mais Pedidas / Destaque."""
    return (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.is_active == True, Product.is_featured == True)  # noqa: E712
        .order_by(Product.title.asc())
        .all()
    )


@router.get("/admin-list", response_model=List[ProductOut])
def list_all_products_admin(
    category_id: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Listar todos os produtos (ativos e inativos) para o painel administrativo."""
    query = db.query(Product).options(joinedload(Product.category))
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    return query.order_by(Product.id.desc()).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de um produto por ID."""
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Cadastrar um novo produto no cardápio (requer autenticação de administrador)."""
    # Verificar se a categoria informada existe
    category = db.query(Category).filter(Category.id == product_in.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categoria vinculada não existe.",
        )

    product = Product(
        title=product_in.title,
        description=product_in.description,
        price=product_in.price,
        image_url=product_in.image_url,
        is_promo=product_in.is_promo,
        is_featured=product_in.is_featured,
        is_active=product_in.is_active,
        category_id=product_in.category_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar dados de um produto existente (requer autenticação de administrador)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    if product_in.category_id is not None:
        category = db.query(Category).filter(Category.id == product_in.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Categoria vinculada não existe.",
            )
        product.category_id = product_in.category_id

    if product_in.title is not None:
        product.title = product_in.title
    if product_in.description is not None:
        product.description = product_in.description
    if product_in.price is not None:
        product.price = product_in.price
    if product_in.image_url is not None:
        product.image_url = product_in.image_url
    if product_in.is_promo is not None:
        product.is_promo = product_in.is_promo
    if product_in.is_featured is not None:
        product.is_featured = product_in.is_featured
    if product_in.is_active is not None:
        product.is_active = product_in.is_active

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/toggle-active", response_model=ProductOut)
def toggle_product_active(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar status de disponibilidade do produto (requer autenticação de administrador)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    product.is_active = not product.is_active
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/toggle-promo", response_model=ProductOut)
def toggle_product_promo(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar destaque de promoção do produto (requer autenticação de administrador)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    product.is_promo = not product.is_promo
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/toggle-featured", response_model=ProductOut)
def toggle_product_featured(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar destaque de Mais Pedida / Destaque (requer autenticação de administrador)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    product.is_featured = not product.is_featured
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir um produto do cardápio (requer autenticação de administrador)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )
    db.delete(product)
    db.commit()
    return None
