const BASE = '/api/v1'

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const resp = await fetch(BASE + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.clear()
      location.href = '/login'
    }
    throw new Error(body?.msg || body?.detail || `HTTP ${resp.status}`)
  }
  return body as T
}

export const get = (path: string) => api(path)
export const post = (path: string, data?: unknown) =>
  api(path, { method: 'POST', body: JSON.stringify(data ?? {}) })
export const put = (path: string, data?: unknown) =>
  api(path, { method: 'PUT', body: JSON.stringify(data ?? {}) })
export const del = (path: string) => api(path, { method: 'DELETE' })
