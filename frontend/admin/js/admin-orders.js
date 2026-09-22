/**
 * DINOS Pizzaria — Admin Orders & Kanban Controller
 * Coordinates 5-column Kanban board, 1-click status mutations, modal inspection,
 * and 20-second resilient auto-polling with audio chime alerts.
 */

import { adminApi } from './admin-api.js';
import { playNewOrderSound } from './admin-sound.js';

const POLLING_INTERVAL_MS = 20000;

// Kanban column definitions mapped strictly to backend enum values
const STATUS_CONFIG = {
  pending: {
    columnId: 'cards-col-pending',
    countId: 'count-col-pending',
    label: 'Novo / Pendente',
    badgeClass: 'order-badge--delivery',
    nextStatus: 'in_preparation',
    nextLabel: 'Iniciar Preparo 🔥',
    allowCancel: true
  },
  confirmed: {
    columnId: 'cards-col-pending',
    countId: 'count-col-pending',
    label: 'Confirmado',
    badgeClass: 'order-badge--delivery',
    nextStatus: 'in_preparation',
    nextLabel: 'Iniciar Preparo 🔥',
    allowCancel: true
  },
  in_preparation: {
    columnId: 'cards-col-in_preparation',
    countId: 'count-col-in_preparation',
    label: 'Em Preparo',
    badgeClass: 'order-badge--pickup',
    nextStatus: 'out_for_delivery',
    nextLabel: 'Despachar 🛵',
    allowCancel: true
  },
  out_for_delivery: {
    columnId: 'cards-col-out_for_delivery',
    countId: 'count-col-out_for_delivery',
    label: 'Em Rota',
    badgeClass: 'order-badge--card',
    nextStatus: 'delivered',
    nextLabel: 'Concluir Entrega ✅',
    allowCancel: true
  },
  delivered: {
    columnId: 'cards-col-delivered',
    countId: 'count-col-delivered',
    label: 'Entregue',
    badgeClass: 'order-badge--pix',
    nextStatus: null,
    nextLabel: null,
    allowCancel: false
  },
  cancelled: {
    columnId: 'cards-col-cancelled',
    countId: 'count-col-cancelled',
    label: 'Cancelado',
    badgeClass: 'order-badge--cash',
    nextStatus: null,
    nextLabel: null,
    allowCancel: false
  }
};

let allOrders = [];
let knownOrderIds = new Set();
let isFirstLoad = true;
let pollingTimer = null;
let toastFn = null;
let activeModalOrderId = null;

/**
 * Initialize Orders Controller
 * @param {Function} showToast
 */
export function initOrders(showToast) {
  toastFn = showToast;

  // Refresh button
  const btnRefresh = document.getElementById('btn-refresh-orders');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      btnRefresh.disabled = true;
      try {
        await loadOrders(false);
        toastFn?.('Pedidos atualizados com sucesso!', 'info');
      } finally {
        btnRefresh.disabled = false;
      }
    });
  }

  // Order Details Modal Listeners
  const modalOrder = document.getElementById('modal-order-details');
  const modalCloseBtn = document.getElementById('modal-order-close');
  const btnAdvance = document.getElementById('btn-advance-order-status');
  const btnCancel = document.getElementById('btn-cancel-order-status');

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeOrderModal());
  }

  if (modalOrder) {
    modalOrder.addEventListener('click', (e) => {
      if (e.target === modalOrder) closeOrderModal();
    });
  }

  if (btnAdvance) {
    btnAdvance.addEventListener('click', handleModalStatusAdvance);
  }

  if (btnCancel) {
    btnCancel.addEventListener('click', handleModalOrderCancel);
  }

  // Load initial orders
  loadOrders(true);
  startOrderPolling();
}

/**
 * Start 20s background polling
 */
export function startOrderPolling() {
  stopOrderPolling();
  pollingTimer = setInterval(() => {
    // Only poll if user is authenticated
    if (adminApi.getToken()) {
      loadOrders(false);
    }
  }, POLLING_INTERVAL_MS);
}

/**
 * Stop polling timer
 */
export function stopOrderPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

/**
 * Fetch and render orders from backend
 * @param {boolean} isInitial
 */
