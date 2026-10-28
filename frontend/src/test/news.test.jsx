import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import EventCard from '../features/news/EventCard.jsx'
import { errorText, safeHref } from '../features/news/newsText.js'

// FIXTURE: scheda evento nella forma restituita dall'API.
const EVENT = {
  idx: 0,
  title: 'Lehman Brothers files for bankruptcy',
  description: 'Lehman Brothers filed for Chapter 11.',
  category: 'financial_crisis',
  category_label: 'Crisi finanziaria',
  tags: ['financial-crisis', 'lehman'],
  event_date: '2008-09-15',
  date_basis: 'searched_day',
  evidence: 'contemporary',
  result_idx: [3, 7],
  independent_sources: 2,
  flags: ['snippet_only'],
  flag_messages: ['Verificato solo su estratti forniti dal motore di ricerca, non sull’articolo completo.'],
  extraction: 'deterministic',
  analysis_id: null,
}
const RESULTS = {
  3: { idx: 3, url: 'https://reuters.com/a', title: 'Reuters story', publisher: 'reuters.com', published_on: '2008-09-15', kind: 'contemporary', snippet: '' },
  7: { idx: 7, url: 'javascript:alert(1)', title: 'Hostile <b>link</b>', publisher: 'x.org', published_on: null, kind: 'retrospective', snippet: 'testo' },
}

afterEach(() => vi.unstubAllGlobals())

function renderCard(props = {}) {
  return render(
    <MemoryRouter initialEntries={['/ricerca']}>
      <Routes>
        <Route path="/ricerca" element={<EventCard searchId="s1" event={EVENT} results={RESULTS} onError={() => {}} {...props} />} />
        <Route path="/analysis/:id" element={<p>Pagina analisi</p>} />
        <Route path="/new" element={<p>Modulo manuale</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ricerca notizie', () => {
  it('accetta solo link http(s)', () => {
    expect(safeHref('https://example.org/a')).toBe('https://example.org/a')
    expect(safeHref('javascript:alert(1)')).toBeUndefined()
    expect(safeHref('data:text/html,x')).toBeUndefined()
  })

  it('distingue errori, budget e assenza di risultati', () => {
    expect(errorText('provider_auth')).toMatch(/credenziali/)
    expect(errorText('provider_timeout')).toMatch(/non ha risposto/)
    expect(errorText('budget_blocked')).toMatch(/Budget/)
    expect(errorText('provider_auth')).not.toMatch(/Nessun evento trovato/)
  })

  it('mostra fonti, date di pubblicazione e avvertenze senza eseguire markup', () => {
    renderCard()
    expect(screen.getByRole('heading', { name: EVENT.title })).toBeInTheDocument()
    expect(screen.getByText('Fonti dell’epoca')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reuters story' })).toHaveAttribute('rel', 'noopener noreferrer nofollow')
    // L'URL non sicuro diventa testo, il markup resta testo.
    expect(screen.queryByRole('link', { name: /Hostile/ })).toBeNull()
    expect(screen.getByText('Hostile <b>link</b>')).toBeInTheDocument()
    expect(screen.getByText(/data di pubblicazione non dichiarata/)).toBeInTheDocument()
    expect(screen.getByText(/Verificato solo su estratti/)).toBeInTheDocument()
  })

  it('«Analizza questo evento» avvia l’analisi senza inserimento manuale', async () => {
    const fetch = vi.fn(async () => ({ ok: true, status: 202, json: async () => ({ analysis_id: 'a1', event_id: 'e1' }) }))
    vi.stubGlobal('fetch', fetch)
    renderCard()
    fireEvent.click(screen.getByRole('button', { name: 'Analizza questo evento' }))
    expect(await screen.findByText('Pagina analisi')).toBeInTheDocument()
    expect(fetch.mock.calls[0][0]).toBe('/api/news/searches/s1/events/0/analyze')
    expect(fetch.mock.calls[0][1].method).toBe('POST')
  })

  it('la correzione manuale è facoltativa e precompilata', async () => {
    renderCard()
    fireEvent.click(screen.getByRole('button', { name: 'Correggi prima di analizzare' }))
    await waitFor(() => expect(screen.getByText('Modulo manuale')).toBeInTheDocument())
  })
})
