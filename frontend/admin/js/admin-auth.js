/**
 * DINOS Pizzaria — Admin Authentication Controller
 * Handles login, logout, session verification, and reactive UI transitions.
 */

import { adminApi } from './admin-api.js';

let authCallback = null;
let logoutCallback = null;

export function initAuth(onAuthSuccess = null, onLogout = null) {
  authCallback = onAuthSuccess;
  logoutCallback = onLogout;

  const loginForm = document.getElementById('login-form');
  const logoutBtn = document.getElementById('btn-logout');

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const usernameInput = document.getElementById('login-username');
      const passwordInput = document.getElementById('login-password');
      const errorAlert = document.getElementById('login-error-alert');
      const errorMsg = document.getElementById('login-error-message');
      const submitBtn = document.getElementById('login-submit-btn');
      const spinner = submitBtn?.querySelector('.btn-spinner');

      const username = usernameInput?.value.trim() || '';
      const password = passwordInput?.value || '';

      if (!username || !password) {
        if (errorAlert && errorMsg) {
          errorMsg.textContent = 'Por favor, preencha todos os campos.';
          errorAlert.classList.remove('d-none');
        }
        return;
      }

      try {
        if (submitBtn) submitBtn.disabled = true;
        if (spinner) spinner.classList.remove('d-none');
        if (errorAlert) errorAlert.classList.add('d-none');

        await handleLogin(username, password);
      } catch (err) {
        if (errorAlert && errorMsg) {
          errorMsg.textContent = err.message || 'Falha ao autenticar.';
          errorAlert.classList.remove('d-none');
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
        if (spinner) spinner.classList.add('d-none');
      }
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
  }

  // Intercept unauthorized event from adminApi
  window.addEventListener('admin:unauthorized', (e) => {
    handleLogout(false);
    const errorAlert = document.getElementById('login-error-alert');
    const errorMsg = document.getElementById('login-error-message');
    if (errorAlert && errorMsg) {
      errorMsg.textContent = e.detail?.message || 'Sessão expirada. Faça login novamente.';
      errorAlert.classList.remove('d-none');
    }
  });

  return checkAuth();
}

export async function checkAuth() {
  const token = adminApi.getToken();
  const loginView = document.getElementById('login-view');
  const adminLayout = document.getElementById('admin-layout');
  const usernameDisplay = document.getElementById('admin-username-display');

  if (!token) {
    if (loginView) loginView.classList.remove('d-none');
    if (adminLayout) adminLayout.classList.add('d-none');
    return false;
  }

  try {
    const adminUser = await adminApi.getMe();
    if (usernameDisplay && adminUser?.username) {
      usernameDisplay.textContent = adminUser.username;
    }
    if (loginView) loginView.classList.add('d-none');
    if (adminLayout) adminLayout.classList.remove('d-none');

    window.dispatchEvent(new CustomEvent('admin:authenticated', { detail: { user: adminUser } }));
    if (typeof authCallback === 'function') {
      authCallback(adminUser);
    }
    return true;
  } catch {
    adminApi.clearToken();
    if (loginView) loginView.classList.remove('d-none');
    if (adminLayout) adminLayout.classList.add('d-none');
    return false;
  }
}

export async function handleLogin(username, password) {
  const data = await adminApi.login(username, password);
  if (!data || !data.access_token) {
    throw new Error('Token de autenticação não retornado pelo servidor.');
  }

  adminApi.setToken(data.access_token);
  await checkAuth();
}

export function handleLogout(notifyCallback = true) {
  adminApi.clearToken();

  const loginView = document.getElementById('login-view');
  const adminLayout = document.getElementById('admin-layout');
  const passwordInput = document.getElementById('login-password');

  if (passwordInput) passwordInput.value = '';
  if (loginView) loginView.classList.remove('d-none');
  if (adminLayout) adminLayout.classList.add('d-none');

  window.dispatchEvent(new CustomEvent('admin:logout'));
  if (notifyCallback && typeof logoutCallback === 'function') {
    logoutCallback();
  }
}
