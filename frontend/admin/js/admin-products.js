/**
 * DINOS Pizzaria — Admin Products Controller
 * Handles product listing, dynamic category filter, live search, 1-click toggles, and CRUD modals.
 */

import { adminApi } from './admin-api.js';
import { setupDropzone } from './admin-dropzone.js';

let allProducts = [];
let categoriesList = [];
let productDropzone = null;
let toastFn = null;

export async function initProducts(showToast) {
  toastFn = showToast;

  // Initialize dropzone for products
  const dropzoneEl = document.getElementById('product-dropzone');
  const fileInputEl = document.getElementById('product-file-input');
  const previewWrapperEl = document.getElementById('product-preview-wrapper');
  const previewImgEl = document.getElementById('product-image-preview');
  const removeBtnEl = document.getElementById('product-remove-image-btn');
  const hiddenInputEl = document.getElementById('product-image-url');

  productDropzone = setupDropzone({
    dropzoneEl,
    fileInputEl,
    previewWrapperEl,
    previewImgEl,
    removeBtnEl,
    hiddenInputEl,
    onUploadSuccess: (url) => {
      toastFn?.('Foto enviada e otimizada com sucesso!', 'success');
    },
    onUploadError: (err) => {
      toastFn?.(err.message || 'Falha ao enviar foto.', 'error');
    }
  });

  // Modal open/close listeners
  const btnNewProduct = document.getElementById('btn-new-product');
  const modalCloseBtn = document.getElementById('modal-product-close');
  const modalCancelBtn = document.getElementById('btn-cancel-product');
  const modalProduct = document.getElementById('modal-product');
  const productForm = document.getElementById('product-form');

  if (btnNewProduct) {
    btnNewProduct.addEventListener('click', () => openProductModal());
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => closeProductModal());
  }

  if (modalCancelBtn) {
    modalCancelBtn.addEventListener('click', () => closeProductModal());
  }

  if (modalProduct) {
    modalProduct.addEventListener('click', (e) => {
      if (e.target === modalProduct) closeProductModal();
    });
  }

  // Form submit handler
  if (productForm) {
    productForm.addEventListener('submit', handleProductFormSubmit);
  }

  // Search and Category Filter handlers
  const searchInput = document.getElementById('products-search');
  const categoryFilter = document.getElementById('products-category-filter');

  if (searchInput) {
    searchInput.addEventListener('input', () => filterAndRenderProducts());
  }

  if (categoryFilter) {
    categoryFilter.addEventListener('change', () => filterAndRenderProducts());
  }

  // Initial load of categories and products
  await loadCategories();
  await loadProducts();
}

export async function loadCategories() {
  try {
    categoriesList = await adminApi.getCategories(false);
    populateCategorySelects();
  } catch (err) {
    console.error('Falha ao carregar categorias:', err);
    toastFn?.('Falha ao carregar categorias do cardápio.', 'error');
  }
}

function populateCategorySelects() {
  const filterSelect = document.getElementById('products-category-filter');
  const formSelect = document.getElementById('product-category');

  if (filterSelect) {
    const currentVal = filterSelect.value;
    filterSelect.innerHTML = '<option value="">Todas as Categorias</option>' +
      categoriesList.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    filterSelect.value = currentVal;
  }

  if (formSelect) {
    formSelect.innerHTML = '<option value="">Selecione...</option>' +
      categoriesList.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
  }
}