export async function loadOrders(isInitial = false) {
  try {
    const orders = await adminApi.getOrders(null, 100);
    const prevOrderIds = new Set(knownOrderIds);
    let newIncomingCount = 0;

    allOrders = Array.isArray(orders) ? orders : [];

    // Detect new orders for audio alerts and visual pulsing
    allOrders.forEach((order) => {
      if (!prevOrderIds.has(order.id)) {
        knownOrderIds.add(order.id);
        if (!isInitial && (order.status === 'pending' || order.status === 'confirmed')) {
          newIncomingCount++;
          order._isNew = true;
        }
      }
    });

    // Play chime sound and toast if new orders arrived during polling
    if (!isInitial && newIncomingCount > 0) {
      playNewOrderSound();
      toastFn?.(
        newIncomingCount === 1
          ? '🔔 Novo pedido recebido!'
          : `🔔 ${newIncomingCount} novos pedidos recebidos!`,
        'success'
      );
    }

    renderKanbanBoard();
    updateSidebarBadge();

    // If modal is currently open inspecting an order, refresh its modal view seamlessly
    if (activeModalOrderId) {
      const currentOrder = allOrders.find(o => o.id === activeModalOrderId);
      if (currentOrder) {
        populateModalData(currentOrder);
      }
    }
  } catch (err) {
    console.error('Erro ao buscar pedidos:', err);
    if (isInitial) {
      toastFn?.(`Falha ao carregar pedidos: ${err.message}`, 'error');
    }
  } finally {
    isFirstLoad = false;
  }
}

/**
 * Render orders into the 5 Kanban Columns
 */
function renderKanbanBoard() {
  const columnGroups = {
    cards_col_pending: [],
    cards_col_in_preparation: [],
    cards_col_out_for_delivery: [],
    cards_col_delivered: [],
    cards_col_cancelled: []
  };

  allOrders.forEach((order) => {
    const status = order.status || 'pending';
    if (status === 'pending' || status === 'confirmed') {
      columnGroups.cards_col_pending.push(order);
    } else if (status === 'in_preparation') {
      columnGroups.cards_col_in_preparation.push(order);
    } else if (status === 'out_for_delivery') {
      columnGroups.cards_col_out_for_delivery.push(order);
    } else if (status === 'delivered') {
      columnGroups.cards_col_delivered.push(order);
    } else if (status === 'cancelled') {
      columnGroups.cards_col_cancelled.push(order);
    }
  });

  // Render each column container and update count headers
  renderColumn('cards-col-pending', 'count-col-pending', columnGroups.cards_col_pending, 'Nenhum pedido novo');
  renderColumn('cards-col-in_preparation', 'count-col-in_preparation', columnGroups.cards_col_in_preparation, 'Nenhum pedido em preparo');
  renderColumn('cards-col-out_for_delivery', 'count-col-out_for_delivery', columnGroups.cards_col_out_for_delivery, 'Nenhum pedido em rota');
  renderColumn('cards-col-delivered', 'count-col-delivered', columnGroups.cards_col_delivered, 'Nenhum pedido concluído');
  renderColumn('cards-col-cancelled', 'count-col-cancelled', columnGroups.cards_col_cancelled, 'Nenhum pedido cancelado');
}

/**
 * Render single Kanban column cards
 */
function renderColumn(containerId, countId, orders, emptyText) {
  const container = document.getElementById(containerId);
  const countEl = document.getElementById(countId);

  if (countEl) {
    countEl.textContent = String(orders.length);
  }

  if (!container) return;

  if (orders.length === 0) {
    container.innerHTML = `<div class="kanban-empty-column">${emptyText}</div>`;
    return;
  }

  container.innerHTML = orders.map((order) => {
    const config = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;
    const timeFormatted = formatTime(order.created_at);
    const totalFormatted = formatCurrency(order.total_amount);
    const deliveryTypeBadge = order.delivery_type === 'pickup'
      ? `<span class="order-badge order-badge--pickup">Retirada</span>`
      : `<span class="order-badge order-badge--delivery">Delivery</span>`;
    const scheduledBadge = order.fulfillment_time_type === 'scheduled' && order.scheduled_for
      ? `<span class="order-badge" style="background: rgba(255, 174, 25, 0.15); color: #FFAE19;">📅 ${new Date(order.scheduled_for).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>`
      : '';
    const paymentBadge = formatPaymentBadge(order.payment_method);
    const itemsSummary = formatItemsSummary(order.items);
    const pulseClass = order._isNew ? 'order-card--new-pulsing' : '';

    return `
      <div class="order-card ${pulseClass}" data-order-id="${order.id}">
        <div class="order-card-header">
          <span class="order-number">#${String(order.id).padStart(3, '0')}</span>
          <span class="order-time">${timeFormatted}</span>
        </div>

        <div class="order-card-customer">${escapeHtml(order.customer_name)}</div>

        <div class="order-badge-row">
          ${deliveryTypeBadge}
          ${scheduledBadge}
          ${paymentBadge}
        </div>

        <div class="order-card-items-preview">
          ${escapeHtml(itemsSummary)}
        </div>

        <div class="order-card-footer">
          <span class="order-card-total">${totalFormatted}</span>
          ${config.nextStatus ? `
            <button
              type="button"
              class="btn btn-primary btn-sm order-card-action-btn btn-quick-advance"
              data-order-id="${order.id}"
              data-next-status="${config.nextStatus}"
            >
              ${config.nextLabel}
            </button>
          ` : `
            <button
              type="button"
              class="btn btn-secondary btn-sm order-card-action-btn btn-view-details"
              data-order-id="${order.id}"
            >
              Ver Detalhes 🔍
            </button>
          `}
        </div>
      </div>
    `;
  }).join('');

  attachCardEventListeners(container);
}

