import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { DataTable, EmptyState, InfoTip, Notice, Stat } from '../../components/ui.jsx'
import { formatDate, formatNumber, formatPct, plural } from '../../lib/format.js'
import { ANIMATION, AXIS_PROPS, GRID_PROPS } from './chartTheme.js'

// Sotto questa numerosità si mostrano i singoli casi: un istogramma sarebbe fuorviante.
export const HISTOGRAM_MIN_N = 12

export function histogramBins(values, binCount = 8) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const width = (max - min) / binCount || 1
  const bins = Array.from({ length: binCount }, (_, i) => ({
    from: min + i * width,
    to: min + (i + 1) * width,
    count: 0,
  }))
  for (const v of values) bins[Math.min(binCount - 1, Math.floor((v - min) / width))].count++
  return bins.map((b) => ({ ...b, label: `${formatNumber(b.from, 1)}…${formatNumber(b.to, 1)}`, mid: (b.from + b.to) / 2 }))
}

function PointTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">{p.title}</div>
      {p.date && <div>{formatDate(p.date, 'medium')}</div>}
      <div className="chart-tooltip__value">{formatPct(p.value)}</div>
    </div>
  )
}

function DotPlot({ points, stats, target }) {
  const rows = [...points].sort((a, b) => a.value - b.value)
  const all = target ? [...rows, target] : rows
  const values = all.map((p) => p.value)
  const { domain, ticks } = niceScale(Math.min(0, ...values), Math.max(0, ...values))
  const height = 56 + all.length * 38
  const labelWidth = typeof window !== 'undefined' && window.innerWidth < 640 ? 110 : 220
  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 24, bottom: 8, left: 8 }} accessibilityLayer>
          <CartesianGrid {...GRID_PROPS} horizontal={false} vertical />
          <XAxis type="number" dataKey="value" domain={domain} ticks={ticks} tickFormatter={(v) => formatPct(v, 0)} {...AXIS_PROPS} />
          <ZAxis range={[90, 90]} />
          <YAxis type="category" dataKey="label" width={labelWidth} interval={0} {...AXIS_PROPS} tick={{ fill: 'var(--text-2)', fontSize: 12 }} allowDuplicatedCategory={false} />
          <ReferenceLine x={0} stroke="var(--text-3)" />
          {stats.median !== null && (
            <ReferenceLine x={stats.median} stroke="var(--accent)" strokeDasharray="4 3" label={{ value: 'Mediana', position: 'top', fill: 'var(--accent)', fontSize: 12 }} />
          )}
          <Tooltip content={<PointTooltip />} cursor={false} />
          <Scatter data={rows} {...ANIMATION}>
            {rows.map((p) => (
              <Cell key={p.id} fill={p.value >= 0 ? 'var(--up)' : 'var(--down)'} />
            ))}
          </Scatter>
          {target && <Scatter data={[target]} fill="var(--text)" shape="diamond" {...ANIMATION} />}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

