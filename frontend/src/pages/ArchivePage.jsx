import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, Skeleton, StatusBadge } from '../components/ui.jsx'
import { api } from '../lib/api.js'
import { formatDate, formatDateTime, PRECISION_LABEL } from '../lib/format.js'
import { useApi } from '../lib/useApi.js'
import { useUrlState } from '../lib/useUrlState.js'

const SCHEMA = {
  q: { default: '' },
  category: { default: '' },
  status: { default: '' },
  from: { default: '' },
  to: { default: '' },
  page: { default: '1' },
}

const PAGE_SIZE = 15

export default function ArchivePage({ meta }) {
  const [filters, setFilters] = useUrlState(SCHEMA)
  const [text, setText] = useState(filters.q)
  useEffect(() => setText(filters.q), [filters.q])

  const result = useApi(
    (opts) => api.analyses({ ...filters, page_size: PAGE_SIZE }, opts),
    [filters.q, filters.category, filters.status, filters.from, filters.to, filters.page],
  )
  const update = (changes) => setFilters({ ...changes, page: '1' }, { replace: false })

  return (
    <div className="page">
      <header className="page-header">
        <h1>Archivio delle analisi</h1>
        <p className="page-header__lead">
          Tutte le analisi salvate. Riaprirne una mostra esattamente il risultato calcolato e persistito.
        </p>
      </header>

      <form
        className="filters"
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: text.trim() })
        }}
      >
        <div className="field field--grow">
          <label htmlFor="f-q">Cerca</label>
          <input id="f-q" type="search" value={text} onChange={(e) => setText(e.target.value)} placeholder="Titolo, descrizione o etichetta" />
        </div>
        <div className="field">
          <label htmlFor="f-cat">Categoria</label>
          <select id="f-cat" value={filters.category} onChange={(e) => update({ category: e.target.value })}>
            <option value="">Tutte</option>
            {meta.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-status">Stato</label>
          <select id="f-status" value={filters.status} onChange={(e) => update({ status: e.target.value })}>
            <option value="">Tutti</option>
            <option value="succeeded">Completate</option>
            <option value="running">In calcolo</option>
            <option value="queued">In coda</option>
            <option value="failed">Non riuscite</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-from">Evento dal</label>
          <input id="f-from" type="date" value={filters.from} onChange={(e) => update({ from: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="f-to">al</label>
          <input id="f-to" type="date" value={filters.to} onChange={(e) => update({ to: e.target.value })} />
        </div>
        <div className="filters__actions">
          <button className="button" type="submit">
            Cerca
          </button>
          <button
            className="button button--ghost"
            type="button"
            onClick={() => setFilters({ q: '', category: '', status: '', from: '', to: '', page: '1' }, { replace: false })}
          >
            Azzera
          </button>
        </div>
      </form>

      {result.loading && !result.data ? (
        <Skeleton height={300} label="Caricamento dell'archivio" />
      ) : result.error ? (
        <ErrorState error={result.error} />
      ) : result.data.items.length === 0 ? (
        <EmptyState title="Nessuna analisi corrisponde ai filtri">Prova a togliere qualche filtro.</EmptyState>
      ) : (
        <>
          <p className="muted" role="status">
            {result.data.total} analisi · pagina {result.data.page} di {result.data.pages}
          </p>
          <div className="table-scroll">
            <table className="archive-table">
              <caption className="sr-only">Analisi salvate</caption>
              <thead>
                <tr>
                  <th scope="col">Data evento</th>
                  <th scope="col">Evento</th>
                  <th scope="col">Categoria</th>
                  <th scope="col">Stato</th>
                  <th scope="col" className="num">
                    Fonti
                  </th>
                  <th scope="col">Calcolata</th>
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <time dateTime={a.occurred_on}>{formatDate(a.occurred_on, 'medium')}</time>
                      <div className="small muted">{PRECISION_LABEL[a.time_precision]}</div>
                    </td>
                    <td>
                      <Link to={`/analysis/${a.id}`}>{a.title}</Link>
                    </td>
                    <td>{a.category_label}</td>
                    <td>
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="num">{a.source_count}</td>
                    <td className="small">{formatDateTime(a.finished_at || a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="pagination" aria-label="Pagine">
            <button
              type="button"
              className="button button--secondary"
              disabled={result.data.page <= 1}
              onClick={() => setFilters({ page: String(result.data.page - 1) }, { replace: false })}
            >
              ← Precedente
            </button>
            <span>
              {result.data.page} / {result.data.pages}
            </span>
            <button
              type="button"
              className="button button--secondary"
              disabled={result.data.page >= result.data.pages}
              onClick={() => setFilters({ page: String(result.data.page + 1) }, { replace: false })}
            >
              Successiva →
            </button>
          </nav>
        </>
      )}
    </div>
  )
}
