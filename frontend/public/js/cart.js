/**
 * DINOS Pizzaria — Reactive Cart Store with LocalStorage Persistence (ES6 Module)
 * Manages customer order items, item-specific notes, subtotal computations, and event broadcasting.
 */

export class CartStore extends EventTarget {
  constructor() {
    super();
    this.STORAGE_KEY = 'dinos_cart_v1';
    this.items = this.loadFromStorage();
    this.deliveryType = 'delivery'; // 'delivery' | 'pickup'
    this.deliveryZone = null; // { id: number, name: string, fee: number } | null
    this.couponCode = null;
    this.discountAmount = 0;
  }

  /**
   * Load and sanitize cart items from browser localStorage.
   * Mitigates T-04-05 & T-04-06 by ensuring valid types and capping quantities.
   * @returns {Array<Object>}
   */
  loadFromStorage() {
    try {
      const raw = localStorage.getItem(this.STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];

      return parsed
        .filter((item) => item && typeof item === 'object' && item.itemId)
        .map((item) => ({
          itemType: item.itemType === 'combo' ? 'combo' : 'product',
          itemId: Number(item.itemId),
          title: String(item.title || 'Item DINOS'),
          unitPrice: Math.max(0, Number(item.unitPrice) || 0),
          quantity: Math.min(Math.max(1, Number(item.quantity) || 1), 50),
          notes: String(item.notes || '').slice(0, 255),
          imageUrl: item.imageUrl ? String(item.imageUrl) : '',
          options: item.options && typeof item.options === 'object' ? item.options : null
        }));
    } catch (err) {
      console.warn('[CartStore] Erro ao carregar dados do localStorage:', err);
      return [];
    }
  }

