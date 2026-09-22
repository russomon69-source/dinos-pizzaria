/**
 * DINOS Pizzaria — Admin Delivery Zones Controller
 * Handles delivery zones listing, live search, 1-click active toggles, and CRUD modals.
 */

import { adminApi } from './admin-api.js';

let allZones = [];
let toastFn = null;

export async function initZones(showToast) {
  toastFn = showToast;

  // Modal open/close listeners
  const btnNewZone = document.getElementById('btn-new-zone');
  const modalCloseBtn = document.getElementById('modal-zone-close');
  const modalCancelBtn = document.getElementById('btn-cancel-zone');
  const modalZone = document.getElementById('modal-zone');
  const zoneForm = document.getElementById('zone-form');

  if (btnNewZone) {
    btnNewZone.addEventListener('click', () => openZoneModal());
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeZoneModal());
  }

  if (modalCancelBtn) {
    modalCancelBtn.addEventListener('click', () => closeZoneModal());
  }

  if (modalZone) {
    modalZone.addEventListener('click', (e) => {
      if (e.target === modalZone) closeZoneModal();
    });
  }

  // Form submit handler
  if (zoneForm) {
    zoneForm.addEventListener('submit', handleZoneFormSubmit);
  }

  // Search input handler
  const searchInput = document.getElementById('zones-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => filterAndRenderZones());
  }

  // Initial load
  await loadZones();
}

export async function loadZones() {
  const tbody = document.getElementById('zones-table-body');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-loading-cell">
          <div class="spinner-inline"></div> Carregando bairros de entrega...
        </td>
      </tr>
    `;
  }

  try {
    allZones = await adminApi.getAdminZones();
    filterAndRenderZones();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="table-empty-cell text-danger">
            ⚠️ Falha ao carregar bairros: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

function filterAndRenderZones() {
  const tbody = document.getElementById('zones-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('zones-search');
  const query = searchInput?.value.trim().toLowerCase() || '';

  let filtered = allZones.filter((zone) => {
    return !query || zone.name.toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-empty-cell">
          Nenhum bairro encontrado com os filtros selecionados.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map((zone) => {
    const formattedFee = formatCurrency(zone.fee);
    const minOrder = zone.min_order_value && parseFloat(zone.min_order_value) > 0
      ? formatCurrency(zone.min_order_value)
      : 'Sem mínimo';
    const estimatedTime = zone.estimated_minutes ? `${zone.estimated_minutes} min` : '—';

    return `
      <tr data-id="${zone.id}">
        <td>
          <div class="product-cell-name">${escapeHtml(zone.name)}</div>
        </td>
        <td>
          <span class="price-tag">${formattedFee}</span>
        </td>
        <td>
          <span class="category-badge">${minOrder}</span>
        </td>
        <td>
          <span class="category-badge">⏱️ ${escapeHtml(estimatedTime)}</span>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Disponibilidade do Bairro">
            <input type="checkbox" class="toggle-zone-active" data-id="${zone.id}" ${zone.is_active ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <div class="action-buttons">
            <button type="button" class="btn-action btn-edit-zone" data-id="${zone.id}" title="Editar Bairro">
              ✏️
            </button>
            <button type="button" class="btn-action btn-delete-zone" data-id="${zone.id}" title="Excluir Bairro">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  attachZoneEventListeners(tbody);
}

function attachZoneEventListeners(tbody) {
  // Toggle Active
  tbody.querySelectorAll('.toggle-zone-active').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleZoneActive(id);
        const zone = allZones.find(z => z.id === id);
        if (zone) zone.is_active = isChecked;
        toastFn?.(`Disponibilidade do bairro "${zone?.name || 'Bairro'}" atualizada!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar disponibilidade: ${err.message}`, 'error');
      }
    });
  });

  // Edit Zone
  tbody.querySelectorAll('.btn-edit-zone').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      const zone = allZones.find(z => z.id === id);
      if (zone) openZoneModal(zone);
    });
  });

  // Delete Zone
  tbody.querySelectorAll('.btn-delete-zone').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id, 10);
      const zone = allZones.find(z => z.id === id);
      const name = zone?.name || 'este bairro';

      if (!confirm(`Tem certeza que deseja excluir o bairro "${name}"? Esta ação não pode ser desfeita.`)) {
        return;
      }

      try {
        await adminApi.deleteZone(id);
        allZones = allZones.filter(z => z.id !== id);
        filterAndRenderZones();
        toastFn?.(`Bairro "${name}" excluído com sucesso!`, 'success');
      } catch (err) {
        toastFn?.(`Erro ao excluir bairro: ${err.message}`, 'error');
      }
    });
  });
}

