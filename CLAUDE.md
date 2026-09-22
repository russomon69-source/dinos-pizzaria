# DINOS Pizzaria — Guidelines & Context

<!-- GSD:project-start source:PROJECT.md -->
## Project

**DINOS Pizzaria — Landing Page + Carrinho + Painel Admin**
Um sistema web completo para a **DINOS Pizzaria** ("Pizzas as Legendary as the Dinos"), composto por uma landing page pública moderna com cardápio dinâmico, combos e promoções em destaque, carrinho interativo de compras, checkout com cálculo automático de taxa de entrega e disparo de pedidos diretamente para o WhatsApp da loja (via Evolution API v2 com fallback para `wa.me`). Inclui também um painel administrativo seguro (com autenticação JWT e senhas em bcrypt) para gestão de produtos, upload de fotos WebP, combos, promoções e taxas de entrega por bairro.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

- **Backend:** Python 3.11+, FastAPI (`^0.115.0`), Uvicorn (`^0.30.6`), Pydantic v2 & Pydantic-Settings (`^2.5.2`)
- **Database:** SQLite3 em modo Write-Ahead Logging (WAL) com SQLAlchemy 2.0 (`^2.0.35`)
- **Frontend:** Vanilla JavaScript ES6+ (Zero-Build Modules), HTML5 semântico, CSS3 moderno com CSS Custom Properties (Design System DINOS Dark & Neon)
- **Segurança & Auth:** PyJWT (`^2.9.0`), Passlib com Bcrypt (`^4.2.0`), SlowAPI (`^0.1.9`) para rate limiting
- **Processamento de Mídia:** Pillow (`^10.4.0`) e Python-Multipart (`^0.0.12`) com conversão para `.webp` e UUIDs
- **Mensageria:** HTTPX (`^0.27.2`) assíncrono para Evolution API v2 com fallback para URLs `wa.me`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- **Identidade Visual:** Paleta oficial DINOS Dark & Neon: Charred Black (`#121212`), Neon Gold (`#FFAE19`), Warm Clay (`#B86B4B`), Rustic Red (`#B33927`).
- **Validação de Preços:** O frontend calcula para feedback visual em tempo real, mas o backend recalcula 100% dos subtotais e taxas de entrega a partir do banco de dados (Single Source of Truth).
- **SQLite Concorrência:** Conexões sempre configuradas com `PRAGMA journal_mode=WAL;` e `PRAGMA busy_timeout=5000;`.
- **Segurança de Upload:** Imagens validadas por magic-bytes, redimensionadas para max 1000px, convertidas para WebP (< 150KB) e salvas com nomes UUID aleatórios.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Decoupled Modular Monolith:
- `backend/app/`: FastAPI REST API, modelos ORM SQLAlchemy, schemas Pydantic v2, serviços de negócio (`OrderCalculationService`, `WhatsAppService`, `ImageService`) e rotas `/api/v1/*`.
- `frontend/public/`: Aplicação pública do cliente (Landing page, cardápio dinâmico, carrinho, frete e checkout guest).
- `frontend/admin/`: Painel administrativo SPA protegido por JWT para gestão de cardápio, combos, taxas de frete e pedidos.
- `static/uploads/`: Armazenamento local de fotos dos produtos em formato WebP otimizado.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to `.claude/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->
