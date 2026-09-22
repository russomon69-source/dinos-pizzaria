/**
 * DINOS Pizzaria — Admin Coupons Controller
 * Handles discount coupons listing, live search, 1-click active toggles, and CRUD modals.
 */

import { adminApi } from './admin-api.js';

let allCoupons = [];
let toastFn = null;

export async function initCoupons(showToast) {
  toastFn = showToast;

  // Modal open/close listeners
  const btnNewCoupon = document.getElementById('btn-new-coupon');
  const modalCloseBtn = document.getElementById('modal-coupon-close');
  const modalCancelBtn = document.getElementById('btn-cancel-coupon');
  const modalCoupon = document.getElementById('modal-coupon');
  const couponForm = document.getElementById('coupon-form');

  if (btnNewCoupon) {
    btnNewCoupon.addEventListener('click', () => openCouponModal());
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeCouponModal());
  }

  if (modalCancelBtn) {
    modalCancelBtn.addEventListener('click', () => closeCouponModal());
  }

  if (modalCoupon) {
    modalCoupon.addEventListener('click', (e) => {
      if (e.target === modalCoupon) closeCouponModal();
    });
  }

  // Form submit handler
  if (couponForm) {
    couponForm.addEventListener('submit', handleCouponFormSubmit);
  }

  // Search input handler
  const searchInput = document.getElementById('coupons-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => filterAndRenderCoupons());
  }

  // Initial load
  await loadCoupons();
}

export async function loadCoupons() {
  const tbody = document.getElementById('coupons-table-body');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="table-loading-cell">
          <div class="spinner-inline"></div> Carregando cupons de desconto...
        </td>
      </tr>
    `;
  }

  try {
    allCoupons = await adminApi.getAdminCoupons();
    filterAndRenderCoupons();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="table-empty-cell text-danger">
            ⚠️ Falha ao carregar cupons: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

function filterAndRenderCoupons() {
  const tbody = document.getElementById('coupons-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('coupons-search');
  const query = searchInput?.value.trim().toLowerCase() || '';

  let filtered = allCoupons.filter((c) => {
    return !query ||
      c.code.toLowerCase().includes(query) ||
      (c.description && c.description.toLowerCase().includes(query));
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="table-empty-cell">
          Nenhum cupom encontrado com os filtros selecionados.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map((coupon) => {
    const isPercent = coupon.discount_type === 'percentage';
    const formattedDiscount = isPercent
      ? `${parseFloat(coupon.discount_value)}%`
      : formatCurrency(coupon.discount_value);

    const minSubtotal = coupon.min_subtotal && parseFloat(coupon.min_subtotal) > 0
      ? formatCurrency(coupon.min_subtotal)
      : 'Sem mínimo';

    const usesText = coupon.max_uses
      ? `${coupon.used_count || 0} / ${coupon.max_uses}`
      : `${coupon.used_count || 0} (ilimitado)`;

    return `
      <tr data-id="${coupon.id}">
        <td>
          <span class="price-tag" style="background: rgba(255, 174, 25, 0.15); color: #FFAE19; font-family: monospace; font-weight: 700;">
            ${escapeHtml(coupon.code)}
          </span>
        </td>
        <td>
          <div class="product-cell-name">${escapeHtml(coupon.description || 'Sem descrição')}</div>
          ${coupon.valid_until ? `<div class="product-cell-desc">⏳ Válido até: ${new Date(coupon.valid_until).toLocaleString('pt-BR')}</div>` : ''}
        </td>
        <td>
          <span class="category-badge" style="background: rgba(0, 230, 118, 0.15); color: #00e676; font-weight: 600;">
            ${formattedDiscount}
            ${isPercent && coupon.max_discount_amount ? `<small style="display:block; opacity:0.8;">Máx ${formatCurrency(coupon.max_discount_amount)}</small>` : ''}
          </span>
        </td>
        <td>
          <span class="category-badge">${minSubtotal}</span>
        </td>
        <td style="text-align: center;">
          <span class="category-badge">${escapeHtml(usesText)}</span>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Ativação do Cupom">
            <input type="checkbox" class="toggle-coupon-active" data-id="${coupon.id}" ${coupon.is_active ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <div class="action-buttons">
            <button type="button" class="btn-action btn-edit-coupon" data-id="${coupon.id}" title="Editar Cupom">
              ✏️
            </button>
            <button type="button" class="btn-action btn-delete-coupon" data-id="${coupon.id}" title="Excluir Cupom">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  attachCouponEventListeners(tbody);
}

function attachCouponEventListeners(tbody) {
  // Toggle Active
  tbody.querySelectorAll('.toggle-coupon-active').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleCouponActive(id);
        const coupon = allCoupons.find(c => c.id === id);
        if (coupon) coupon.is_active = isChecked;
        toastFn?.(`Status do cupom "${coupon?.code || 'Cupom'}" atualizado!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar status: ${err.message}`, 'error');
      }
    });
  });

  // Edit Coupon
  tbody.querySelectorAll('.btn-edit-coupon').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      const coupon = allCoupons.find(c => c.id === id);
      if (coupon) openCouponModal(coupon);
    });
  });

  // Delete Coupon
  tbody.querySelectorAll('.btn-delete-coupon').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id, 10);
      const coupon = allCoupons.find(c => c.id === id);
      const code = coupon?.code || 'este cupom';

      if (!confirm(`Tem certeza que deseja excluir o cupom "${code}"? Esta ação não pode ser desfeita.`)) {
        return;
      }

      try {
        await adminApi.deleteCoupon(id);
        allCoupons = allCoupons.filter(c => c.id !== id);
        filterAndRenderCoupons();
        toastFn?.(`Cupom "${code}" excluído com sucesso!`, 'success');
      } catch (err) {
        toastFn?.(`Erro ao excluir cupom: ${err.message}`, 'error');
      }
    });
  });
}

