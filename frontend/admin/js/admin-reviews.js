/**
 * DINOS Pizzaria — Admin Reviews Controller
 * Handles customer reviews listing, live search, 1-click publish toggles, and CRUD modals.
 */

import { adminApi } from './admin-api.js';

let allReviews = [];
let toastFn = null;

export async function initReviews(showToast) {
  toastFn = showToast;

  // Modal open/close listeners
  const btnNewReview = document.getElementById('btn-new-review');
  const modalCloseBtn = document.getElementById('modal-review-close');
  const modalCancelBtn = document.getElementById('btn-cancel-review');
  const modalReview = document.getElementById('modal-review');
  const reviewForm = document.getElementById('review-form');

  if (btnNewReview) {
    btnNewReview.addEventListener('click', () => openReviewModal());
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeReviewModal());
  }

  if (modalCancelBtn) {
    modalCancelBtn.addEventListener('click', () => closeReviewModal());
  }

  if (modalReview) {
    modalReview.addEventListener('click', (e) => {
      if (e.target === modalReview) closeReviewModal();
    });
  }

  // Form submit handler
  if (reviewForm) {
    reviewForm.addEventListener('submit', handleReviewFormSubmit);
  }

  // Search input handler
  const searchInput = document.getElementById('reviews-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => filterAndRenderReviews());
  }

  // Initial load
  await loadReviews();
}

export async function loadReviews() {
  const tbody = document.getElementById('reviews-table-body');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-loading-cell">
          <div class="spinner-inline"></div> Carregando avaliações...
        </td>
      </tr>
    `;
  }

  try {
    allReviews = await adminApi.getAdminReviews();
    filterAndRenderReviews();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="table-empty-cell text-danger">
            ⚠️ Falha ao carregar avaliações: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

function filterAndRenderReviews() {
  const tbody = document.getElementById('reviews-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('reviews-search');
  const query = searchInput?.value.trim().toLowerCase() || '';

  let filtered = allReviews.filter((r) => {
    return !query ||
      r.customer_name.toLowerCase().includes(query) ||
      r.comment.toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-empty-cell">
          Nenhuma avaliação encontrada com os filtros selecionados.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map((review) => {
    const stars = '⭐'.repeat(Math.max(1, Math.min(5, review.rating || 5)));

    return `
      <tr data-id="${review.id}">
        <td>
          <div class="product-cell-name">${escapeHtml(review.customer_name)}</div>
          <div class="product-cell-desc">${new Date(review.created_at).toLocaleDateString('pt-BR')}</div>
        </td>
        <td>
          <span title="${review.rating} estrelas" style="font-size: 0.95rem; letter-spacing: 1px;">
            ${stars}
          </span>
        </td>
        <td>
          <div class="product-cell-desc" style="max-width: 400px; white-space: normal; line-height: 1.4;">
            "${escapeHtml(review.comment)}"
          </div>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Exibição no Site">
            <input type="checkbox" class="toggle-review-published" data-id="${review.id}" ${review.is_published ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <div class="action-buttons">
            <button type="button" class="btn-action btn-edit-review" data-id="${review.id}" title="Editar Avaliação">
              ✏️
            </button>
            <button type="button" class="btn-action btn-delete-review" data-id="${review.id}" title="Excluir Avaliação">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  attachReviewEventListeners(tbody);
}

function attachReviewEventListeners(tbody) {
  // Toggle Published
  tbody.querySelectorAll('.toggle-review-published').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleReviewPublished(id);
        const review = allReviews.find(r => r.id === id);
        if (review) review.is_published = isChecked;
        toastFn?.(`Visibilidade do depoimento de "${review?.customer_name || 'Cliente'}" atualizada!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar visibilidade: ${err.message}`, 'error');
      }
    });
  });

  // Edit Review
  tbody.querySelectorAll('.btn-edit-review').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id, 10);
      const review = allReviews.find(r => r.id === id);
      if (review) openReviewModal(review);
    });
  });

  // Delete Review
  tbody.querySelectorAll('.btn-delete-review').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id, 10);
      const review = allReviews.find(r => r.id === id);
      const name = review?.customer_name || 'esta avaliação';

      if (!confirm(`Tem certeza que deseja excluir o depoimento de "${name}"? Esta ação não pode ser desfeita.`)) {
        return;
      }

      try {
        await adminApi.deleteReview(id);
        allReviews = allReviews.filter(r => r.id !== id);
        filterAndRenderReviews();
        toastFn?.(`Avaliação de "${name}" excluída com sucesso!`, 'success');
      } catch (err) {
        toastFn?.(`Erro ao excluir avaliação: ${err.message}`, 'error');
      }
    });
  });
}

export function openReviewModal(review = null) {
  const modal = document.getElementById('modal-review');
  const modalTitle = document.getElementById('modal-review-title');
  const form = document.getElementById('review-form');

  if (!modal || !form) return;

  form.reset();

  const idInput = document.getElementById('review-id');
  const nameInput = document.getElementById('review-customer-name');
  const ratingSelect = document.getElementById('review-rating');
  const commentInput = document.getElementById('review-comment');
  const publishedCheckbox = document.getElementById('review-is-published');

  if (review) {
    if (modalTitle) modalTitle.textContent = 'Editar Avaliação / Depoimento';
    if (idInput) idInput.value = review.id;
    if (nameInput) nameInput.value = review.customer_name || '';
    if (ratingSelect) ratingSelect.value = String(review.rating || 5);
    if (commentInput) commentInput.value = review.comment || '';
    if (publishedCheckbox) publishedCheckbox.checked = Boolean(review.is_published);
  } else {
    if (modalTitle) modalTitle.textContent = 'Nova Avaliação / Depoimento';
    if (idInput) idInput.value = '';
    if (ratingSelect) ratingSelect.value = '5';
    if (publishedCheckbox) publishedCheckbox.checked = true;
  }

  modal.classList.remove('d-none');
}

export function closeReviewModal() {
  const modal = document.getElementById('modal-review');
  if (modal) modal.classList.add('d-none');
}

async function handleReviewFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('review-id')?.value;
  const customerName = document.getElementById('review-customer-name')?.value.trim();
  const rating = parseInt(document.getElementById('review-rating')?.value, 10);
  const comment = document.getElementById('review-comment')?.value.trim();
  const isPublished = document.getElementById('review-is-published')?.checked ?? true;

  const submitBtn = document.getElementById('btn-save-review');
  const spinner = submitBtn?.querySelector('.btn-spinner');

  if (!customerName || customerName.length < 2) {
    toastFn?.('Nome do cliente deve ter pelo menos 2 caracteres.', 'warning');
    return;
  }

  if (isNaN(rating) || rating < 1 || rating > 5) {
    toastFn?.('Por favor, selecione uma nota de 1 a 5 estrelas.', 'warning');
    return;
  }

  if (!comment || comment.length < 5) {
    toastFn?.('O comentário deve ter pelo menos 5 caracteres.', 'warning');
    return;
  }

  const payload = {
    customer_name: customerName,
    rating,
    comment,
    is_published: isPublished
  };

  try {
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    if (id) {
      await adminApi.updateReview(parseInt(id, 10), payload);
      toastFn?.(`Avaliação de "${customerName}" atualizada com sucesso!`, 'success');
    } else {
      await adminApi.createReview(payload);
      toastFn?.(`Avaliação de "${customerName}" cadastrada com sucesso!`, 'success');
    }

    closeReviewModal();
    await loadReviews();
  } catch (err) {
    toastFn?.(`Erro ao salvar avaliação: ${err.message}`, 'error');
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (spinner) spinner.classList.add('d-none');
  }
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
