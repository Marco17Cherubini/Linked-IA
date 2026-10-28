import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import BudgetPanel from '../../components/BudgetPanel.jsx'
import { Notice, Skeleton } from '../../components/ui.jsx'
import { api } from '../../lib/api.js'
import { useAuth } from '../../lib/auth.jsx'
import { useApi } from '../../lib/useApi.js'
import { formatDate, formatDateTime } from '../../lib/format.js'
import EventCard from './EventCard.jsx'
import { EXCLUDED_TEXT, MODES, STAGE_LABEL, errorText } from './newsText.js'

const PENDING = ['queued', 'running']
const MAX_POLL_RETRIES = 5
const transient = (error) => error.status === 0 || error.status === 429 || error.status >= 500
const today = () => new Date().toISOString().slice(0, 10)

// Avanzamento reale letto dal server: nessuna chiamata ai provider, solo lo stato salvato.
function useSearch(id) {
  const [state, setState] = useState({ data: null, error: null })
  useEffect(() => {
    if (!id) return undefined
    const controller = new AbortController()
    let timer = null
    let delay = 1200
    let retries = 0
    let cancelled = false
    const schedule = () => {
      timer = setTimeout(load, delay)
      delay = Math.min(delay * 1.5, 8000)
    }
    const load = async () => {
      try {
        const data = await api.newsSearch(id, { signal: controller.signal })
        if (cancelled) return
        retries = 0
        setState({ data, error: null })
        if (PENDING.includes(data.status)) schedule()
      } catch (error) {
        if (error.name === 'AbortError' || cancelled) return
        setState((s) => ({ data: s.data, error }))
        if (transient(error) && retries < MAX_POLL_RETRIES) {
          retries += 1
          schedule()
        }
      }
    }
    setState({ data: null, error: null })
    load()
    return () => {
      cancelled = true
      controller.abort()
      clearTimeout(timer)
    }
  }, [id])
  return state
}

