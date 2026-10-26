// Pannelli del workspace senza grafici: intestazione, cifre chiave, indicatori, qualità, fonti.
import { Link } from 'react-router-dom'
import { InfoTip, Notice, Stat } from '../../components/ui.jsx'
import {
  formatDate,
  formatDateTime,
  formatEventTime,
  formatNumber,
  formatPct,
  formatValue,
  plural,
  PRECISION_LABEL,
} from '../../lib/format.js'

export function EventHeader({ event, analysis }) {
  const time = formatEventTime(event.occurred_at)
  return (
    <header className="event-header">
      <nav aria-label="Percorso" className="breadcrumb">
        <Link to="/archive">Archivio</Link> <span aria-hidden="true">/</span> <span>{event.category_label}</span>
      </nav>
      <h1 className="event-header__title">{event.title}</h1>
      <p className="event-header__meta">
        <time dateTime={event.occurred_at || event.occurred_on}>
          {formatDate(event.occurred_on)}
          {time && ` · ${time}`}
        </time>
        <span className={`precision precision--${event.time_precision}`}>{PRECISION_LABEL[event.time_precision]}</span>
        <span>{plural(event.sources.length, 'fonte', 'fonti')}</span>
        {analysis?.computed_at && <span className="muted">Calcolata il {formatDateTime(analysis.computed_at)}</span>}
      </p>
      <p className="event-header__description">{event.description}</p>
    </header>
  )
}

export function KeyFigures({ data, view, horizon, market }) {
  const asOf = view === 'as_of'
  const outcome = data.outcomes?.returns.find((r) => String(r.h) === horizon)
  const first = data.outcomes?.returns.find((r) => r.h === 1)
  const stats = data.stats[horizon]
  const tone = (v) => (v === null || v === undefined ? undefined : v >= 0 ? 'up' : 'down')
  return (
    <div className="stat-grid stat-grid--key" aria-live="polite">
      <Stat
        label="Seduta base"
        term="base"
        value={formatDate(data.base.date, 'medium')}
        detail={`Chiusura ${formatNumber(data.base.close)} ${market.currency}`}
      />
      <Stat
        label="Prima seduta dopo l'evento"
        value={asOf ? 'Nascosta' : formatPct(first?.value)}
        tone={asOf ? undefined : tone(first?.value)}
        detail={asOf ? 'Vista al cutoff' : first?.end_date ? formatDate(first.end_date, 'medium') : 'Non ancora disponibile'}
      />
      <Stat
        label={`Esito a ${plural(Number(horizon), 'seduta', 'sedute')}`}
        term="horizon"
        value={asOf ? 'Nascosto' : formatPct(outcome?.value)}
        tone={asOf ? undefined : tone(outcome?.value)}
        detail={asOf ? 'Vista al cutoff' : outcome?.end_date ? `al ${formatDate(outcome.end_date, 'medium')}` : 'Non ancora osservabile'}
      />
      <Stat
        label="Precedenti nel campione"
        term="precedents"
        value={stats?.n ?? 0}
        detail={stats?.median !== null && stats?.median !== undefined ? `Mediana ${formatPct(stats.median)}` : 'Mediana non calcolabile'}
      />
    </div>
  )
}

