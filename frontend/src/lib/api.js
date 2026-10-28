// Client dell'API. Gli errori del server arrivano come { error: { code, message, retry_after?, retry_at? } }.
//
// L'accesso dell'operatore usa un cookie di sessione HttpOnly impostato dal server: il browser
// lo invia da solo e JavaScript non può leggerlo. Il token CSRF della sessione resta soltanto
// in memoria (mai in localStorage, sessionStorage o nell'URL) e accompagna le richieste che
// modificano lo stato.

let csrfToken = ''

export function setCsrfToken(token) {
  csrfToken = token || ''
}

export class ApiError extends Error {
  constructor(status, code, message, { retryAfter = null, retryAt = null } = {}) {
    super(message)
    this.status = status
    this.code = code
    this.retryAfter = retryAfter
    this.retryAt = retryAt
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken
  let response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError(0, 'network', 'Server non raggiungibile. Controlla la connessione e riprova.')
  }
  let data = null
  try {
    data = await response.json()
  } catch {
    /* risposta vuota o non JSON */
  }
  if (!response.ok) {
    const err = data?.error
    throw new ApiError(response.status, err?.code || 'http_error', err?.message || `Errore ${response.status}`, {
      retryAfter: err?.retry_after ?? null,
      retryAt: err?.retry_at ?? null,
    })
  }
  return data
}

// Le analisi concluse sono immutabili: si tengono in memoria per non ripetere richieste
// quando si cambia mercato o vista e poi si torna indietro.
const analysisCache = new Map()

export const api = {
  meta: (opts) => request('/meta', opts),
  featured: (opts) => request('/featured', opts),
  events: (params, opts) => request(`/events?${new URLSearchParams(clean(params))}`, opts),
  analyses: (params, opts) => request(`/analyses?${new URLSearchParams(clean(params))}`, opts),
  async analysis(id, { market, view }, opts = {}) {
    const key = `${id}|${market}|${view}`
    if (analysisCache.has(key)) return analysisCache.get(key)
    const data = await request(`/analyses/${encodeURIComponent(id)}?${new URLSearchParams({ market, view })}`, opts)
    const summaryPending = data.summary && ['queued', 'running'].includes(data.summary.status)
    if (data.status === 'succeeded' && !summaryPending) analysisCache.set(key, data)
    return data
  },
  forgetAnalysis(id) {
    for (const key of analysisCache.keys()) if (key.startsWith(`${id}|`)) analysisCache.delete(key)
  },
  forgetAll() {
    analysisCache.clear()
  },
  session: (opts) => request('/auth/session', opts),
  login: (password) => request('/auth/login', { method: 'POST', body: { password } }),
  logout: () => request('/auth/logout', { method: 'POST', body: {} }),
  budget: (opts) => request('/operator/budget', opts),
  rerun: (eventId) => request(`/events/${encodeURIComponent(eventId)}/analyses`, { method: 'POST', body: {} }),
  createEvent: (payload) => request('/events', { method: 'POST', body: payload }),
  requestSummary: (id, body) => request(`/analyses/${encodeURIComponent(id)}/summary`, { method: 'POST', body }),
  startNewsSearch: (body) => request('/news/searches', { method: 'POST', body }),
  newsSearch: (id, opts) => request(`/news/searches/${encodeURIComponent(id)}`, opts),
  recentNewsSearches: (opts) => request('/news/searches', opts),
  analyzeNewsEvent: (id, idx) =>
    request(`/news/searches/${encodeURIComponent(id)}/events/${Number(idx)}/analyze`, { method: 'POST', body: {} }),
}

function clean(params = {}) {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
}
