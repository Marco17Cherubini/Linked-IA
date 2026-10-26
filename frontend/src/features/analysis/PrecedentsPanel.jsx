import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DataTable, EmptyState, InfoTip } from '../../components/ui.jsx'
import { formatDate, formatNumber, formatPct, PRECISION_LABEL } from '../../lib/format.js'
import { ANIMATION, AXIS_PROPS, colorFor, GRID_PROPS } from './chartTheme.js'

function ComparisonTooltip({ active, payload, label, names }) {
  if (!active || !payload?.length) return null
  const rows = [...payload].filter((p) => p.value !== undefined && p.value !== null).sort((a, b) => b.value - a.value)
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">Seduta {label > 0 ? `+${label}` : label}</div>
      <ul className="chart-tooltip__list">
        {rows.map((p) => (
          <li key={p.dataKey}>
            <span className="swatch" style={{ background: p.stroke }} aria-hidden="true" />
            {names[p.dataKey]}: <strong>{formatNumber(p.value, 1)}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PrecedentDetail({ item, horizon, onClose }) {
  return (
    <aside className="precedent-detail" aria-labelledby="precedent-detail-title">
      <div className="precedent-detail__head">
        <h3 id="precedent-detail-title">{item.title}</h3>
        <button type="button" className="button button--ghost" onClick={onClose}>
          Chiudi
        </button>
      </div>
      <dl className="facts">
        <div>
          <dt>Data dell'evento</dt>
          <dd>
            {formatDate(item.occurred_on)} · {PRECISION_LABEL[item.time_precision]}
          </dd>
        </div>
        <div>
          <dt>Seduta base del precedente</dt>
          <dd>{formatDate(item.base_date)}</dd>
        </div>
        <div>
          <dt>Perché è stato selezionato</dt>
          <dd>
            {item.same_category ? 'Stessa categoria' : 'Categoria diversa'}
            {item.shared_tags.length > 0 && `; etichette in comune: ${item.shared_tags.join(', ')}`}. Punteggio{' '}
            {formatNumber(item.score, 2)}.
          </dd>
        </div>
        <div>
          <dt>Rendimenti dalla base</dt>
          <dd>
            {Object.entries(item.returns).map(([h, v]) => (
              <span key={h} className={`chip${h === horizon ? ' chip--active' : ''}`}>
                {h} sed.: {formatPct(v)}
              </span>
            ))}
          </dd>
        </div>
        <div>
          <dt>Minimo nelle 20 sedute successive</dt>
          <dd>{formatPct(item.min_after)}</dd>
        </div>
      </dl>
      <h4>Fonti</h4>
      <ul className="source-list">
        {item.sources.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noreferrer noopener">
              {s.title}
            </a>{' '}
            <span className="muted">— {s.publisher}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}

export default function PrecedentsPanel({ data, view, horizon, hidden, selected, onToggle, onSelect, eventTitle }) {
  const [hover, setHover] = useState(null)
  const items = data.precedents.items
  const asOf = view === 'as_of'

  const rows = useMemo(() => {
    const byS = new Map()
    const put = (s, key, value) => {
      if (!byS.has(s)) byS.set(s, { s })
      byS.get(s)[key] = value
    }
    for (const p of data.target_path) if (!asOf || p.s <= 0) put(p.s, 'target', p.index100)
    for (const item of items) for (const p of item.path) put(p.s, item.event_id, p.index100)
    return [...byS.values()].sort((a, b) => a.s - b.s)
  }, [data, items, asOf])

  if (!items.length) {
    return (
      <EmptyState title="Nessun precedente utilizzabile">
        Nessun evento del catalogo soddisfa i criteri di pertinenza con un esito già osservabile alla seduta base (
        {formatDate(data.base.date)}). Esclusi: {data.precedents.excluded.not_relevant} non pertinenti,{' '}
        {data.precedents.excluded.outcome_after_cutoff} con esito successivo al cutoff.
      </EmptyState>
    )
  }

  const names = { target: `${eventTitle} (evento analizzato)` }
  items.forEach((it) => (names[it.event_id] = it.title))
  const visible = items.filter((it) => !hidden.includes(it.event_id))
  const emphasis = hover || selected
  const selectedItem = items.find((it) => it.event_id === selected)

  return (
    <div className="precedents">
      <figure className="chart-figure">
        <div className="chart-figure__header">
          <figcaption className="chart-title">
            Confronto con i precedenti
            <InfoTip term="precedents" />
          </figcaption>
        </div>
        <p className="chart-note">
          Ogni serie è in base 100 alla propria seduta base; l'asse orizzontale conta le sedute rispetto all'evento.
          {asOf && ' Nella vista al cutoff l’evento analizzato è mostrato solo fino alla seduta base.'}
        </p>
        <div className="chart-box" style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 16, right: 16, bottom: 8, left: 8 }} accessibilityLayer>
              <CartesianGrid {...GRID_PROPS} />
              <XAxis dataKey="s" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} tickFormatter={(s) => (s > 0 ? `+${s}` : s)} {...AXIS_PROPS} />
              <YAxis domain={['auto', 'auto']} width={48} tickFormatter={(v) => formatNumber(v, 0)} {...AXIS_PROPS} />
              <ReferenceLine y={100} stroke="var(--border-strong)" strokeDasharray="2 4" />
              <ReferenceLine x={0} stroke="var(--text-3)" />
              <ReferenceLine x={Number(horizon)} stroke="var(--accent)" strokeDasharray="3 3" label={{ value: `Orizzonte ${horizon}`, position: Number(horizon) >= 20 ? 'insideTopRight' : 'top', fill: 'var(--accent)', fontSize: 12 }} />
              <Tooltip content={<ComparisonTooltip names={names} />} />
              {items.map((it, i) =>
                hidden.includes(it.event_id) ? null : (
                  <Line
                    key={it.event_id}
                    dataKey={it.event_id}
                    name={it.title}
                    stroke={colorFor(i)}
                    strokeWidth={emphasis === it.event_id ? 3 : 1.75}
                    strokeOpacity={emphasis && emphasis !== it.event_id ? 0.3 : 1}
                    dot={false}
                    activeDot={{ r: 3 }}
                    connectNulls
                    onClick={() => onSelect(it.event_id)}
                    style={{ cursor: 'pointer' }}
                    {...ANIMATION}
                  />
                ),
              )}
              <Line dataKey="target" name={names.target} stroke="var(--text)" strokeWidth={3} dot={false} connectNulls {...ANIMATION} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="chart-summary">
          {visible.length} precedenti visibili su {items.length}. All'orizzonte di {horizon} sedute:{' '}
          {visible.map((it) => `${it.title} ${formatPct(it.returns[horizon])}`).join('; ')}.
        </p>
      </figure>

      <div className="legend-list" role="group" aria-label="Precedenti: mostra, nascondi e apri i dettagli">
        <div className="legend-list__item legend-list__item--target">
          <span className="swatch swatch--line" style={{ background: 'var(--text)' }} aria-hidden="true" />
          <span className="legend-list__title">{names.target}</span>
        </div>
        {items.map((it, i) => {
          const isHidden = hidden.includes(it.event_id)
          return (
            <div
              key={it.event_id}
              className={`legend-list__item${selected === it.event_id ? ' is-selected' : ''}${isHidden ? ' is-hidden' : ''}`}
              onMouseEnter={() => setHover(it.event_id)}
              onMouseLeave={() => setHover(null)}
            >
              <label className="legend-list__toggle">
                <input type="checkbox" checked={!isHidden} onChange={() => onToggle(it.event_id)} aria-label={`Mostra ${it.title} nel grafico`} />
                <span className="swatch swatch--line" style={{ background: colorFor(i) }} aria-hidden="true" />
              </label>
              <button type="button" className="legend-list__title link-button" onClick={() => onSelect(selected === it.event_id ? '' : it.event_id)} aria-expanded={selected === it.event_id}>
                {it.title}
              </button>
              <span className="legend-list__meta">{formatDate(it.occurred_on, 'medium')}</span>
              <span className={`legend-list__value tone-${it.returns[horizon] >= 0 ? 'up' : 'down'}`}>{formatPct(it.returns[horizon])}</span>
            </div>
          )
        })}
      </div>

      {selectedItem && <PrecedentDetail item={selectedItem} horizon={horizon} onClose={() => onSelect('')} />}

      <p className="muted small">
        {data.precedents.criteria.description} Candidati esclusi: {data.precedents.excluded.not_relevant} non pertinenti,{' '}
        {data.precedents.excluded.outcome_after_cutoff} con esito non ancora osservabile al {formatDate(data.precedents.cutoff_date)}
        {data.precedents.excluded.no_data ? `, ${data.precedents.excluded.no_data} senza dati` : ''}.
      </p>

      <DataTable
        caption="Precedenti selezionati e rendimenti dalla rispettiva seduta base"
        columns={[
          { key: 'title', label: 'Precedente' },
          { key: 'date', label: 'Data' },
          { key: 'score', label: 'Punteggio', numeric: true },
          { key: 'r1', label: '1 seduta', numeric: true },
          { key: 'r5', label: '5 sedute', numeric: true },
          { key: 'r20', label: '20 sedute', numeric: true },
        ]}
        rows={items.map((it) => ({
          key: it.event_id,
          title: it.title,
          date: formatDate(it.occurred_on, 'medium'),
          score: formatNumber(it.score, 2),
          r1: formatPct(it.returns['1']),
          r5: formatPct(it.returns['5']),
          r20: formatPct(it.returns['20']),
        }))}
      />
    </div>
  )
}
