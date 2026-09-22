/**
 * DINOS Pizzaria — Admin Storefront Texts Controller
 * Lets admins edit customer-facing landing page copy without changing code.
 */

import { adminApi } from './admin-api.js';

let siteContentItems = [];
let toastFn = null;

const FIELD_LABELS = {
  top_banner_enabled: 'Banner promocional no topo — Ativação',
  top_banner_text: 'Banner promocional no topo — Mensagem',
  top_banner_cta: 'Banner promocional no topo — Texto do botão',
  top_banner_link: 'Banner promocional no topo — Link do botão',
  store_is_open: 'Status de funcionamento da loja (Aberta / Fechada)',
  store_closed_message: 'Mensagem exibida quando a loja estiver fechada',
  featured_section_title: 'Título da seção “Mais Pedidas”',
  featured_section_subtitle: 'Subtítulo da seção “Mais Pedidas”',
  reviews_section_title: 'Título da seção de avaliações',
  reviews_section_subtitle: 'Subtítulo da seção de avaliações',
  brand_tagline: 'Assinatura no topo',
  header_status: 'Status do forno no cabeçalho',
  hero_badge: 'Selo acima do título principal',
  hero_title: 'Título principal da landing page',
  hero_highlight: 'Trecho destacado do título',
  hero_subtitle: 'Subtítulo do hero',
  hero_primary_cta: 'Botão principal do hero',
  hero_secondary_cta: 'Botão secundário do hero',
  hero_signature: 'Assinatura abaixo dos botões',
  highlight_1: 'Destaque 1',
  highlight_2: 'Destaque 2',
  highlight_3: 'Destaque 3',
  highlight_4: 'Destaque 4',
  highlight_5: 'Destaque 5',
  trust_1_title: 'Card confiança 1 — título',
  trust_1_text: 'Card confiança 1 — texto',
  trust_2_title: 'Card confiança 2 — título',
  trust_2_text: 'Card confiança 2 — texto',
  trust_3_title: 'Card confiança 3 — título',
  trust_3_text: 'Card confiança 3 — texto',
  trust_4_title: 'Card confiança 4 — título',
  trust_4_text: 'Card confiança 4 — texto',
  menu_search_placeholder: 'Placeholder da busca do cardápio',
  menu_filter_all: 'Filtro “Todos”',
  menu_filter_promos: 'Filtro “Promoções”',
  menu_filter_combos: 'Filtro “Combos”',
  footer_brand_desc: 'Rodapé — descrição da marca',
  footer_badge: 'Rodapé — selo da marca',
  footer_hours_title: 'Rodapé — título de horários',
  footer_hours_1: 'Rodapé — horário 1',
  footer_hours_2: 'Rodapé — horário 2',
  footer_hours_3: 'Rodapé — horário 3',
  footer_hours_closed: 'Rodapé — dia fechado',
  footer_payment_title: 'Rodapé — título de pagamento',
  footer_payment_text: 'Rodapé — texto de pagamento',
  footer_delivery_title: 'Rodapé — título de entrega',
  footer_delivery_text: 'Rodapé — texto de entrega',
  footer_contact_title: 'Rodapé — título de atendimento',
  footer_contact_text: 'Rodapé — texto de atendimento',
  footer_whatsapp_button: 'Rodapé — botão WhatsApp',
  footer_location_text: 'Rodapé — texto de localização',
  footer_bottom_text: 'Rodapé — direitos reservados',
  footer_slogan: 'Rodapé — slogan final'
};

const FIELD_HELP = {
  top_banner_enabled: 'Se ativado, exibe uma barra promocional no topo de todas as páginas.',
  store_is_open: 'Quando fechada, bloqueia pedidos imediatos e orienta o cliente a agendar.',
  store_closed_message: 'Explicativo exibido ao cliente caso a loja esteja temporariamente fechada.',
  hero_highlight: 'Deve ser uma parte do título principal para aparecer em dourado.',
  hero_subtitle: 'Texto maior de venda abaixo do título.',
  trust_1_text: 'Texto curto do card “Por que pedir na DINOS?”.',
  trust_2_text: 'Texto curto do card “Por que pedir na DINOS?”.',
  trust_3_text: 'Texto curto do card “Por que pedir na DINOS?”.',
  trust_4_text: 'Texto curto do card “Por que pedir na DINOS?”.'
};

