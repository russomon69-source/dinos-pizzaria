from typing import Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.models.site_content import SiteContent
from app.schemas.site_content import SiteContentOut, SiteContentUpdate

router = APIRouter(prefix="/site-content", tags=["Site Content"])

DEFAULT_SITE_CONTENT: Dict[str, str] = {
    "top_banner_enabled": "true",
    "top_banner_text": "🔥 Terça Jurássica: Cupom DINOS10 com 10% OFF em pedidos acima de R$ 60!",
    "top_banner_cta": "Ver Cardápio",
    "top_banner_link": "#cardapio",
    "store_is_open": "true",
    "store_closed_message": "No momento nossa cozinha está fechada para pedidos imediatos. Você pode agendar seu pedido para o horário de atendimento!",
    "featured_section_title": "🦖 Mais Pedidas da DINOS",
    "featured_section_subtitle": "As pizzas favoritas dos nossos clientes forjadas no fogo lendário",
    "reviews_section_title": "⭐ O que dizem os amantes de DINOS",
    "reviews_section_subtitle": "Depoimentos reais de quem já experimentou nossas receitas lendárias",
    "brand_tagline": "— Pizzas as Legendary as the Dinos",
    "header_status": "Forno a Lenha Aceso",
    "hero_badge": "Forno artesanal aceso • Pedido direto no WhatsApp",
    "hero_title": "Pizza artesanal forjada no fogo lendário",
    "hero_highlight": "forjada no fogo lendário",
    "hero_subtitle": "Massa de longa fermentação, borda tostada no forno de alta temperatura e sabores jurássicos criados para chegar quentinhos no seu pedido.",
    "hero_primary_cta": "Ver cardápio e pedir",
    "hero_secondary_cta": "🔥 Ver combos de hoje",
    "hero_signature": "Pizzas as Legendary as the Dinos",
    "highlight_1": "Forno a lenha 450°C",
    "highlight_2": "Fermentação lenta 48h",
    "highlight_3": "Molho pelati",
    "highlight_4": "Entrega 35–45 min",
    "highlight_5": "Pedido no WhatsApp",
    "trust_1_title": "Forno no ponto",
    "trust_1_text": "Calor alto para borda tostada, massa leve e queijo borbulhando.",
    "trust_2_title": "Combos lendários",
    "trust_2_text": "Promoções jurássicas pensadas para dividir ou matar a fome sozinho.",
    "trust_3_title": "Entrega calculada",
    "trust_3_text": "Escolha seu bairro e veja o total antes de enviar o pedido.",
    "trust_4_title": "Finaliza no WhatsApp",
    "trust_4_text": "Checkout rápido e confirmação direta com a cozinha da DINOS.",
    "menu_search_placeholder": "Buscar pizza, combo ou ingrediente...",
    "menu_filter_all": "Todos",
    "menu_filter_promos": "Promoções",
    "menu_filter_combos": "Combos",
    "footer_brand_desc": "Pizzas artesanais com sabor da era jurássica. Ingredientes nobres selecionados, fermentação lenta de 48 horas e cocção em forno em altíssima temperatura.",
    "footer_badge": "🦖 Tradição & Fogo",
    "footer_hours_title": "⏰ Horários",
    "footer_hours_1": "Terça a Quinta: 18:00 às 23:30",
    "footer_hours_2": "Sexta e Sábado: 18:00 às 00:30",
    "footer_hours_3": "Domingo: 18:00 às 23:30",
    "footer_hours_closed": "Segunda-feira: Fechado para descanso da equipe",
    "footer_payment_title": "💳 Pagamento",
    "footer_payment_text": "Aceitamos diversas formas de pagamento no checkout e na entrega:",
    "footer_delivery_title": "🛵 Raio de Entrega:",
    "footer_delivery_text": "Entrega rápida com taxa calculada por bairro.",
    "footer_contact_title": "📲 Atendimento",
    "footer_contact_text": "Faça seu pedido diretamente pelo site ou tire dúvidas com nossos pizzaiolos:",
    "footer_whatsapp_button": "💬 WhatsApp Direto",
    "footer_location_text": "📍 Atendimento para pedidos online e balcão.",
    "footer_bottom_text": "© 2026 DINOS Pizzaria. Todos os direitos reservados.",
    "footer_slogan": "🦖 Pizzas as Legendary as the Dinos 🍕",
}


def _ensure_defaults(db: Session) -> None:
    existing_keys = {row[0] for row in db.query(SiteContent.key).all()}
    missing = [
        SiteContent(key=key, value=value)
        for key, value in DEFAULT_SITE_CONTENT.items()
        if key not in existing_keys
    ]
    if missing:
        db.add_all(missing)
        db.commit()


@router.get("", response_model=List[SiteContentOut])
def list_site_content(db: Session = Depends(get_db)):
    """Listar textos públicos editáveis da landing page."""
    _ensure_defaults(db)
    return db.query(SiteContent).order_by(SiteContent.key.asc()).all()


@router.put("", response_model=List[SiteContentOut])
def update_site_content(
    payload: SiteContentUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Atualizar textos da landing page exibidos aos clientes."""
    _ensure_defaults(db)
    allowed_keys = set(DEFAULT_SITE_CONTENT.keys())

    for item in payload.items:
        if item.key not in allowed_keys:
            continue
        row = db.query(SiteContent).filter(SiteContent.key == item.key).first()
        if row:
            row.value = item.value.strip()
        else:
            db.add(SiteContent(key=item.key, value=item.value.strip()))

    db.commit()
    return db.query(SiteContent).order_by(SiteContent.key.asc()).all()