function SearchForm({ meta, onStarted, disabled }) {
  const [range, setRange] = useState(false)
  const [form, setForm] = useState({ date: '', start: '', end: '', mode: 'auto', topic: '', region: '', category: '' })
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setSending(true)
    setError(null)
    const body = {
      ...(range ? { start: form.start, end: form.end } : { date: form.date }),
      mode: form.mode,
      topic: form.topic.trim() || undefined,
      region: form.region.trim() || undefined,
      category: form.category || undefined,
    }
    try {
      onStarted(await api.startNewsSearch(body))
    } catch (err) {
      setError(err)
    } finally {
      setSending(false)
    }
  }

  return (
    <form className="panel news-form" onSubmit={submit}>
      {error && (
        <Notice tone="error" title="Ricerca non avviata">
          {errorText(error.code, error.message)}
          {error.retryAt ? ` Riprova non prima delle ${formatDateTime(error.retryAt)}.` : ''}
        </Notice>
      )}
      <fieldset className="fieldset">
        <legend>Quando</legend>
        <div className="segmented-inline">
          <label>
            <input type="radio" name="period" checked={!range} onChange={() => setRange(false)} /> Un giorno
          </label>
          <label>
            <input type="radio" name="period" checked={range} onChange={() => setRange(true)} /> Intervallo breve (max 7 giorni)
          </label>
        </div>
        {range ? (
          <div className="form__row">
            <div className="field">
              <label htmlFor="ns-start">Dal</label>
              <input id="ns-start" type="date" required min="1990-01-01" max={today()} value={form.start} onChange={set('start')} />
            </div>
            <div className="field">
              <label htmlFor="ns-end">Al</label>
              <input id="ns-end" type="date" required min={form.start || '1990-01-01'} max={today()} value={form.end} onChange={set('end')} />
            </div>
          </div>
        ) : (
          <div className="field">
            <label htmlFor="ns-date">Data</label>
            <input id="ns-date" type="date" required min="1990-01-01" max={today()} value={form.date} onChange={set('date')} />
          </div>
        )}
      </fieldset>
      <details className="news-form__advanced">
        <summary>Filtri facoltativi</summary>
        <div className="form__row">
          <div className="field field--grow">
            <label htmlFor="ns-topic">Argomento</label>
            <input id="ns-topic" maxLength={80} value={form.topic} onChange={set('topic')} placeholder="es. banche, petrolio" />
          </div>
          <div className="field">
            <label htmlFor="ns-region">Area geografica</label>
            <input id="ns-region" maxLength={80} value={form.region} onChange={set('region')} placeholder="es. Europa" />
          </div>
          <div className="field">
            <label htmlFor="ns-cat">Categoria</label>
            <select id="ns-cat" value={form.category} onChange={set('category')}>
              <option value="">Qualsiasi</option>
              {meta.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label htmlFor="ns-mode">Fonti</label>
          <select id="ns-mode" value={form.mode} onChange={set('mode')}>
            {MODES.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
          <p className="field__hint">
            Le fonti dell’epoca sono pubblicate entro due giorni dalla data cercata; le ricostruzioni successive possono
            contenere informazioni non disponibili all’epoca e sono segnalate come tali.
          </p>
        </div>
      </details>
      <button className="button button--large" type="submit" disabled={sending || disabled}>
        {sending ? 'Avvio…' : 'Cerca eventi'}
      </button>
      <p className="small muted">
        Una ricerca usa al massimo due richieste al servizio di ricerca e, se configurata, un’estrazione con IA; il costo
        massimo viene prenotato sul budget prima di ogni richiesta. Ripetere la stessa ricerca usa i risultati salvati.
      </p>
    </form>
  )
}

function Results({ search, onAnalyzeError }) {
  const byIdx = useMemo(() => Object.fromEntries(search.results.map((r) => [r.idx, r])), [search.results])
  const period =
    search.params.start === search.params.end
      ? formatDate(search.params.start)
      : `${formatDate(search.params.start)} – ${formatDate(search.params.end)}`
  const excluded = Object.entries(search.excluded || {}).filter(([, n]) => n > 0)

  if (search.status === 'failed') {
    return (
      <Notice tone="error" title="Ricerca non riuscita">
        {errorText(search.error_code, search.error_message)}
      </Notice>
    )
  }
  return (
    <section aria-labelledby="news-results-title" className="news-results">
      <h2 id="news-results-title">
        {search.events.length
          ? `${search.events.length} eventi trovati nelle fonti consultate · ${period}`
          : `Nessun evento trovato nelle fonti consultate · ${period}`}
      </h2>
      {search.status === 'empty' && (
        <p className="muted">
          La ricerca è riuscita ma non ha restituito fonti utilizzabili. Non significa che quel giorno non sia accaduto nulla:
          prova un argomento, un intervallo o il tipo di fonti diverso.
        </p>
      )}
      {(search.warnings || []).map((w) => (
        <Notice key={w.code + w.message} tone="warning">
          {w.message}
        </Notice>
      ))}
      {excluded.length > 0 && (
        <p className="small muted">
          Risultati esclusi dai controlli: {excluded.map(([code, n]) => `${n} ${EXCLUDED_TEXT[code] ?? code}`).join(', ')}.
        </p>
      )}
      {search.events.map((event) => (
        <EventCard key={event.idx} searchId={search.id} event={event} results={byIdx} onError={onAnalyzeError} />
      ))}
    </section>
  )
}

export default function NewsSearchPage({ meta }) {
  const auth = useAuth()
  const [params, setParams] = useSearchParams()
  const searchId = params.get('id') || ''
  const { data: search, error } = useSearch(searchId)
  const [analyzeError, setAnalyzeError] = useState(null)
  useEffect(() => setAnalyzeError(null), [searchId])
  const recent = useApi((opts) => (auth.authenticated ? api.recentNewsSearches(opts) : Promise.resolve(null)), [auth.authenticated, searchId])

  if (auth.status === 'loading') return <div className="page"><Skeleton /></div>
  if (!auth.authenticated) {
    return (
      <div className="page narrow">
        <Notice tone="info" title="Accesso richiesto">
          La ricerca delle notizie usa servizi a pagamento ed è riservata all’operatore.{' '}
          <Link to="/accesso?next=/ricerca">Accedi</Link>.
        </Notice>
      </div>
    )
  }
  const pending = search && PENDING.includes(search.status)
  // Dall'avvio alla prima risposta dello stato il modulo resta bloccato: niente doppio invio.
  const starting = Boolean(searchId) && !search && !error
  const statusText = pending
    ? `${STAGE_LABEL[search.stage] ?? 'In corso'}… La pagina si aggiorna da sola.`
    : search && search.status !== 'failed'
      ? `Ricerca completata: ${search.events.length} eventi trovati nelle fonti consultate.`
      : search?.status === 'failed'
        ? 'Ricerca non riuscita.'
        : ''

  return (
    <div className="page news-page">
      <header className="page-header">
        <h1>Ricerca notizie per data</h1>
        <p className="page-header__lead">
          Scegli un giorno: LiA cerca le notizie, le raggruppa in eventi con le fonti e le date di pubblicazione, e ti lascia
          scegliere quale analizzare sui mercati. Nessuna ricerca è esaustiva: sono gli eventi trovati nelle fonti consultate.
        </p>
      </header>

      {!meta.features.news_search ? (
        <Notice tone="warning" title="Ricerca automatica non configurata">
          Su questo server manca la chiave del servizio di ricerca. Puoi comunque{' '}
          <Link to="/new">inserire un evento manualmente</Link>.
        </Notice>
      ) : (
        <div className="news-layout">
          <div>
            <SearchForm meta={meta} disabled={pending || starting} onStarted={(res) => setParams({ id: res.search_id })} />
            <BudgetPanel refreshKey={search?.status} />
            <p className="small">
              Percorso secondario: <Link to="/new">inserimento manuale di un evento</Link>.
            </p>
          </div>
          <div>
            {error && (
              <Notice tone="error" title="Stato della ricerca non disponibile">
                {error.message} La ricerca prosegue sul server.{' '}
                <button type="button" className="button button--ghost" onClick={() => window.location.reload()}>
                  Riprova
                </button>
              </Notice>
            )}
            <p role="status" aria-live="polite" className={pending ? 'job-status' : 'sr-only'}>
              {pending && <span className="spinner" aria-hidden="true" />} {statusText}
            </p>
            {analyzeError && (
              <Notice tone="error" title="Analisi non avviata">
                {errorText(analyzeError.code, analyzeError.message)}
              </Notice>
            )}
            {search && !pending && <Results search={search} onAnalyzeError={setAnalyzeError} />}
            {!searchId && recent.data?.items?.length > 0 && (
              <section aria-labelledby="recent-title">
                <h2 id="recent-title">Ricerche recenti</h2>
                <ul className="news-recent">
                  {recent.data.items.map((r) => (
                    <li key={r.id}>
                      <Link to={`/ricerca?id=${encodeURIComponent(r.id)}`}>
                        {r.params.start === r.params.end ? formatDate(r.params.start) : `${formatDate(r.params.start)} – ${formatDate(r.params.end)}`}
                      </Link>{' '}
                      <span className="small muted">
                        {r.params.topic ? `«${r.params.topic}» · ` : ''}
                        {r.status === 'failed' ? 'non riuscita' : `${r.event_count} eventi`} · {formatDateTime(r.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
