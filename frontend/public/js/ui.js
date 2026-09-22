/**
 * DINOS Pizzaria — UI Helper & Component Renderer Module (ES6 Module)
 * Handles BRL currency formatting, toast notifications, item customization modal, and cart drawer rendering.
 */

import { cart } from './cart.js';

/**
 * Format numeric value to Brazilian Real currency format (e.g. "R$ 49,90").
 * @param {number|string} value
 * @returns {string}
 */
export function formatCurrency(value) {
  const num = typeof value === 'number' ? value : parseFloat(value) || 0;
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(num);
}

/**
 * Escape unsafe HTML characters from user input strings to mitigate XSS (T-04-04).
 * @param {string} str
 * @returns {string}
 */
export function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Display a floating toast notification.
 * @param {string} message - Text to display
 * @param {'info'|'success'|'error'|'warning'} [type='info'] - Visual style
 * @param {number} [duration=3000] - Duration in milliseconds
 */
export function animateFlyToCart(sourceEl) {
  const targetEl = document.getElementById('cart-count-badge') || document.getElementById('cart-trigger-btn');
  if (!sourceEl || !targetEl || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  const sourceRect = sourceEl.getBoundingClientRect();
  const targetRect = targetEl.getBoundingClientRect();
  const startX = sourceRect.left + sourceRect.width / 2 - 11;
  const startY = sourceRect.top + sourceRect.height / 2 - 11;
  const endX = targetRect.left + targetRect.width / 2 - 11;
  const endY = targetRect.top + targetRect.height / 2 - 11;
  const midX = (startX + endX) / 2;
  const midY = Math.min(startY, endY) - Math.max(90, Math.abs(endX - startX) * 0.16);

  const particle = document.createElement('span');
  particle.className = 'fly-to-cart-particle';
  particle.setAttribute('aria-hidden', 'true');
  particle.style.setProperty('--fly-start-x', `${startX}px`);
  particle.style.setProperty('--fly-start-y', `${startY}px`);
  particle.style.setProperty('--fly-mid-x', `${midX}px`);
  particle.style.setProperty('--fly-mid-y', `${midY}px`);
  particle.style.setProperty('--fly-end-x', `${endX}px`);
  particle.style.setProperty('--fly-end-y', `${endY}px`);

  document.body.appendChild(particle);
  particle.addEventListener('animationend', () => particle.remove(), { once: true });
}

export function showToast(message, type = 'info', duration = 3000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon =
    type === 'success'
      ? '🦖✅'
      : type === 'error'
      ? '⚠️'
      : type === 'warning'
      ? '🔥'
      : 'ℹ️';

  toast.innerHTML = `
    <span class="toast-icon" aria-hidden="true">${icon}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  // Trigger animation frame
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => {
      toast.remove();
    }, { once: true });
    // Fallback if transition event didn't fire
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 400);
  }, duration);
}

// --------------------------------------------------------------------------
// Item Customizer Modal State & Handlers
// --------------------------------------------------------------------------
let currentModalItem = null;
let currentModalQty = 1;
let onModalAddCallback = null;
let pizzaFlavorCatalog = [];

function getItemTitle(item) {
  return item?.name || item?.title || 'Item DINOS';
}

function getBaseUnitPrice(item) {
  return item?.is_promo && item?.promo_price ? Number(item.promo_price) : Number(item?.price) || 0;
}

function isLikelyBeverage(item) {
  const text = `${getItemTitle(item)} ${item?.description || ''} ${item?.category?.name || ''}`.toLowerCase();
  return /\b(coca|guaran[áa]|refrigerante|bebida|suco|[áa]gua|cerveja|lata|2l|1l|600ml|350ml)\b/.test(text);
}

function hasPizzaSizePrices(description = '') {
  return /(pequena|broto|m[ée]dia|grande|fam[íi]lia|gigante)\s*[:\-]?\s*r\$/i.test(description || '');
}

function isPizzaProduct(item) {
  if (!item || item.is_promo_of_day !== undefined || item.items) return false;
  if (isLikelyBeverage(item)) return false;

  const title = getItemTitle(item).toLowerCase();
  const categoryName = String(item.category?.name || '').toLowerCase();
  const description = String(item.description || '').toLowerCase();

  return (
    title.includes('pizza') ||
    categoryName.includes('pizza') ||
    hasPizzaSizePrices(description) ||
    description.includes('borda')
  );
}

function normalizeSizeLabel(label) {
  const raw = String(label || '').toLowerCase();
  if (raw.includes('pequena') || raw.includes('broto')) return 'Pequena';
  if (raw.includes('média') || raw.includes('media') || raw.includes('grande')) return 'Média';
  if (raw.includes('família') || raw.includes('familia')) return 'Família';
  if (raw.includes('gigante')) return 'Gigante';
  return label || 'Família';
}

function parseCurrencyBR(value) {
  const clean = String(value || '').replace(/\./g, '').replace(',', '.');
  const parsed = Number.parseFloat(clean);
  return Number.isFinite(parsed) ? parsed : 0;
}

function extractPizzaSizeOptions(item) {
  const basePrice = getBaseUnitPrice(item);
  const prices = new Map();
  const description = String(item?.description || '');
  const regex = /(Pequena|Broto|M[ée]dia|Media|Grande|Fam[íi]lia|Familia|Gigante)\s*[:\-]?\s*R\$\s*([\d.]+,\d{2}|[\d,]+)/gi;
  let match;

  while ((match = regex.exec(description)) !== null) {
    prices.set(normalizeSizeLabel(match[1]), parseCurrencyBR(match[2]));
  }

  return ['Média', 'Família', 'Gigante'].map((label) => ({
    label,
    value: label,
    price: prices.get(label) || basePrice
  }));
}

export function setPizzaFlavorCatalog(products = []) {
  pizzaFlavorCatalog = Array.isArray(products)
    ? products
        .filter(isPizzaProduct)
        .map((product) => ({ id: Number(product.id), title: getItemTitle(product) }))
        .filter((product, index, list) => product.title && list.findIndex((p) => p.title === product.title) === index)
    : [];
}

function updateFlavorCounter() {
  const flavorsGrid = document.getElementById('item-modal-flavors');
  const helpEl = document.getElementById('item-modal-flavors-help');
  if (!flavorsGrid || !helpEl) return;

  const selectedCount = flavorsGrid.querySelectorAll('.pizza-flavor-checkbox:checked').length;
  helpEl.textContent = selectedCount > 0
    ? `${selectedCount}/4 sabor(es) escolhido(s). Toque novamente para desmarcar.`
    : 'Toque nas caixas para montar sua pizza. Se não escolher, usamos o sabor do item aberto.';
}

function configurePizzaOptions(item) {
  const panel = document.getElementById('item-modal-pizza-options');
  const sizeSelect = document.getElementById('item-modal-size');
  const crustSelect = document.getElementById('item-modal-crust');
  const flavorsGrid = document.getElementById('item-modal-flavors');
  const showPizzaOptions = isPizzaProduct(item);

  if (panel) panel.classList.toggle('d-none', !showPizzaOptions);
  if (!showPizzaOptions) {
    if (flavorsGrid) flavorsGrid.innerHTML = '';
    return;
  }

  if (sizeSelect) {
    const sizeOptions = extractPizzaSizeOptions(item);
    sizeSelect.innerHTML = sizeOptions
      .map((opt) => `<option value="${escapeHtml(opt.value)}" data-price="${opt.price.toFixed(2)}">${escapeHtml(opt.label)} — ${formatCurrency(opt.price)}</option>`)
      .join('');
    sizeSelect.value = sizeOptions.some((opt) => opt.value === 'Família') ? 'Família' : sizeOptions[0]?.value || '';
  }

  if (crustSelect) crustSelect.value = 'none';

  if (flavorsGrid) {
    const currentTitle = getItemTitle(item);
    const flavorList = pizzaFlavorCatalog.length > 0 ? pizzaFlavorCatalog : [{ id: Number(item.id), title: currentTitle }];
    flavorsGrid.innerHTML = flavorList
      .map((flavor, index) => {
        const safeTitle = escapeHtml(flavor.title);
        const inputId = `pizza-flavor-${Number(flavor.id) || index}`;
        return `
          <label class="pizza-flavor-box" for="${inputId}">
            <input
              type="checkbox"
              class="pizza-flavor-checkbox"
              id="${inputId}"
              value="${safeTitle}"
              aria-label="Selecionar sabor ${safeTitle}"
            >
            <span class="pizza-flavor-check" aria-hidden="true">✓</span>
            <span class="pizza-flavor-name">${safeTitle}</span>
          </label>
        `;
      })
      .join('');
    updateFlavorCounter();
  }
}

function getSelectedPizzaFlavors() {
  const flavorsGrid = document.getElementById('item-modal-flavors');
  if (!flavorsGrid || !currentModalItem || !isPizzaProduct(currentModalItem)) return [];

  const selected = Array.from(flavorsGrid.querySelectorAll('.pizza-flavor-checkbox:checked'))
    .map((input) => input.value)
    .filter(Boolean);
  return selected.length > 0 ? selected.slice(0, 4) : [getItemTitle(currentModalItem)];
}

function getConfiguredUnitPrice() {
  if (!currentModalItem || !isPizzaProduct(currentModalItem)) return getBaseUnitPrice(currentModalItem);

  const sizeSelect = document.getElementById('item-modal-size');
  const crustSelect = document.getElementById('item-modal-crust');
  const sizePrice = sizeSelect?.selectedOptions?.[0]?.dataset?.price;
  const crustPrice = crustSelect?.selectedOptions?.[0]?.dataset?.price;
  return (Number(sizePrice) || getBaseUnitPrice(currentModalItem)) + (Number(crustPrice) || 0);
}

function getConfiguredPizzaOptions() {
  if (!currentModalItem || !isPizzaProduct(currentModalItem)) return null;

  const sizeSelect = document.getElementById('item-modal-size');
  const crustSelect = document.getElementById('item-modal-crust');
  return {
    size: sizeSelect?.value || 'Família',
    crust: crustSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sem borda recheada',
    flavors: getSelectedPizzaFlavors()
  };
}

/**
 * Open Item Customization Modal (D-03) with photo, quantity controls and notes.
 *
 * @param {Object} item - Product or Combo object
 * @param {Function} [onAdd] - Callback invoked when customer confirms addition
 */
export function openItemModal(item, onAdd = null) {
  currentModalItem = item;
  currentModalQty = 1;
  onModalAddCallback = onAdd;

  const overlay = document.getElementById('item-modal-overlay');
  const titleEl = document.getElementById('item-modal-title');
  const descEl = document.getElementById('item-modal-desc');
  const priceEl = document.getElementById('item-modal-price');
  const imageEl = document.getElementById('item-modal-image');
  const notesEl = document.getElementById('item-modal-notes');
  const qtyValEl = document.getElementById('item-modal-qty-val');
  const subtotalEl = document.getElementById('item-modal-subtotal');

  if (!overlay) return;

  configurePizzaOptions(item);
  const unitPrice = getConfiguredUnitPrice();
  const itemTitle = getItemTitle(item);

  if (titleEl) titleEl.textContent = itemTitle;
  if (descEl) descEl.textContent = item.description || '';
  if (priceEl) priceEl.textContent = formatCurrency(unitPrice);
  if (notesEl) {
    notesEl.value = '';
    notesEl.setAttribute('maxlength', '255');
  }
  if (qtyValEl) qtyValEl.textContent = '1';
  if (subtotalEl) subtotalEl.textContent = formatCurrency(unitPrice);

  if (imageEl) {
    imageEl.alt = itemTitle || 'Foto do produto';
    imageEl.src = item.image_url || '/static/uploads/placeholder_pizza.webp';
    imageEl.onerror = () => {
      imageEl.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect fill="%23222222" width="400" height="300"/><text fill="%23FFAE19" font-family="sans-serif" font-size="28" font-weight="bold" x="50%" y="45%" text-anchor="middle">🦖 DINOS PIZZARIA</text><text fill="%238E8E8E" font-family="sans-serif" font-size="16" x="50%" y="60%" text-anchor="middle">Sabor Lendário</text></svg>';
    };
  }

  overlay.classList.add('active');
  overlay.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

/**
 * Close the item customization modal and reset fields.
 */
export function closeItemModal() {
  const overlay = document.getElementById('item-modal-overlay');
  if (overlay) {
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
  }
  currentModalItem = null;
  currentModalQty = 1;
  onModalAddCallback = null;
  document.body.style.overflow = '';
}

/**
 * Initialize event listeners for the item customization modal.
 */
export function initItemModalListeners() {
  const overlay = document.getElementById('item-modal-overlay');
  const closeBtn = document.getElementById('item-modal-close-btn');
  const minusBtn = document.getElementById('item-modal-qty-minus');
  const plusBtn = document.getElementById('item-modal-qty-plus');
  const qtyValEl = document.getElementById('item-modal-qty-val');
  const subtotalEl = document.getElementById('item-modal-subtotal');
  const notesEl = document.getElementById('item-modal-notes');
  const addBtn = document.getElementById('item-modal-add-btn');
  const addContinueBtn = document.getElementById('item-modal-add-continue-btn');
  const addCartBtn = document.getElementById('item-modal-add-cart-btn');
  const sizeSelect = document.getElementById('item-modal-size');
  const crustSelect = document.getElementById('item-modal-crust');
  const flavorsGrid = document.getElementById('item-modal-flavors');

  if (closeBtn) {
    closeBtn.addEventListener('click', closeItemModal);
  }

  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeItemModal();
    });
  }

  const updateModalSubtotal = () => {
    if (!currentModalItem) return;
    const unitPrice = getConfiguredUnitPrice();
    const priceEl = document.getElementById('item-modal-price');
    if (priceEl) priceEl.textContent = formatCurrency(unitPrice);
    if (qtyValEl) qtyValEl.textContent = String(currentModalQty);
    if (subtotalEl) subtotalEl.textContent = formatCurrency(unitPrice * currentModalQty);
  };

  [sizeSelect, crustSelect].forEach((select) => {
    if (select) select.addEventListener('change', updateModalSubtotal);
  });

  if (flavorsGrid) {
    flavorsGrid.addEventListener('change', (event) => {
      const checkbox = event.target;
      if (!checkbox.classList || !checkbox.classList.contains('pizza-flavor-checkbox')) return;

      const selected = Array.from(flavorsGrid.querySelectorAll('.pizza-flavor-checkbox:checked'));
      if (selected.length > 4) {
        checkbox.checked = false;
        showToast('Escolha até 4 sabores por pizza.', 'warning');
      }
      updateFlavorCounter();
    });
  }

  if (minusBtn) {
    minusBtn.addEventListener('click', () => {
      if (currentModalQty > 1) {
        currentModalQty -= 1;
        updateModalSubtotal();
      }
    });
  }

  if (plusBtn) {
    plusBtn.addEventListener('click', () => {
      if (currentModalQty < 50) {
        currentModalQty += 1;
        updateModalSubtotal();
      } else {
        showToast('Quantidade máxima de 50 unidades por item.', 'warning');
      }
    });
  }

  const handleAddItem = (goToCart = false) => {
    if (!currentModalItem) return;

    const unitPrice = getConfiguredUnitPrice();
    const itemTitle = getItemTitle(currentModalItem);
    const notes = notesEl ? notesEl.value.trim().slice(0, 255) : '';
    const itemType = currentModalItem.is_promo_of_day !== undefined || currentModalItem.items ? 'combo' : 'product';
    const options = getConfiguredPizzaOptions();

    const payload = {
      itemType,
      itemId: currentModalItem.id,
      title: itemTitle,
      unitPrice,
      quantity: currentModalQty,
      notes,
      imageUrl: currentModalItem.image_url || '',
      options
    };

    const sourceEl = document.getElementById('item-modal-add-cart-btn') || document.getElementById('item-modal-card');
    animateFlyToCart(sourceEl);
    cart.addItem(payload);
    showToast(`${itemTitle} adicionado ao seu pedido!`, 'success');

    if (typeof onModalAddCallback === 'function') {
      onModalAddCallback(payload);
    }

    closeItemModal();

    if (goToCart) {
      toggleCartDrawer(true);
    }
  };

  if (addContinueBtn) {
    addContinueBtn.addEventListener('click', () => handleAddItem(false));
  }

  if (addCartBtn) {
    addCartBtn.addEventListener('click', () => handleAddItem(true));
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => handleAddItem(false));
  }
}

// --------------------------------------------------------------------------
// Cart Drawer Rendering & Control
// --------------------------------------------------------------------------

/**
 * Open or close the cart drawer sidebar.
 * @param {boolean} open
 */
export function toggleCartDrawer(open) {
  const drawer = document.getElementById('cart-drawer');
  const backdrop = document.getElementById('cart-backdrop');

  if (!drawer || !backdrop) return;

  if (open) {
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    backdrop.classList.add('active');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  } else {
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    backdrop.classList.remove('active');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
}

function syncStickyCartBar(state) {
  const bar = document.getElementById('sticky-cart-bar');
  const btn = document.getElementById('sticky-cart-btn');
  const countEl = document.getElementById('sticky-cart-count');
  const totalEl = document.getElementById('sticky-cart-total');
  const hasItems = state && state.itemCount > 0;

  if (!bar) return;
  if (countEl) countEl.textContent = String(state.itemCount || 0);
  if (totalEl) totalEl.textContent = formatCurrency(state.total || state.subtotal || 0);

  bar.classList.toggle('visible', hasItems);
  bar.setAttribute('aria-hidden', hasItems ? 'false' : 'true');
  document.body.classList.toggle('has-sticky-cart', hasItems);

  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = 'true';
    btn.addEventListener('click', () => toggleCartDrawer(true));
  }
}

function updateCartProgressBanner(state) {
  const footer = document.getElementById('cart-footer');
  if (!footer) return;

  let banner = footer.querySelector('.cart-progress-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.className = 'cart-progress-banner';
    footer.insertBefore(banner, footer.firstChild);
  }

  if (!state.items || state.items.length === 0) {
    banner.style.display = 'none';
    return;
  }

  const missingForTreat = Math.max(0, 80 - state.subtotal);
  banner.style.display = 'flex';
  banner.innerHTML = missingForTreat > 0
    ? `<span>🔥 Faltam <strong>${formatCurrency(missingForTreat)}</strong> para um pedido lendário.</span><span>🦖</span>`
    : '<span>🦖 Pedido lendário montado — agora é só finalizar no WhatsApp.</span><span>🔥</span>';
}

/**
 * Render the cart drawer contents dynamically reflecting current state (D-04).
 * @param {Object} [cartState=null]
 */
export function renderCartDrawer(cartState = null) {
  const state = cartState || cart.getState();
  syncStickyCartBar(state);
  const itemsContainer = document.getElementById('cart-items-list');
  const subtotalEl = document.getElementById('cart-subtotal');
  const totalEl = document.getElementById('cart-total');
  const deliveryFeeEl = document.getElementById('cart-delivery-fee');
  const deliveryRow = document.getElementById('cart-delivery-row');
  const checkoutBtn = document.getElementById('cart-checkout-btn');
  const badgeEl = document.getElementById('cart-count-badge');

  // Update badge count with bounce animation
  if (badgeEl) {
    const prevCount = parseInt(badgeEl.textContent, 10) || 0;
    badgeEl.textContent = String(state.itemCount);
    if (state.itemCount !== prevCount) {
      badgeEl.classList.add('bump');
      setTimeout(() => badgeEl.classList.remove('bump'), 300);
    }
  }

  // Update summary amounts
  if (subtotalEl) subtotalEl.textContent = formatCurrency(state.subtotal);
  if (totalEl) totalEl.textContent = formatCurrency(state.total);

  if (deliveryFeeEl && deliveryRow) {
    if (state.deliveryType === 'pickup') {
      deliveryFeeEl.textContent = 'Grátis (Retirada)';
      deliveryFeeEl.className = 'text-success';
    } else if (state.deliveryZone) {
      deliveryFeeEl.textContent = formatCurrency(state.deliveryFee);
      deliveryFeeEl.className = '';
    } else {
      deliveryFeeEl.textContent = 'A calcular no checkout';
      deliveryFeeEl.className = 'text-muted';
    }
  }

  updateCartProgressBanner(state);

  if (checkoutBtn) {
    checkoutBtn.disabled = state.items.length === 0;
    if (state.items.length === 0) {
      checkoutBtn.textContent = 'Sacola Vazia';
      checkoutBtn.style.opacity = '0.6';
      checkoutBtn.style.cursor = 'not-allowed';
    } else {
      checkoutBtn.textContent = 'Continuar para Entrega';
      checkoutBtn.style.opacity = '1';
      checkoutBtn.style.cursor = 'pointer';
    }
  }

  if (!itemsContainer) return;

  // Empty state rendering
  if (!state.items || state.items.length === 0) {
    itemsContainer.innerHTML = `
      <div class="cart-empty-state">
        <div class="cart-empty-icon" aria-hidden="true">🦖🛒</div>
        <p style="font-weight: 700; color: var(--color-text-primary); margin-bottom: var(--space-xs);">Sua sacola está vazia</p>
        <p style="font-size: 0.85rem;">Escolha suas pizzas e combos lendários no cardápio para começar.</p>
      </div>
    `;
    return;
  }

  // Render items list safely avoiding XSS
  itemsContainer.innerHTML = '';
  state.items.forEach((item, index) => {
    const itemRow = document.createElement('div');
    itemRow.className = 'cart-item-row';

    const itemSubtotal = item.unitPrice * item.quantity;
    const badgeType = item.itemType === 'combo' ? '<span class="badge-combo" style="font-size: 0.65rem; background: var(--color-rustic-red); color: #fff; padding: 2px 6px; border-radius: 4px; margin-right: 4px; font-weight: 800;">COMBO</span>' : '';

    const optionsParts = [];
    if (item.options?.size) optionsParts.push(`Tamanho: ${escapeHtml(item.options.size)}`);
    if (item.options?.crust && !String(item.options.crust).toLowerCase().includes('sem borda')) {
      optionsParts.push(`Borda: ${escapeHtml(item.options.crust)}`);
    }
    if (Array.isArray(item.options?.flavors) && item.options.flavors.length > 0) {
      optionsParts.push(`Sabores: ${item.options.flavors.map(escapeHtml).join(' / ')}`);
    }
    const safeOptions = optionsParts.length > 0 ? `<div class="cart-item-options">🍕 ${optionsParts.join(' • ')}</div>` : '';
    const safeNotes = item.notes ? `<div class="cart-item-notes">📝 <em>${escapeHtml(item.notes)}</em></div>` : '';

    itemRow.innerHTML = `
      <div class="cart-item-top">
        <div style="flex: 1;">
          <div class="cart-item-title">${badgeType}${escapeHtml(item.title)}</div>
          ${safeOptions}
          ${safeNotes}
        </div>
        <button type="button" class="cart-item-remove-btn" data-index="${index}" aria-label="Remover item da sacola">&times;</button>
      </div>
      <div class="cart-item-bottom">
        <div class="qty-control">
          <button type="button" class="qty-btn btn-minus" data-index="${index}" aria-label="Diminuir quantidade">-</button>
          <span class="qty-val">${item.quantity}</span>
          <button type="button" class="qty-btn btn-plus" data-index="${index}" aria-label="Aumentar quantidade">+</button>
        </div>
        <span class="cart-item-price">${formatCurrency(itemSubtotal)}</span>
      </div>
    `;

    // Hook listeners for quantity and remove buttons
    const removeBtn = itemRow.querySelector('.cart-item-remove-btn');
    const minusBtn = itemRow.querySelector('.btn-minus');
    const plusBtn = itemRow.querySelector('.btn-plus');

    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        cart.removeItem(index);
        showToast('Item removido da sacola.', 'info', 2000);
      });
    }

    if (minusBtn) {
      minusBtn.addEventListener('click', () => {
        cart.updateQuantity(index, item.quantity - 1);
      });
    }

    if (plusBtn) {
      plusBtn.addEventListener('click', () => {
        if (item.quantity < 50) {
          cart.updateQuantity(index, item.quantity + 1);
        } else {
          showToast('Limite máximo de 50 unidades por item atingido.', 'warning');
        }
      });
    }

    itemsContainer.appendChild(itemRow);
  });
}

/**
 * Apply Brazilian phone mask (10 or 11 digits: (99) 99999-9999 or (99) 9999-9999).
 * @param {string} value
 * @returns {string}
 */
export function maskPhone(value) {
  if (!value) return '';
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 2) {
    return digits ? `(${digits}` : '';
  }
  if (digits.length <= 6) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  }
  if (digits.length <= 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7, 11)}`;
}

/**
 * Format currency input string while user is typing.
 * @param {string} value
 * @returns {string}
 */
export function maskCurrencyInput(value) {
  if (!value) return '';
  const digits = value.replace(/\D/g, '');
  if (!digits) return '';
  const num = (parseInt(digits, 10) / 100).toFixed(2);
  return num.replace('.', ',');
}

// --------------------------------------------------------------------------
// Success / WhatsApp Modal State & Handlers
// --------------------------------------------------------------------------

/**
 * Open Success / WhatsApp Confirmation Modal (D-07).
 * @param {Object} responseData - Response from POST /api/v1/orders
 */
export function openSuccessModal(responseData) {
  const order = responseData.order || responseData;
  const whatsappUrl = responseData.whatsapp_url || '#';

  const overlay = document.getElementById('success-modal-overlay');
  const idEl = document.getElementById('success-order-id');
  const nameEl = document.getElementById('success-customer-name');
  const typeEl = document.getElementById('success-order-type');
  const totalEl = document.getElementById('success-order-total');
  const waBtn = document.getElementById('success-whatsapp-btn');

  if (!overlay) return;

  if (idEl) idEl.textContent = `#${String(order.id).padStart(4, '0')}`;
  if (nameEl) nameEl.textContent = order.customer_name || 'Cliente';
  if (typeEl) {
    typeEl.textContent = order.delivery_type === 'pickup' ? '🏪 Retirada no Balcão' : '🛵 Entrega em Domicílio';
  }
  if (totalEl) totalEl.textContent = formatCurrency(order.total_amount);

  if (waBtn) {
    waBtn.href = whatsappUrl;
    waBtn.setAttribute('target', '_blank');
    waBtn.setAttribute('rel', 'noopener noreferrer');
  }

  overlay.classList.add('active');
  overlay.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  // Automatically attempt opening WhatsApp URL in a new tab (if popup blockers permit, Pitfall 1 mitigation)
  if (whatsappUrl && whatsappUrl !== '#') {
    try {
      window.open(whatsappUrl, '_blank', 'noopener,noreferrer');
    } catch {
      // Ignored if popup blocker is active; the prominent WhatsApp button is already visible in the modal
    }
  }
}

/**
 * Close the Success / WhatsApp modal.
 */
export function closeSuccessModal() {
  const overlay = document.getElementById('success-modal-overlay');
  if (overlay) {
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
  }
  document.body.style.overflow = '';
}

/**
 * Initialize Success Modal event listeners.
 */
export function initSuccessModalListeners() {
  const overlay = document.getElementById('success-modal-overlay');
  const closeBtn = document.getElementById('success-close-btn');

  if (closeBtn) {
    closeBtn.addEventListener('click', closeSuccessModal);
  }

  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeSuccessModal();
    });
  }
}

/**
 * Initialize Cart Drawer triggers and listeners.
 */
export function initCartDrawerListeners() {
  const triggerBtn = document.getElementById('cart-trigger-btn');
  const closeBtn = document.getElementById('cart-close-btn');
  const backdrop = document.getElementById('cart-backdrop');

  if (triggerBtn) {
    triggerBtn.addEventListener('click', () => toggleCartDrawer(true));
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => toggleCartDrawer(false));
  }

  if (backdrop) {
    backdrop.addEventListener('click', () => toggleCartDrawer(false));
  }

  // Subscribe to CartStore updates
  cart.addEventListener('cart:updated', (e) => {
    renderCartDrawer(e.detail);
  });
}
