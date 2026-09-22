/**
 * DINOS Pizzaria — Admin Combos Controller
 * Handles combos listing, live search, 1-click toggles, and CRUD modals.
 */

import { adminApi } from './admin-api.js';
import { setupDropzone } from './admin-dropzone.js';

let allCombos = [];
let comboDropzone = null;
let toastFn = null;

export async function initCombos(showToast) {
  toastFn = showToast;

  // Initialize dropzone for combos
  const dropzoneEl = document.getElementById('combo-dropzone');
  const fileInputEl = document.getElementById('combo-file-input');
  const previewWrapperEl = document.getElementById('combo-preview-wrapper');
  const previewImgEl = document.getElementById('combo-image-preview');
  const removeBtnEl = document.getElementById('combo-remove-image-btn');
  const hiddenInputEl = document.getElementById('combo-image-url');

  comboDropzone = setupDropzone({
    dropzoneEl,
    fileInputEl,
    previewWrapperEl,
    previewImgEl,
    removeBtnEl,
    hiddenInputEl,
    onUploadSuccess: (url) => {
      toastFn?.('Foto do combo enviada com sucesso!', 'success');
    },
    onUploadError: (err) => {
      toastFn?.(err.message || 'Falha ao enviar foto do combo.', 'error');
    }
  });

  // Modal open/close listeners
  const btnNewCombo = document.getElementById('btn-new-combo');
  const modalCloseBtn = document.getElementById('modal-combo-close');
  const modalCancelBtn = document.getElementById('btn-cancel-combo');
  const modalCombo = document.getElementById('modal-combo');
  const comboForm = document.getElementById('combo-form');

  if (btnNewCombo) {
    btnNewCombo.addEventListener('click', () => openComboModal());
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeComboModal());
  }

  if (modalCancelBtn) {
    modalCancelBtn.addEventListener('click', () => closeComboModal());
  }

  if (modalCombo) {
    modalCombo.addEventListener('click', (e) => {
      if (e.target === modalCombo) closeComboModal();
    });
  }

  // Form submit handler
  if (comboForm) {
    comboForm.addEventListener('submit', handleComboFormSubmit);
  }

  // Search filter handler
  const searchInput = document.getElementById('combos-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => filterAndRenderCombos());
  }

  // Initial load
  await loadCombos();
}

export async function loadCombos() {
  const tbody = document.getElementById('combos-table-body');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-loading-cell">
          <div class="spinner-inline"></div> Carregando combos...
        </td>
      </tr>
    `;
  }

  try {
    allCombos = await adminApi.getAdminCombos();
    filterAndRenderCombos();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="table-empty-cell text-danger">
            ⚠️ Falha ao carregar combos: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

function filterAndRenderCombos() {
  const tbody = document.getElementById('combos-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('combos-search');
  const query = searchInput?.value.trim().toLowerCase() || '';

  let filtered = allCombos.filter((combo) => {
    return !query ||
      combo.title.toLowerCase().includes(query) ||
      (combo.description && combo.description.toLowerCase().includes(query));
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="table-empty-cell">
          Nenhum combo encontrado com os filtros selecionados.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map((combo) => {
    const photoSrc = combo.image_url || '';
    const formattedPrice = formatCurrency(combo.price);

    return `
      <tr data-id="${combo.id}">
        <td>
          ${photoSrc
            ? `<img src="${escapeHtml(photoSrc)}" alt="${escapeHtml(combo.title)}" class="table-thumb">`
            : `<div class="table-thumb-placeholder">🦖</div>`
          }
        </td>
        <td>
          <div class="product-cell-name">
            ${escapeHtml(combo.title)}
            ${combo.is_promo_of_day ? '<span class="badge-promo-fire" title="Promoção do Dia">🔥 Promo do Dia</span>' : ''}
          </div>
          <div class="product-cell-desc">${escapeHtml(combo.description || 'Sem descrição')}</div>
        </td>
        <td>
          <span class="price-tag">${formattedPrice}</span>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Disponibilidade">
            <input type="checkbox" class="toggle-combo-active" data-id="${combo.id}" ${combo.is_active ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Promoção do Dia">
            <input type="checkbox" class="toggle-combo-promo" data-id="${combo.id}" ${combo.is_promo_of_day ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <div class="action-buttons">
            <button type="button" class="btn-action btn-edit-combo" data-id="${combo.id}" title="Editar Combo">
              ✏️
            </button>
            <button type="button" class="btn-action btn-delete-combo" data-id="${combo.id}" title="Excluir Combo">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  attachTableEventListeners(tbody);
}

function attachTableEventListeners(tbody) {
  // Toggle Active
  tbody.querySelectorAll('.toggle-combo-active').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleComboActive(id);
        const combo = allCombos.find(c => c.id === id);
        if (combo) combo.is_active = isChecked;
        toastFn?.(`Disponibilidade de "${combo?.title || 'Combo'}" atualizada!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked;
        toastFn?.(`Erro ao alterar disponibilidade: ${err.message}`, 'error');
      }
    });
  });

  // Toggle Promo of the Day
  tbody.querySelectorAll('.toggle-combo-promo').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleComboPromo(id);
        const combo = allCombos.find(c => c.id === id);
        if (combo) combo.is_promo_of_day = isChecked;
        filterAndRenderCombos(); // re-render to update flame badge
        toastFn?.(`Status de Promoção do Dia de "${combo?.title || 'Combo'}" atualizado!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked;
        toastFn?.(`Erro ao alterar promoção do dia: ${err.message}`, 'error');
      }
    });
  });

  // Edit Combo
  tbody.querySelectorAll('.btn-edit-combo').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      const combo = allCombos.find(c => c.id === id);
      if (combo) openComboModal(combo);
    });
  });

  // Delete Combo
  tbody.querySelectorAll('.btn-delete-combo').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id, 10);
      const combo = allCombos.find(c => c.id === id);
      const name = combo?.title || 'este combo';

      if (!confirm(`Tem certeza que deseja excluir "${name}"? Esta ação não pode ser desfeita.`)) {
        return;
      }

      try {
        await adminApi.deleteCombo(id);
        allCombos = allCombos.filter(c => c.id !== id);
        filterAndRenderCombos();
        toastFn?.(`Combo "${name}" excluído com sucesso!`, 'success');
      } catch (err) {
        toastFn?.(`Erro ao excluir combo: ${err.message}`, 'error');
      }
    });
  });
}

