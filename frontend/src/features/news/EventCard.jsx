import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Notice } from '../../components/ui.jsx'
import { api } from '../../lib/api.js'
import { formatDate } from '../../lib/format.js'
import { DATE_BASIS_TEXT, safeHref } from './newsText.js'

function SourceItem({ result }) {
  const href = safeHref(result.url)
  return (
    <li className="news-source">
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer nofollow">
          {result.title}
        </a>
      ) : (
        <span>{result.title}</span>
      )}
      <span className="news-source__meta">
        {result.publisher} ·{' '}
        {result.published_on ? `pubblicato il ${formatDate(result.published_on, 'medium')}` : 'data di pubblicazione non dichiarata'}
        {result.kind === 'retrospective' ? ' · ricostruzione successiva' : ''}
      </span>
      {result.snippet && <span className="news-source__snippet">{result.snippet}</span>}
    </li>
  )
}

export default function EventCard({ searchId, event, results, onError }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const sources = event.result_idx.map((i) => results[i]).filter(Boolean)
  const titleId = `news-event-${event.idx}`

  const analyze = async () => {
    setBusy(true)
    onError(null)
    try {
      const res = await api.analyzeNewsEvent(searchId, event.idx)
      navigate(`/analysis/${res.analysis_id}`)
    } catch (err) {
      onError(err)
      setBusy(false)
    }
  }

  const editFirst = () =>
    navigate('/new', {
      state: {
        prefill: {
          title: event.title,
          description: event.description,
          category: event.category,
          tags: event.tags,
          date: event.event_date,
          sources: sources.slice(0, 5).map((s) => ({ url: s.url, publisher: s.publisher, title: s.title, kind: 'news' })),
        },
      },
    })

  return (
    <article className="panel news-event" aria-labelledby={titleId}>
      <header className="news-event__header">
        <p className="eyebrow">
          {formatDate(event.event_date)} · data: {DATE_BASIS_TEXT[event.date_basis] ?? event.date_basis} · {event.category_label}
        </p>
        <h3 id={titleId} className="news-event__title">
          {event.title}
        </h3>
        <p className="news-event__badges">
          <span className={`badge ${event.evidence === 'contemporary' ? 'badge--succeeded' : 'badge--queued'}`}>
            {event.evidence === 'contemporary' ? 'Fonti dell’epoca' : 'Solo fonti successive'}
          </span>
          <span className="badge">
            {event.independent_sources} {event.independent_sources === 1 ? 'fonte indipendente' : 'fonti indipendenti'}
          </span>
          {event.extraction === 'model' && <span className="badge">Testo organizzato da IA</span>}
        </p>
      </header>
      <p>{event.description}</p>
      {event.tags.length > 0 && <p className="small muted">Etichette: {event.tags.join(', ')}</p>}
      {event.flag_messages.length > 0 && (
        <Notice tone="warning" title="Da tenere presente">
          <ul className="news-event__flags">
            {event.flag_messages.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </Notice>
      )}
      <details className="news-event__sources">
        <summary>Fonti ({sources.length})</summary>
        <ul>
          {sources.map((s) => (
            <SourceItem key={s.idx} result={s} />
          ))}
        </ul>
      </details>
      <div className="news-event__actions">
        {event.analysis_id ? (
          <button type="button" className="button" onClick={() => navigate(`/analysis/${event.analysis_id}`)}>
            Apri l’analisi
          </button>
        ) : (
          <button type="button" className="button" onClick={analyze} disabled={busy}>
            {busy ? 'Avvio…' : 'Analizza questo evento'}
          </button>
        )}
        <button type="button" className="button button--ghost" onClick={editFirst}>
          Correggi prima di analizzare
        </button>
      </div>
    </article>
  )
}