function Histogram({ values }) {
  const bins = histogramBins(values)
  return (
    <div className="chart-box" style={{ height: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={bins} margin={{ top: 16, right: 16, bottom: 8, left: 8 }} accessibilityLayer>
          <CartesianGrid {...GRID_PROPS} />
          <XAxis dataKey="label" {...AXIS_PROPS} />
          <YAxis allowDecimals={false} width={32} {...AXIS_PROPS} />
          <Tooltip formatter={(v) => [v, 'Casi']} />
          <Bar dataKey="count" {...ANIMATION}>
            {bins.map((b) => (
              <Cell key={b.label} fill={b.mid >= 0 ? 'var(--up)' : 'var(--down)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function OutcomesPanel({ data, view, horizon, eventTitle }) {
  const stats = data.stats[horizon]
  const items = data.precedents.items
  const outcome = view === 'retrospective' ? data.outcomes?.returns.find((r) => String(r.h) === horizon) : null

  if (!stats || stats.n === 0) {
    return (
      <EmptyState title="Nessun esito storico disponibile">
        Non ci sono precedenti con un esito a {horizon} sedute osservabile alla seduta base.
      </EmptyState>
    )
  }

  const points = items
    .filter((it) => it.returns[horizon] !== null && it.returns[horizon] !== undefined)
    .map((it) => ({ id: it.event_id, title: it.title, label: shortLabel(it), date: it.occurred_on, value: it.returns[horizon] }))
  const target =
    outcome && outcome.value !== null
      ? { id: 'target', title: `${eventTitle} (evento analizzato, non nel campione)`, label: 'Evento analizzato', value: outcome.value }
      : null

  return (
    <div className="outcomes">
      <div className="stat-grid">
        <Stat label="Casi nel campione" value={stats.n} detail={stats.small_sample ? 'Campione piccolo' : null} />
        <Stat label="Mediana" term="median" value={formatPct(stats.median)} detail={stats.median === null ? 'Servono almeno 3 casi' : `${horizon} sedute`} />
        <Stat
          label="Intervallo interquartile"
          value={stats.q1 === null ? '—' : `${formatPct(stats.q1)} … ${formatPct(stats.q3)}`}
          detail={stats.q1 === null ? 'Servono almeno 5 casi' : 'Metà centrale dei casi'}
        />
        <Stat
          label="Rialzi osservati"
          term="observed_frequency"
          value={`${stats.up_count} su ${stats.n}`}
          detail="Frequenza osservata, non probabilità"
        />
      </div>

      <figure className="chart-figure">
        <div className="chart-figure__header">
          <figcaption className="chart-title">
            Esiti del campione storico a {plural(Number(horizon), 'seduta', 'sedute')}
            <InfoTip term="horizon" />
          </figcaption>
        </div>
        <p className="chart-note">
          {stats.n < HISTOGRAM_MIN_N
            ? 'Con pochi casi ogni precedente è mostrato singolarmente: blu = rendimento positivo, arancio = negativo.'
            : 'Distribuzione dei rendimenti dei precedenti per classi di ampiezza uguale.'}
          {target && ' Il rombo nero è l’evento analizzato: non fa parte del campione.'}
        </p>
        {stats.n < HISTOGRAM_MIN_N ? <DotPlot points={points} stats={stats} target={target} /> : <Histogram values={stats.values} />}
        <p className="chart-summary">
          {plural(stats.n, 'precedente', 'precedenti')} a {horizon} sedute: minimo {formatPct(stats.min)}, massimo{' '}
          {formatPct(stats.max)}
          {stats.median !== null && `, mediana ${formatPct(stats.median)}`}. Rendimenti positivi in {stats.up_count} casi su{' '}
          {stats.n}.{target && ` Evento analizzato: ${formatPct(target.value)}.`}
        </p>
        <DataTable
          caption={`Rendimenti a ${horizon} sedute dalla seduta base`}
          columns={[
            { key: 'title', label: 'Caso' },
            { key: 'date', label: 'Data' },
            { key: 'value', label: 'Rendimento', numeric: true },
          ]}
          rows={[...points, ...(target ? [target] : [])].map((p) => ({
            key: p.id,
            title: p.title,
            date: p.date ? formatDate(p.date, 'medium') : '—',
            value: formatPct(p.value),
          }))}
        />
      </figure>

      <Notice tone="warning" title="Come leggere questi numeri">
        Le statistiche descrivono {plural(stats.n, 'caso storico', 'casi storici')} scelti con regole esplicite. Non sono
        probabilità, intervalli di confidenza o previsioni: con campioni così piccoli un solo caso cambia il risultato.
        {stats.notes.length > 0 && ` ${stats.notes.join('; ')}.`}
      </Notice>
    </div>
  )
}

// Scala con passo "tondo" (1, 2, 2.5, 5 × 10^k) per tacche leggibili anche con valori estremi.
export function niceScale(min, max, target = 6) {
  const raw = (max - min || 1) / target
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)
  const lo = Math.floor(min / step) * step
  const hi = Math.ceil(max / step) * step
  const ticks = []
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(Math.round(v * 1e6) / 1e6)
  return { domain: [lo, hi], ticks }
}

function shortLabel(item) {
  const year = item.occurred_on.slice(0, 4)
  const title = item.title.length > 34 ? `${item.title.slice(0, 33)}…` : item.title
  return `${title} (${year})`
}