export function openCouponModal(coupon = null) {
  const modal = document.getElementById('modal-coupon');
  const modalTitle = document.getElementById('modal-coupon-title');
  const form = document.getElementById('coupon-form');

  if (!modal || !form) return;

  form.reset();

  const idInput = document.getElementById('coupon-id');
  const codeInput = document.getElementById('coupon-code');
  const descInput = document.getElementById('coupon-description');
  const typeSelect = document.getElementById('coupon-discount-type');
  const valueInput = document.getElementById('coupon-discount-value');
  const minSubtotalInput = document.getElementById('coupon-min-subtotal');
  const maxDiscountInput = document.getElementById('coupon-max-discount');
  const maxUsesInput = document.getElementById('coupon-max-uses');
  const validUntilInput = document.getElementById('coupon-valid-until');
  const activeCheckbox = document.getElementById('coupon-is-active');

  if (coupon) {
    if (modalTitle) modalTitle.textContent = 'Editar Cupom de Desconto';
    if (idInput) idInput.value = coupon.id;
    if (codeInput) codeInput.value = coupon.code || '';
    if (descInput) descInput.value = coupon.description || '';
    if (typeSelect) typeSelect.value = coupon.discount_type || 'percentage';
    if (valueInput) valueInput.value = parseFloat(coupon.discount_value).toFixed(2);
    if (minSubtotalInput) minSubtotalInput.value = coupon.min_subtotal ? parseFloat(coupon.min_subtotal).toFixed(2) : '';
    if (maxDiscountInput) maxDiscountInput.value = coupon.max_discount_amount ? parseFloat(coupon.max_discount_amount).toFixed(2) : '';
    if (maxUsesInput) maxUsesInput.value = coupon.max_uses != null ? coupon.max_uses : '';

    if (validUntilInput) {
      if (coupon.valid_until) {
        const d = new Date(coupon.valid_until);
        // format to YYYY-MM-DDTHH:mm
        const tzOffset = d.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(d.getTime() - tzOffset)).toISOString().slice(0, 16);
        validUntilInput.value = localISOTime;
      } else {
        validUntilInput.value = '';
      }
    }

    if (activeCheckbox) activeCheckbox.checked = Boolean(coupon.is_active);
  } else {
    if (modalTitle) modalTitle.textContent = 'Novo Cupom de Desconto';
    if (idInput) idInput.value = '';
    if (typeSelect) typeSelect.value = 'percentage';
    if (activeCheckbox) activeCheckbox.checked = true;
  }

  modal.classList.remove('d-none');
}

export function closeCouponModal() {
  const modal = document.getElementById('modal-coupon');
  if (modal) modal.classList.add('d-none');
}

async function handleCouponFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('coupon-id')?.value;
  const code = document.getElementById('coupon-code')?.value.trim().toUpperCase();
  const description = document.getElementById('coupon-description')?.value.trim() || null;
  const discountType = document.getElementById('coupon-discount-type')?.value;
  const discountVal = parseFloat(document.getElementById('coupon-discount-value')?.value);
  const minSubtotalRaw = document.getElementById('coupon-min-subtotal')?.value.trim();
  const minSubtotalVal = minSubtotalRaw ? parseFloat(minSubtotalRaw) : 0.00;
  const maxDiscountRaw = document.getElementById('coupon-max-discount')?.value.trim();
  const maxDiscountVal = maxDiscountRaw ? parseFloat(maxDiscountRaw) : null;
  const maxUsesRaw = document.getElementById('coupon-max-uses')?.value.trim();
  const maxUses = maxUsesRaw ? parseInt(maxUsesRaw, 10) : null;
  const validUntilRaw = document.getElementById('coupon-valid-until')?.value;
  const validUntil = validUntilRaw ? new Date(validUntilRaw).toISOString() : null;
  const isActive = document.getElementById('coupon-is-active')?.checked ?? true;

  const submitBtn = document.getElementById('btn-save-coupon');
  const spinner = submitBtn?.querySelector('.btn-spinner');

  if (!code || code.length < 2) {
    toastFn?.('Código do cupom deve ter pelo menos 2 caracteres.', 'warning');
    return;
  }

  if (isNaN(discountVal) || discountVal <= 0) {
    toastFn?.('Informe um valor de desconto válido maior que zero.', 'warning');
    return;
  }

  if (discountType === 'percentage' && discountVal > 100) {
    toastFn?.('Desconto percentual não pode ultrapassar 100%.', 'warning');
    return;
  }

  const payload = {
    code,
    description,
    discount_type: discountType,
    discount_value: discountVal,
    min_subtotal: minSubtotalVal,
    max_discount_amount: maxDiscountVal,
    max_uses: maxUses,
    valid_until: validUntil,
    is_active: isActive
  };

  try {
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    if (id) {
      await adminApi.updateCoupon(parseInt(id, 10), payload);
      toastFn?.(`Cupom "${code}" atualizado com sucesso!`, 'success');
    } else {
      await adminApi.createCoupon(payload);
      toastFn?.(`Cupom "${code}" cadastrado com sucesso!`, 'success');
    }

    closeCouponModal();
    await loadCoupons();
  } catch (err) {
    toastFn?.(`Erro ao salvar cupom: ${err.message}`, 'error');
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (spinner) spinner.classList.add('d-none');
  }
}

function formatCurrency(value) {
  const num = typeof value === 'number' ? value : parseFloat(value) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
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
