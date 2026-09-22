/**
 * DINOS Pizzaria — Customer Storefront Main Application Entry Point (ES6 Module)
 * Orchestrates catalog rendering, hero promos section, sticky category navigation, item modals, and cart drawer.
 */

import { api } from './api.js';
import { cart } from './cart.js';
import { initCheckout } from './checkout.js';
import {
  formatCurrency,
  escapeHtml,
  showToast,
  openItemModal,
  closeItemModal,
  initItemModalListeners,
  setPizzaFlavorCatalog,
  renderCartDrawer,
  initCartDrawerListeners,
  initSuccessModalListeners,
  toggleCartDrawer
} from './ui.js';

/**
 * Placeholder SVG for products without images or failed image loading.
 */
const FALLBACK_IMAGE_SVG =
  'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250"><rect fill="%231a1a1a" width="400" height="250"/><text fill="%23FFAE19" font-family="sans-serif" font-size="24" font-weight="bold" x="50%" y="45%" text-anchor="middle">🦖 DINOS PIZZARIA</text><text fill="%238E8E8E" font-family="sans-serif" font-size="14" x="50%" y="60%" text-anchor="middle">Pizzas as Legendary as the Dinos</text></svg>';

/**
 * Global App State cache
 */
const state = {
  categories: [],
  products: [],
  combos: [],
  promoCombos: [],
  searchTerm: '',
  activeFilter: 'all'
};

/**
 * Render the Hero Promos section with featured combos and promotions of the day (D-01, PROMO-01).
 * @param {Array<Object>} promosList
 */
function renderHeroPromos(promosList) {
  const container = document.getElementById('hero-promos-grid');
  if (!container) return;

  if (!promosList || promosList.length === 0) {
    // If no promo combos, try regular active combos or hide hero grid
    if (state.combos && state.combos.length > 0) {
      promosList = state.combos.slice(0, 3);
    } else {
      const heroSection = document.getElementById('hero-promos');
      if (heroSection) heroSection.style.display = 'none';
      return;
    }
  }

  container.innerHTML = '';
  promosList.forEach((combo) => {
    const card = document.createElement('div');
    card.className = 'promo-card';
    const comboTitle = combo.name || combo.title || 'Combo DINOS';
    card.dataset.searchText = `${comboTitle || ''} ${combo.description || ''}`.toLowerCase();
    card.dataset.filterType = 'combo';

    const badgeLabel = combo.is_promo_of_day ? '🔥 PROMOÇÃO DO DIA' : '🦖 COMBO ESPECIAL';
    const comboPrice = Number(combo.price) || 0;
    const imageUrl = combo.image_url || FALLBACK_IMAGE_SVG;

    card.innerHTML = `
      <div class="promo-badge-tag badge-neon-gold" style="background: var(--color-rustic-red); color: #fff; font-family: var(--font-display); font-size: 0.75rem; font-weight: 800; padding: 4px 10px; border-radius: var(--radius-full); box-shadow: var(--shadow-neon-red);">
        ${badgeLabel}
      </div>
      <img src="${imageUrl}" alt="${escapeHtml(comboTitle)}" class="promo-card-image" loading="lazy">
      <div class="promo-card-body">
        <h3 class="promo-card-title">${escapeHtml(comboTitle)}</h3>
        <p class="promo-card-desc">${escapeHtml(combo.description || 'Combo lendário com ingredientes selecionados.')}</p>
        <div class="promo-card-footer">
          <span class="promo-price">${formatCurrency(comboPrice)}</span>
          <button type="button" class="btn btn-primary btn-sm btn-order-combo" aria-label="Pedir combo ${escapeHtml(comboTitle)}">
            Pedir Combo
          </button>
        </div>
      </div>
    `;

    // Fallback on image error
    const imgEl = card.querySelector('.promo-card-image');
    if (imgEl) {
      imgEl.onerror = () => {
        imgEl.src = FALLBACK_IMAGE_SVG;
      };
    }

    // Quick action trigger modal
    const orderBtn = card.querySelector('.btn-order-combo');
    if (orderBtn) {
      orderBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openItemModal(combo);
      });
    }

    // Clicking card opens modal
    card.addEventListener('click', () => {
      openItemModal(combo);
    });

    container.appendChild(card);
  });
}

