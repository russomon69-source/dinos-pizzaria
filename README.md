# 🦖 DINOS Pizzaria — Sistema Completo de Gestão e Cardápio Digital

> **"Pizzas as Legendary as the Dinos"**
> Sistema web de alta performance e segurança militar para pizzarias artesanais, composto por Cardápio Digital Interativo, Checkout com Cálculo Autônomo de Frete, Disparo Inteligente de Pedidos via WhatsApp (Evolution API v2 + Fallback `wa.me`) e Painel Administrativo em Tempo Real (Kanban & Gestão de Cardápio).

---

## 📋 Sumário

- [Visão Geral & Stack Tecnológica](#-visão-geral--stack-tecnológica)
- [Identidade Visual DINOS Dark & Neon](#-identidade-visual-dinos-dark--neon)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Instalação & Guia Rápido](#-instalação--guia-rápido)
- [Inicialização do Banco de Dados & Seeding](#-inicialização-do-banco-de-dados--seeding)
- [Dicionário de Variáveis de Ambiente (.env)](#-dicionário-de-variáveis-de-ambiente-env)
- [Estrutura de Diretórios](#-estrutura-de-diretórios)
- [Pilares de Segurança & Hardening (OWASP ASVS)](#-pilares-de-segurança--hardening-owasp-asvs)
- [Resiliência do WhatsApp (Dual-Path Failover)](#-resiliência-do-whatsapp-dual-path-failover)
- [Deploy em Produção (Linux / Nginx / Systemd)](#-deploy-em-produção-linux--nginx--systemd)
- [Suíte de Testes Automatizados](#-suíte-de-testes-automatizados)

---

## 🚀 Visão Geral & Stack Tecnológica

O sistema foi arquitetado como um **Monólito Modular Desacoplado** de altíssima eficiência e custo zero de build no frontend:

- **Backend:** Python 3.11+ / 3.12+, **FastAPI** (`0.115.0`), **Uvicorn** (`0.30.6`), **Pydantic v2** (`2.9.2`) com tipagem estrita e validação assíncrona.
- **Banco de Dados:** **SQLite3 em modo WAL (Write-Ahead Logging)** com SQLAlchemy 2.0 (`2.0.35`). Permite concorrência simultânea massiva com zero erros de `database is locked`.
- **Frontend Público (`/`):** Vanilla JavaScript ES6+ Modular (Zero-Build), HTML5 Semântico, CSS3 Moderno com CSS Grid, Flexbox e Tokens de Design.
- **Painel Administrativo SPA (`/admin`):** Single Page Application com autenticação JWT Bearer, quadro Kanban com drag/select de status, upload assíncrono de fotos com drag-and-drop e polling reativo (20s) com alertas sonoros (Web Audio API).
- **Processamento de Mídia:** **Pillow** (`10.4.0`) com conversão automática de imagens enviadas para `.webp` otimizado (< 150KB) e redimensionamento proporcional.
- **Mensageria & Notificações:** **HTTPX** assíncrono para integração com **Evolution API v2** e fallback autônomo para URLs `https://wa.me/...`.
- **Segurança & Criptografia:** **PyJWT**, **Bcrypt** (cost factor 12) e **SlowAPI** para rate limiting em endpoints críticos.

---

## 🎨 Identidade Visual DINOS Dark & Neon

Toda a interface do cliente e do painel administrativo segue a paleta proprietária **DINOS Dark & Neon**:

| Nome do Token | Valor Hexadecimal | Aplicação Principal |
| :--- | :--- | :--- |
| **Charred Black** | `#121212` | Fundo principal da aplicação (dark theme imersivo) |
| **Charred Card** | `#1A1A1A` | Superfície dos cards de produtos, modais e containers |
| **Neon Gold** | `#FFAE19` | Destaques primários, botões de ação, badges e preços |
| **Warm Clay** | `#B86B4B` | Bordas secundárias, badges de categoria e subtítulos |
| **Rustic Red** | `#B33927` | Botões de perigo, cancelamento e badges de promoção |
| **Off-White** | `#F9F6F0` | Tipografia principal de alta legibilidade |

---

## 🏗️ Arquitetura do Sistema

```
                   +-----------------------------------------------+
                   |              Nginx Reverse Proxy              |
                   +-----------------------------------------------+
                          /                        \
           Static Files  /                          \  /api/v1/*
                        v                            v
          +-------------------------+      +-------------------------+
          | Frontend (Zero-Build)   |      | FastAPI Backend Server  |
          | - Storefront: /         |      | - Auth (JWT & Bcrypt)   |
          | - Admin SPA: /admin     |      | - Orders Engine         |
          | - Uploads: /static/...  |      | - WhatsApp Service      |
          +-------------------------+      +-------------------------+
                                                         |
                                 +-----------------------+-----------------------+
                                 |                                               |
                                 v                                               v
                   +---------------------------+                   +---------------------------+
                   | SQLite WAL Database       |                   | WhatsApp Integration      |
                   | (Single Source of Truth)  |                   | 1. Evolution API v2       |
                   | - Authoritative Prices    |                   | 2. Fallback: wa.me Direct |
                   +---------------------------+                   +---------------------------+
```

---

## 📦 Instalação & Guia Rápido

### 1. Pré-requisitos
- Python 3.11 ou superior instalado
- Git (opcional para clonagem)

### 2. Clonar o Repositório e Criar Ambiente Virtual

```bash
# Navegar até o diretório do projeto
cd dinos-pizzaria

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux / macOS:
source .venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 4. Configurar Arquivo `.env`

Crie um arquivo `.env` na raiz do projeto (ou copie de um modelo) conforme detalhado na seção [Dicionário de Variáveis de Ambiente](#-dicionário-de-variáveis-de-ambiente-env).

---

## 🦖 Inicialização do Banco de Dados & Seeding

O sistema possui um **seeder idempotente e autônomo** (`backend/seed_data.py`) que:
1. Cria todas as 7 tabelas do banco de dados SQLite caso não existam;
2. Gera o usuário administrador padrão (`admin` / `dinos@admin123`);
3. Cadastra 5 categorias oficiais (Pizzas Salgadas, Pizzas Doces, Combos, Bebidas, Sobremesas);
4. Popula 12 produtos e 3 combos lendários com descrições temáticas e preços em BRL;
5. Cadastra 5 zonas de entrega com taxas e tempos estimados;
6. **Sintetiza automaticamente 15 imagens placeholder em formato `.webp` otimizado** na pasta `static/uploads/` utilizando a paleta DINOS.

Execute o comando:

```bash
# Executar a partir da raiz do projeto
python -m backend.seed_data
```

### 5. Iniciar o Servidor de Desenvolvimento

```bash
# Iniciar Uvicorn com hot-reload
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Cardápio Digital Público:** `http://127.0.0.1:8000/`
- **Painel Administrativo:** `http://127.0.0.1:8000/admin`
- **Documentação OpenAPI (Swagger UI):** `http://127.0.0.1:8000/docs`
- **Documentação ReDoc:** `http://127.0.0.1:8000/redoc`

---

## ⚙️ Dicionário de Variáveis de Ambiente (.env)

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | string | `"DINOS Pizzaria"` | Nome oficial da aplicação |
| `SECRET_KEY` | string | `"dinos-super-secret-production-key-change-me-min-32-chars"` | Chave simétrica para assinatura de tokens JWT (mínimo 32 caracteres) |
| `JWT_ALGORITHM` | string | `"HS256"` | Algoritmo de assinatura criptográfica do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `480` | Tempo de expiração do token de sessão do admin (8 horas) |
| `ADMIN_INITIAL_USERNAME` | string | `"admin"` | Nome de usuário padrão criado no primeiro startup |
| `ADMIN_INITIAL_PASSWORD` | string | `"dinos@admin123"` | Senha inicial do administrador (hasheada com bcrypt) |
| `DATABASE_URL` | string | `"sqlite:///./pizzaria.db"` | URI de conexão SQLAlchemy com SQLite WAL |
| `CORS_ORIGINS` | string | `"http://localhost:8000,http://127.0.0.1:8000"` | Origens permitidas separadas por vírgula |
| `EVOLUTION_API_URL` | string | `""` | URL base do gateway Evolution API v2 (ex: `https://api.evolution.io`) |
| `EVOLUTION_API_KEY` | string | `""` | Chave de autenticação (API Key / Global Token) da Evolution API |
| `EVOLUTION_INSTANCE_NAME` | string | `""` | Nome da instância do WhatsApp pareada na Evolution API |
| `WHATSAPP_PHONE_NUMBER` | string | `"5511999999999"` | Número oficial de atendimento com DDI + DDD (somente dígitos) |
| `MAX_UPLOAD_SIZE_MB` | int | `5` | Limite máximo para upload de imagens de produtos/combos |
| `UPLOAD_DIR` | string | `"static/uploads"` | Diretório no servidor para armazenamento das fotos WebP |
| `RATE_LIMIT_LOGIN` | string | `"5/minute"` | Limite de tentativas de login por IP contra ataques de força bruta |

---

## 📁 Estrutura de Diretórios

```
dinos-pizzaria/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Configurações Pydantic-Settings & leitura de .env
│   │   │   ├── database.py           # Engine SQLAlchemy, SessionLocal & PRAGMA WAL
│   │   │   └── security.py           # Bcrypt password hashing & PyJWT token utilities
│   │   ├── models/                   # Modelos ORM SQLAlchemy 2.0
│   │   │   ├── admin.py              # Modelo AdminUser
│   │   │   ├── category.py           # Modelo Category
│   │   │   ├── combo.py              # Modelo Combo
│   │   │   ├── delivery.py           # Modelo DeliveryZone
│   │   │   ├── order.py              # Modelos Order e OrderItem
│   │   │   └── product.py            # Modelo Product
│   │   ├── schemas/                  # Schemas de validação e serialização Pydantic v2
│   │   │   ├── auth.py               # Schemas de Login e Token
│   │   │   ├── category.py           # Schemas CRUD de Categorias
│   │   │   ├── combo.py              # Schemas CRUD de Combos
│   │   │   ├── delivery.py           # Schemas CRUD de Taxas de Entrega
│   │   │   ├── order.py              # Schemas de Pedidos (Guest Checkout & Admin)
│   │   │   └── product.py            # Schemas CRUD de Produtos
│   │   ├── services/                 # Regras de Negócio Puras
│   │   │   ├── image_service.py      # Magic-bytes validation, WebP resize e persistência
│   │   │   ├── order_service.py      # Recálculo autoritativo de valores (Zero-Tampering)
│   │   │   └── whatsapp_service.py   # Despacho Evolution API v2 e gerador de link wa.me
│   │   ├── api/                      # Rotas RESTful (/api/v1/*)
│   │   │   └── v1/
│   │   │       ├── auth.py           # Autenticação e /me
│   │   │       ├── categories.py     # Endpoints de categorias
│   │   │       ├── combos.py         # Endpoints de combos
│   │   │       ├── delivery.py       # Endpoints de taxas de entrega
│   │   │       ├── orders.py         # Endpoints de checkout e Kanban admin
│   │   │       ├── products.py       # Endpoints de produtos
│   │   │       └── uploads.py        # Endpoint de upload seguro de imagens
│   │   └── main.py                   # Ponto de entrada FastAPI, Lifespan e Static Mounts
│   ├── seed_data.py                  # Seeder autônomo e gerador de placeholders Pillow
│   ├── requirements.txt              # Dependências Python de produção e testes
│   ├── pytest.ini                    # Configuração do pytest e pytest-asyncio
│   └── tests/                        # 131 testes automatizados (Unit, E2E, Security)
├── frontend/
│   ├── public/                       # Storefront do Cliente
│   │   ├── index.html                # Landing page principal
│   │   ├── css/                      # Estilização modular DINOS Dark & Neon
│   │   │   ├── variables.css         # CSS Custom Properties & Cores
│   │   │   ├── typography.css        # Tipografia e espaçamentos
│   │   │   ├── layout.css            # Header, Hero, Grid de Produtos e Footer
│   │   │   ├── components.css        # Cards, Badges, Botões e Modais
│   │   │   └── cart.css              # Drawer lateral e Checkout
│   │   └── js/                       # Módulos JavaScript ES6
│   │       ├── api.js                # Cliente HTTP para API pública
│   │       ├── app.js                # Orquestrador de inicialização e eventos
│   │       ├── cart.js               # Gerenciador de estado do carrinho (LocalStorage)
│   │       ├── checkout.js           # Validação e submissão de pedidos
│   │       └── ui.js                 # Renderização reativa de catálogo e modais
│   └── admin/                        # Painel Administrativo SPA
│       ├── index.html                # Shell SPA do painel
│       ├── css/
│       │   ├── admin-theme.css       # Tema dark para administração
│       │   ├── admin-layout.css      # Sidebar fixa e container responsivo
│       │   └── admin-components.css  # Tabela, Kanban board e Modais
│       └── js/
│           ├── admin-api.js          # Cliente HTTP autenticado com Bearer Token
│           ├── admin-app.js          # Roteamento SPA e lifecycle
│           ├── admin-auth.js         # Controle de sessão e login
│           ├── admin-catalog.js      # CRUD de produtos e combos com dropzone
│           ├── admin-orders.js       # Monitor Kanban, drag-and-drop e polling
│           └── admin-zones.js        # Gestão de taxas de frete por bairro
├── static/
│   └── uploads/                      # Armazenamento local de imagens WebP (< 150KB)
├── .planning/                        # Documentação de Roadmap e Fases GSD
├── CLAUDE.md                         # Diretrizes de desenvolvimento e convenções
├── pizzaria.db                       # Banco de dados SQLite local
└── README.md                         # Guia de implantação e documentação completa
```

---

## 🛡️ Pilares de Segurança & Hardening (OWASP ASVS)

O DINOS Pizzaria foi projetado contra as principais ameaças do OWASP Top 10 e ASVS:

1. **Recálculo Autoritativo de Preços (Anti-Price Tampering - T-06-01):**
   - O cliente pode enviar qualquer valor de subtotal, taxa ou preço unitário no payload JSON; o `OrderCalculationService` ignora 100% dos valores enviados e busca os preços vigentes diretamente no banco de dados.
2. **Upload Seguro de Arquivos (Anti-Malware & Traversal - T-06-02 / T-06-03):**
   - Verificação rigorosa de **Magic Bytes** via Pillow (arquivos de script ou falsos JPEGs são rejeitados com HTTP 400).
   - Nomes de arquivo originais são descartados; cada imagem é salva com um **UUID4 aleatório** e extensão estrita `.webp`.
   - Redimensionamento automático limitando a largura/altura máxima a 1000px e compactação WebP com qualidade 85.
3. **Proteção contra SQL Injection (T-06-04):**
   - 100% das consultas utilizam ORM SQLAlchemy 2.0 com consultas tipadas e parâmetros blindados.
4. **Resiliência de Concorrência SQLite WAL (T-06-05):**
   - Configuração de `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;` e `PRAGMA synchronous=NORMAL;` permitindo múltiplos leitores e escritores simultâneos sem contenção de lock.
5. **Autenticação Segura & Hashing (T-06-06):**
   - Senhas criptografadas com **Bcrypt** (cost factor 12).
   - Tokens JWT com validação estrita de algoritmo (`HS256`), expiração (`exp`), data de emissão (`iat`) e sujeito (`sub`).
6. **Proteção contra Força Bruta (Rate Limiting - T-06-07):**
   - Endpoint `/api/v1/auth/login` protegido por SlowAPI (máximo de 5 requisições por minuto por IP antes de retornar HTTP 429 Too Many Requests).

---

## 📲 Resiliência do WhatsApp (Dual-Path Failover)

O sistema possui uma arquitetura de disparo de pedidos em duas camadas sem ponto único de falha:

```
                  [ Pedido Criado no Backend ]
                               |
                               v
               +-------------------------------+
               | A Evolution API está ativa e  |
               | configurada com credenciais?  |
               +-------------------------------+
                       /               \
                SIM   /                 \  NÃO (ou timeout >3.0s / erro 500)
                     v                   v
        +-------------------------+  +-------------------------------+
        | Disparo Automático via  |  | Gera URL Formatada no Padrão  |
        | HTTPX AsyncClient       |  | https://wa.me/5511...         |
        +-------------------------+  +-------------------------------+
                     |                               |
                     v                               v
             Status: `sent`             Status: `fallback_generated`
                                                     |
                                                     v
                                     [ Cliente clica no botão do modal ]
```

### Formato da Mensagem Gerada (WhatsApp Markdown):

```text
*🦖 DINOS PIZZARIA - NOVO PEDIDO #42 🍕*
----------------------------------------
*Cliente:* Dr. Alan Grant
*Telefone:* (11) 98765-4321
*Tipo:* 🛵 Entrega (Delivery)
*Endereço:* Alameda dos Dinossauros, 100
*Ponto de Referência:* Portão 3

*ITENS DO PEDIDO:*
1. 1x Pizza T-Rex Suprema - R$ 68.90
   _Obs: Sem cebola, massa crocante_
2. 1x Refrigerante Dinos 2L - R$ 12.00

----------------------------------------
*Subtotal:* R$ 80.90
*Taxa de Entrega:* R$ 8.50
*Total:* R$ 89.40
*Forma de Pagamento:* Dinheiro
*Troco para:* R$ 100.00 (Levar de troco: R$ 10.60)
*Observações:* Cuidado com os velociraptors no portão.
```

---

## 🌐 Deploy em Produção (Linux / Nginx / Systemd)

### 1. Serviço Systemd (`/etc/systemd/system/dinos-pizzaria.service`)

```ini
[Unit]
Description=DINOS Pizzaria FastAPI Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/dinos-pizzaria
EnvironmentFile=/var/www/dinos-pizzaria/.env
ExecStart=/var/www/dinos-pizzaria/.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 4

Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Ativar e iniciar o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dinos-pizzaria
sudo systemctl start dinos-pizzaria
```

### 2. Configuração Nginx (`/etc/nginx/sites-available/dinos-pizzaria`)

```nginx
server {
    listen 80;
    server_name dinospizzaria.com.br www.dinospizzaria.com.br;

    # Redirecionamento HTTP para HTTPS (com Certbot)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dinospizzaria.com.br www.dinospizzaria.com.br;

    # Certificados SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/dinospizzaria.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dinospizzaria.com.br/privkey.pem;

    client_max_body_size 10M;
    root /var/www/dinos-pizzaria;

    # 1. Arquivos estáticos de upload (com cache longo)
    location /static/uploads/ {
        alias /var/www/dinos-pizzaria/static/uploads/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        try_files $uri =404;
    }

    # 2. Painel Administrativo SPA
    location /admin {
        alias /var/www/dinos-pizzaria/frontend/admin;
        index index.html;
        try_files $uri $uri/ /admin/index.html;
    }

    # 3. Frontend Público Storefront
    location / {
        root /var/www/dinos-pizzaria/frontend/public;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 4. Proxy Reverso da API REST FastAPI
    location ~ ^/(api|docs|openapi.json|redoc) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

### 3. Estratégia de Backup do Banco de Dados SQLite WAL

Para efetuar backups consistentes do SQLite em produção sem interromper leituras ou escritas:

```bash
# Script de backup seguro com SQLite .backup
sqlite3 /var/www/dinos-pizzaria/pizzaria.db ".backup '/var/backups/pizzaria_$(date +\%Y\%m\%d_\%H\%M\%S).db'"
```

---

## 🧪 Suíte de Testes Automatizados

O sistema possui uma suíte com **131 testes automatizados** cobrindo 100% dos requisitos de negócio e ameaças de segurança.

### Executar Toda a Suíte de Testes:

```bash
# Executar todos os testes com saída detalhada
pytest backend/tests/ -v
```

### Executar Testes Específicos:

```bash
# 1. Testes de Integração E2E (Fluxo de Compra e Kanban)
pytest backend/tests/test_e2e_integration.py -v

# 2. Testes de Resiliência e Failover do WhatsApp
pytest backend/tests/test_whatsapp_resilience.py -v

# 3. Testes de Auditoria de Segurança e Penetração ASVS
pytest backend/tests/test_security_audit.py -v

# 4. Testes de Estresse e Concorrência SQLite WAL
pytest backend/tests/test_sqlite_concurrency.py -v
```

---

## 🦖 Licença

Projeto desenvolvido sob medida para a **DINOS Pizzaria**. Todos os direitos reservados.
"Sabor lendário forjado no calor do fogo artesanal!" 🍕🔥
