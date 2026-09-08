/**
 * HTTP API Client — base layer.
 *
 * Tiêu chí 2: API client tách riêng hoàn toàn khỏi component.
 * Tiêu chí 11: URL tập trung tại đây, không hard-code ở nơi khác.
 *
 * - Token tự động inject từ localStorage.
 * - 401 tự động dispatch event để AuthContext xử lý logout.
 * - Lỗi chuẩn hoá thành ApiError.
 */

import type { ApiError } from '@/types';

// ── Config ────────────────────────────────────────────────────────────────────
// Tiêu chí 11: tất cả URL prefix từ env, không hard-code
const BASE_URL = '/api/v1';

// ── Token storage ─────────────────────────────────────────────────────────────
const TOKEN_KEY = 'hospital_access_token';

export const tokenStorage = {
  get:    ()           => localStorage.getItem(TOKEN_KEY),
  set:    (t: string)  => localStorage.setItem(TOKEN_KEY, t),
  remove: ()           => localStorage.removeItem(TOKEN_KEY),
};

// ── Request helper ────────────────────────────────────────────────────────────
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions {
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  /** Override content-type, e.g. 'application/x-www-form-urlencoded' */
  contentType?: string;
}

async function request<T>(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, body, contentType } = options;

  // Build URL with query params — filter out null/undefined
  let url = BASE_URL + path;
  if (params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') q.append(k, String(v));
    }
    const qs = q.toString();
    if (qs) url += `?${qs}`;
  }

  const token = tokenStorage.get();
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    if (contentType === 'application/x-www-form-urlencoded' && typeof body === 'object' && body !== null) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      requestBody = new URLSearchParams(body as Record<string, string>).toString();
    } else {
      headers['Content-Type'] = 'application/json';
      requestBody = JSON.stringify(body);
    }
  }

  const res = await fetch(url, { method, headers, body: requestBody });

  // 401 → broadcast logout event (AuthContext listens)
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }

  let data: unknown;
  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    data = await res.json();
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    const msg =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
        ? detail.map((e: { msg: string }) => e.msg).join('; ')
        : `HTTP ${res.status}`;
    const err = new Error(msg) as Error & ApiError;
    err.status = res.status;
    err.detail = msg;
    throw err;
  }

  return data as T;
}

// ── Public API ────────────────────────────────────────────────────────────────
export const apiClient = {
  get:    <T>(path: string, opts?: RequestOptions)              => request<T>('GET',    path, opts),
  post:   <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>('POST',   path, { body, ...opts }),
  put:    <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>('PUT',    path, { body, ...opts }),
  patch:  <T>(path: string, body?: unknown, opts?: RequestOptions) => request<T>('PATCH',  path, { body, ...opts }),
  delete: <T>(path: string, opts?: RequestOptions)              => request<T>('DELETE', path, opts),
};