export async function loadProducts() {
  const tbody = document.getElementById('products-table-body');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="table-loading-cell">
          <div class="spinner-inline"></div> Carregando cardápio...
        </td>
      </tr>
    `;
  }

  try {
    allProducts = await adminApi.getAdminProducts();
    filterAndRenderProducts();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="table-empty-cell text-danger">
            ⚠️ Falha ao carregar produtos: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

function filterAndRenderProducts() {
  const tbody = document.getElementById('products-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('products-search');
  const categoryFilter = document.getElementById('products-category-filter');

  const query = searchInput?.value.trim().toLowerCase() || '';
  const categoryId = categoryFilter?.value ? parseInt(categoryFilter.value, 10) : null;

  let filtered = allProducts.filter((product) => {
    const matchesSearch = !query ||
      product.title.toLowerCase().includes(query) ||
      (product.description && product.description.toLowerCase().includes(query));
    const matchesCategory = !categoryId || product.category_id === categoryId;
    return matchesSearch && matchesCategory;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="table-empty-cell">
          Nenhum produto encontrado com os filtros selecionados.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map((product) => {
    const photoSrc = product.image_url || '';
    const categoryName = product.category?.name || categoriesList.find(c => c.id === product.category_id)?.name || 'Geral';
    const formattedPrice = formatCurrency(product.price);

    return `
      <tr data-id="${product.id}">
        <td>
          ${photoSrc
            ? `<img src="${escapeHtml(photoSrc)}" alt="${escapeHtml(product.title)}" class="table-thumb">`
            : `<div class="table-thumb-placeholder">🍕</div>`
          }
        </td>
        <td>
          <div class="product-cell-name">${escapeHtml(product.title)}</div>
          <div class="product-cell-desc">${escapeHtml(product.description || 'Sem descrição')}</div>
        </td>
        <td>
          <span class="category-badge">${escapeHtml(categoryName)}</span>
        </td>
        <td>
          <span class="price-tag">${formattedPrice}</span>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Disponibilidade">
            <input type="checkbox" class="toggle-product-active" data-id="${product.id}" ${product.is_active ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Destaque Promoção">
            <input type="checkbox" class="toggle-product-promo" data-id="${product.id}" ${product.is_promo ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <label class="switch" title="Alternar Mais Pedidas / Destaque">
            <input type="checkbox" class="toggle-product-featured" data-id="${product.id}" ${product.is_featured ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </td>
        <td style="text-align: center;">
          <div class="action-buttons">
            <button type="button" class="btn-action btn-edit-product" data-id="${product.id}" title="Editar Produto">
              ✏️
            </button>
            <button type="button" class="btn-action btn-delete-product" data-id="${product.id}" title="Excluir Produto">
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
  tbody.querySelectorAll('.toggle-product-active').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleProductActive(id);
        const prod = allProducts.find(p => p.id === id);
        if (prod) prod.is_active = isChecked;
        toastFn?.(`Disponibilidade de "${prod?.title || 'Produto'}" atualizada!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar disponibilidade: ${err.message}`, 'error');
      }
    });
  });

  // Toggle Promo
  tbody.querySelectorAll('.toggle-product-promo').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleProductPromo(id);
        const prod = allProducts.find(p => p.id === id);
        if (prod) prod.is_promo = isChecked;
        toastFn?.(`Status promocional de "${prod?.title || 'Produto'}" atualizado!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar promoção: ${err.message}`, 'error');
      }
    });
  });

  // Toggle Featured (Mais Pedidas)
  tbody.querySelectorAll('.toggle-product-featured').forEach((checkbox) => {
    checkbox.addEventListener('change', async (e) => {
      const id = parseInt(e.target.dataset.id, 10);
      const isChecked = e.target.checked;
      try {
        await adminApi.toggleProductFeatured(id);
        const prod = allProducts.find(p => p.id === id);
        if (prod) prod.is_featured = isChecked;
        toastFn?.(`Destaque em Mais Pedidas de "${prod?.title || 'Produto'}" atualizado!`, 'success');
      } catch (err) {
        e.target.checked = !isChecked; // revert
        toastFn?.(`Erro ao alterar destaque: ${err.message}`, 'error');
      }
    });
  });

  // Edit Product
  tbody.querySelectorAll('.btn-edit-product').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const id = parseInt(btn.dataset.id, 10);
      const product = allProducts.find(p => p.id === id);
      if (product) openProductModal(product);
    });
  });

  // Delete Product
  tbody.querySelectorAll('.btn-delete-product').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const id = parseInt(btn.dataset.id, 10);
      const product = allProducts.find(p => p.id === id);
      const name = product?.title || 'este produto';

      if (!confirm(`Tem certeza que deseja excluir "${name}"? Esta ação não pode ser desfeita.`)) {
        return;
      }

      try {
        await adminApi.deleteProduct(id);
        allProducts = allProducts.filter(p => p.id !== id);
        filterAndRenderProducts();
        toastFn?.(`Produto "${name}" excluído com sucesso!`, 'success');
      } catch (err) {
        toastFn?.(`Erro ao excluir produto: ${err.message}`, 'error');
      }
    });
  });
}

