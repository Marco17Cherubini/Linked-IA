import { Line, LineChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { formatDate, formatNumber } from '../../lib/format.js'
import { AXIS_PROPS } from './chartTheme.js'

// Anteprima statica (dati reali dell'API) del grafico principale: ±20 sedute in base 100.
export default function FeaturedPreview({ data }) {
  const points = [...data.observed.series, ...(data.outcomes?.series || [])].filter((p) => p.s >= -20 && p.s <= 20)
  const last = points[points.length - 1]
  return (
    <figure className="featured__chart">
      <div style={{ height: 180 }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="s" type="number" domain={['dataMin', 'dataMax']} hide />
            <YAxis domain={['auto', 'auto']} width={36} tickFormatter={(v) => formatNumber(v, 0)} {...AXIS_PROPS} />
            <ReferenceLine y={100} stroke="var(--border-strong)" strokeDasharray="2 4" />
            <ReferenceLine x={0.5} stroke="var(--event)" strokeWidth={2} strokeDasharray="5 4" />
            <Line dataKey="index100" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="small muted">
        S&amp;P 500 in base 100 alla chiusura del {formatDate(data.base.date)}, 20 sedute prima e dopo l'evento (linea
        ambra). Ultimo valore: {formatNumber(last.index100, 1)}.
      </figcaption>
    </figure>
  )
}
