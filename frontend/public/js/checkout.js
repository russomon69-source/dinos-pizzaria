/**
 * DINOS Pizzaria — Guest Checkout & Delivery Selector Module (ES6 Module)
 * Handles delivery vs pickup selection, zone fee calculations, input masks, validation, order submission, and WhatsApp handover.
 */

import { api } from './api.js';
import { cart } from './cart.js';
import {
  formatCurrency,
  escapeHtml,
  showToast,
  maskPhone,
  maskCurrencyInput,
  openSuccessModal,
  toggleCartDrawer
} from './ui.js';

/**
 * Cached delivery zones list
 * @type {Array<{ id: number, name: string, fee: number, estimated_minutes: number }>}
 */
let deliveryZones = [];
let isSubmitting = false;
let deliveryTimelineTimers = [];
const CUSTOMER_STORAGE_KEY = 'dinos_customer_v1';

function clearDeliveryTimelineTimers() {
  deliveryTimelineTimers.forEach((timerId) => clearTimeout(timerId));
  deliveryTimelineTimers = [];
}

function setDeliveryTimelineStep(activeIndex) {
  const steps = document.querySelectorAll('.delivery-step');
  steps.forEach((step, index) => {
    step.classList.toggle('done', index < activeIndex);
    step.classList.toggle('active', index === activeIndex);
  });

  const titleEl = document.getElementById('delivery-runner-title');
  const messageEl = document.getElementById('delivery-runner-message');
  const messages = [
    ['Validando seu pedido lendário', 'Conferindo sabores, quantidades e forma de pagamento.'],
    ['Aquecendo a cozinha DINOS', 'O dino entregador já está correndo para avisar o forno.'],
    ['Chamando o WhatsApp da loja', 'Montamos tudo para você acompanhar direto com a equipe.'],
    ['Quase lá!', 'Abrindo a conversa para confirmar seu pedido sem atrito.']
  ];
  const [title, message] = messages[activeIndex] || messages[0];
  if (titleEl) titleEl.textContent = title;
  if (messageEl) messageEl.textContent = message;
}

function runDeliveryTimeline() {
  clearDeliveryTimelineTimers();
  setDeliveryTimelineStep(0);

  return new Promise((resolve) => {
    [0, 520, 1040, 1560].forEach((delay, index) => {
      const timerId = setTimeout(() => setDeliveryTimelineStep(index), delay);
      deliveryTimelineTimers.push(timerId);
    });

    const doneTimer = setTimeout(resolve, 1900);
    deliveryTimelineTimers.push(doneTimer);
  });
}

function toggleDeliveryRunner(show) {
  const overlay = document.getElementById('delivery-runner-overlay');
  if (!overlay) return;

  overlay.classList.toggle('active', Boolean(show));
  overlay.setAttribute('aria-hidden', show ? 'false' : 'true');
  if (!show) {
    clearDeliveryTimelineTimers();
    setDeliveryTimelineStep(0);
  }
}

