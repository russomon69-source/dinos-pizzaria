/**
 * DINOS Pizzaria — Admin Drag-and-Drop WebP Image Uploader
 * Handles file selection, drag events, client validation, upload execution, and preview state.
 */

import { adminApi } from './admin-api.js';

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB (FastAPI compresses to WebP < 150KB)

/**
 * Initializes a dropzone component.
 * @param {Object} config
 * @param {HTMLElement} config.dropzoneEl
 * @param {HTMLInputElement} config.fileInputEl
 * @param {HTMLElement} config.previewWrapperEl
 * @param {HTMLImageElement} config.previewImgEl
 * @param {HTMLElement} config.removeBtnEl
 * @param {HTMLInputElement} config.hiddenInputEl
 * @param {Function} [config.onUploadSuccess]
 * @param {Function} [config.onUploadError]
 */
export function setupDropzone({
  dropzoneEl,
  fileInputEl,
  previewWrapperEl,
  previewImgEl,
  removeBtnEl,
  hiddenInputEl,
  onUploadSuccess = null,
  onUploadError = null
}) {
  if (!dropzoneEl || !fileInputEl) return null;

  const contentEl = dropzoneEl.querySelector('.dropzone-content');
  const spinnerEl = dropzoneEl.querySelector('.dropzone-spinner');

  // Prevent default drag behaviors on window & dropzone
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
    dropzoneEl.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  // Highlight dropzone on drag
  ['dragenter', 'dragover'].forEach((eventName) => {
    dropzoneEl.addEventListener(eventName, () => {
      dropzoneEl.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropzoneEl.addEventListener(eventName, () => {
      dropzoneEl.classList.remove('dragover');
    }, false);
  });

  // Handle dropped files
  dropzoneEl.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt?.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  });

  // Handle file input change
  fileInputEl.addEventListener('change', (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  });

  // Handle remove image
  if (removeBtnEl) {
    removeBtnEl.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      clearPreview();
    });
  }

  async function processFile(file) {
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      const err = new Error('Formato inválido. Apenas imagens JPEG, PNG ou WebP são permitidas.');
      if (onUploadError) onUploadError(err);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      const err = new Error('Arquivo muito grande. O tamanho máximo permitido é de 10MB.');
      if (onUploadError) onUploadError(err);
      return;
    }

    try {
      showLoading(true);

      const result = await adminApi.uploadImage(file);
      const imageUrl = result.url || result.image_url || (result.filename ? `/static/uploads/${result.filename}` : '');

      setPreview(imageUrl);

      if (typeof onUploadSuccess === 'function') {
        onUploadSuccess(imageUrl, result);
      }
    } catch (err) {
      if (typeof onUploadError === 'function') {
        onUploadError(err);
      }
    } finally {
      showLoading(false);
    }
  }

  function showLoading(isLoading) {
    if (spinnerEl) {
      if (isLoading) spinnerEl.classList.remove('d-none');
      else spinnerEl.classList.add('d-none');
    }
    if (contentEl) {
      if (isLoading) contentEl.classList.add('d-none');
      else if (!hiddenInputEl?.value) contentEl.classList.remove('d-none');
    }
  }

  function setPreview(imageUrl) {
    if (hiddenInputEl) hiddenInputEl.value = imageUrl || '';
    if (previewImgEl) previewImgEl.src = imageUrl || '';

    if (imageUrl) {
      if (contentEl) contentEl.classList.add('d-none');
      if (previewWrapperEl) previewWrapperEl.classList.remove('d-none');
    } else {
      if (contentEl) contentEl.classList.remove('d-none');
      if (previewWrapperEl) previewWrapperEl.classList.add('d-none');
    }
  }

  function clearPreview() {
    if (fileInputEl) fileInputEl.value = '';
    if (hiddenInputEl) hiddenInputEl.value = '';
    if (previewImgEl) previewImgEl.src = '';
    if (previewWrapperEl) previewWrapperEl.classList.add('d-none');
    if (contentEl) contentEl.classList.remove('d-none');
  }

  return {
    setPreview,
    clearPreview,
    processFile
  };
}
