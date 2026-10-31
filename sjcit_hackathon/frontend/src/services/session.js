// Single module for all session/token storage. Uses sessionStorage only
// (never localStorage), always inside try/catch.
const STALE_LOCAL_KEYS = ['access_token', 'ps04_session', 'auth_role']

function store() {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

export function getItem(key) {
  try {
    return store()?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function setItem(key, value) {
  try {
    store()?.setItem(key, value)
  } catch {
    /* storage unavailable */
  }
}

export function removeItem(key) {
  try {
    store()?.removeItem(key)
  } catch {
    /* storage unavailable */
  }
}

export const getToken = () => getItem('access_token')
export const setToken = (t) => setItem('access_token', t)
export const setRole = (r) => setItem('auth_role', r)
export const getAppMode = () => getItem('appMode')

export function getSession() {
  try {
    return JSON.parse(getItem('ps04_session'))
  } catch {
    return null
  }
}

export function saveSession(data) {
  setItem('ps04_session', JSON.stringify(data))
  if (data?.access_token) setToken(data.access_token)
  if (data?.user?.role) setRole(data.user.role)
}

export function clearSession() {
  STALE_LOCAL_KEYS.forEach(removeItem)
}

// Remove stale token keys left in localStorage by older builds.
export function purgeLegacyLocalStorage() {
  try {
    STALE_LOCAL_KEYS.forEach((k) => window.localStorage.removeItem(k))
  } catch {
    /* ignore */
  }
}

purgeLegacyLocalStorage()
