/**
 * DINOS Pizzaria — Admin Authenticated API Client
 * Manages JWT tokens, automatic Bearer injection, and 401 Unauthorized interceptor.
 */

const API_BASE = '/api/v1';
const TOKEN_KEY = 'dinos_admin_token';

export const adminApi = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  isAuthenticated: () => Boolean(localStorage.getItem(TOKEN_KEY)),

  /**
   * Core request wrapper with automatic JWT header and 401 auto-logout interceptor.
   */
  async request(endpoint, options = {}, requiresAuth = true) {
    const headers = {
      'Accept': 'application/json',
      ...(options.headers || {})
    };

    // Do NOT set Content-Type if payload is FormData (browser computes multipart boundary)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    if (requiresAuth) {
      const token = this.getToken();
      if (!token) {
        window.dispatchEvent(new CustomEvent('admin:unauthorized'));
        throw new Error('Sessão não autenticada. Faça login para continuar.');
      }
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });

      if (response.status === 401) {
        this.clearToken();
        window.dispatchEvent(new CustomEvent('admin:unauthorized', {
          detail: { message: 'Sessão expirada. Faça login novamente.' }
        }));
        throw new Error('Sessão expirada. Faça login novamente.');
      }

      if (response.status === 204) {
        return null;
      }

      if (!response.ok) {
        let errorMsg = `Erro ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData && errorData.detail) {
            errorMsg = Array.isArray(errorData.detail)
              ? errorData.detail.map(d => d.msg || JSON.stringify(d)).join(', ')
              : errorData.detail;
          }
        } catch {
          // If JSON parse fails, fallback to default errorMsg
        }
        throw new Error(errorMsg);
      }

      return await response.json();
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error('Falha de conexão com o servidor da DINOS Pizzaria.');
      }
      throw err;
    }
  },

  // ---------------------------------------------------------------------------
  // Authentication Endpoints
  // ---------------------------------------------------------------------------
  login(username, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    }, false);
  },

  getMe() {
    return this.request('/auth/me', { method: 'GET' }, true);
  },

  // ---------------------------------------------------------------------------
  // Categories Endpoints
  // ---------------------------------------------------------------------------
  getCategories(activeOnly = false) {
    return this.request(`/categories?active_only=${activeOnly}`, { method: 'GET' }, false);
  },

  // ---------------------------------------------------------------------------
  // Products Management Endpoints
  // ---------------------------------------------------------------------------
  getAdminProducts(categoryId = null) {
    const query = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : '';
    return this.request(`/products/admin-list${query}`, { method: 'GET' }, true);
  },

  createProduct(payload) {
    return this.request('/products', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);
  },

  updateProduct(id, payload) {
    return this.request(`/products/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }, true);
  },

  toggleProductActive(id) {
    return this.request(`/products/${id}/toggle-active`, {
      method: 'PATCH'
    }, true);
  },

  toggleProductPromo(id) {
    return this.request(`/products/${id}/toggle-promo`, {
      method: 'PATCH'
    }, true);
  },

  toggleProductFeatured(id) {
    return this.request(`/products/${id}/toggle-featured`, {
      method: 'PATCH'
    }, true);
  },

  deleteProduct(id) {
    return this.request(`/products/${id}`, {
      method: 'DELETE'
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Coupons Management Endpoints
  // ---------------------------------------------------------------------------
  getAdminCoupons() {
    return this.request('/coupons/admin-list', { method: 'GET' }, true);
  },

  createCoupon(payload) {
    return this.request('/coupons', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);
  },

  updateCoupon(id, payload) {
    return this.request(`/coupons/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }, true);
  },

  toggleCouponActive(id) {
    return this.request(`/coupons/${id}/toggle-active`, {
      method: 'PATCH'
    }, true);
  },

  deleteCoupon(id) {
    return this.request(`/coupons/${id}`, {
      method: 'DELETE'
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Reviews Management Endpoints
  // ---------------------------------------------------------------------------
  getAdminReviews() {
    return this.request('/reviews/admin-list', { method: 'GET' }, true);
  },

  createReview(payload) {
    return this.request('/reviews', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);
  },

  updateReview(id, payload) {
    return this.request(`/reviews/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }, true);
  },

  toggleReviewPublished(id) {
    return this.request(`/reviews/${id}/toggle-published`, {
      method: 'PATCH'
    }, true);
  },

  deleteReview(id) {
    return this.request(`/reviews/${id}`, {
      method: 'DELETE'
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Combos Management Endpoints
  // ---------------------------------------------------------------------------
  getAdminCombos() {
    return this.request('/combos/admin-list', { method: 'GET' }, true);
  },

  createCombo(payload) {
    return this.request('/combos', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);
  },

  updateCombo(id, payload) {
    return this.request(`/combos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }, true);
  },

  toggleComboActive(id) {
    return this.request(`/combos/${id}/toggle-active`, {
      method: 'PATCH'
    }, true);
  },

  toggleComboPromo(id) {
    return this.request(`/combos/${id}/toggle-promo`, {
      method: 'PATCH'
    }, true);
  },

  deleteCombo(id) {
    return this.request(`/combos/${id}`, {
      method: 'DELETE'
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Delivery Zones Management Endpoints
  // ---------------------------------------------------------------------------
  getAdminZones() {
    return this.request('/delivery-zones/admin-list', { method: 'GET' }, true);
  },

  createZone(payload) {
    return this.request('/delivery-zones', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, true);
  },

  updateZone(id, payload) {
    return this.request(`/delivery-zones/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }, true);
  },

  toggleZoneActive(id) {
    return this.request(`/delivery-zones/${id}/toggle-active`, {
      method: 'PATCH'
    }, true);
  },

  deleteZone(id) {
    return this.request(`/delivery-zones/${id}`, {
      method: 'DELETE'
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Orders Endpoints
  // ---------------------------------------------------------------------------
  getOrders(status = null, limit = 100) {
    const query = status ? `?status=${encodeURIComponent(status)}&limit=${limit}` : `?limit=${limit}`;
    return this.request(`/orders${query}`, { method: 'GET' }, true);
  },

  getOrderDetails(id) {
    return this.request(`/orders/${id}`, { method: 'GET' }, true);
  },

  updateOrderStatus(id, status) {
    return this.request(`/orders/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    }, true);
  },

  // ---------------------------------------------------------------------------
  // Uploads Endpoints
  // ---------------------------------------------------------------------------
  getSiteContent() {
    return this.request('/site-content', { method: 'GET' }, false);
  },

  updateSiteContent(items) {
    return this.request('/site-content', {
      method: 'PUT',
      body: JSON.stringify({ items })
    }, true);
  },

  uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/uploads/image', {
      method: 'POST',
      body: formData
    }, true);
  }
};
