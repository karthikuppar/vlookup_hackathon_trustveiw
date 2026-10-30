// Small fetch wrapper used by all views. Errors carry `status` and friendly messages.
export class ApiError extends Error {
  constructor(message, status, retryAfter) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfter = retryAfter
  }
}

export const api = async (path, token, options = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  }
  let res
  try {
    res = await fetch(path, { ...options, headers })
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0)
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : data.message
    if (res.status === 429) {
      const secs = parseInt(res.headers.get('Retry-After') || '', 10)
      const msg = Number.isFinite(secs)
        ? `Too many attempts, try again in ${secs} seconds`
        : 'Too many attempts, please try again shortly'
      throw new ApiError(msg, 429, Number.isFinite(secs) ? secs : undefined)
    }
    if (res.status === 403) {
      throw new ApiError(detail || 'You do not have permission to view or do this. It may be restricted to administrators.', 403)
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status)
  }
  return data
}

export const isAdminRole = (role) => role === 'client_admin' || role === 'system_admin'