function safeGetCustomerMemory() {
  try {
    const raw = localStorage.getItem(CUSTOMER_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch (err) {
    console.warn('[Checkout] Não foi possível ler memória do cliente:', err);
    return null;
  }
}

function saveCustomerMemory() {
  const nameInput = document.getElementById('customer-name');
  const phoneInput = document.getElementById('customer-phone');
  const zoneSelect = document.getElementById('delivery-zone-select');
  const streetInput = document.getElementById('customer-street');
  const numberInput = document.getElementById('customer-number');
  const complementInput = document.getElementById('customer-complement');
  const referenceInput = document.getElementById('customer-reference');

  const data = {
    name: nameInput ? nameInput.value.trim().slice(0, 120) : '',
    phone: phoneInput ? phoneInput.value.trim().slice(0, 30) : '',
    zoneId: zoneSelect && zoneSelect.value ? zoneSelect.value : '',
    street: streetInput ? streetInput.value.trim().slice(0, 180) : '',
    number: numberInput ? numberInput.value.trim().slice(0, 30) : '',
    complement: complementInput ? complementInput.value.trim().slice(0, 120) : '',
    reference: referenceInput ? referenceInput.value.trim().slice(0, 160) : ''
  };

  try {
    localStorage.setItem(CUSTOMER_STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.warn('[Checkout] Não foi possível salvar memória do cliente:', err);
  }
}

function restoreCustomerMemory() {
  const memory = safeGetCustomerMemory();
  if (!memory) return;

  const fill = (id, value) => {
    const el = document.getElementById(id);
    if (el && !el.value && value) el.value = String(value);
  };

  fill('customer-name', memory.name);
  fill('customer-phone', memory.phone);
  fill('customer-street', memory.street);
  fill('customer-number', memory.number);
  fill('customer-complement', memory.complement);
  fill('customer-reference', memory.reference);

  const zoneSelect = document.getElementById('delivery-zone-select');
  if (zoneSelect && memory.zoneId && !zoneSelect.value) {
    zoneSelect.value = String(memory.zoneId);
    const matched = deliveryZones.find((z) => String(z.id) === String(memory.zoneId));
    if (matched) cart.setDeliveryZone(matched);
  }

  showCustomerMemoryNote(memory.name);
}

function showCustomerMemoryNote(name) {
  const section = document.querySelector('#checkout-form .checkout-section');
  if (!section || section.querySelector('.customer-memory-note')) return;

  const note = document.createElement('div');
  note.className = 'customer-memory-note visible';
  note.textContent = name
    ? `🦖 Bem-vindo de volta, ${String(name).split(' ')[0]}! Preenchemos seus dados salvos neste navegador.`
    : '🦖 Preenchemos seus dados salvos neste navegador.';
  section.insertBefore(note, section.firstChild);
}

/**
 * Load available delivery zones from the backend and populate the select element.
 */
export async function loadDeliveryZones() {
  const selectEl = document.getElementById('delivery-zone-select');
  if (!selectEl) return;

  try {
    deliveryZones = await api.getDeliveryZones();
    selectEl.innerHTML = '<option value="">Selecione o bairro...</option>';

    deliveryZones.forEach((zone) => {
      const option = document.createElement('option');
      option.value = String(zone.id);
      option.setAttribute('data-fee', String(zone.fee));
      const minOrderNotice = zone.min_order_value > 0 ? ` [Mín. ${formatCurrency(zone.min_order_value)}]` : '';
      option.textContent = `🦕 ${zone.name} — ${formatCurrency(zone.fee)} (~${zone.estimated_minutes} min)${minOrderNotice}`;
      selectEl.appendChild(option);
    });

    restoreCustomerMemory();
    updateCheckoutSummary();
  } catch (err) {
    console.error('[Checkout] Erro ao carregar zonas de entrega:', err);
    selectEl.innerHTML = '<option value="">Erro ao carregar bairros</option>';
  }
}

/**
 * Update the order summary inside the checkout modal in real-time.
 */
export function updateCheckoutSummary() {
  const subtotalEl = document.getElementById('checkout-summary-subtotal');
  const feeEl = document.getElementById('checkout-summary-fee');
  const totalEl = document.getElementById('checkout-summary-total');
  const discountRow = document.getElementById('checkout-summary-discount-row');
  const discountCodeEl = document.getElementById('checkout-summary-coupon-code');
  const discountValEl = document.getElementById('checkout-summary-discount');

  const state = cart.getState();

  if (subtotalEl) subtotalEl.textContent = formatCurrency(state.subtotal);

  if (discountRow) {
    if (state.couponCode && state.discountAmount > 0) {
      discountRow.classList.remove('d-none');
      if (discountCodeEl) discountCodeEl.textContent = state.couponCode;
      if (discountValEl) discountValEl.textContent = `- ${formatCurrency(state.discountAmount)}`;
    } else {
      discountRow.classList.add('d-none');
    }
  }

  if (feeEl) {
    if (state.deliveryType === 'pickup') {
      feeEl.textContent = 'Grátis (Retirada no Balcão)';
      feeEl.style.color = '#10B981';
    } else if (state.deliveryZone) {
      feeEl.textContent = formatCurrency(state.deliveryFee);
      feeEl.style.color = '';
    } else {
      feeEl.textContent = 'Selecione o bairro';
      feeEl.style.color = 'var(--color-text-muted)';
    }
  }

  if (totalEl) totalEl.textContent = formatCurrency(state.total);
}

/**
 * Setup delivery type toggle between Delivery (🛵) and Pickup (🏪) (DELIV-01, Pitfall 3).
 */
export function setupDeliveryTypeToggle() {
  const tabDelivery = document.getElementById('tab-delivery');
  const tabPickup = document.getElementById('tab-pickup');
  const deliveryFields = document.getElementById('delivery-fields-container');
  const zoneSelect = document.getElementById('delivery-zone-select');
  const streetInput = document.getElementById('customer-street');
  const numberInput = document.getElementById('customer-number');

  if (!tabDelivery || !tabPickup) return;

  const setDelivery = () => {
    tabDelivery.classList.add('active');
    tabPickup.classList.remove('active');
    if (deliveryFields) deliveryFields.style.display = 'block';

    if (zoneSelect) zoneSelect.required = true;
    if (streetInput) streetInput.required = true;
    if (numberInput) numberInput.required = true;

    cart.setDeliveryType('delivery');

    // Restore selected zone if already chosen
    if (zoneSelect && zoneSelect.value) {
      const zoneId = parseInt(zoneSelect.value, 10);
      const matched = deliveryZones.find((z) => z.id === zoneId);
      cart.setDeliveryZone(matched || null);
    } else {
      cart.setDeliveryZone(null);
    }

    updateCheckoutSummary();
  };

  const setPickup = () => {
    tabPickup.classList.add('active');
    tabDelivery.classList.remove('active');
    if (deliveryFields) deliveryFields.style.display = 'none';

    if (zoneSelect) zoneSelect.required = false;
    if (streetInput) streetInput.required = false;
    if (numberInput) numberInput.required = false;

    cart.setDeliveryType('pickup');
    updateCheckoutSummary();
  };

  tabDelivery.addEventListener('click', setDelivery);
  tabPickup.addEventListener('click', setPickup);
}

/**
 * Setup delivery zone selector change handler.
 */
export function setupDeliveryZoneListener() {
  const zoneSelect = document.getElementById('delivery-zone-select');
  if (!zoneSelect) return;

  zoneSelect.addEventListener('change', () => {
    const val = zoneSelect.value;
    if (!val) {
      cart.setDeliveryZone(null);
    } else {
      const zoneId = parseInt(val, 10);
      const matched = deliveryZones.find((z) => z.id === zoneId);
      cart.setDeliveryZone(matched || null);
    }
    updateCheckoutSummary();
  });
}

/**
 * Setup payment method selection and dynamic change field display.
 */
export function setupPaymentMethodListener() {
  const radios = document.querySelectorAll('input[name="payment_method"]');
  const changeGroup = document.getElementById('cash-change-group');

  radios.forEach((radio) => {
    radio.addEventListener('change', () => {
      if (radio.checked && radio.value === 'cash') {
        if (changeGroup) changeGroup.classList.remove('d-none');
      } else {
        if (changeGroup) changeGroup.classList.add('d-none');
      }
    });
  });
}

/**
 * Setup fulfillment time selection (Pedir Agora vs Agendar).
 */
export function setupFulfillmentTimeListener() {
  const radios = document.querySelectorAll('input[name="fulfillment_time_type"]');
  const scheduledGroup = document.getElementById('scheduled-for-group');
  const scheduledInput = document.getElementById('scheduled-for-input');

  // Set min datetime for scheduling (at least 30 minutes from now)
  if (scheduledInput) {
    const now = new Date(Date.now() + 30 * 60 * 1000);
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
    scheduledInput.min = localISOTime;
  }

  radios.forEach((radio) => {
    radio.addEventListener('change', () => {
      if (radio.checked && radio.value === 'scheduled') {
        if (scheduledGroup) scheduledGroup.classList.remove('d-none');
        if (scheduledInput) scheduledInput.required = true;
      } else {
        if (scheduledGroup) scheduledGroup.classList.add('d-none');
        if (scheduledInput) scheduledInput.required = false;
      }
    });
  });
}

/**
 * Setup coupon code validation, apply and removal.
 */
export function setupCouponActions() {
  const applyBtn = document.getElementById('apply-coupon-btn');
  const removeBtn = document.getElementById('remove-coupon-btn');
  const inputEl = document.getElementById('coupon-code-input');
  const msgEl = document.getElementById('coupon-message');

  const showMsg = (text, isError = false) => {
    if (!msgEl) return;
    msgEl.textContent = text;
    msgEl.style.color = isError ? 'var(--color-rustic-red)' : '#10B981';
    msgEl.classList.remove('d-none');
  };

  const clearMsg = () => {
    if (msgEl) {
      msgEl.textContent = '';
      msgEl.classList.add('d-none');
    }
  };

  if (applyBtn) {
    applyBtn.addEventListener('click', async () => {
      const code = inputEl ? inputEl.value.trim().toUpperCase() : '';
      if (!code) {
        showToast('Informe o código do cupom.', 'warning');
        return;
      }

      applyBtn.disabled = true;
      applyBtn.textContent = '...';

      try {
        const res = await api.validateCoupon({
          code,
          subtotal: cart.getSubtotal()
        });

        if (res.valid) {
          cart.setCoupon(res.code, res.discount_amount);
          showMsg(res.message || `Cupom aplicado! Desconto de ${formatCurrency(res.discount_amount)}`);
          if (applyBtn) applyBtn.classList.add('d-none');
          if (removeBtn) removeBtn.classList.remove('d-none');
          if (inputEl) inputEl.disabled = true;
          showToast(`Cupom ${res.code} aplicado com sucesso!`, 'success');
        } else {
          showMsg(res.message || 'Cupom inválido.', true);
        }
      } catch (err) {
        showMsg(err.message || 'Erro ao validar cupom.', true);
      } finally {
        applyBtn.disabled = false;
        applyBtn.textContent = 'Aplicar';
      }
    });
  }

  if (removeBtn) {
    removeBtn.addEventListener('click', () => {
      cart.removeCoupon();
      clearMsg();
      if (inputEl) {
        inputEl.value = '';
        inputEl.disabled = false;
      }
      if (applyBtn) applyBtn.classList.remove('d-none');
      if (removeBtn) removeBtn.classList.add('d-none');
      showToast('Cupom removido.', 'info');
    });
  }
}

/**
 * Setup phone and currency input masks.
 */
export function setupInputMasks() {
  const phoneInput = document.getElementById('customer-phone');
  if (phoneInput) {
    phoneInput.addEventListener('input', (e) => {
      const val = e.target.value;
      e.target.value = maskPhone(val);
    });
  }

  const changeInput = document.getElementById('change-for-input');
  if (changeInput) {
    changeInput.addEventListener('input', (e) => {
      const val = e.target.value;
      e.target.value = maskCurrencyInput(val);
    });
  }
}

/**
 * Open the checkout modal dialog.
 */
export function openCheckoutModal() {
  if (cart.items.length === 0) {
    showToast('Sua sacola está vazia. Escolha suas pizzas para continuar.', 'warning');
    return;
  }

  // Close the cart drawer
  toggleCartDrawer(false);

  const overlay = document.getElementById('checkout-modal-overlay');
  if (overlay) {
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  restoreCustomerMemory();
  updateCheckoutSummary();
}

/**
 * Close the checkout modal dialog.
 */
export function closeCheckoutModal() {
  const overlay = document.getElementById('checkout-modal-overlay');
  if (overlay) {
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
  }
  document.body.style.overflow = '';
}

/**
 * Validate customer checkout form fields prior to submission.
 * @returns {boolean}
 */
export function validateCheckoutForm() {
  const nameInput = document.getElementById('customer-name');
  const phoneInput = document.getElementById('customer-phone');
  const zoneSelect = document.getElementById('delivery-zone-select');
  const streetInput = document.getElementById('customer-street');
  const numberInput = document.getElementById('customer-number');
  const changeInput = document.getElementById('change-for-input');
  const paymentMethodEl = document.querySelector('input[name="payment_method"]:checked');

  const name = nameInput ? nameInput.value.trim() : '';
  const phone = phoneInput ? phoneInput.value.trim() : '';
  const phoneDigits = phone.replace(/\D/g, '');

  // 1. Customer Name validation
  if (!name || name.length < 2) {
    showToast('Por favor, informe seu nome completo.', 'warning');
    if (nameInput) nameInput.focus();
    return false;
  }

  // 2. Customer Phone validation (10 or 11 digits)
  if (!phoneDigits || phoneDigits.length < 10) {
    showToast('Por favor, informe um WhatsApp ou telefone válido com DDD.', 'warning');
    if (phoneInput) phoneInput.focus();
    return false;
  }

  // 3. Delivery address validation (if delivery type)
  if (cart.deliveryType === 'delivery') {
    if (!zoneSelect || !zoneSelect.value) {
      showToast('Por favor, selecione o bairro para entrega.', 'warning');
      if (zoneSelect) zoneSelect.focus();
      return false;
    }

    const street = streetInput ? streetInput.value.trim() : '';
    const number = numberInput ? numberInput.value.trim() : '';

    if (!street || !number) {
      showToast('Por favor, informe a rua e o número para entrega.', 'warning');
      if (!street && streetInput) streetInput.focus();
      else if (!number && numberInput) numberInput.focus();
      return false;
    }

    // Check minimum order value for delivery zone
    if (cart.deliveryZone && cart.deliveryZone.min_order_value > 0) {
      const minVal = Number(cart.deliveryZone.min_order_value);
      if (cart.getSubtotal() < minVal) {
        showToast(
          `O valor mínimo dos produtos para entrega no bairro ${cart.deliveryZone.name} é de ${formatCurrency(minVal)}. Adicione mais itens.`,
          'warning'
        );
        return false;
      }
    }
  }

  // 4. Fulfillment time scheduling validation
  const fulfillmentRadio = document.querySelector('input[name="fulfillment_time_type"]:checked');
  if (fulfillmentRadio && fulfillmentRadio.value === 'scheduled') {
    const scheduledInput = document.getElementById('scheduled-for-input');
    if (!scheduledInput || !scheduledInput.value) {
      showToast('Por favor, informe a data e horário para o agendamento do pedido.', 'warning');
      if (scheduledInput) scheduledInput.focus();
      return false;
    }

    const scheduledDate = new Date(scheduledInput.value);
    if (isNaN(scheduledDate.getTime()) || scheduledDate.getTime() < Date.now() + 14 * 60 * 1000) {
      showToast('O agendamento deve ser de pelo menos 15 minutos no futuro.', 'warning');
      if (scheduledInput) scheduledInput.focus();
      return false;
    }
  }

  // 4. Cash change validation (Pitfall 4)
  const paymentMethod = paymentMethodEl ? paymentMethodEl.value : 'pix';
  if (paymentMethod === 'cash' && changeInput && changeInput.value.trim()) {
    const rawVal = changeInput.value.replace(/\./g, '').replace(',', '.');
    const changeAmount = parseFloat(rawVal) || 0;
    const orderTotal = cart.getTotal();

    if (changeAmount < orderTotal) {
      showToast(
        `O valor do troco (${formatCurrency(changeAmount)}) deve ser maior ou igual ao total do pedido (${formatCurrency(orderTotal)}).`,
        'warning'
      );
      changeInput.focus();
      return false;
    }
  }

  return true;
}

/**
 * Handle checkout form submission to POST /api/v1/orders (T-04-07, T-04-08).
 * @param {Event} [event]
 */
export async function submitOrder(event) {
  if (event) event.preventDefault();

  if (isSubmitting) return;

  if (cart.items.length === 0) {
    showToast('Sua sacola está vazia.', 'warning');
    return;
  }

  if (!validateCheckoutForm()) {
    return;
  }

  const submitBtn = document.getElementById('submit-order-btn');
  const nameInput = document.getElementById('customer-name');
  const phoneInput = document.getElementById('customer-phone');
  const zoneSelect = document.getElementById('delivery-zone-select');
  const streetInput = document.getElementById('customer-street');
  const numberInput = document.getElementById('customer-number');
  const complementInput = document.getElementById('customer-complement');
  const referenceInput = document.getElementById('customer-reference');
  const changeInput = document.getElementById('change-for-input');
  const paymentMethodEl = document.querySelector('input[name="payment_method"]:checked');

  // Prevent double submits (Threat T-04-08)
  isSubmitting = true;
  toggleDeliveryRunner(true);
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = '🦖 Dino entregador correndo...';
  }

  try {
    const isDelivery = cart.deliveryType === 'delivery';
    const street = streetInput ? streetInput.value.trim() : '';
    const number = numberInput ? numberInput.value.trim() : '';
    const complement = complementInput ? complementInput.value.trim() : '';
    const reference = referenceInput ? referenceInput.value.trim() : '';

    let formattedAddress = null;
    if (isDelivery) {
      formattedAddress = `${street}, Nº ${number}`;
      if (complement) formattedAddress += ` - ${complement}`;
    }

    const paymentMethod = paymentMethodEl ? paymentMethodEl.value : 'pix';

    let changeFor = null;
    if (paymentMethod === 'cash' && changeInput && changeInput.value.trim()) {
      const rawVal = changeInput.value.replace(/\./g, '').replace(',', '.');
      const num = parseFloat(rawVal);
      if (!isNaN(num) && num > 0) {
        changeFor = num;
      }
    }

    // Build items payload (Threat T-04-07: prices are recalculated 100% on the server)
    const itemsPayload = cart.items.map((item) => ({
      item_type: item.itemType === 'combo' ? 'combo' : 'product',
      item_id: Number(item.itemId),
      quantity: Number(item.quantity),
      notes: item.notes ? String(item.notes).trim().slice(0, 255) : null,
      options: item.options && typeof item.options === 'object' ? item.options : null
    }));

    const fulfillmentRadio = document.querySelector('input[name="fulfillment_time_type"]:checked');
    const fulfillmentTimeType = fulfillmentRadio ? fulfillmentRadio.value : 'asap';
    const scheduledInput = document.getElementById('scheduled-for-input');
    let scheduledFor = null;
    if (fulfillmentTimeType === 'scheduled' && scheduledInput && scheduledInput.value) {
      scheduledFor = new Date(scheduledInput.value).toISOString();
    }

    const orderPayload = {
      customer_name: nameInput ? nameInput.value.trim() : '',
      customer_phone: phoneInput ? phoneInput.value.trim() : '',
      customer_address: formattedAddress,
      customer_reference: isDelivery && reference ? reference : null,
      delivery_type: isDelivery ? 'delivery' : 'pickup',
      delivery_zone_id: isDelivery && zoneSelect ? Number(zoneSelect.value) : null,
      payment_method: paymentMethod,
      change_for: changeFor,
      coupon_code: cart.couponCode || null,
      fulfillment_time_type: fulfillmentTimeType,
      scheduled_for: scheduledFor,
      items: itemsPayload
    };

    const [response] = await Promise.all([
      api.createOrder(orderPayload),
      runDeliveryTimeline()
    ]);

    saveCustomerMemory();

    // Order created successfully: clear cart and close checkout modal
    cart.clear();
    closeCheckoutModal();

    // Open Success / WhatsApp modal (D-07)
    openSuccessModal(response);
    showToast('🦖 Pedido realizado com sucesso!', 'success');
  } catch (err) {
    console.error('[Checkout] Erro ao criar pedido:', err);
    showToast(err.message || 'Erro ao enviar pedido. Tente novamente.', 'error');
  } finally {
    toggleDeliveryRunner(false);
    isSubmitting = false;
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Confirmar & Enviar para o WhatsApp';
    }
  }
}

/**
 * Initialize all checkout listeners and state.
 */
export function initCheckout() {
  loadDeliveryZones();
  setupDeliveryTypeToggle();
  setupDeliveryZoneListener();
  setupPaymentMethodListener();
  setupFulfillmentTimeListener();
  setupCouponActions();
  setupInputMasks();

  // Cart drawer checkout button
  const cartCheckoutBtn = document.getElementById('cart-checkout-btn');
  if (cartCheckoutBtn) {
    cartCheckoutBtn.addEventListener('click', () => {
      openCheckoutModal();
    });
  }

  // Close button and backdrop listeners
  const closeBtn = document.getElementById('checkout-modal-close-btn');
  const overlay = document.getElementById('checkout-modal-overlay');
  const form = document.getElementById('checkout-form');

  if (closeBtn) {
    closeBtn.addEventListener('click', closeCheckoutModal);
  }

  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeCheckoutModal();
    });
  }

  if (form) {
    form.addEventListener('submit', submitOrder);
  }

  // Subscribe cart changes to update checkout summary if open
  cart.addEventListener('cart:updated', () => {
    updateCheckoutSummary();
  });
}
