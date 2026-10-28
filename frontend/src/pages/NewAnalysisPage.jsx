import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import BudgetPanel from '../components/BudgetPanel.jsx'
import { Notice } from '../components/ui.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { formatDateTime } from '../lib/format.js'

const OFFSETS = ['-08:00', '-07:00', '-06:00', '-05:00', '-04:00', '+00:00', '+01:00', '+02:00', '+03:00', '+04:00', '+05:30', '+08:00', '+09:00']

export function slugify(title, date) {
  const base = title
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
    .replace(/-+$/, '')
  const year = date ? date.slice(0, 4) : ''
  return [base, year].filter(Boolean).join('-')
}

export function buildPayload(form) {
  const precision = form.time ? form.precision : 'unknown'
  return {
    id: slugify(form.title, form.date),
    title: form.title.trim(),
    description: form.description.trim(),
    category: form.category,
    tags: form.tags
      .split(',')
      .map((t) => t.trim().toLowerCase().replace(/\s+/g, '-'))
      .filter(Boolean),
    occurred_on: form.date,
    occurred_at: form.time ? `${form.date}T${form.time}:00${form.offset}` : null,
    time_precision: precision,
    sources: form.sources
      .filter((s) => s.url.trim())
      .map((s) => ({ url: s.url.trim(), publisher: s.publisher.trim() || undefined, title: s.title.trim() || undefined, kind: s.kind })),
  }
}

const EMPTY_SOURCE = { url: '', publisher: '', title: '', kind: 'news' }

