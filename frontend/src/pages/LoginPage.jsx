import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { Notice } from '../components/ui.jsx'
import { useAuth } from '../lib/auth.jsx'
import { formatDateTime } from '../lib/format.js'

// Solo percorsi interni: un parametro "next" non può portare fuori dal sito.
function safeNext(value) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/ricerca'
}

export default function LoginPage({ meta }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)

  if (auth.authenticated) return <Navigate to={next} replace />

  const submit = async (e) => {
    e.preventDefault()
    setSending(true)
    setError(null)
    try {
      await auth.login(password)
      setPassword('')
      navigate(next, { replace: true })
    } catch (err) {
      setError(err)
      setPassword('')
    } finally {
      setSending(false)
    }
  }

  const hours = meta?.legal?.session_hours ?? 8

  return (
    <div className="page narrow">
      <header className="page-header">
        <h1>Accesso operatore</h1>
        <p className="page-header__lead">
          La consultazione dei casi dimostrativi è libera. Nuove analisi, ricalcoli e sintesi IA contattano servizi esterni
          e sono riservati all'operatore.
        </p>
      </header>

      {meta && !meta.features.login ? (
        <Notice tone="info" title="Accesso non attivo">
          Su questo server le funzioni riservate sono disabilitate.
        </Notice>
      ) : (
        <form className="panel login-form" onSubmit={submit}>
          {error && (
            <Notice tone="error" title="Accesso non riuscito">
              {error.message}
              {error.retryAt ? ` Nuovo tentativo possibile dalle ${formatDateTime(error.retryAt)}.` : ''}
            </Notice>
          )}
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              maxLength={256}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="button" type="submit" disabled={sending || !password}>
            {sending ? 'Verifica…' : 'Accedi'}
          </button>
          <p className="small muted">
            L'accesso usa un cookie tecnico di sessione, valido al massimo {hours} ore e cancellato all'uscita. Dettagli
            nella <Link to="/privacy">informativa privacy</Link> e nella <Link to="/cookie">cookie policy</Link>.
          </p>
        </form>
      )}
    </div>
  )
}