/**
 * Attach interaction events to cards in container
 */
function attachCardEventListeners(container) {
  // Click on card opens full details inspection modal
  container.querySelectorAll('.order-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      // Do not trigger modal if clicking directly on quick action button
      if (e.target.closest('.btn-quick-advance')) return;

      const orderId = parseInt(card.dataset.orderId, 10);
      const order = allOrders.find(o => o.id === orderId);
      if (order) {
        order._isNew = false;
        card.classList.remove('order-card--new-pulsing');
        openOrderModal(order);
      }
    });
  });

  // Quick 1-click status advance
  container.querySelectorAll('.btn-quick-advance').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const orderId = parseInt(btn.dataset.orderId, 10);
      const nextStatus = btn.dataset.nextStatus;
      await mutateOrderStatus(orderId, nextStatus, btn);
    });
  });

  // View details buttons on terminal columns
  container.querySelectorAll('.btn-view-details').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const orderId = parseInt(btn.dataset.orderId, 10);
      const order = allOrders.find(o => o.id === orderId);
      if (order) openOrderModal(order);
    });
  });
}

/**
 * Mutate Order Status via API and refresh Kanban
 */
async function mutateOrderStatus(orderId, newStatus, triggerBtn = null) {
  try {
    if (triggerBtn) triggerBtn.disabled = true;

    await adminApi.updateOrderStatus(orderId, newStatus);
    toastFn?.(`Pedido #${String(orderId).padStart(3, '0')} atualizado com sucesso!`, 'success');

    // Update local state and re-render
    const order = allOrders.find(o => o.id === orderId);
    if (order) {
      order.status = newStatus;
      order._isNew = false;
    }

    renderKanbanBoard();
    updateSidebarBadge();

    // If modal is open for this order, update modal content
    if (activeModalOrderId === orderId && order) {
      populateModalData(order);
    }
  } catch (err) {
    toastFn?.(`Erro ao atualizar status: ${err.message}`, 'error');
  } finally {
    if (triggerBtn) triggerBtn.disabled = false;
  }
}

/**
 * Update Sidebar Badge Count for pending/active orders
 */
function updateSidebarBadge() {
  const badge = document.getElementById('orders-badge');
  if (!badge) return;

  const activeCount = allOrders.filter(
    o => o.status === 'pending' || o.status === 'confirmed' || o.status === 'in_preparation'
  ).length;

  if (activeCount > 0) {
    badge.textContent = String(activeCount);
    badge.classList.remove('d-none');
  } else {
    badge.classList.add('d-none');
  }
}

/**
 * Open Order Details Modal
 */
export function openOrderModal(order) {
  const modal = document.getElementById('modal-order-details');
  if (!modal || !order) return;

  activeModalOrderId = order.id;
  populateModalData(order);
  modal.classList.remove('d-none');
}

/**
 * Populate Order Data inside Modal
 */
