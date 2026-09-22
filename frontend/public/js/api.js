/**
 * DINOS Pizzaria — REST API Client (ES6 Module)
 * Handles communication with the FastAPI backend (/api/v1/*)
 */

const API_BASE = '/api/v1';

/**
 * Utility wrapper around fetch API with default headers, error normalization and logging.
 *
 * @param {string} endpoint - The relative API path (e.g. '/categories')
 * @param {RequestInit} [options={}] - Fetch configuration options
 * @returns {Promise<any>} Parsed JSON response
 */
async function request(endpoint, options = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {})
    }
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    // Handle HTTP Error responses
    if (!response.ok) {
      let errorDetail = `Erro na requisição: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // Pydantic validation error list
            errorDetail = errorData.detail.map((err) => err.msg || JSON.stringify(err)).join(', ');
          } else if (typeof errorData.detail === 'string') {
            errorDetail = errorData.detail;
          }
        }
      } catch {
        // Fallback to generic status text if response is not JSON
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      console.error(`[API Network Error] Falha ao conectar em ${API_BASE}${endpoint}:`, err);
      throw new Error('Não foi possível conectar ao servidor da DINOS Pizzaria. Verifique sua conexão com a internet.');
    }
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

/**
 * Public REST API client object for DINOS Storefront.
 */
export const api = {
  /**
   * Fetch all active categories ordered by priority.
   * @returns {Promise<Array<{ id: number, name: string, description: string, icon: string }>>}
   */
  getCategories: () => request('/categories?active_only=true'),

  /**
   * Fetch all active products, optionally filtered by category ID.
   * @param {number|null} [categoryId=null]
   * @returns {Promise<Array<{ id: number, name: string, description: string, price: number, image_url: string, is_promo: boolean, promo_price: number, category_id: number }>>}
   */
  getProducts: (categoryId = null) => {
    const query = categoryId ? `?active_only=true&category_id=${categoryId}` : '?active_only=true';
    return request(`/products${query}`);
  },

  /**
   * Fetch all active featured / best-seller products.
   * @returns {Promise<Array<{ id: number, name: string, description: string, price: number, image_url: string, is_promo: boolean, promo_price: number, is_featured: boolean }>>}
   */
  getFeaturedProducts: () => request('/products/featured'),

  /**
   * Fetch all published customer reviews.
   * @returns {Promise<Array<{ id: number, customer_name: string, rating: number, comment: string, created_at: string }>>}
   */
  getReviews: () => request('/reviews'),

  /**
   * Validate a discount coupon code for a given subtotal.
   * @param {{ code: string, subtotal: number }} payload
   * @returns {Promise<{ valid: boolean, code: string, discount_type: string, discount_value: number, discount_amount: number, message: string }>}
   */
  validateCoupon: (payload) =>
    request('/coupons/validate', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  /**
   * Track an order status by order ID and customer phone verification.
   * @param {number|string} orderId
   * @param {string} phone
   * @returns {Promise<{ id: number, order_number: string, status: string, delivery_type: string, fulfillment_time_type: string, scheduled_for: string|null, estimated_delivery_time: string|null, total_amount: number, created_at: string, items_summary: Array<{ item_name: string, quantity: number, final_price: number }> }>}
   */
  trackOrder: (orderId, phone) =>
    request(`/orders/track?order_id=${encodeURIComponent(orderId)}&phone=${encodeURIComponent(phone)}`),

  /**
   * Fetch all active combos.
   * @returns {Promise<Array<{ id: number, name: string, description: string, price: number, image_url: string, is_promo_of_day: boolean }>>}
   */
  getCombos: () => request('/combos?active_only=true'),

  /**
   * Fetch active combos marked as promotion of the day.
   * @returns {Promise<Array<{ id: number, name: string, description: string, price: number, image_url: string, is_promo_of_day: boolean }>>}
   */
  getPromoCombos: () => request('/combos/promos'),

  /**
   * Fetch all active delivery zones and fees.
   * @returns {Promise<Array<{ id: number, name: string, fee: number, estimated_minutes: number }>>}
   */
  getDeliveryZones: () => request('/delivery-zones?active_only=true'),

  /**
   * Fetch editable storefront copy/content.
   * @returns {Promise<Array<{ key: string, value: string }>>}
   */
  getSiteContent: () => request('/site-content'),

  /**
   * Create a new guest order and trigger WhatsApp notification.
   * @param {Object} orderPayload
   * @returns {Promise<{ order_id: number, order_number: string, total_amount: number, status: string, whatsapp_url: string, message_sent: boolean }>}
   */
  createOrder: (orderPayload) =>
    request('/orders', {
      method: 'POST',
      body: JSON.stringify(orderPayload)
    })
};