export function openProductModal(product = null) {
  const modal = document.getElementById('modal-product');
  const modalTitle = document.getElementById('modal-product-title');
  const form = document.getElementById('product-form');

  if (!modal || !form) return;

  form.reset();
  productDropzone?.clearPreview();

  const idInput = document.getElementById('product-id');
  const titleInput = document.getElementById('product-title');
  const categorySelect = document.getElementById('product-category');
  const descInput = document.getElementById('product-description');
  const priceInput = document.getElementById('product-price');
  const activeCheckbox = document.getElementById('product-is-active');
  const promoCheckbox = document.getElementById('product-is-promo');
  const featuredCheckbox = document.getElementById('product-is-featured');

  if (product) {
    if (modalTitle) modalTitle.textContent = 'Editar Produto';
    if (idInput) idInput.value = product.id;
    if (titleInput) titleInput.value = product.title || '';
    if (categorySelect) categorySelect.value = product.category_id || '';
    if (descInput) descInput.value = product.description || '';
    if (priceInput) priceInput.value = parseFloat(product.price).toFixed(2);
    if (activeCheckbox) activeCheckbox.checked = Boolean(product.is_active);
    if (promoCheckbox) promoCheckbox.checked = Boolean(product.is_promo);
    if (featuredCheckbox) featuredCheckbox.checked = Boolean(product.is_featured);

    if (product.image_url) {
      productDropzone?.setPreview(product.image_url);
    }
  } else {
    if (modalTitle) modalTitle.textContent = 'Novo Produto';
    if (idInput) idInput.value = '';
    if (activeCheckbox) activeCheckbox.checked = true;
    if (promoCheckbox) promoCheckbox.checked = false;
    if (featuredCheckbox) featuredCheckbox.checked = false;
  }

  modal.classList.remove('d-none');
}

export function closeProductModal() {
  const modal = document.getElementById('modal-product');
  if (modal) modal.classList.add('d-none');
}

async function handleProductFormSubmit(e) {
  e.preventDefault();

  const id = document.getElementById('product-id')?.value;
  const title = document.getElementById('product-title')?.value.trim();
  const categoryId = parseInt(document.getElementById('product-category')?.value, 10);
  const description = document.getElementById('product-description')?.value.trim() || null;
  const priceVal = parseFloat(document.getElementById('product-price')?.value);
  const imageUrl = document.getElementById('product-image-url')?.value.trim() || null;
  const isActive = document.getElementById('product-is-active')?.checked ?? true;
  const isPromo = document.getElementById('product-is-promo')?.checked ?? false;
  const isFeatured = document.getElementById('product-is-featured')?.checked ?? false;

  const submitBtn = document.getElementById('btn-save-product');
  const spinner = submitBtn?.querySelector('.btn-spinner');

  if (!title || title.length < 2) {
    toastFn?.('Nome do produto deve ter pelo menos 2 caracteres.', 'warning');
    return;
  }

  if (isNaN(categoryId) || categoryId <= 0) {
    toastFn?.('Por favor, selecione uma categoria válida.', 'warning');
    return;
  }

  if (isNaN(priceVal) || priceVal <= 0) {
    toastFn?.('Por favor, insira um preço válido maior que zero.', 'warning');
    return;
  }

  const payload = {
    title,
    category_id: categoryId,
    description,
    price: priceVal,
    image_url: imageUrl,
    is_active: isActive,
    is_promo: isPromo,
    is_featured: isFeatured
  };

  try {
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');

    if (id) {
      await adminApi.updateProduct(parseInt(id, 10), payload);
      toastFn?.(`Produto "${title}" atualizado com sucesso!`, 'success');
    } else {
      await adminApi.createProduct(payload);
      toastFn?.(`Produto "${title}" cadastrado com sucesso!`, 'success');
    }

    closeProductModal();
    await loadProducts();
  } catch (err) {
    toastFn?.(`Erro ao salvar produto: ${err.message}`, 'error');
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
