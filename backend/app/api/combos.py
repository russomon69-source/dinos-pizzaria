from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.combo import Combo
from app.schemas.combo import ComboCreate, ComboOut, ComboUpdate

router = APIRouter(prefix="/combos", tags=["Combos"])


@router.get("", response_model=List[ComboOut])
def list_combos(
    active_only: bool = Query(True, description="Filtrar apenas combos ativos"),
    db: Session = Depends(get_db),
):
    """Listar combos com destaque prioritário para a promoção do dia."""
    query = db.query(Combo)
    if active_only:
        query = query.filter(Combo.is_active == True)  # noqa: E712
    return query.order_by(Combo.is_promo_of_day.desc(), Combo.id.desc()).all()


@router.get("/promos", response_model=List[ComboOut])
def list_promo_combos(db: Session = Depends(get_db)):
    """Listar exclusivamente os combos ativos marcados como Promoção do Dia."""
    return (
        db.query(Combo)
        .filter(Combo.is_active == True, Combo.is_promo_of_day == True)  # noqa: E712
        .order_by(Combo.id.desc())
        .all()
    )


@router.get("/admin-list", response_model=List[ComboOut])
def list_all_combos_admin(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Listar todos os combos (ativos e inativos) para o painel de gestão."""
    return db.query(Combo).order_by(Combo.id.desc()).all()


@router.get("/{combo_id}", response_model=ComboOut)
def get_combo(combo_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de um combo por ID."""
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combo não encontrado.",
        )
    return combo


@router.post("", response_model=ComboOut, status_code=status.HTTP_201_CREATED)
def create_combo(
    combo_in: ComboCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Cadastrar um novo combo ou oferta (requer autenticação de administrador)."""
    combo = Combo(
        title=combo_in.title,
        description=combo_in.description,
        price=combo_in.price,
        image_url=combo_in.image_url,
        is_active=combo_in.is_active,
        is_promo_of_day=combo_in.is_promo_of_day,
    )
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo


@router.put("/{combo_id}", response_model=ComboOut)
def update_combo(
    combo_id: int,
    combo_in: ComboUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar dados de um combo existente (requer autenticação de administrador)."""
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combo não encontrado.",
        )

    if combo_in.title is not None:
        combo.title = combo_in.title
    if combo_in.description is not None:
        combo.description = combo_in.description
    if combo_in.price is not None:
        combo.price = combo_in.price
    if combo_in.image_url is not None:
        combo.image_url = combo_in.image_url
    if combo_in.is_active is not None:
        combo.is_active = combo_in.is_active
    if combo_in.is_promo_of_day is not None:
        combo.is_promo_of_day = combo_in.is_promo_of_day

    db.commit()
    db.refresh(combo)
    return combo


@router.patch("/{combo_id}/toggle-active", response_model=ComboOut)
def toggle_combo_active(
    combo_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar status de ativação do combo (requer autenticação de administrador)."""
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combo não encontrado.",
        )
    combo.is_active = not combo.is_active
    db.commit()
    db.refresh(combo)
    return combo


@router.patch("/{combo_id}/toggle-promo", response_model=ComboOut)
def toggle_combo_promo(
    combo_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar destaque de Promoção do Dia do combo (requer autenticação de administrador)."""
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combo não encontrado.",
        )
    combo.is_promo_of_day = not combo.is_promo_of_day
    db.commit()
    db.refresh(combo)
    return combo


@router.delete("/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_combo(
    combo_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir um combo (requer autenticação de administrador)."""
    combo = db.query(Combo).filter(Combo.id == combo_id).first()
    if not combo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combo não encontrado.",
        )
    db.delete(combo)
    db.commit()
    return None
