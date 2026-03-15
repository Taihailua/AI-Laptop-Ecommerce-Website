/**
 * api.js – Shared API helpers for AI Laptop Ecommerce
 * Backend base URL: http://localhost:8000
 */

const API_BASE = 'http://localhost:8000';

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
export async function fetchProducts(search = '') {
  const url = search
    ? `${API_BASE}/api/products/?search=${encodeURIComponent(search)}`
    : `${API_BASE}/api/products/`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch products');
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
  if (!res.ok) throw new Error(await res.text());
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
export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message })
  });
  if (!res.ok) throw new Error('AI chat error');
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