/**
 * Render sticky category tabs (D-02, MENU-01).
 * @param {Array<Object>} categories
 */
function renderCategoryTabs(categories) {
  const tabsContainer = document.getElementById('category-tabs-container');
  if (!tabsContainer) return;

  tabsContainer.innerHTML = '';
  categories.forEach((category, idx) => {
    const tabBtn = document.createElement('button');
    tabBtn.type = 'button';
    tabBtn.className = `category-tab ${idx === 0 ? 'active' : ''}`;
    tabBtn.setAttribute('data-target', `category-sec-${category.id}`);
    tabBtn.setAttribute('role', 'tab');
    tabBtn.setAttribute('aria-selected', idx === 0 ? 'true' : 'false');

    const icon = category.icon || '🍕';
    tabBtn.innerHTML = `<span>${icon}</span> <span>${escapeHtml(category.name)}</span>`;

    tabsContainer.appendChild(tabBtn);
  });
}

/**
 * Setup smooth scrolling and active tab tracking with IntersectionObserver (D-02).
 */
export function setupCategoryNavigation() {
  const tabs = document.querySelectorAll('.category-tab');
  const sections = document.querySelectorAll('.menu-category-section');

  tabs.forEach((tab) => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = tab.getAttribute('data-target');
      const targetSection = document.getElementById(targetId);

      if (targetSection) {
        // Calculate offset position accounting for sticky header + category bar
        const header = document.getElementById('site-header');
        const nav = document.getElementById('category-nav');
        const headerOffset = (header ? header.offsetHeight : 60) + (nav ? nav.offsetHeight : 50) + 10;

        const bodyRect = document.body.getBoundingClientRect().top;
        const elementRect = targetSection.getBoundingClientRect().top;
        const elementPosition = elementRect - bodyRect;
        const offsetPosition = elementPosition - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });

        // Update active tab styling immediately for responsive click feedback
        tabs.forEach((t) => {
          const isActive = t === tab;
          t.classList.toggle('active', isActive);
          t.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
      }
    });
  });

  // IntersectionObserver to auto-highlight category tab on scroll
  if ('IntersectionObserver' in window && sections.length > 0) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            tabs.forEach((tab) => {
              const matches = tab.getAttribute('data-target') === id;
              tab.classList.toggle('active', matches);
              tab.setAttribute('aria-selected', matches ? 'true' : 'false');

              if (matches) {
                // Ensure active tab is visible inside scrollable container
                tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
              }
            });
          }
        });
      },
      {
        rootMargin: '-120px 0px -60% 0px',
        threshold: 0.1
      }
    );

    sections.forEach((section) => observer.observe(section));
  }
}

/**
 * Render product sections grouped by category (MENU-01, D-03).
 * @param {Array<Object>} categories
 * @param {Array<Object>} products
 */
