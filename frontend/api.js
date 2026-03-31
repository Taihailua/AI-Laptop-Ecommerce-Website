/**
 * api.js – Shared API helpers for AI Laptop Ecommerce
 * Backend base URL: http://localhost:8000
 */

const API_BASE = 'http://localhost:8000';

async function readErrorMessage(res, fallback = 'Request failed') {
  try {
    const data = await res.json();
    if (data?.detail) return data.detail;
    if (data?.message) return data.message;
  } catch (_) {}

  try {
    const text = await res.text();
    if (text) return text;
  } catch (_) {}

  return fallback;
}

// ─── Cart (localStorage) ─────────────────────────────────────────────────────
export const Cart = {
  getAll() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
  },
  add(product, qty = 1) {
    const cart = Cart.getAll();
    const existing = cart.find(i => i.product_id === product.id);
    if (existing) {
      existing.quantity += qty;
    } else {
      cart.push({ product_id: product.id, name: product.name, price: product.price, quantity: qty, image_url: product.image_url });
    }
    localStorage.setItem('cart', JSON.stringify(cart));
  },
  remove(product_id) {
    const cart = Cart.getAll().filter(i => i.product_id !== product_id);
    localStorage.setItem('cart', JSON.stringify(cart));
  },
  updateQty(product_id, qty) {
    const cart = Cart.getAll().map(i => i.product_id === product_id ? { ...i, quantity: qty } : i);
    localStorage.setItem('cart', JSON.stringify(cart));
  },
  clear() {
    localStorage.removeItem('cart');
  },
  total() {
    return Cart.getAll().reduce((sum, i) => sum + i.price * i.quantity, 0);
  }
};

// ─── Products ─────────────────────────────────────────────────────────────────
export async function fetchProducts(searchOrOptions = '', maybeOptions = {}) {
  const isObjectArg = typeof searchOrOptions === 'object' && searchOrOptions !== null;
  const search = isObjectArg ? String(searchOrOptions.search || '') : String(searchOrOptions || '');
  const options = isObjectArg ? searchOrOptions : maybeOptions;
  const includePaused = Boolean(options?.includePaused);

  const params = new URLSearchParams();
  if (search.trim()) params.set('search', search.trim());
  if (includePaused) params.set('include_paused', 'true');
  if (options?.specsFilter) params.set('specs_filter', options.specsFilter);
  if (options?.sortPrice) params.set('sort_by_price', options.sortPrice);

  const qs = params.toString();
  const url = qs ? `${API_BASE}/api/products/?${qs}` : `${API_BASE}/api/products/`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}

export async function fetchFilters() {
  const res = await fetch(`${API_BASE}/api/products/filters`);
  if (!res.ok) throw new Error('Failed to fetch product filters');
  return res.json();
}

