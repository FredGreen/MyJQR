const BASE = '/api/v1'

// 401 时用 refresh_token 静默续期（30 天滑动免登录）；并发 401 共享同一次刷新
let refreshing: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const rt = localStorage.getItem('refresh_token')
  if (!rt) return false
  try {
    const resp = await fetch(BASE + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    const body = await resp.json().catch(() => ({}))
    // refresh 接口 tokens 直接挂在 data 上（兼容 data.tokens 包装形态）
    const tokens = body?.data?.tokens ?? body?.data
    if (!resp.ok || !tokens?.access_token) return false
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    return true
  } catch {
    return false
  }
}

function forceLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (!location.pathname.startsWith('/login')) location.href = '/login'
}

export async function api<T = any>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
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
      // 这三个接口的 401 是业务失败（密码错/refresh 失效），不能再续期
      const noRefresh = ['/auth/login', '/auth/register', '/auth/refresh'].includes(path)
      if (!noRefresh && !retried) {
        refreshing = refreshing ?? tryRefresh().finally(() => { refreshing = null })
        if (await refreshing) return api<T>(path, options, true)
      }
      forceLogout()
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
