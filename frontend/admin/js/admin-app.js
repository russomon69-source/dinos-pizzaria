/**
 * DINOS Pizzaria — Admin Management Dashboard App Entry Point
 * Orchestrates authentication, responsive navigation tabs, URL hash routing,
 * sound alerts, global toasts, and module bootstrapping for catalog, delivery zones, and orders.
 */

import { initAuth } from './admin-auth.js';
import { initProducts, loadProducts } from './admin-products.js';
import { initCombos, loadCombos } from './admin-combos.js';
import { initZones, loadZones } from './admin-zones.js';
import { initCoupons, loadCoupons } from './admin-coupons.js';
import { initReviews, loadReviews } from './admin-reviews.js';
import { initOrders, loadOrders, startOrderPolling, stopOrderPolling } from './admin-orders.js';
import { initSound, toggleSound, isSoundMuted } from './admin-sound.js';
import { initSiteContent, loadSiteContent } from './admin-site-content.js';

const TAB_TITLES = {
  orders: 'Pedidos em Tempo Real',
  products: 'Produtos do Cardápio',
  combos: 'Combos & Promoções',
  zones: 'Bairros & Taxas de Entrega',
  coupons: 'Cupons de Desconto',
  reviews: 'Avaliações de Clientes',
  settings: 'Textos do Site'
};

let currentTab = 'products';
let isAppInitialized = false;

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Toast system globally
  window.showAdminToast = showToast;

  // Initialize Web Audio Sound Subsystem
  initSound();
  initSoundToggle();

  // Initialize Navigation Tabs & Hash routing
  initNavigation();

  // Initialize Mobile Sidebar Toggle
  initMobileSidebar();

  // Global Keyboard Shortcuts (Escape to close modals)
  initKeyboardShortcuts();

  // Bootstrapping Auth & Core Controllers
  initAuth(
    // onAuthSuccess
    (adminUser) => {
      showToast(`Bem-vindo ao painel, ${adminUser?.username || 'Administrador'}!`, 'success');
      bootstrapAdminModules();
    },
    // onLogout
    () => {
      stopOrderPolling();
      showToast('Sessão encerrada com sucesso.', 'info');
    }
  );
});

/**
 * Bootstrap all admin modules when user is authenticated
 */
function bootstrapAdminModules() {
  if (isAppInitialized) {
    // If re-authenticating, just reload current tab data and start polling
    refreshCurrentTabData();
    startOrderPolling();
    return;
  }

  isAppInitialized = true;

  // Initialize feature controllers
  initProducts(showToast);
  initCombos(showToast);
  initZones(showToast);
  initCoupons(showToast);
  initReviews(showToast);
  initOrders(showToast);
  initSiteContent(showToast);

  // Parse initial URL hash or fallback to default tab
  const initialHash = window.location.hash.replace('#', '').toLowerCase();
  if (TAB_TITLES[initialHash]) {
    switchTab(initialHash, false);
  } else {
    switchTab('products', false);
  }
}

/**
 * Tab Navigation Controller with URL Hash Sync
 */
function initNavigation() {
  const navButtons = document.querySelectorAll('.sidebar-nav .nav-item');

  navButtons.forEach((button) => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const targetTab = button.dataset.tab;
      if (targetTab) {
        switchTab(targetTab, true);

        // On mobile, close sidebar after clicking nav item
        const sidebar = document.getElementById('admin-sidebar');
        if (sidebar && sidebar.classList.contains('sidebar-open')) {
          sidebar.classList.remove('sidebar-open');
        }
      }
    });
  });

  // Handle browser back/forward history navigation
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    if (TAB_TITLES[hash] && hash !== currentTab) {
      switchTab(hash, false);
    }
  });
}

export function switchTab(tabId, updateHash = true) {
  if (!TAB_TITLES[tabId]) return;
  currentTab = tabId;

  if (updateHash && window.location.hash !== `#${tabId}`) {
    window.location.hash = tabId;
  }

  // Update Nav Buttons
  document.querySelectorAll('.sidebar-nav .nav-item').forEach((btn) => {
    if (btn.dataset.tab === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update Tab Content Panes
  document.querySelectorAll('.admin-content .tab-pane').forEach((pane) => {
    if (pane.id === `tab-${tabId}`) {
      pane.classList.add('tab-pane--active');
    } else {
      pane.classList.remove('tab-pane--active');
    }
  });

  // Update Header Title
  const headerTitle = document.getElementById('header-tab-title');
  if (headerTitle) {
    headerTitle.textContent = TAB_TITLES[tabId] || 'Painel Administrativo';
  }

  // Refresh tab data
  refreshCurrentTabData();
}

function refreshCurrentTabData() {
  if (currentTab === 'products') {
    loadProducts();
  } else if (currentTab === 'combos') {
    loadCombos();
  } else if (currentTab === 'zones') {
    loadZones();
  } else if (currentTab === 'coupons') {
    loadCoupons();
  } else if (currentTab === 'reviews') {
    loadReviews();
  } else if (currentTab === 'orders') {
    loadOrders(false);
  } else if (currentTab === 'settings') {
    loadSiteContent();
  }
}

/**
 * Mobile Sidebar Drawer Controller
 */
function initMobileSidebar() {
  const toggleBtn = document.getElementById('btn-toggle-sidebar');
  const sidebar = document.getElementById('admin-sidebar');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('sidebar-open');
    });

    // Close sidebar on click outside
    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('sidebar-open') && !sidebar.contains(e.target) && e.target !== toggleBtn) {
        sidebar.classList.remove('sidebar-open');
      }
    });
  }
}

/**
 * Sound Alerts Controller
 */
function initSoundToggle() {
  const soundBtn = document.getElementById('btn-toggle-sound');
  const soundIcon = document.getElementById('sound-icon');
  const soundLabel = document.getElementById('sound-label');

  updateSoundUI();

  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      const isEnabled = toggleSound();
      updateSoundUI();
      showToast(isEnabled ? 'Alertas sonoros ativados 🔔' : 'Alertas sonoros silenciados 🔕', 'info');
    });
  }

  function updateSoundUI() {
    const isMuted = isSoundMuted();
    if (soundIcon && soundLabel) {
      soundIcon.textContent = isMuted ? '🔕' : '🔔';
      soundLabel.textContent = `Alertas Sonoros: ${isMuted ? 'OFF' : 'ON'}`;
    }
  }
}

/**
 * Global Keyboard Shortcuts
 */
function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModals = document.querySelectorAll('.modal-overlay:not(.d-none)');
      activeModals.forEach((modal) => {
        modal.classList.add('d-none');
      });
    }
  });
}

/**
 * Global Toast Notification Dispatcher
 * @param {string} message
 * @param {'info' | 'success' | 'warning' | 'error'} [type]
 * @param {number} [duration]
 */
export function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;

  const iconMap = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };

  toast.innerHTML = `
    <span class="toast-icon">${iconMap[type] || 'ℹ️'}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button type="button" class="toast-close" aria-label="Fechar">&times;</button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => dismissToast(toast));
  }

  container.appendChild(toast);

  const timer = setTimeout(() => {
    dismissToast(toast);
  }, duration);

  toast._timer = timer;
}

function dismissToast(toast) {
  if (!toast) return;
  if (toast._timer) clearTimeout(toast._timer);
  toast.style.animation = 'toastSlideOut 0.25s forwards cubic-bezier(0.16, 1, 0.3, 1)';
  setTimeout(() => {
    toast.remove();
  }, 250);
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