function populateModalData(order) {
  const titleEl = document.getElementById('modal-order-title');
  const statusBadgeEl = document.getElementById('order-detail-status-badge');
  const customerNameEl = document.getElementById('order-customer-name');
  const customerPhoneEl = document.getElementById('order-customer-phone');
  const whatsappLinkEl = document.getElementById('order-whatsapp-link');
  const createdAtEl = document.getElementById('order-created-at');
  const deliveryTypeEl = document.getElementById('order-delivery-type');
  const fulfillmentTypeEl = document.getElementById('order-fulfillment-type');
  const addressEl = document.getElementById('order-address');
  const paymentMethodEl = document.getElementById('order-payment-method');
  const changeWrapperEl = document.getElementById('order-change-wrapper');
  const changeForEl = document.getElementById('order-change-for');
  const notesBlockEl = document.getElementById('order-notes-block');
  const notesEl = document.getElementById('order-customer-notes');
  const itemsContainer = document.getElementById('order-items-container');
  const subtotalEl = document.getElementById('order-subtotal-val');
  const discountRowEl = document.getElementById('order-discount-row');
  const couponCodeEl = document.getElementById('order-coupon-code');
  const discountValEl = document.getElementById('order-discount-val');
  const deliveryFeeEl = document.getElementById('order-delivery-fee-val');
  const totalEl = document.getElementById('order-total-val');
  const btnAdvance = document.getElementById('btn-advance-order-status');
  const btnAdvanceLabel = document.getElementById('btn-advance-label');
  const btnCancel = document.getElementById('btn-cancel-order-status');

  const config = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;

  if (titleEl) {
    titleEl.textContent = `Pedido #${String(order.id).padStart(3, '0')}`;
  }

  if (statusBadgeEl) {
    statusBadgeEl.textContent = config.label.toUpperCase();
    statusBadgeEl.className = `order-badge ${config.badgeClass}`;
  }

  if (customerNameEl) customerNameEl.textContent = order.customer_name || 'Não informado';
  if (customerPhoneEl) customerPhoneEl.textContent = order.customer_phone || 'Não informado';

  // WhatsApp direct link button
  if (whatsappLinkEl) {
    const rawDigits = (order.customer_phone || '').replace(/\D/g, '');
    if (rawDigits.length >= 10) {
      const fullPhone = rawDigits.startsWith('55') ? rawDigits : `55${rawDigits}`;
      whatsappLinkEl.href = `https://wa.me/${fullPhone}`;
      whatsappLinkEl.classList.remove('d-none');
    } else {
      whatsappLinkEl.classList.add('d-none');
    }
  }

  if (createdAtEl) createdAtEl.textContent = formatDateTime(order.created_at);
  if (deliveryTypeEl) {
    deliveryTypeEl.textContent = order.delivery_type === 'pickup' ? 'Retirada no Balcão' : 'Entrega em Domicílio (Delivery)';
  }

  if (fulfillmentTypeEl) {
    if (order.fulfillment_time_type === 'scheduled' && order.scheduled_for) {
      fulfillmentTypeEl.innerHTML = `<span style="color: #FFAE19; font-weight: 600;">📅 Agendado para ${formatDateTime(order.scheduled_for)}</span>`;
    } else {
      fulfillmentTypeEl.textContent = '⚡ Imediato (O mais rápido possível)';
    }
  }

  if (addressEl) {
    if (order.delivery_type === 'pickup') {
      addressEl.textContent = 'Retirada presencial na loja DINOS';
    } else {
      const parts = [
        order.delivery_street ? `${order.delivery_street}, ${order.delivery_number || 'S/N'}` : '',
        order.delivery_complement ? `(${order.delivery_complement})` : '',
        order.delivery_neighborhood ? `- Bairro: ${order.delivery_neighborhood}` : '',
        order.delivery_reference ? `[Ref: ${order.delivery_reference}]` : ''
      ].filter(Boolean);
      addressEl.textContent = parts.join(' ') || 'Endereço não detalhado';
    }
  }

  if (paymentMethodEl) {
    const pmap = { pix: 'PIX (Chave Dinâmica)', credit_card: 'Cartão de Crédito', debit_card: 'Cartão de Débito', cash: 'Dinheiro na Entrega' };
    paymentMethodEl.textContent = pmap[order.payment_method] || order.payment_method;
  }

  if (changeWrapperEl && changeForEl) {
    if (order.payment_method === 'cash' && order.change_for) {
      changeForEl.textContent = formatCurrency(order.change_for);
      changeWrapperEl.classList.remove('d-none');
    } else {
      changeWrapperEl.classList.add('d-none');
    }
  }

  if (notesBlockEl && notesEl) {
    if (order.customer_notes && order.customer_notes.trim()) {
      notesEl.textContent = order.customer_notes;
      notesBlockEl.classList.remove('d-none');
    } else {
      notesBlockEl.classList.add('d-none');
    }
  }

  // Items breakdown list
  if (itemsContainer) {
    const items = Array.isArray(order.items) ? order.items : [];
    if (items.length === 0) {
      itemsContainer.innerHTML = `<div class="order-item-row"><span class="order-item-title">Nenhum item registrado.</span></div>`;
    } else {
      itemsContainer.innerHTML = items.map((item) => {
        const itemTotal = formatCurrency(item.unit_price * item.quantity);
        return `
          <div class="order-item-row">
            <div class="order-item-qty-title">
              <span class="order-item-title">${item.quantity}x ${escapeHtml(item.item_title)}</span>
              ${item.customization_notes ? `<span class="order-item-notes">Obs: ${escapeHtml(item.customization_notes)}</span>` : ''}
            </div>
            <span class="order-item-price">${itemTotal}</span>
          </div>
        `;
      }).join('');
    }
  }

  // Summary financials
  if (subtotalEl) subtotalEl.textContent = formatCurrency(order.subtotal);

  if (discountRowEl && discountValEl && couponCodeEl) {
    const discountAmt = parseFloat(order.discount_amount || 0);
    if (discountAmt > 0) {
      couponCodeEl.textContent = order.coupon_code || 'Cupom';
      discountValEl.textContent = `- ${formatCurrency(discountAmt)}`;
      discountRowEl.classList.remove('d-none');
    } else {
      discountRowEl.classList.add('d-none');
    }
  }

  if (deliveryFeeEl) deliveryFeeEl.textContent = formatCurrency(order.delivery_fee);
  if (totalEl) totalEl.textContent = formatCurrency(order.total_amount);

  // Status Action Buttons
  if (btnAdvance && btnAdvanceLabel) {
    if (config.nextStatus) {
      btnAdvance.classList.remove('d-none');
      btnAdvanceLabel.textContent = config.nextLabel;
      btnAdvance.dataset.nextStatus = config.nextStatus;
    } else {
      btnAdvance.classList.add('d-none');
    }
  }

  if (btnCancel) {
    if (config.allowCancel) {
      btnCancel.classList.remove('d-none');
    } else {
      btnCancel.classList.add('d-none');
    }
  }
}