export async function createProduct(formData) {
  // Now accepts FormData instead of object
  const res = await fetch(`${API_BASE}/api/products/`, {
    method: 'POST',
    body: formData // No Content-Type header needed for FormData
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateProduct(id, formData) {
  const res = await fetch(`${API_BASE}/api/products/${id}`, {
    method: 'PUT',
    body: formData
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteProduct(id) {
  const res = await fetch(`${API_BASE}/api/products/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await readErrorMessage(res, 'Xóa sản phẩm thất bại.'));
}

export async function setProductBusinessPaused(id, isPaused) {
  const res = await fetch(`${API_BASE}/api/products/${id}/business-status?is_paused=${isPaused ? 'true' : 'false'}`, {
    method: 'PATCH'
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, 'Không cập nhật được trạng thái kinh doanh.'));
  return res.json();
}


// ─── Orders ───────────────────────────────────────────────────────────────────
export async function checkout(orderData) {
  const res = await fetch(`${API_BASE}/api/orders/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(orderData)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function trackOrderByPhone(phone) {
  const res = await fetch(`${API_BASE}/api/orders/track/${encodeURIComponent(phone)}`);
  if (!res.ok) throw new Error('Không tìm thấy đơn hàng.');
  return res.json();
}

export async function fetchAllOrders() {
  const res = await fetch(`${API_BASE}/api/orders/`);
  if (!res.ok) throw new Error('Failed to fetch orders');
  return res.json();
}

// ─── AI Chat ──────────────────────────────────────────────────────────────────
export async function sendChatMessage(sessionId, message, customer = {}) {
  const res = await fetch(`${API_BASE}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      customer_name: customer.customer_name || null,
      customer_phone: customer.customer_phone || null,
      customer_address: customer.customer_address || null
    })
  });
  if (!res.ok) throw new Error('AI chat error');
  return res.json();
}

export async function uploadTicketAttachment(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/chat/attachments`, {
    method: 'POST',
    body: formData // No Content-Type header for FormData
  });

  if (!res.ok) {
    let message = 'Upload bằng chứng thất bại.';
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
      else if (data?.message) message = data.message;
    } catch (_) {
      try {
        const text = await res.text();
        if (text) message = text;
      } catch (_) {}
    }
    throw new Error(message);
  }

  return res.json();
}

export async function sendAssistantMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/chat/assistant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message
    })
  });
  if (!res.ok) throw new Error('AI assistant error');
  return res.json();
}

export async function fetchTicketDetail(ticketId) {
  const res = await fetch(`${API_BASE}/api/chat/tickets/${Number(ticketId)}`);
  if (!res.ok) throw new Error('Không lấy được chi tiết ticket.');
  return res.json();
}

export async function fetchTicketsByPhone(phoneNumber) {
  const res = await fetch(`${API_BASE}/api/chat/tickets/by-phone/${encodeURIComponent(phoneNumber)}`);
  if (!res.ok) throw new Error('Không lấy được danh sách ticket theo số điện thoại.');
  return res.json();
}

export async function submitTicketSatisfaction(ticketId, score, note = '') {
  const res = await fetch(`${API_BASE}/api/chat/tickets/${Number(ticketId)}/satisfaction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score: Number(score), note: note || null })
  });
  if (!res.ok) throw new Error('Không gửi được đánh giá hài lòng.');
  return res.json();
}

export async function fetchTicketSatisfactionSummary() {
  const res = await fetch(`${API_BASE}/api/chat/tickets/summary/satisfaction`);
  if (!res.ok) throw new Error('Không tải được thống kê hài lòng.');
  return res.json();
}

export async function fetchAdminTickets(status = '') {
  const url = status
    ? `${API_BASE}/api/chat/admin/tickets?status=${encodeURIComponent(status)}`
    : `${API_BASE}/api/chat/admin/tickets`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Không tải được danh sách ticket quản trị.');
  return res.json();
}

export async function updateAdminTicket(ticketId, payload) {
  const res = await fetch(`${API_BASE}/api/chat/admin/tickets/${Number(ticketId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let message = 'Không cập nhật được ticket.';
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch (_) {}
    throw new Error(message);
  }
  return res.json();
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Login failed');
  }
  return res.json();
}

function buildAdminHeaders(json = false) {
  const token = getAdminToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json) headers['Content-Type'] = 'application/json';
  return headers;
}

async function adminRequest(path, options = {}) {
  const { method = 'GET', body = null } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: buildAdminHeaders(Boolean(body)),
    body: body ? JSON.stringify(body) : undefined
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Admin request failed'));
  }

  return res.json();
}

export async function fetchSupportKB() {
  return adminRequest('/api/admin/support-kb');
}

export async function updateSupportKB(data) {
  return adminRequest('/api/admin/support-kb', {
    method: 'PUT',
    body: data
  });
}

export async function reindexSupportKB() {
  return adminRequest('/api/admin/support-kb/reindex', {
    method: 'POST'
  });
}

export async function previewSupportKBContext(query) {
  const params = new URLSearchParams({ query: String(query || '') });
  return adminRequest(`/api/admin/support-kb/preview-context?${params.toString()}`);
}

// ─── Admin Auth ───────────────────────────────────────────────────────────────
export function getAdminToken() {
  return localStorage.getItem('admin_token');
}

export function setAdminToken(token) {
  localStorage.setItem('admin_token', token);
}

export function clearAdminToken() {
  localStorage.removeItem('admin_token');
}
