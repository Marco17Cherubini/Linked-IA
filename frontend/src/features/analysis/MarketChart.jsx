import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DataTable, EmptyState, InfoTip, Segmented } from '../../components/ui.jsx'
import { formatDate, formatNumber, formatPct } from '../../lib/format.js'
import { ANIMATION, AXIS_PROPS, GRID_PROPS } from './chartTheme.js'

// Variazione calcolata dalle chiusure (come i rendimenti del backend), non dalla base 100 arrotondata.
const changeFromBase = (p, baseClose) => (p.close / baseClose - 1) * 100

function ChartTooltip({ active, payload, scale, currency, baseClose }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">{formatDate(p.date, 'medium')}</div>
      <div>
        Seduta {p.s > 0 ? `+${p.s}` : p.s} {p.s === 0 && '(base)'}
      </div>
      <div className="chart-tooltip__value">
        {scale === 'index100'
          ? `${formatNumber(p.index100, 2)} (base 100)`
          : `${formatNumber(p.close, 2)} ${currency}`}
      </div>
      {p.s !== 0 && <div className="muted">{formatPct(changeFromBase(p, baseClose))} dalla base</div>}
    </div>
  )
}

export default function MarketChart({ data, market, view, windowSize }) {
  const [scale, setScale] = useState('index100')
  const asOf = view === 'as_of'
  const points = useMemo(() => {
    const all = [...data.observed.series, ...(asOf ? [] : data.outcomes?.series || [])]
    return all.filter((p) => p.s >= -windowSize && p.s <= windowSize)
  }, [data, asOf, windowSize])

  if (points.length < 2) {
    return <EmptyState title="Serie non disponibile">Non ci sono abbastanza sedute per disegnare il grafico.</EmptyState>
  }

  const byS = Object.fromEntries(points.map((p) => [p.s, p]))
  const maxS = points[points.length - 1].s
  const minS = points[0].s
  const key = scale === 'index100' ? 'index100' : 'close'
  const last = points[points.length - 1]
  const baseDate = formatDate(data.base.date)

  const summary = asOf
    ? `${market.name}: ${points.length} sedute fino alla seduta base del ${baseDate} (chiusura ${formatNumber(data.base.close)} ${market.currency}). Gli esiti successivi sono nascosti nella vista al cutoff.`
    : `${market.name}: chiusura base ${formatNumber(data.base.close)} ${market.currency} il ${baseDate}. ` +
      (maxS > 0
        ? `Dopo ${maxS} sedute (${formatDate(last.date)}) l'indice è a ${formatNumber(last.index100)} in base 100 (${formatPct(changeFromBase(last, data.base.close))}).`
        : 'Non ci sono ancora sedute successive all’evento.')

  return (
    <figure className="chart-figure">
      <div className="chart-figure__header">
        <figcaption className="chart-title">
          Mercato intorno all'evento
          <InfoTip term="base" />
        </figcaption>
        <Segmented
          name="market-scale"
          label="Scala"
          value={scale}
          onChange={setScale}
          options={[
            { value: 'index100', label: 'Base 100' },
            { value: 'close', label: `Livello (${market.currency})` },
          ]}
        />
      </div>
      <p className="chart-note">
        <strong>Come leggere il grafico:</strong> ogni movimento è misurato dalla chiusura del {baseDate}, l'ultima
        avvenuta prima dell'evento del {formatDate(data.event_time?.occurred_on ?? data.base.date)}. A sinistra della
        linea ambra c'è ciò che si sapeva prima; a destra, la reazione del mercato a partire dalla prima seduta dopo
        l'evento{data.first_reaction && !asOf ? ` (${formatDate(data.first_reaction.date)})` : ''}.{' '}
        {scale === 'index100' ? `Base 100 = chiusura del ${baseDate}.` : `Livello dell'indice in ${market.currency}.`}
      </p>
      <div className="chart-box" style={{ height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 24, right: 16, bottom: 8, left: 8 }} accessibilityLayer>
            <CartesianGrid {...GRID_PROPS} />
            {!asOf && maxS > 0 && (
              <ReferenceArea x1={0.5} x2={maxS} fill="var(--post-area)" ifOverflow="hidden" label={{ value: 'Dopo l’evento', position: 'insideBottomRight', fill: 'var(--text-3)', fontSize: 12 }} />
            )}
            <XAxis
              dataKey="s"
              type="number"
              domain={[minS, Math.max(maxS, Math.ceil(windowSize / 6))]}
              allowDecimals={false}
              tickFormatter={(s) => (byS[s] ? formatDate(byS[s].date, 'short') : '')}
              minTickGap={24}
              {...AXIS_PROPS}
            />
            <YAxis
              domain={['auto', 'auto']}
              width={64}
              tickFormatter={(v) => formatNumber(v, scale === 'index100' ? 0 : 0)}
              {...AXIS_PROPS}
            />
            {scale === 'index100' && <ReferenceLine y={100} stroke="var(--border-strong)" strokeDasharray="2 4" />}
            <ReferenceLine x={0} stroke="var(--text-3)" label={{ value: 'Ultima chiusura prima', position: 'top', fill: 'var(--text-2)', fontSize: 12 }} />
            <ReferenceLine
              x={0.5}
              stroke="var(--event)"
              strokeWidth={2}
              strokeDasharray="5 4"
              label={{ value: `Evento · ${formatDate(data.event_time?.occurred_on ?? data.base.date, 'short')}`, position: 'insideTopLeft', fill: 'var(--event)', fontSize: 12, fontWeight: 600 }}
            />
            <Tooltip content={<ChartTooltip scale={scale} currency={market.currency} baseClose={data.base.close} />} cursor={{ stroke: 'var(--border-strong)' }} />
            <Line type="linear" dataKey={key} stroke="var(--accent)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} {...ANIMATION} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-summary">{summary}</p>
      <DataTable
        caption={`${market.name}, sedute da ${minS} a ${maxS} rispetto alla base`}
        columns={[
          { key: 's', label: 'Seduta', numeric: true },
          { key: 'date', label: 'Data' },
          { key: 'close', label: `Chiusura (${market.currency})`, numeric: true },
          { key: 'index100', label: 'Base 100', numeric: true },
        ]}
        rows={points.map((p) => ({
          key: p.s,
          s: p.s > 0 ? `+${p.s}` : p.s,
          date: formatDate(p.date, 'medium'),
          close: formatNumber(p.close),
          index100: formatNumber(p.index100),
        }))}
      />
    </figure>
  )
}
