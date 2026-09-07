/**
 * Hospital Queue Management System
 * API Client + WebSocket Manager + Toast + Utilities
 */

// ============================================================
// CONFIG
// ============================================================
const CONFIG = {
  BASE_URL: '/api/v1',
  WS_BASE:  `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/v1/queue/ws`,
  WS_RECONNECT_DELAY: 3000,
  WS_MAX_RECONNECTS:  10,
};

// ============================================================
// HTTP API CLIENT
// ============================================================
const api = (() => {
  async function request(method, path, { body, params } = {}) {
    let url = CONFIG.BASE_URL + path;
    if (params) {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '')
      );
      if (q.toString()) url += '?' + q;
    }

    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);

    const res = await fetch(url, opts);

    let data;
    try { data = await res.json(); } catch { data = null; }

    if (!res.ok) {
      const msg =
        data?.detail
          ? (Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('; ') : data.detail)
          : `HTTP ${res.status}`;
      const err = new Error(msg);
      err.status = res.status;
      err.data   = data;
      throw err;
    }
    return data;
  }

  return {
    get:    (path, opts)  => request('GET',    path, opts),
    post:   (path, body, opts) => request('POST',   path, { body, ...(opts||{}) }),
    put:    (path, body, opts) => request('PUT',    path, { body, ...(opts||{}) }),
    patch:  (path, body, opts) => request('PATCH',  path, { body, ...(opts||{}) }),
    delete: (path, opts)  => request('DELETE', path, opts),
  };
})();

// ============================================================
// DOMAIN API WRAPPERS
// ============================================================

/* --- Patients --- */
const patientApi = {
  list:   (params) => api.get('/patients', { params }),
  get:    (id)     => api.get(`/patients/${id}`),
  getByCccd: (cccd)=> api.get(`/patients/cccd/${cccd}`),
  create: (data)   => api.post('/patients', data),
  update: (id, data) => api.put(`/patients/${id}`, data),
  history: (id, params) => api.get(`/patients/${id}/history`, { params }),
};

/* --- Queue --- */
const queueApi = {
  takeTicket:    (data)   => api.post('/queue/ticket', data),
  summary:       (params) => api.get('/queue/summary', { params }),
  waiting:       (params) => api.get('/queue/waiting', { params }),
  tickets:       (params) => api.get('/queue/tickets', { params }),
  getTicket:     (id)     => api.get(`/queue/tickets/${id}`),
  callNext:      (counter_number) => api.post('/queue/call-next', null, { params: { counter_number } }),
  updateStatus:  (id, data)  => api.patch(`/queue/tickets/${id}/status`, data),
  skipTicket:    (id)     => api.patch(`/queue/tickets/${id}/skip`),
  doneTicket:    (id)     => api.patch(`/queue/tickets/${id}/done`),
};

/* --- Reception --- */
const receptionApi = {
  scanCccd:   (data)    => api.post('/receptions/scan-cccd', data),
  create:     (data)    => api.post('/receptions', data),
  stats:      ()        => api.get('/receptions/stats'),
  list:       (params)  => api.get('/receptions', { params }),
  get:        (id)      => api.get(`/receptions/${id}`),
  update:     (id, data)=> api.put(`/receptions/${id}`, data),
  checkIn:    (id, data)=> api.post(`/receptions/${id}/check-in`, data),
  complete:   (id)      => api.post(`/receptions/${id}/complete`),
  cancel:     (id)      => api.post(`/receptions/${id}/cancel`),
};

// ============================================================
// WEBSOCKET MANAGER
// ============================================================
class WSManager {
  /**
   * @param {'display'|'kiosk'|'reception'} room
   */
  constructor(room) {
    this.room       = room;
    this.ws         = null;
    this.reconnects = 0;
    this.listeners  = {};         // { eventType: [callbacks] }
    this.pingTimer  = null;
    this._reconnectTimer = null;
    this._intentionalClose = false;
    this._statusEl  = null;       // optional DOM element for status indicator
  }

  setStatusEl(el) { this._statusEl = el; return this; }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    this._intentionalClose = false;
    this._setStatus('connecting');