export default function NewAnalysisPage({ meta }) {
  const navigate = useNavigate()
  // Precompilazione facoltativa da una scheda della ricerca automatica (correzione manuale).
  const prefill = useLocation().state?.prefill
  const auth = useAuth()
  const [form, setForm] = useState(() => ({
    title: prefill?.title ?? '',
    description: prefill?.description ?? '',
    category: meta.categories.some((c) => c.id === prefill?.category) ? prefill.category : meta.categories[0].id,
    tags: prefill?.tags?.join(', ') ?? '',
    date: prefill?.date ?? '',
    time: '',
    offset: '+00:00',
    precision: 'approximate',
    sources: prefill?.sources?.length ? prefill.sources.slice(0, 5).map((s) => ({ ...EMPTY_SOURCE, ...s })) : [{ ...EMPTY_SOURCE }],
  }))
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)

  if (!meta.features.create) {
    return (
      <div className="page">
        <Notice tone="info" title="Creazione non attiva">
          Questo server consente solo la consultazione delle analisi esistenti.
        </Notice>
      </div>
    )
  }

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const setSource = (i, key) => (e) =>
    setForm((f) => ({ ...f, sources: f.sources.map((s, j) => (j === i ? { ...s, [key]: e.target.value } : s)) }))

  const submit = async (e) => {
    e.preventDefault()
    setSending(true)
    setError(null)
    try {
      const res = await api.createEvent(buildPayload(form))
      navigate(`/analysis/${res.analysis_id}`)
    } catch (err) {
      setError(err)
      if (err.status === 401) auth.expired()
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="page narrow">
      <header className="page-header">
        <h1>Inserimento manuale</h1>
        <p className="page-header__lead">
          Percorso secondario per casi che la <Link to="/ricerca">ricerca automatica per data</Link> non trova o descrive in
          modo ambiguo. Il calcolo scarica prezzi gratuiti e non usa servizi IA: la sintesi IA si richiede a parte.
        </p>
        {prefill && (
          <Notice tone="info" title="Dati precompilati dalla ricerca">
            Controlla e correggi i campi: l'analisi partirà con i valori che confermi.
          </Notice>
        )}
      </header>

      {auth.status === 'loading' ? null : !auth.authenticated ? (
        <Notice tone="info" title="Accesso richiesto">
          {error?.status === 401 ? 'La sessione è scaduta. ' : ''}
          Per creare un'analisi <Link to="/accesso?next=/new">accedi come operatore</Link>.
        </Notice>
      ) : (
        <form className="form" onSubmit={submit} noValidate={false}>
          <BudgetPanel />
          {error && (
            <Notice tone="error" title="Analisi non creata">
              {error.message}
              {error.retryAt ? ` Riprova non prima delle ${formatDateTime(error.retryAt)}.` : ''}
            </Notice>
          )}
          <div className="field">
            <label htmlFor="n-title">Titolo dell'evento</label>
            <input id="n-title" required maxLength={160} value={form.title} onChange={set('title')} />
            <p className="field__hint">Identificativo: {slugify(form.title, form.date) || '—'}</p>
          </div>
          <div className="field">
            <label htmlFor="n-desc">Descrizione</label>
            <textarea id="n-desc" required maxLength={1200} rows={3} value={form.description} onChange={set('description')} />
          </div>
          <div className="form__row">
            <div className="field">
              <label htmlFor="n-cat">Categoria</label>
              <select id="n-cat" value={form.category} onChange={set('category')}>
                {meta.categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field field--grow">
              <label htmlFor="n-tags">Etichette</label>
              <input id="n-tags" value={form.tags} onChange={set('tags')} placeholder="war, europe, energy" aria-describedby="n-tags-hint" />
              <p className="field__hint" id="n-tags-hint">
                Separate da virgole. Usate per scegliere i precedenti (servono almeno 2 etichette comuni se la categoria è diversa).
              </p>
            </div>
          </div>
          <fieldset className="fieldset">
            <legend>Quando</legend>
            <div className="form__row">
              <div className="field">
                <label htmlFor="n-date">Data (locale del luogo dell'evento)</label>
                <input id="n-date" type="date" required value={form.date} onChange={set('date')} max={new Date().toISOString().slice(0, 10)} />
              </div>
              <div className="field">
                <label htmlFor="n-time">Orario (facoltativo)</label>
                <input id="n-time" type="time" value={form.time} onChange={set('time')} />
              </div>
              <div className="field">
                <label htmlFor="n-offset">Fuso (UTC)</label>
                <select id="n-offset" value={form.offset} onChange={set('offset')} disabled={!form.time}>
                  {OFFSETS.map((o) => (
                    <option key={o} value={o}>
                      UTC{o}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="n-prec">Precisione</label>
                <select id="n-prec" value={form.precision} onChange={set('precision')} disabled={!form.time}>
                  <option value="exact">Documentato</option>
                  <option value="approximate">Approssimato</option>
                </select>
              </div>
            </div>
            <p className="field__hint">
              Senza orario si usa la convenzione prudente: seduta base = ultima seduta del giorno precedente.
            </p>
          </fieldset>
          <fieldset className="fieldset">
            <legend>Fonti</legend>
            {form.sources.map((s, i) => (
              <div className="form__row source-row" key={i}>
                <div className="field field--grow">
                  <label htmlFor={`s-url-${i}`}>URL fonte {i + 1}</label>
                  <input id={`s-url-${i}`} type="url" required={i === 0} value={s.url} onChange={setSource(i, 'url')} placeholder="https://" />
                </div>
                <div className="field">
                  <label htmlFor={`s-pub-${i}`}>Editore</label>
                  <input id={`s-pub-${i}`} value={s.publisher} onChange={setSource(i, 'publisher')} />
                </div>
                <div className="field">
                  <label htmlFor={`s-kind-${i}`}>Tipo</label>
                  <select id={`s-kind-${i}`} value={s.kind} onChange={setSource(i, 'kind')}>
                    <option value="news">Notizia</option>
                    <option value="official">Fonte ufficiale</option>
                    <option value="reference">Consultazione</option>
                  </select>
                </div>
              </div>
            ))}
            {form.sources.length < 5 && (
              <button type="button" className="button button--ghost" onClick={() => setForm((f) => ({ ...f, sources: [...f.sources, { ...EMPTY_SOURCE }] }))}>
                Aggiungi una fonte
              </button>
            )}
          </fieldset>
          <div className="form__actions">
            <button className="button button--large" type="submit" disabled={sending}>
              {sending ? 'Invio…' : 'Crea e calcola'}
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => auth.logout()}
            >
              Esci
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