function renderMenuCatalog(categories, products) {
  const wrapper = document.getElementById('menu-sections-wrapper');
  if (!wrapper) return;

  wrapper.innerHTML = '';

  categories.forEach((category) => {
    // Filter products belonging to this category
    const categoryProducts = products.filter((p) => p.category_id === category.id);
    if (categoryProducts.length === 0) return; // Skip empty categories

    const section = document.createElement('section');
    section.className = 'menu-category-section';
    section.id = `category-sec-${category.id}`;

    const icon = category.icon || '🍕';
    section.innerHTML = `
      <div class="category-header">
        <h2 class="category-title">
          <span>${icon}</span> ${escapeHtml(category.name)}
        </h2>
        ${category.description ? `<p style="font-size: 0.85rem; color: var(--color-text-muted); margin-top: 4px;">${escapeHtml(category.description)}</p>` : ''}
      </div>
      <div class="products-grid"></div>
    `;

    const grid = section.querySelector('.products-grid');

    categoryProducts.forEach((product) => {
      const card = document.createElement('div');
      card.className = 'product-card';
      const productTitle = product.name || product.title || 'Pizza DINOS';
      card.dataset.searchText = `${productTitle || ''} ${product.description || ''} ${category.name || ''}`.toLowerCase();
      card.dataset.filterType = product.is_promo && product.promo_price ? 'promo' : 'product';

      const hasPromo = product.is_promo && product.promo_price;
      const displayPrice = hasPromo ? Number(product.promo_price) : Number(product.price);
      const originalPrice = hasPromo ? Number(product.price) : null;
      const imageUrl = product.image_url || FALLBACK_IMAGE_SVG;

      const promoBadge = hasPromo
        ? `<span class="product-promo-badge" style="position: absolute; top: 12px; left: 12px; z-index: 2; background: var(--color-rustic-red); color: #FFFFFF; font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: var(--radius-full); box-shadow: var(--shadow-neon-red);">🔥 OFERTA</span>`
        : '';

      const priceHtml = hasPromo
        ? `<div>
             <span class="product-card-price">${formatCurrency(displayPrice)}</span>
             <span style="font-size: 0.8rem; text-decoration: line-through; color: var(--color-text-muted); margin-left: 6px;">${formatCurrency(originalPrice)}</span>
           </div>`
        : `<span class="product-card-price">${formatCurrency(displayPrice)}</span>`;

      card.innerHTML = `
        <div class="product-card-image-wrap">
          ${promoBadge}
          <img src="${imageUrl}" alt="${escapeHtml(productTitle)}" class="product-card-image" loading="lazy">
        </div>
        <div class="product-card-body">
          <h3 class="product-card-title">${escapeHtml(productTitle)}</h3>
          <p class="product-card-desc">${escapeHtml(product.description || 'Ingredientes selecionados da cozinha jurássica.')}</p>
          <div class="product-card-footer">
            ${priceHtml}
            <button type="button" class="btn-add-item" aria-label="Adicionar ${escapeHtml(productTitle)} ao pedido">
              + Adicionar
            </button>
          </div>
        </div>
      `;

      // Fallback image error handler
      const imgEl = card.querySelector('.product-card-image');
      if (imgEl) {
        imgEl.onerror = () => {
          imgEl.src = FALLBACK_IMAGE_SVG;
        };
      }

      // Add button click opens customization modal (D-03)
      const addBtn = card.querySelector('.btn-add-item');
      if (addBtn) {
        addBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          openItemModal(product);
        });
      }

      // Clicking entire card opens customization modal
      card.addEventListener('click', () => {
        openItemModal(product);
      });

      grid.appendChild(card);
    });

    wrapper.appendChild(section);
  });
}

/**
 * Display loading skeleton placeholders while fetching data.
 */
function renderSkeletons() {
  const heroGrid = document.getElementById('hero-promos-grid');
  if (heroGrid) {
    heroGrid.innerHTML = `
      <div class="skeleton-card skeleton-hero" aria-label="Carregando combos lendários"></div>
      <div class="skeleton-card skeleton-hero" aria-label="Carregando combos lendários"></div>
      <div class="skeleton-card skeleton-hero" aria-label="Carregando combos lendários"></div>
    `;
  }

  const menuWrapper = document.getElementById('menu-sections-wrapper');
  if (menuWrapper) {
    menuWrapper.innerHTML = `
      <div class="products-grid" aria-label="Carregando cardápio">
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
      </div>
    `;
  }
}

/**
 * Display error state when API fails to load.
 * @param {Error} error
 */
function renderApiError(error) {
  const menuWrapper = document.getElementById('menu-sections-wrapper');
  if (menuWrapper) {
    menuWrapper.innerHTML = `
      <div style="text-align: center; padding: var(--space-2xl) var(--space-md); background: var(--color-bg-card); border-radius: var(--radius-lg); border: 1px solid var(--color-rustic-red);">
        <div style="font-size: 3rem; margin-bottom: var(--space-sm);">⚠️🦖</div>
        <h3 style="color: var(--color-text-primary); margin-bottom: var(--space-xs);">Cardápio Temporariamente Indisponível</h3>
        <p style="color: var(--color-text-secondary); max-width: 500px; margin: 0 auto var(--space-md);">
          Não foi possível carregar as pizzas no momento. Verifique sua conexão ou tente novamente em instantes.
        </p>
        <button type="button" class="btn btn-primary" id="btn-retry-catalog">
          🔄 Tentar Novamente
        </button>
      </div>
    `;

    const retryBtn = document.getElementById('btn-retry-catalog');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        window.location.reload();
      });
    }
  }
}