    const url = `${CONFIG.WS_BASE}/${this.room}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnects = 0;
      this._setStatus('connected');
      this._startPing();
      this._emit('_connected');
    };

    this.ws.onmessage = ({ data }) => {
      let msg;
      try { msg = JSON.parse(data); } catch { msg = { type: data, data: null }; }
      if (msg === 'pong' || msg?.type === 'pong') return;
      this._emit(msg.type, msg.data);
      this._emit('*', msg);         // wildcard listener
    };

    this.ws.onerror = () => { /* close will fire next */ };

    this.ws.onclose = (e) => {
      this._stopPing();
      this._setStatus('disconnected');
      this._emit('_disconnected', e);
      if (!this._intentionalClose && this.reconnects < CONFIG.WS_MAX_RECONNECTS) {
        const delay = CONFIG.WS_RECONNECT_DELAY * Math.min(this.reconnects + 1, 4);
        this._reconnectTimer = setTimeout(() => {
          this.reconnects++;
          this.connect();
        }, delay);
      }
    };

    return this;
  }

  disconnect() {
    this._intentionalClose = true;
    clearTimeout(this._reconnectTimer);
    this._stopPing();
    if (this.ws) { this.ws.close(); this.ws = null; }
  }

  on(type, fn) {
    (this.listeners[type] = this.listeners[type] || []).push(fn);
    return this;
  }

  off(type, fn) {
    if (!this.listeners[type]) return this;
    this.listeners[type] = fn
      ? this.listeners[type].filter(f => f !== fn)
      : [];
    return this;
  }

  _emit(type, payload) {
    (this.listeners[type] || []).forEach(fn => { try { fn(payload); } catch (e) { console.error(e); } });
  }

  _startPing() {
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send('ping');
    }, 25_000);
  }

  _stopPing() {
    clearInterval(this.pingTimer);
    this.pingTimer = null;
  }

  _setStatus(status) {
    if (this._statusEl) {
      this._statusEl.className = `ws-indicator ${status}`;
      const label = this._statusEl.nextElementSibling;
      if (label) {
        label.textContent = { connected: 'Đã kết nối', connecting: 'Đang kết nối…', disconnected: 'Mất kết nối' }[status] ?? status;
      }
    }
  }
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
const toast = (() => {
  let container;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  const ICONS = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️',
  };

  function show(type, title, message = '', duration = 4000) {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.style.position = 'relative';
    el.innerHTML = `
      <span class="toast-icon">${ICONS[type] ?? 'ℹ️'}</span>
      <div class="toast-content">
        <div class="toast-title">${escHtml(title)}</div>
        ${message ? `<div class="toast-message">${escHtml(message)}</div>` : ''}
      </div>
      <button class="toast-close" aria-label="Đóng">✕</button>
      <div class="toast-progress" style="animation-duration:${duration}ms"></div>`;

    el.querySelector('.toast-close').onclick = () => remove(el);
    getContainer().appendChild(el);

    const timer = setTimeout(() => remove(el), duration);
    el._timer = timer;
    return el;
  }

  function remove(el) {
    clearTimeout(el._timer);
    el.classList.add('removing');
    el.addEventListener('transitionend', () => el.remove(), { once: true });
  }

  return {
    success: (t, m, d) => show('success', t, m, d),
    error:   (t, m, d) => show('error',   t, m, d ?? 6000),
    warning: (t, m, d) => show('warning', t, m, d),
    info:    (t, m, d) => show('info',    t, m, d),
  };
})();

// ============================================================
// UTILITIES
// ============================================================

/** Escape HTML special chars */
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Format ISO date string to DD/MM/YYYY */
function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleDateString('vi-VN');
}

/** Format ISO datetime string to HH:mm DD/MM/YYYY */
function fmtDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** Format HH:mm */
function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

/** Today's date string YYYY-MM-DD */
function today() {
  return new Date().toISOString().slice(0, 10);
}

/** Format gender */
function fmtGender(g) {
  return { male: 'Nam', female: 'Nữ', other: 'Khác' }[g] ?? g ?? '—';
}

/** Priority label */
function fmtPriority(p) {
  return ['Bình thường', 'Ưu tiên', 'Cấp cứu'][+p] ?? '—';
}

/** Status badge HTML */
function statusBadge(status) {
  const labels = {
    WAITING:    'Chờ',
    CALLING:    'Đang gọi',
    SERVING:    'Đang phục vụ',
    DONE:       'Hoàn thành',
    SKIPPED:    'Bỏ qua',
    PENDING:    'Chờ tiếp nhận',
    CHECKED_IN: 'Đã tiếp nhận',
    COMPLETED:  'Hoàn thành',
    CANCELLED:  'Đã huỷ',
  };
  const cls = (status ?? '').toLowerCase().replace('_', '_');
  return `<span class="badge badge-${cls}">${escHtml(labels[status] ?? status ?? '—')}</span>`;
}

/** Get initials from full name */
function initials(name) {
  if (!name) return '?';
  return name.trim().split(/\s+/).map(w => w[0]).slice(-2).join('').toUpperCase();
}

/** Debounce */
function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

/** Query selector shorthand */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/** Set element text safely */
function setText(sel, val, root = document) {
  const el = $(sel, root);
  if (el) el.textContent = val ?? '—';
}

/** Show/hide element */
function show(sel, root = document) {
  const el = typeof sel === 'string' ? $(sel, root) : sel;
  if (el) el.classList.remove('hidden');
}
function hide(sel, root = document) {
  const el = typeof sel === 'string' ? $(sel, root) : sel;
  if (el) el.classList.add('hidden');
}

/** Simple HTML sanitiser for dynamic content */
function setHtml(sel, html, root = document) {
  const el = $(sel, root);
  if (el) el.innerHTML = html;
}

/** Loading button state */
function btnLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn._originalText = btn.innerHTML;
    btn.classList.add('btn-loading');
    btn.innerHTML = '';
  } else {
    btn.disabled = false;
    btn.classList.remove('btn-loading');
    if (btn._originalText !== undefined) btn.innerHTML = btn._originalText;
  }
}

/** Render pagination controls */
function renderPagination(containerSel, { page, total_pages }, onPage) {
  const el = $(containerSel);
  if (!el || total_pages <= 1) { if (el) el.innerHTML = ''; return; }

  const pages = [];
  // Always show first/last and a window around current
  const range = new Set([1, total_pages]);
  for (let i = Math.max(1, page - 2); i <= Math.min(total_pages, page + 2); i++) range.add(i);
  const sorted = [...range].sort((a, b) => a - b);

  let html = `<button class="page-btn" ${page === 1 ? 'disabled' : ''} data-p="${page - 1}">‹</button>`;
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) html += `<span class="page-btn" style="pointer-events:none;border:none">…</span>`;
    html += `<button class="page-btn ${p === page ? 'active' : ''}" data-p="${p}">${p}</button>`;
    prev = p;
  }
  html += `<button class="page-btn" ${page === total_pages ? 'disabled' : ''} data-p="${page + 1}">›</button>`;

  el.innerHTML = `<div class="pagination">${html}</div>`;
  el.querySelectorAll('[data-p]').forEach(btn => {
    btn.addEventListener('click', () => onPage(+btn.dataset.p));
  });
}

/** Build modal and return { el, close } */
function createModal({ title, body, footer = '', size = '' }) {
  const el = document.createElement('div');
  el.className = 'modal-backdrop';
  el.innerHTML = `
    <div class="modal ${size ? 'modal-' + size : ''}">
      <div class="modal-header">
        <h2 class="modal-title">${title}</h2>
        <button class="modal-close" aria-label="Đóng">✕</button>
      </div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
    </div>`;

  const close = () => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.15s';
    setTimeout(() => el.remove(), 150);
  };

  el.querySelector('.modal-close').addEventListener('click', close);
  el.addEventListener('mousedown', e => { if (e.target === el) close(); });
  document.addEventListener('keydown', function esc(e) {
    if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); }
  });

  document.body.appendChild(el);
  return { el, close };
}

/** Format number with leading zero */
function pad(n, len = 3) { return String(n).padStart(len, '0'); }

/** Confirm dialog (returns Promise<boolean>) */
function confirm(message) {
  return new Promise(resolve => {
    const { el, close } = createModal({
      title: '⚠️ Xác nhận',
      body: `<p style="font-size:var(--text-base);line-height:1.7">${escHtml(message)}</p>`,
      footer: `
        <button class="btn btn-ghost" id="confirm-cancel">Huỷ</button>
        <button class="btn btn-danger" id="confirm-ok">Xác nhận</button>`,
      size: 'sm',
    });
    el.querySelector('#confirm-cancel').onclick = () => { close(); resolve(false); };
    el.querySelector('#confirm-ok').onclick     = () => { close(); resolve(true);  };
  });
}

// ============================================================
// LIVE CLOCK
// ============================================================
function startClock(selector) {
  const el = document.querySelector(selector);
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleString('vi-VN', {
      weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }
  tick();
  return setInterval(tick, 1000);
}

// Export to global scope (no module bundler needed)
window.HospitalApp = {
  api, patientApi, queueApi, receptionApi,
  WSManager,
  toast,
  escHtml, fmtDate, fmtDateTime, fmtTime, today,
  fmtGender, fmtPriority, statusBadge, initials,
  debounce, $, $$, setText, setHtml, show, hide,
  btnLoading, renderPagination, createModal, pad, confirm,
  startClock,
};
