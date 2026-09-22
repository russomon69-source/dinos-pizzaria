from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.coupon import Coupon
from app.schemas.coupon import (
    CouponCreate,
    CouponOut,
    CouponUpdate,
    CouponValidateIn,
    CouponValidateOut,
)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


def calculate_coupon_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    """Calcula o valor do desconto dado um cupom e subtotal."""
    if subtotal < coupon.min_subtotal:
        return Decimal("0.00")

    if coupon.discount_type == "percentage":
        discount = (subtotal * coupon.discount_value) / Decimal("100.00")
        if coupon.max_discount_amount is not None and coupon.max_discount_amount > 0:
            discount = min(discount, coupon.max_discount_amount)
    else:  # "fixed"
        discount = coupon.discount_value

    discount = min(discount, subtotal)
    return discount.quantize(Decimal("0.01"))


@router.post("/validate", response_model=CouponValidateOut)
def validate_coupon(payload: CouponValidateIn, db: Session = Depends(get_db)):
    """Valida um código de cupom para preview no checkout do cliente."""
    clean_code = payload.code.strip().upper()
    coupon = db.query(Coupon).filter(Coupon.code == clean_code).first()

    if not coupon or not coupon.is_active:
        return CouponValidateOut(
            valid=False,
            code=clean_code,
            discount_amount=Decimal("0.00"),
            discount_type="none",
            discount_value=Decimal("0.00"),
            description=None,
            message="Cupom inválido ou inativo.",
        )

    now = datetime.now(timezone.utc)
    if coupon.valid_until is not None:
        valid_until_utc = coupon.valid_until
        if valid_until_utc.tzinfo is None:
            valid_until_utc = valid_until_utc.replace(tzinfo=timezone.utc)
        if now > valid_until_utc:
            return CouponValidateOut(
                valid=False,
                code=clean_code,
                discount_amount=Decimal("0.00"),
                discount_type=coupon.discount_type,
                discount_value=coupon.discount_value,
                description=coupon.description,
                message="Este cupom já expirou.",
            )

    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        return CouponValidateOut(
            valid=False,
            code=clean_code,
            discount_amount=Decimal("0.00"),
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            description=coupon.description,
            message="Limite de uso deste cupom atingido.",
        )

    if payload.subtotal < coupon.min_subtotal:
        return CouponValidateOut(
            valid=False,
            code=clean_code,
            discount_amount=Decimal("0.00"),
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            description=coupon.description,
            message=f"Subtotal mínimo de R$ {coupon.min_subtotal:.2f} necessário para aplicar este cupom.",
        )

    discount = calculate_coupon_discount(coupon, payload.subtotal)
    return CouponValidateOut(
        valid=True,
        code=coupon.code,
        discount_amount=discount,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        description=coupon.description,
        message="Cupom aplicado com sucesso!",
    )


@router.get("/admin-list", response_model=List[CouponOut])
def list_coupons_admin(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Listar todos os cupons cadastrados para o painel admin."""
    return db.query(Coupon).order_by(Coupon.id.desc()).all()


@router.get("/{coupon_id}", response_model=CouponOut)
def get_coupon_admin(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Obter detalhes de um cupom específico."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")
    return coupon


@router.post("", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
def create_coupon(
    payload: CouponCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Criar novo cupom de desconto (requer admin)."""
    clean_code = payload.code.strip().upper()
    existing = db.query(Coupon).filter(Coupon.code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um cupom cadastrado com este código.",
        )

    coupon = Coupon(
        code=clean_code,
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        min_subtotal=payload.min_subtotal,
        max_discount_amount=payload.max_discount_amount,
        max_uses=payload.max_uses,
        is_active=payload.is_active,
        valid_until=payload.valid_until,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.put("/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar cupom existente (requer admin)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")

    if payload.code is not None:
        clean_code = payload.code.strip().upper()
        if clean_code != coupon.code:
            existing = db.query(Coupon).filter(Coupon.code == clean_code).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe um cupom cadastrado com este código.",
                )
            coupon.code = clean_code

    if payload.description is not None:
        coupon.description = payload.description
    if payload.discount_type is not None:
        coupon.discount_type = payload.discount_type
    if payload.discount_value is not None:
        coupon.discount_value = payload.discount_value
    if payload.min_subtotal is not None:
        coupon.min_subtotal = payload.min_subtotal
    if payload.max_discount_amount is not None:
        coupon.max_discount_amount = payload.max_discount_amount
    if payload.max_uses is not None:
        coupon.max_uses = payload.max_uses
    if payload.is_active is not None:
        coupon.is_active = payload.is_active
    if payload.valid_until is not None:
        coupon.valid_until = payload.valid_until

    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/{coupon_id}/toggle-active", response_model=CouponOut)
def toggle_coupon_active(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar status de ativação do cupom (requer admin)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")
    coupon.is_active = not coupon.is_active
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir cupom de desconto (requer admin)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cupom não encontrado.")
    db.delete(coupon)
    db.commit()
    return None