export function openZoneModal(zone = null) {
  const modal = document.getElementById('modal-zone');
  const modalTitle = document.getElementById('modal-zone-title');
  const form = document.getElementById('zone-form');

  if (!modal || !form) return;

  form.reset();

  const idInput = document.getElementById('zone-id');
  const nameInput = document.getElementById('zone-name');
  const feeInput = document.getElementById('zone-fee');
  const minOrderInput = document.getElementById('zone-min-order-value');
  const timeInput = document.getElementById('zone-estimated-minutes');
  const activeCheckbox = document.getElementById('zone-is-active');

  if (zone) {
    if (modalTitle) modalTitle.textContent = 'Editar Bairro de Entrega';
    if (idInput) idInput.value = zone.id;
    if (nameInput) nameInput.value = zone.name || '';
    if (feeInput) feeInput.value = parseFloat(zone.fee).toFixed(2);
    if (minOrderInput) minOrderInput.value = zone.min_order_value ? parseFloat(zone.min_order_value).toFixed(2) : '';
    if (timeInput) timeInput.value = zone.estimated_minutes != null ? zone.estimated_minutes : '';
    if (activeCheckbox) activeCheckbox.checked = Boolean(zone.is_active);
  } else {
    if (modalTitle) modalTitle.textContent = 'Novo Bairro de Entrega';
    if (idInput) idInput.value = '';
    if (minOrderInput) minOrderInput.value = '';
    if (activeCheckbox) activeCheckbox.checked = true;
  }

  modal.classList.remove('d-none');
}

export function closeZoneModal() {
  const modal = document.getElementById('modal-zone');
  if (modal) modal.classList.add('d-none');
}

async function handleZoneFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('zone-id')?.value;
  const name = document.getElementById('zone-name')?.value.trim();
  const feeVal = parseFloat(document.getElementById('zone-fee')?.value);
  const minOrderRaw = document.getElementById('zone-min-order-value')?.value.trim();
  const minOrderVal = minOrderRaw ? parseFloat(minOrderRaw) : 0.00;
  const timeValRaw = document.getElementById('zone-estimated-minutes')?.value.trim();
  const estimatedMinutes = timeValRaw ? parseInt(timeValRaw, 10) : null;
  const isActive = document.getElementById('zone-is-active')?.checked ?? true;

  const submitBtn = document.getElementById('btn-save-zone');
  const spinner = submitBtn?.querySelector('.btn-spinner');

  if (!name || name.length < 2) {
    toastFn?.('Nome do bairro deve ter pelo menos 2 caracteres.', 'warning');
    return;
  }

  if (isNaN(feeVal) || feeVal < 0) {
    toastFn?.('Por favor, informe uma taxa de entrega válida (maior ou igual a 0).', 'warning');
    return;
  }

  if (isNaN(minOrderVal) || minOrderVal < 0) {
    toastFn?.('Por favor, informe um valor de pedido mínimo válido (maior ou igual a 0).', 'warning');
    return;
  }

  if (estimatedMinutes !== null && (isNaN(estimatedMinutes) || estimatedMinutes <= 0)) {
    toastFn?.('O tempo estimado deve ser um número inteiro positivo.', 'warning');
    return;
  }

  const payload = {
    name,
    fee: feeVal,
    min_order_value: minOrderVal,
    estimated_minutes: estimatedMinutes,
    is_active: isActive
  };

  try {
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    if (id) {
      await adminApi.updateZone(parseInt(id, 10), payload);
      toastFn?.(`Bairro "${name}" atualizado com sucesso!`, 'success');
    } else {
      await adminApi.createZone(payload);
      toastFn?.(`Bairro "${name}" cadastrado com sucesso!`, 'success');
    }

    closeZoneModal();
    await loadZones();
  } catch (err) {
    toastFn?.(`Erro ao salvar bairro: ${err.message}`, 'error');
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