export function openComboModal(combo = null) {
  const modal = document.getElementById('modal-combo');
  const modalTitle = document.getElementById('modal-combo-title');
  const form = document.getElementById('combo-form');

  if (!modal || !form) return;

  form.reset();
  comboDropzone?.clearPreview();

  const idInput = document.getElementById('combo-id');
  const titleInput = document.getElementById('combo-title');
  const descInput = document.getElementById('combo-description');
  const priceInput = document.getElementById('combo-price');
  const activeCheckbox = document.getElementById('combo-is-active');
  const promoCheckbox = document.getElementById('combo-is-promo');

  if (combo) {
    if (modalTitle) modalTitle.textContent = 'Editar Combo';
    if (idInput) idInput.value = combo.id;
    if (titleInput) titleInput.value = combo.title || '';
    if (descInput) descInput.value = combo.description || '';
    if (priceInput) priceInput.value = parseFloat(combo.price).toFixed(2);
    if (activeCheckbox) activeCheckbox.checked = Boolean(combo.is_active);
    if (promoCheckbox) promoCheckbox.checked = Boolean(combo.is_promo_of_day);

    if (combo.image_url) {
      comboDropzone?.setPreview(combo.image_url);
    }
  } else {
    if (modalTitle) modalTitle.textContent = 'Novo Combo';
    if (idInput) idInput.value = '';
    if (activeCheckbox) activeCheckbox.checked = true;
    if (promoCheckbox) promoCheckbox.checked = false;
  }

  modal.classList.remove('d-none');
}

export function closeComboModal() {
  const modal = document.getElementById('modal-combo');
  if (modal) modal.classList.add('d-none');
}

async function handleComboFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('combo-id')?.value;
  const title = document.getElementById('combo-title')?.value.trim();
  const description = document.getElementById('combo-description')?.value.trim();
  const priceVal = parseFloat(document.getElementById('combo-price')?.value);
  const imageUrl = document.getElementById('combo-image-url')?.value.trim() || null;
  const isActive = document.getElementById('combo-is-active')?.checked ?? true;
  const isPromoOfDay = document.getElementById('combo-is-promo')?.checked ?? false;

  const submitBtn = document.getElementById('btn-save-combo');
  const spinner = submitBtn?.querySelector('.btn-spinner');

  if (!title || title.length < 2) {
    toastFn?.('Título do combo deve ter pelo menos 2 caracteres.', 'warning');
    return;
  }

  if (!description || description.length < 2) {
    toastFn?.('Por favor, descreva os itens inclusos no combo.', 'warning');
    return;
  }

  if (isNaN(priceVal) || priceVal <= 0) {
    toastFn?.('Por favor, insira um preço válido maior que zero.', 'warning');
    return;
  }

  const payload = {
    title,
    description,
    price: priceVal,
    image_url: imageUrl,
    is_active: isActive,
    is_promo_of_day: isPromoOfDay
  };

  try {
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    if (id) {
      await adminApi.updateCombo(parseInt(id, 10), payload);
      toastFn?.(`Combo "${title}" atualizado com sucesso!`, 'success');
    } else {
      await adminApi.createCombo(payload);
      toastFn?.(`Combo "${title}" cadastrado com sucesso!`, 'success');
    }

    closeComboModal();
    await loadCombos();
  } catch (err) {
    toastFn?.(`Erro ao salvar combo: ${err.message}`, 'error');
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