/**
 * Handle Advance Status Click inside Modal
 */
async function handleModalStatusAdvance() {
  if (!activeModalOrderId) return;
  const btnAdvance = document.getElementById('btn-advance-order-status');
  const spinner = btnAdvance?.querySelector('.btn-spinner');
  const nextStatus = btnAdvance?.dataset.nextStatus;

  if (!nextStatus) return;

  try {
    if (btnAdvance) btnAdvance.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    await mutateOrderStatus(activeModalOrderId, nextStatus);
  } finally {
    if (btnAdvance) btnAdvance.disabled = false;
    if (spinner) spinner.classList.add('d-none');
  }
}

/**
 * Handle Order Cancellation Click inside Modal
 */
async function handleModalOrderCancel() {
  if (!activeModalOrderId) return;

  if (!confirm(`Tem certeza que deseja CANCELAR o Pedido #${String(activeModalOrderId).padStart(3, '0')}?`)) {
    return;
  }

  const btnCancel = document.getElementById('btn-cancel-order-status');
  try {
    if (btnCancel) btnCancel.disabled = true;
    await mutateOrderStatus(activeModalOrderId, 'cancelled');
  } finally {
    if (btnCancel) btnCancel.disabled = false;
  }
}

/**
 * Close Order Modal
 */
export function closeOrderModal() {
  const modal = document.getElementById('modal-order-details');
  if (modal) modal.classList.add('d-none');
  activeModalOrderId = null;
}

// Helpers
function formatCurrency(value) {
  const num = typeof value === 'number' ? value : parseFloat(value) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return `${d.toLocaleDateString('pt-BR')} às ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return dateStr;
  }
}

function formatPaymentBadge(method) {
  if (method === 'pix') return `<span class="order-badge order-badge--pix">PIX</span>`;
  if (method === 'credit_card' || method === 'debit_card') return `<span class="order-badge order-badge--card">Cartão</span>`;
  if (method === 'cash') return `<span class="order-badge order-badge--cash">Dinheiro</span>`;
  return `<span class="order-badge">${escapeHtml(method || 'Outro')}</span>`;
}

function formatItemsSummary(items) {
  if (!Array.isArray(items) || items.length === 0) return 'Sem itens';
  return items.map(i => `${i.quantity}x ${i.item_title}`).join(', ');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
