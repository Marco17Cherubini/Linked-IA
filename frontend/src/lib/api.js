// Client dell'API. Gli errori del server arrivano come { error: { code, message } }.

const TOKEN_KEY = 'lia.analystToken'

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

// Il token resta solo nella sessione del browser: mai nell'URL, mai in localStorage.
export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* archiviazione non disponibile: il token vale solo per questa pagina */
  }
}

async function request(path, { method = 'GET', body, auth = false, signal } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  let response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
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
    throw new ApiError(response.status, err?.code || 'http_error', err?.message || `Errore ${response.status}`)
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
  rerun: (eventId) => request(`/events/${encodeURIComponent(eventId)}/analyses`, { method: 'POST', auth: true }),
  createEvent: (payload) => request('/events', { method: 'POST', body: payload, auth: true }),
  requestSummary: (id, body) => request(`/analyses/${encodeURIComponent(id)}/summary`, { method: 'POST', body, auth: true }),
}

function clean(params = {}) {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
}
