import { useApi } from '../lib/useApi.js'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/format.js'
import { Notice } from './ui.jsx'

function money(value) {
  if (value == null) return '—'
  // Gli importi arrivano come stringhe decimali esatte: si arrotonda solo per la lettura.
  const [whole, frac = ''] = value.split('.')
  return `${whole},${(frac + '0000').slice(0, 4)} USD`
}

// Stato del budget delle chiamate IA. Si aggiorna solo a richiesta (nessun ciclo automatico).
export default function BudgetPanel({ refreshKey = 0 }) {
  const { data, error, loading } = useApi((opts) => api.budget(opts), [refreshKey])

  if (loading && !data) return <p className="small muted">Caricamento del budget…</p>
  if (error) return <p className="small muted">Budget non disponibile: {error.message}</p>

  return (
    <section className="panel budget" aria-labelledby="budget-title">
      <h2 id="budget-title" className="panel__title">
        Budget chiamate a pagamento · ultime {data.window_hours} ore
      </h2>
      <dl className="budget__grid">
        <div>
          <dt>Limite</dt>
          <dd>{money(data.budget_usd)}</dd>
        </div>
        <div>
          <dt>Costo confermato</dt>
          <dd>{money(data.confirmed_usd)}</dd>
        </div>
        <div>
          <dt>Riservato (stima, in corso)</dt>
          <dd>{money(data.reserved_usd)}</dd>
        </div>
        <div>
          <dt>Esito incerto (stima trattenuta)</dt>
          <dd>{money(data.uncertain_usd)}</dd>
        </div>
        <div>
          <dt>Residuo</dt>
          <dd>{money(data.remaining_usd)}</dd>
        </div>
      </dl>
      {data.blocked ? (
        <Notice tone="error" title="Nuove sintesi IA sospese">
          Il budget è esaurito o in pausa.
          {data.next_possible_at ? ` Nuovo tentativo possibile non prima delle ${formatDateTime(data.next_possible_at)}.` : ''}{' '}
          I casi già salvati restano consultabili.
        </Notice>
      ) : (
        <p className="small muted">
          {data.ai_enabled ? `Modello: ${data.ai_model}. ` : 'Sintesi IA non attiva su questo server. '}
          Ogni chiamata prenota il costo massimo stimato prima di partire; le stime incerte non vengono liberate.
        </p>
      )}
    </section>
  )
}