export function IndicatorsPanel({ indicators }) {
  return (
    <section className="panel" aria-labelledby="indicators-title">
      <h2 id="indicators-title" className="panel__title">
        Indicatori alla seduta base
      </h2>
      <p className="panel__subtitle">Calcolati solo con sedute fino a s = 0: informazione disponibile al cutoff.</p>
      <dl className="indicator-list">
        {indicators.map((ind) => (
          <div key={ind.id} className="indicator-list__row">
            <dt>
              {ind.label}
              <InfoTip term={ind.id} anchor="indicatori" />
            </dt>
            <dd className={ind.value === null ? 'muted' : undefined} title={ind.reason || undefined}>
              {ind.value === null ? `— (${ind.reason})` : formatValue(ind.value, ind.unit)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

const SEVERITY_TONE = { error: 'error', warning: 'warning', info: 'info' }

export function Warnings({ warnings }) {
  if (!warnings?.length) return null
  return (
    <ul className="warning-list" aria-label="Avvisi sui dati">
      {warnings.map((w) => (
        <li key={w.code} className={`warning-list__item tone-bg-${SEVERITY_TONE[w.severity] || 'info'}`}>
          {w.message}
        </li>
      ))}
    </ul>
  )
}

export function QualityPanel({ data, event, priceSource, method, market, marketError }) {
  const q = data.quality
  return (
    <div className="quality">
      {marketError && (
        <Notice tone="warning" title="Aggiornamento prezzi non riuscito">
          {marketError.message} I dati mostrati sono quelli già in archivio.
        </Notice>
      )}
      <div className="stat-grid">
        <Stat label="Fonti dell'evento" value={event.sources.length} detail={sourceKinds(event.sources)} />
        <Stat
          label="Copertura prezzi"
          value={`${formatDate(q.coverage.first_date, 'medium')} – ${formatDate(q.coverage.last_date, 'medium')}`}
          detail={`${formatNumber(q.sessions_available, 0)} sedute ${market.name}`}
        />
        <Stat
          label="Casi utilizzabili"
          value={Object.entries(q.usable_precedents)
            .map(([h, n]) => `${n} (${h}s)`)
            .join(' · ')}
          detail="Per orizzonte in sedute"
        />
        <Stat
          label="Dati mancanti nella finestra"
          value={q.missing_in_window}
          detail={`${q.window.sessions} sedute dal ${formatDate(q.window.start, 'medium')} al ${formatDate(q.window.end, 'medium')}`}
        />
      </div>

      <section className="panel" aria-labelledby="warnings-title">
        <h2 id="warnings-title" className="panel__title">
          Avvisi e convenzioni
        </h2>
        <Warnings warnings={data.warnings} />
        <p className="small">{data.base.rule_description}</p>
      </section>

      <section className="panel" aria-labelledby="sources-title">
        <h2 id="sources-title" className="panel__title">
          Fonti dell'evento
        </h2>
        <ul className="source-list">
          {event.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noreferrer noopener">
                {s.title}
              </a>
              <span className="muted">
                {' '}
                — {s.publisher} · {KIND_LABEL[s.kind] || s.kind}
                {s.accessed_on && ` · consultata il ${formatDate(s.accessed_on, 'medium')}`}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel" aria-labelledby="provenance-title">
        <h2 id="provenance-title" className="panel__title">
          Provenienza dei dati
        </h2>
        <dl className="facts">
          <div>
            <dt>Prezzi</dt>
            <dd>
              {priceSource?.provider || '—'}, aggiornati il {formatDateTime(priceSource?.fetched_at)}
            </dd>
          </div>
          <div>
            <dt>Mercato</dt>
            <dd>
              {market.name} ({market.symbol}), {market.exchange}. Chiusura della seduta base:{' '}
              {data.base.close_at.slice(11, 16)} ora di {market.timezone} (UTC{data.base.close_at.slice(19)})
            </dd>
          </div>
          <div>
            <dt>Versione del metodo</dt>
            <dd>
              {method} · <Link to="/methodology">metodologia</Link>
            </dd>
          </div>
        </dl>
      </section>
    </div>
  )
}

const KIND_LABEL = { reference: 'opera di consultazione', official: 'fonte ufficiale', news: 'notizia' }

function sourceKinds(sources) {
  const counts = {}
  for (const s of sources) counts[s.kind] = (counts[s.kind] || 0) + 1
  return Object.entries(counts)
    .map(([k, n]) => `${n} ${KIND_LABEL[k] || k}`)
    .join(', ')
}

export function OutcomeMin({ data }) {
  if (!data.outcomes) return null
  return (
    <section className="panel" aria-labelledby="after-title">
      <h2 id="after-title" className="panel__title">
        Dopo l'evento
      </h2>
      <p className="panel__subtitle">Esiti: non erano disponibili al cutoff.</p>
      <dl className="indicator-list">
        {data.outcomes.returns.map((r) => (
          <div key={r.h} className="indicator-list__row">
            <dt>Rendimento a {r.h} {r.h === 1 ? 'seduta' : 'sedute'}</dt>
            <dd className={r.value === null ? 'muted' : r.value >= 0 ? 'tone-up' : 'tone-down'}>{formatPct(r.value)}</dd>
          </div>
        ))}
        <div className="indicator-list__row">
          <dt>
            Minimo nelle 20 sedute
            <InfoTip term="min_after" anchor="indicatori" />
          </dt>
          <dd>{formatPct(data.outcomes.min_after.value)}</dd>
        </div>
      </dl>
    </section>
  )
}
