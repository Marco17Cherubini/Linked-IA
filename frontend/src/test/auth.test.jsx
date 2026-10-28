import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, setCsrfToken } from '../lib/api.js'
import CookiePage from '../pages/CookiePage.jsx'
import LoginPage from '../pages/LoginPage.jsx'
import PrivacyPage from '../pages/PrivacyPage.jsx'

function mockFetch(body = {}, status = 200) {
  const fn = vi.fn(async () => ({ ok: status < 400, status, json: async () => body }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken('')
  localStorage.clear()
  sessionStorage.clear()
})

describe('client API', () => {
  it('invia il token CSRF solo alle richieste che modificano e senza credenziali nell\'URL', async () => {
    const fetch = mockFetch({ analysis_id: 'a' })
    setCsrfToken('csrf-fixture')
    await api.createEvent({ id: 'x' })
    await api.meta()
    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe('/api/events')
    expect(options.headers['X-CSRF-Token']).toBe('csrf-fixture')
    expect(options.credentials).toBe('same-origin')
    expect(options.headers.Authorization).toBeUndefined()
    expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBeUndefined()
  })

  it('non salva password, token o sessioni nello storage del browser', async () => {
    mockFetch({ authenticated: true, csrf_token: 'csrf-fixture', expires_at: '2026-10-28T20:00:00+00:00' })
    await api.login('password-fixture')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('riporta codice e tempo di riprova degli errori strutturati', async () => {
    mockFetch({ error: { code: 'budget_blocked', message: 'Budget esaurito', retry_after: 60, retry_at: '2026-10-28T13:00:00+00:00' } }, 429)
    await expect(api.requestSummary('a', { confirm_cost: true })).rejects.toMatchObject({
      status: 429,
      code: 'budget_blocked',
      retryAfter: 60,
    })
  })
})

describe('pagine pubbliche', () => {
  const meta = { features: { login: true }, legal: { controller_name: null, controller_email: null, session_hours: 8 } }

  it('la pagina di accesso collega le informative', () => {
    render(
      <MemoryRouter>
        <LoginPage meta={meta} />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')
    expect(screen.getByRole('link', { name: 'informativa privacy' })).toHaveAttribute('href', '/privacy')
    expect(screen.getByRole('link', { name: 'cookie policy' })).toHaveAttribute('href', '/cookie')
  })

  it('senza dati del titolare l\'informativa si dichiara non definitiva', () => {
    render(
      <MemoryRouter>
        <PrivacyPage meta={meta} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Informativa in completamento')).toBeInTheDocument()
  })

  it('la cookie policy elenca il solo cookie tecnico con la durata configurata', () => {
    render(
      <MemoryRouter>
        <CookiePage meta={{ ...meta, legal: { controller_name: 'FIXTURE titolare', controller_email: 'a@example.org', session_hours: 8 } }} />
      </MemoryRouter>,
    )
    expect(screen.getByText('__Host-lia_session')).toBeInTheDocument()
    expect(screen.getByText('Fino a 8 ore, o fino all\'uscita')).toBeInTheDocument()
    expect(screen.getAllByText('FIXTURE titolare').length).toBeGreaterThan(0)
  })
})