  /**
   * Persist cart items to localStorage and notify listeners.
   */
  saveToStorage() {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.items));
    } catch (err) {
      console.error('[CartStore] Falha ao persistir no localStorage:', err);
    }
    this.dispatchEvent(new CustomEvent('cart:updated', { detail: this.getState() }));
  }

  /**
   * Add an item to the cart.
   * Groups identical items if both itemId and notes match; creates separate entries if notes differ.
   *
   * @param {Object} itemParams
   * @param {'product'|'combo'} [itemParams.itemType='product']
   * @param {number} itemParams.itemId
   * @param {string} itemParams.title
   * @param {number} itemParams.unitPrice
   * @param {number} [itemParams.quantity=1]
   * @param {string} [itemParams.notes='']
   * @param {string} [itemParams.imageUrl='']
   * @param {Object|null} [itemParams.options=null]
   */
  addItem({
    itemType = 'product',
    itemId,
    title,
    unitPrice,
    quantity = 1,
    notes = '',
    imageUrl = '',
    options = null
  }) {
    const cleanNotes = (notes || '').trim().slice(0, 255);
    const validQty = Math.min(Math.max(1, Number(quantity) || 1), 50);
    const validPrice = Math.max(0, Number(unitPrice) || 0);
    const validItemId = Number(itemId);
    const validType = itemType === 'combo' ? 'combo' : 'product';
    const cleanOptions = options && typeof options === 'object' ? options : null;
    const optionsKey = cleanOptions ? JSON.stringify(cleanOptions) : '';

    // Pitfall 2: Match by itemType, itemId, notes, and selected options
    const existingIndex = this.items.findIndex(
      (item) =>
        item.itemType === validType &&
        item.itemId === validItemId &&
        (item.notes || '').trim().toLowerCase() === cleanNotes.toLowerCase() &&
        JSON.stringify(item.options || null) === (optionsKey || JSON.stringify(null))
    );

    if (existingIndex > -1) {
      const currentQty = this.items[existingIndex].quantity;
      this.items[existingIndex].quantity = Math.min(currentQty + validQty, 50);
    } else {
      this.items.push({
        itemType: validType,
        itemId: validItemId,
        title: String(title || 'Item'),
        unitPrice: validPrice,
        quantity: validQty,
        notes: cleanNotes,
        imageUrl: imageUrl ? String(imageUrl) : '',
        options: cleanOptions
      });
    }

    this.saveToStorage();
  }

  /**
   * Update quantity of an item at a specific index.
   * If newQty <= 0, the item is removed from the cart.
   *
   * @param {number} index
   * @param {number} newQty
   */
  updateQuantity(index, newQty) {
    const idx = Number(index);
    if (idx >= 0 && idx < this.items.length) {
      const qty = Number(newQty);
      if (qty <= 0) {
        this.items.splice(idx, 1);
      } else {
        this.items[idx].quantity = Math.min(Math.max(1, qty), 50);
      }
      this.saveToStorage();
    }
  }

  /**
   * Remove an item from the cart by its array index.
   *
   * @param {number} index
   */
  removeItem(index) {
    const idx = Number(index);
    if (idx >= 0 && idx < this.items.length) {
      this.items.splice(idx, 1);
      this.saveToStorage();
    }
  }

  /**
   * Clear all items in the cart and reset storage.
   */
  clear() {
    this.items = [];
    this.couponCode = null;
    this.discountAmount = 0;
    this.saveToStorage();
  }

  /**
   * Set discount coupon details.
   * @param {string} code
   * @param {number} discountAmount
   */
  setCoupon(code, discountAmount) {
    this.couponCode = code ? String(code).trim().toUpperCase() : null;
    this.discountAmount = Math.max(0, Number(discountAmount) || 0);
    this.dispatchEvent(new CustomEvent('cart:updated', { detail: this.getState() }));
  }

  /**
   * Remove active coupon.
   */
  removeCoupon() {
    this.couponCode = null;
    this.discountAmount = 0;
    this.dispatchEvent(new CustomEvent('cart:updated', { detail: this.getState() }));
  }

  /**
   * Set delivery fulfillment type ('delivery' | 'pickup').
   * @param {'delivery'|'pickup'} type
   */
  setDeliveryType(type) {
    this.deliveryType = type === 'pickup' ? 'pickup' : 'delivery';
    this.dispatchEvent(new CustomEvent('cart:updated', { detail: this.getState() }));
  }

  /**
   * Set the selected delivery zone object.
   * @param {{ id: number, name: string, fee: number } | null} zone
   */
  setDeliveryZone(zone) {
    this.deliveryZone = zone
      ? {
          id: Number(zone.id),
          name: String(zone.name),
          fee: Number(zone.fee) || 0,
          min_order_value: Number(zone.min_order_value) || 0
        }
      : null;
    this.dispatchEvent(new CustomEvent('cart:updated', { detail: this.getState() }));
  }

  /**
   * Calculate subtotal of all items in the cart.
   * @returns {number}
   */
  getSubtotal() {
    return this.items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  }

  /**
   * Get applicable delivery fee based on fulfillment type and zone.
   * @returns {number}
   */
  getDeliveryFee() {
    if (this.deliveryType === 'pickup' || !this.deliveryZone) {
      return 0;
    }
    return Number(this.deliveryZone.fee) || 0;
  }

  /**
   * Calculate order grand total (subtotal - discount + delivery fee).
   * @returns {number}
   */
  getTotal() {
    return Math.max(0, this.getSubtotal() - this.discountAmount) + this.getDeliveryFee();
  }

  /**
   * Get total item count in cart.
   * @returns {number}
   */
  getItemCount() {
    return this.items.reduce((sum, item) => sum + item.quantity, 0);
  }

  /**
   * Returns a snapshot object of the current cart state.
   * @returns {Object}
   */
  getState() {
    return {
      items: this.items.map((it) => ({ ...it })),
      itemCount: this.getItemCount(),
      subtotal: this.getSubtotal(),
      deliveryType: this.deliveryType,
      deliveryZone: this.deliveryZone ? { ...this.deliveryZone } : null,
      deliveryFee: this.getDeliveryFee(),
      couponCode: this.couponCode,
      discountAmount: this.discountAmount,
      total: this.getTotal()
    };
  }
}

/**
 * Singleton instance of the CartStore for the DINOS Storefront.
 */
export const cart = new CartStore();