function initHeroEmbers() {
  const container = document.getElementById('hero-embers');
  if (!container || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  container.innerHTML = '';
  const emberCount = 34;
  for (let i = 0; i < emberCount; i += 1) {
    const ember = document.createElement('span');
    ember.className = 'hero-ember';
    ember.style.setProperty('--ember-left', `${Math.random() * 100}%`);
    ember.style.setProperty('--ember-size', `${3 + Math.random() * 6}px`);
    ember.style.setProperty('--ember-drift', `${-45 + Math.random() * 90}px`);
    ember.style.setProperty('--ember-duration', `${4.8 + Math.random() * 5.4}s`);
    ember.style.setProperty('--ember-delay', `${Math.random() * 6}s`);
    container.appendChild(ember);
  }
}

function applyMenuFilters() {
  const term = state.searchTerm.trim().toLowerCase();
  const activeFilter = state.activeFilter;
  let visibleProducts = 0;
  let visiblePromos = 0;

  document.querySelectorAll('.product-card').forEach((card) => {
    const matchesSearch = !term || (card.dataset.searchText || '').includes(term);
    const matchesFilter =
      activeFilter === 'all' ||
      (activeFilter === 'promos' && card.dataset.filterType === 'promo') ||
      (activeFilter === 'combos' && card.dataset.filterType === 'combo');
    const isVisible = matchesSearch && matchesFilter;
    card.classList.toggle('is-filter-hidden', !isVisible);
    if (isVisible) visibleProducts += 1;
  });

  document.querySelectorAll('.promo-card').forEach((card) => {
    const matchesSearch = !term || (card.dataset.searchText || '').includes(term);
    const matchesFilter = activeFilter === 'all' || activeFilter === 'promos' || activeFilter === 'combos';
    const isVisible = matchesSearch && matchesFilter;
    card.classList.toggle('is-filter-hidden', !isVisible);
    if (isVisible) visiblePromos += 1;
  });

  document.querySelectorAll('.menu-category-section').forEach((section) => {
    const visibleCards = section.querySelectorAll('.product-card:not(.is-filter-hidden)').length;
    section.classList.toggle('is-filter-hidden', visibleCards === 0);
  });

  renderMenuNoResults(visibleProducts + visiblePromos === 0);
}

function renderMenuNoResults(show) {
  const wrapper = document.getElementById('menu-sections-wrapper');
  if (!wrapper) return;

  let empty = document.getElementById('menu-no-results');
  if (!empty) {
    empty = document.createElement('div');
    empty.id = 'menu-no-results';
    empty.className = 'menu-no-results';
    empty.innerHTML = '<strong>Nenhum sabor encontrado</strong><span>Tente buscar por outro ingrediente ou volte para “Todos”.</span>';
    wrapper.appendChild(empty);
  }
  empty.classList.toggle('d-none', !show);
}

function applySiteContent(items = []) {
  const content = Object.fromEntries((items || []).map((item) => [item.key, item.value]));
  const setText = (selector, value) => {
    const el = document.querySelector(selector);
    if (el && value) el.textContent = value;
  };

  setText('.brand-tagline', content.brand_tagline);
  setText('.header-status-badge span:last-child', content.header_status);
  setText('.hero-tag-badge', content.hero_badge);
  setText('.hero-subtitle', content.hero_subtitle);
  setText('.hero-cta-main', content.hero_primary_cta);
  setText('.hero-cta-secondary', content.hero_secondary_cta);
  setText('.hero-brand-signature', content.hero_signature);

  if (content.hero_title) {
    const titleEl = document.querySelector('.hero-title');
    if (titleEl) {
      const highlight = content.hero_highlight || '';
      if (highlight && content.hero_title.includes(highlight)) {
        titleEl.innerHTML = `${escapeHtml(content.hero_title.replace(highlight, '').trim())} <span>${escapeHtml(highlight)}</span>`;
      } else {
        titleEl.textContent = content.hero_title;
      }
    }
  }

  document.querySelectorAll('.highlight-pill span:last-child').forEach((el, index) => {
    const value = content[`highlight_${index + 1}`];
    if (value) el.textContent = value;
  });

  for (let i = 1; i <= 4; i += 1) {
    setText(`.conversion-card:nth-child(${i}) h3`, content[`trust_${i}_title`]);
    setText(`.conversion-card:nth-child(${i}) p`, content[`trust_${i}_text`]);
  }

  const searchInput = document.getElementById('menu-search-input');
  if (searchInput && content.menu_search_placeholder) searchInput.placeholder = content.menu_search_placeholder;
  setText('.menu-filter-chip[data-filter="all"]', content.menu_filter_all);
  setText('.menu-filter-chip[data-filter="promos"]', content.menu_filter_promos);
  setText('.menu-filter-chip[data-filter="combos"]', content.menu_filter_combos);

  setText('.footer-brand-desc', content.footer_brand_desc);
  setText('.footer-brand .badge-gold', content.footer_badge);
  setText('.site-footer .footer-grid > div:nth-child(2) .footer-col-title', content.footer_hours_title);
  setText('.site-footer .footer-grid > div:nth-child(2) .footer-info-item:nth-of-type(1)', content.footer_hours_1);
  setText('.site-footer .footer-grid > div:nth-child(2) .footer-info-item:nth-of-type(2)', content.footer_hours_2);
  setText('.site-footer .footer-grid > div:nth-child(2) .footer-info-item:nth-of-type(3)', content.footer_hours_3);
  setText('.site-footer .footer-grid > div:nth-child(2) .footer-info-item:nth-of-type(4)', content.footer_hours_closed);
  setText('.site-footer .footer-grid > div:nth-child(3) .footer-col-title', content.footer_payment_title);
  setText('.site-footer .footer-grid > div:nth-child(3) > p', content.footer_payment_text);
  setText('.site-footer .footer-grid > div:nth-child(3) > div[style*="margin-top"] strong', content.footer_delivery_title);
  setText('.site-footer .footer-grid > div:nth-child(3) > div[style*="margin-top"] div', content.footer_delivery_text);
  setText('.site-footer .footer-grid > div:nth-child(4) .footer-col-title', content.footer_contact_title);
  setText('.site-footer .footer-grid > div:nth-child(4) > p', content.footer_contact_text);
  setText('.btn-whatsapp span', content.footer_whatsapp_button);
  setText('.site-footer .footer-grid > div:nth-child(4) > div[style*="margin-top"]', content.footer_location_text);
  setText('.footer-bottom > div:first-child', content.footer_bottom_text);
  setText('.footer-bottom > div:last-child', content.footer_slogan);

  // Top Announcement Banner
  const topBanner = document.getElementById('top-promo-banner');
  const topText = document.getElementById('top-promo-text');
  const topLink = document.getElementById('top-promo-link');
  if (topBanner && topText) {
    if (content.top_banner_enabled === 'true' && content.top_banner_text) {
      topText.textContent = content.top_banner_text;
      if (topLink) {
        if (content.top_banner_cta && content.top_banner_link) {
          topLink.textContent = content.top_banner_cta;
          topLink.href = content.top_banner_link;
          topLink.classList.remove('d-none');
        } else {
          topLink.classList.add('d-none');
        }
      }
      topBanner.classList.remove('d-none');
    } else {
      topBanner.classList.add('d-none');
    }
  }

  // Store Open / Closed Status
  const closedWarning = document.getElementById('store-closed-warning');
  const closedMsgEl = document.getElementById('store-closed-message');
  const headerStatusBadge = document.querySelector('.header-status-badge');
  const isOpen = content.store_is_open !== 'false';

  if (closedWarning) {
    if (!isOpen) {
      closedWarning.classList.remove('d-none');
      if (closedMsgEl && content.store_closed_message) {
        closedMsgEl.textContent = content.store_closed_message;
      }
    } else {
      closedWarning.classList.add('d-none');
    }
  }

  if (headerStatusBadge) {
    const dot = headerStatusBadge.querySelector('.status-dot');
    const textSpan = headerStatusBadge.querySelector('span:last-child');
    if (dot && textSpan) {
      if (!isOpen) {
        dot.style.background = 'var(--color-rustic-red)';
        dot.style.boxShadow = 'var(--shadow-neon-red)';
        textSpan.textContent = 'Fechado Agora';
      } else {
        dot.style.background = '#00FF66';
        dot.style.boxShadow = '0 0 8px #00FF66';
        textSpan.textContent = content.header_status || 'Aberto Agora';
      }
    }
  }
}

/**
 * Render Featured / Best-seller products showcase grid.
 * @param {Array<Object>} featuredProducts
 */
function renderFeaturedProducts(featuredProducts) {
  const section = document.getElementById('featured-products-section');
  const grid = document.getElementById('featured-products-grid');
  if (!section || !grid) return;

  if (!featuredProducts || featuredProducts.length === 0) {
    section.classList.add('d-none');
    return;
  }

  section.classList.remove('d-none');
  grid.innerHTML = '';

  featuredProducts.forEach((product) => {
    const card = document.createElement('div');
    card.className = 'product-card';
    const productTitle = product.name || product.title || 'Pizza DINOS';
    card.dataset.searchText = `${productTitle || ''} ${product.description || ''}`.toLowerCase();
    card.dataset.filterType = product.is_promo && product.promo_price ? 'promo' : 'product';

    const hasPromo = product.is_promo && product.promo_price;
    const displayPrice = hasPromo ? Number(product.promo_price) : Number(product.price);
    const originalPrice = hasPromo ? Number(product.price) : null;
    const imageUrl = product.image_url || FALLBACK_IMAGE_SVG;

    const featuredBadge = `<span class="product-promo-badge" style="position: absolute; top: 12px; left: 12px; z-index: 2; background: var(--color-gold); color: #000; font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: var(--radius-full); box-shadow: 0 0 10px rgba(255, 174, 25, 0.4);">⭐ MAIS PEDIDA</span>`;

    const priceHtml = hasPromo
      ? `<div>
           <span class="product-card-price">${formatCurrency(displayPrice)}</span>
           <span style="font-size: 0.8rem; text-decoration: line-through; color: var(--color-text-muted); margin-left: 6px;">${formatCurrency(originalPrice)}</span>
         </div>`
      : `<span class="product-card-price">${formatCurrency(displayPrice)}</span>`;

    card.innerHTML = `
      <div class="product-card-image-wrap">
        ${featuredBadge}
        <img src="${imageUrl}" alt="${escapeHtml(productTitle)}" class="product-card-image" loading="lazy">
      </div>
      <div class="product-card-body">
        <h3 class="product-card-title">${escapeHtml(productTitle)}</h3>
        <p class="product-card-desc">${escapeHtml(product.description || 'Ingredientes selecionados da cozinha jurássica.')}</p>
        <div class="product-card-footer">
          ${priceHtml}
          <button type="button" class="btn-add-item" aria-label="Adicionar ${escapeHtml(productTitle)} ao pedido">
            + Adicionar
          </button>
        </div>
      </div>
    `;

    const imgEl = card.querySelector('.product-card-image');
    if (imgEl) {
      imgEl.onerror = () => {
        imgEl.src = FALLBACK_IMAGE_SVG;
      };
    }

    const addBtn = card.querySelector('.btn-add-item');
    if (addBtn) {
      addBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openItemModal(product);
      });
    }

    card.addEventListener('click', () => {
      openItemModal(product);
    });

    grid.appendChild(card);
  });
}