const BOOLEAN_FIELDS = new Set([
  'top_banner_enabled',
  'store_is_open'
]);

const LONG_FIELDS = new Set([
  'store_closed_message',
  'hero_subtitle',
  'trust_1_text',
  'trust_2_text',
  'trust_3_text',
  'trust_4_text',
  'footer_brand_desc',
  'footer_payment_text',
  'footer_contact_text'
]);

export function initSiteContent(showToast) {
  toastFn = showToast;

  const form = document.getElementById('site-content-form');
  const saveBtn = document.getElementById('btn-save-site-content');

  if (form && !form.dataset.bound) {
    form.dataset.bound = 'true';
    form.addEventListener('submit', handleSubmit);
  }

  if (saveBtn && !saveBtn.dataset.bound) {
    saveBtn.dataset.bound = 'true';
    saveBtn.addEventListener('click', () => form?.requestSubmit());
  }
}

export async function loadSiteContent() {
  const container = document.getElementById('site-content-fields');
  if (container) {
    container.innerHTML = '<div class="table-loading-cell"><div class="spinner-inline"></div> Carregando textos do site...</div>';
  }

  try {
    siteContentItems = await adminApi.getSiteContent();
    renderSiteContentForm();
  } catch (err) {
    if (container) {
      container.innerHTML = `<div class="table-empty-cell text-danger">⚠️ Falha ao carregar textos: ${escapeHtml(err.message)}</div>`;
    }
  }
}

function renderSiteContentForm() {
  const container = document.getElementById('site-content-fields');
  if (!container) return;

  const knownItems = siteContentItems.filter((item) => FIELD_LABELS[item.key]);
  if (knownItems.length === 0) {
    container.innerHTML = '<div class="table-empty-cell">Nenhum texto configurável encontrado.</div>';
    return;
  }

  container.innerHTML = knownItems.map((item) => {
    const label = FIELD_LABELS[item.key] || item.key;
    const help = FIELD_HELP[item.key] || '';
    const value = escapeHtml(item.value || '');
    let control = '';
    if (BOOLEAN_FIELDS.has(item.key)) {
      const isTrue = item.value === 'true';
      control = `
        <select class="form-select settings-input" data-key="${item.key}">
          <option value="true" ${isTrue ? 'selected' : ''}>✅ Ativado / Aberto (true)</option>
          <option value="false" ${!isTrue ? 'selected' : ''}>❌ Desativado / Fechado (false)</option>
        </select>
      `;
    } else if (LONG_FIELDS.has(item.key)) {
      control = `<textarea class="form-textarea settings-input" rows="3" data-key="${item.key}" maxlength="1000">${value}</textarea>`;
    } else {
      control = `<input type="text" class="form-input settings-input" data-key="${item.key}" value="${value}" maxlength="1000">`;
    }

    return `
      <div class="settings-field ${LONG_FIELDS.has(item.key) ? 'settings-field--wide' : ''}">
        <label class="form-label">${escapeHtml(label)}</label>
        ${control}
        ${help ? `<small class="settings-help">${escapeHtml(help)}</small>` : ''}
      </div>
    `;
  }).join('');
}

async function handleSubmit(event) {
  event.preventDefault();

  const saveBtn = document.getElementById('btn-save-site-content');
  const inputs = Array.from(document.querySelectorAll('#site-content-fields .settings-input'));
  const items = inputs.map((input) => ({
    key: input.dataset.key,
    value: input.value.trim()
  })).filter((item) => item.key);

  if (items.some((item) => !item.value)) {
    toastFn?.('Preencha todos os textos antes de salvar.', 'warning');
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Salvando...';
  }

  try {
    siteContentItems = await adminApi.updateSiteContent(items);
    renderSiteContentForm();
    toastFn?.('Textos do site atualizados com sucesso!', 'success');
  } catch (err) {
    toastFn?.(err.message || 'Falha ao salvar textos do site.', 'error');
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Salvar Textos';
    }
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
