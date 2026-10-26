import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui.jsx'

export default function NotFoundPage() {
  return (
    <div className="page">
      <EmptyState
        title="Pagina non trovata"
        action={
          <Link className="button" to="/">
            Torna all'inizio
          </Link>
        }
      >
        L'indirizzo non corrisponde a nessuna pagina di LiA.
      </EmptyState>
    </div>
  )
}