/**
 * Render Customer Reviews / Testimonials grid.
 * @param {Array<Object>} reviews
 */
function renderReviews(reviews) {
  const section = document.getElementById('reviews-section');
  const grid = document.getElementById('reviews-grid');
  if (!section || !grid) return;

  if (!reviews || reviews.length === 0) {
    section.classList.add('d-none');
    return;
  }

  section.classList.remove('d-none');
  grid.innerHTML = '';

  reviews.forEach((review) => {
    const card = document.createElement('div');
    card.className = 'review-card';
    card.style.cssText = 'background: var(--color-bg-elevated); padding: var(--space-md); border-radius: var(--radius-md); border: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 8px;';

    const starsCount = Math.min(Math.max(1, Number(review.rating) || 5), 5);
    const starsHtml = '⭐'.repeat(starsCount);

    const formattedDate = review.created_at
      ? new Date(review.created_at).toLocaleDateString('pt-BR')
      : '';

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 0.95rem; font-weight: 700; color: var(--color-text);">${escapeHtml(review.customer_name || 'Cliente')}</div>
        <div style="font-size: 0.8rem; color: var(--color-gold);">${starsHtml}</div>
      </div>
      <p style="font-size: 0.88rem; color: var(--color-text-secondary); line-height: 1.4; margin: 0; flex-grow: 1;">"${escapeHtml(review.comment || '')}"</p>
      ${formattedDate ? `<div style="font-size: 0.75rem; color: var(--color-text-muted); text-align: right;">${formattedDate}</div>` : ''}
    `;

    grid.appendChild(card);
  });
}

/**
 * Public Order Tracking Modal Controller.
 */
function initOrderTracking() {
  const trackBtn = document.getElementById('track-order-btn');
  const modalOverlay = document.getElementById('track-order-modal-overlay');
  const closeBtn = document.getElementById('track-order-close-btn');
  const submitBtn = document.getElementById('track-order-submit-btn');
  const idInput = document.getElementById('track-order-id-input');
  const phoneInput = document.getElementById('track-order-phone-input');
  const resultContainer = document.getElementById('track-order-result');

  if (!trackBtn || !modalOverlay) return;

  const openModal = () => {
    modalOverlay.classList.add('active');
    if (resultContainer) resultContainer.classList.add('d-none');
    if (idInput) idInput.focus();
  };

  const closeModal = () => {
    modalOverlay.classList.remove('active');
  };

  trackBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  const STATUS_MAP = {
    pending: { label: 'Recebido ⏳', color: 'var(--color-gold)' },
    confirmed: { label: 'Confirmado ✅', color: 'var(--color-gold)' },
    in_preparation: { label: 'No Forno / Em Preparo 🔥', color: 'var(--color-clay)' },
    out_for_delivery: { label: 'Saiu para Entrega 🛵', color: 'var(--color-rustic-red)' },
    delivered: { label: 'Entregue / Concluído 🎉', color: '#00FF66' },
    cancelled: { label: 'Cancelado ❌', color: '#888' }
  };

  const handleTrackSubmit = async () => {
    const orderId = (idInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();

    if (!orderId || !phone) {
      showToast('Preencha o número do pedido e seu telefone.', 'warning');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Consultando...';
    }

    try {
      const order = await api.trackOrder(orderId, phone);
      if (!resultContainer) return;

      const statusInfo = STATUS_MAP[order.status] || { label: order.status, color: 'var(--color-text)' };

      let itemsHtml = '';
      if (order.items_summary && order.items_summary.length > 0) {
        itemsHtml = `
          <div style="margin-top: 10px; text-align: left; font-size: 0.85rem; border-top: 1px dashed var(--color-border); padding-top: 8px;">
            <strong>Itens do Pedido:</strong>
            <ul style="margin: 4px 0 0 16px; padding: 0; color: var(--color-text-secondary);">
              ${order.items_summary.map((it) => `<li>${it.quantity}x ${escapeHtml(it.item_name)} (${formatCurrency(it.final_price)})</li>`).join('')}
            </ul>
          </div>
        `;
      }

      let fulfillmentHtml = '';
      if (order.fulfillment_time_type === 'scheduled' && order.scheduled_for) {
        const scheduledDt = new Date(order.scheduled_for).toLocaleString('pt-BR');
        fulfillmentHtml = `<p style="font-size: 0.85rem; color: var(--color-gold); margin: 4px 0;">⏰ Agendado para: <strong>${scheduledDt}</strong></p>`;
      }

      resultContainer.innerHTML = `
        <div style="font-size: 1.1rem; font-weight: 700; color: var(--color-text); margin-bottom: 6px;">
          Pedido #${escapeHtml(order.order_number || String(order.id))}
        </div>
        <div style="display: inline-block; padding: 4px 12px; border-radius: var(--radius-full); font-size: 0.85rem; font-weight: 700; background: rgba(255,255,255,0.05); color: ${statusInfo.color}; margin-bottom: 8px;">
          ${statusInfo.label}
        </div>
        <p style="font-size: 0.85rem; color: var(--color-text-muted); margin: 2px 0;">Tipo: ${order.delivery_type === 'pickup' ? 'Retirada no Balcão' : 'Entrega em Domicílio'}</p>
        ${fulfillmentHtml}
        <p style="font-size: 0.95rem; font-weight: 700; color: var(--color-gold); margin: 8px 0 0 0;">Total: ${formatCurrency(order.total_amount)}</p>
        ${itemsHtml}
      `;
      resultContainer.classList.remove('d-none');
    } catch (err) {
      showToast(err.message || 'Pedido não encontrado ou telefone incorreto.', 'error');
      if (resultContainer) {
        resultContainer.innerHTML = `<p style="color: var(--color-rustic-red); font-size: 0.85rem; margin: 0;">${escapeHtml(err.message || 'Pedido não encontrado. Verifique o número e o telefone.')}</p>`;
        resultContainer.classList.remove('d-none');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Consultar Status';
      }
    }
  };

  if (submitBtn) {
    submitBtn.addEventListener('click', handleTrackSubmit);
  }
}

function initMenuSearchAndFilters() {
  const input = document.getElementById('menu-search-input');
  const chips = document.querySelectorAll('.menu-filter-chip');

  if (input && !input.dataset.bound) {
    input.dataset.bound = 'true';
    input.addEventListener('input', () => {
      state.searchTerm = input.value || '';
      applyMenuFilters();
    });
  }

  chips.forEach((chip) => {
    if (chip.dataset.bound) return;
    chip.dataset.bound = 'true';
    chip.addEventListener('click', () => {
      state.activeFilter = chip.dataset.filter || 'all';
      chips.forEach((c) => c.classList.toggle('active', c === chip));
      applyMenuFilters();
    });
  });
}

/**
 * Application Bootstrap & Initialization.
 */
async function initApp() {
  initHeroEmbers();
  initMenuSearchAndFilters();

  // 1. Initialize UI listeners (Modals, Drawer, Success & Checkout)
  initItemModalListeners();
  initCartDrawerListeners();
  initSuccessModalListeners();
  initCheckout();
  renderCartDrawer();

  // 2. Render skeletons
  renderSkeletons();

  // 3. Fetch data from FastAPI backend in parallel
  try {
    const [categories, products, promoCombos, combos, siteContent, featuredProducts, reviews] = await Promise.all([
      api.getCategories().catch(() => []),
      api.getProducts().catch(() => []),
      api.getPromoCombos().catch(() => []),
      api.getCombos().catch(() => []),
      api.getSiteContent().catch(() => []),
      api.getFeaturedProducts().catch(() => []),
      api.getReviews().catch(() => [])
    ]);

    state.categories = categories;
    state.products = products;
    state.promoCombos = promoCombos;
    state.combos = combos;
    setPizzaFlavorCatalog(products);
    applySiteContent(siteContent);

    // 4. Render Hero Promos section
    renderHeroPromos(promoCombos.length > 0 ? promoCombos : combos);

    // 4.1 Render Featured Products
    renderFeaturedProducts(featuredProducts);

    // 4.2 Render Customer Reviews
    renderReviews(reviews);

    // 5. Render Category Tabs & Navigation
    renderCategoryTabs(categories);

    // 6. Render Product Catalog
    renderMenuCatalog(categories, products);

    // 7. Setup IntersectionObserver, Smooth Scroll, and live search filters
    setupCategoryNavigation();
    applyMenuFilters();

    // 8. Setup Order Tracking Modal
    initOrderTracking();

    console.log(`[DINOS Storefront] Cardápio carregado com sucesso: ${categories.length} categorias, ${products.length} produtos.`);
  } catch (err) {
    console.error('[DINOS Storefront] Erro ao inicializar cardápio:', err);
    renderApiError(err);
    showToast('Erro ao carregar cardápio da pizzaria.', 'error');
  }
}

// Auto-run on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

export { initApp, renderHeroPromos, renderCategoryTabs, renderMenuCatalog };
