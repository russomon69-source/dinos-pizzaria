from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.delivery import DeliveryZone
from app.schemas.delivery import DeliveryZoneCreate, DeliveryZoneOut, DeliveryZoneUpdate

router = APIRouter(prefix="/delivery-zones", tags=["Delivery Zones"])


@router.get("", response_model=List[DeliveryZoneOut])
def list_delivery_zones(
    active_only: bool = Query(True, description="Filtrar apenas zonas ativas"),
    db: Session = Depends(get_db),
):
    """Listar zonas de entrega ativas e taxas de frete por bairro."""
    query = db.query(DeliveryZone)
    if active_only:
        query = query.filter(DeliveryZone.is_active == True)  # noqa: E712
    return query.order_by(DeliveryZone.name.asc()).all()


@router.get("/admin-list", response_model=List[DeliveryZoneOut])
def list_all_delivery_zones_admin(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Listar todas as zonas de entrega cadastradas para gestão de taxas."""
    return db.query(DeliveryZone).order_by(DeliveryZone.name.asc()).all()


@router.get("/{zone_id}", response_model=DeliveryZoneOut)
def get_delivery_zone(zone_id: int, db: Session = Depends(get_db)):
    """Obter taxa e prazo estimado de uma zona de entrega específica."""
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de entrega não encontrada.",
        )
    return zone


@router.post("", response_model=DeliveryZoneOut, status_code=status.HTTP_201_CREATED)
def create_delivery_zone(
    zone_in: DeliveryZoneCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Cadastrar novo bairro ou zona de entrega com respectiva taxa (requer autenticação de administrador)."""
    existing = db.query(DeliveryZone).filter(DeliveryZone.name == zone_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma zona de entrega cadastrada com este nome.",
        )

    zone = DeliveryZone(
        name=zone_in.name,
        fee=zone_in.fee,
        min_order_value=zone_in.min_order_value,
        estimated_minutes=zone_in.estimated_minutes,
        is_active=zone_in.is_active,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/{zone_id}", response_model=DeliveryZoneOut)
def update_delivery_zone(
    zone_id: int,
    zone_in: DeliveryZoneUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar dados ou valor de taxa de uma zona de entrega (requer autenticação de administrador)."""
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de entrega não encontrada.",
        )

    if zone_in.name is not None and zone_in.name != zone.name:
        if db.query(DeliveryZone).filter(DeliveryZone.name == zone_in.name).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma zona de entrega cadastrada com este nome.",
            )
        zone.name = zone_in.name

    if zone_in.fee is not None:
        zone.fee = zone_in.fee
    if zone_in.min_order_value is not None:
        zone.min_order_value = zone_in.min_order_value
    if zone_in.estimated_minutes is not None:
        zone.estimated_minutes = zone_in.estimated_minutes
    if zone_in.is_active is not None:
        zone.is_active = zone_in.is_active

    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/{zone_id}/toggle-active", response_model=DeliveryZoneOut)
def toggle_delivery_zone_active(
    zone_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Alternar status de ativação da zona de entrega (requer autenticação de administrador)."""
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de entrega não encontrada.",
        )
    zone.is_active = not zone.is_active
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Excluir uma zona de entrega (requer autenticação de administrador)."""
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de entrega não encontrada.",
        )
    db.delete(zone)
    db.commit()
    return None
