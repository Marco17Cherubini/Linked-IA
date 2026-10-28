import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import BudgetPanel from '../../components/BudgetPanel.jsx'
import { Notice } from '../../components/ui.jsx'
import { api } from '../../lib/api.js'
import { useAuth } from '../../lib/auth.jsx'
import { formatDateTime } from '../../lib/format.js'

export default function SummaryPanel({ analysisId, summary, aiEnabled, onRequested }) {
  const dialogRef = useRef(null)
  const auth = useAuth()
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)
  const [budgetKey, setBudgetKey] = useState(0)
  const pending = summary && ['queued', 'running'].includes(summary.status)

  const confirm = async () => {
    setSending(true)
    setError(null)
    try {
      await api.requestSummary(analysisId, { confirm_cost: true, regenerate: summary?.status === 'succeeded' })
      dialogRef.current?.close()
      onRequested()
    } catch (err) {
      if (err.status === 401) auth.expired()
      setError(err)
    } finally {
      setSending(false)
      setBudgetKey((k) => k + 1)
    }
  }

  return (
    <div className="summary">
      <Notice tone="info" title="Che cos'è questa sezione">
        Una sintesi testuale scritta da un modello linguistico a partire dai soli dati calcolati in questa analisi. Può
        contenere errori: i numeri di riferimento sono quelli dei grafici e delle tabelle.
      </Notice>

      {summary?.status === 'succeeded' && summary.content && (
        <article className="panel summary__content" aria-labelledby="summary-title">
          <p className="eyebrow">Testo generato da IA · {summary.model} · {formatDateTime(summary.finished_at)}</p>
          <h2 id="summary-title" className="summary__headline">
            {summary.content.headline}
          </h2>
          <h3>Che cosa mostrano i dati</h3>
          <ul>
            {summary.content.observations.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
          <h3>Interpretazione</h3>
          <p>{summary.content.interpretation}</p>
          <h3>Limiti</h3>
          <ul>
            {summary.content.limitations.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </article>
      )}

      {pending && (
        <p role="status" className="job-status">
          <span className="spinner" aria-hidden="true" /> Sintesi in preparazione… La pagina si aggiorna da sola.
        </p>
      )}

      {summary?.status === 'failed' && (
        <Notice tone="error" title="Sintesi non riuscita">
          {summary.error_message}
        </Notice>
      )}

      {!summary && <p className="muted">Nessuna sintesi IA è stata generata per questa analisi.</p>}

      {!pending &&
        (aiEnabled && auth.authenticated ? (
          <>
            <BudgetPanel refreshKey={budgetKey} />
            <button type="button" className="button" onClick={() => dialogRef.current?.showModal()}>
              {summary?.status === 'succeeded' ? 'Rigenera la sintesi IA' : 'Genera la sintesi IA'}
            </button>
            <dialog ref={dialogRef} className="dialog" aria-labelledby="confirm-title">
              <h2 id="confirm-title">Confermi la generazione?</h2>
              <p>
                La sintesi usa un servizio esterno a pagamento (una richiesta al modello, al massimo un nuovo tentativo se
                la prima non viene elaborata). Il costo massimo stimato viene prenotato sul budget prima dell'invio. Il
                risultato viene salvato: consultare l'analisi non genera altri costi.
              </p>
              {error && (
                <Notice tone="error">
                  {error.message}
                  {error.retryAt ? ` Riprova non prima delle ${formatDateTime(error.retryAt)}.` : ''}
                </Notice>
              )}
              <div className="dialog__actions">
                <button type="button" className="button button--secondary" onClick={() => dialogRef.current?.close()}>
                  Annulla
                </button>
                <button type="button" className="button" onClick={confirm} disabled={sending}>
                  {sending ? 'Invio…' : 'Conferma e genera'}
                </button>
              </div>
            </dialog>
          </>
        ) : (
          <p className="small muted">
            {aiEnabled ? (
              <>
                La generazione è riservata all'operatore: <Link to="/accesso">accedi</Link>.
              </>
            ) : (
              'La generazione delle sintesi non è attiva su questo server.'
            )}
          </p>
        ))}
    </div>
  )
}
