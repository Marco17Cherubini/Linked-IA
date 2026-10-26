import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, Skeleton, StatusBadge } from '../components/ui.jsx'
import { api } from '../lib/api.js'
import { formatDate, formatPct, PRECISION_LABEL } from '../lib/format.js'
import { useApi } from '../lib/useApi.js'

const FeaturedPreview = lazy(() => import('../features/analysis/FeaturedPreview.jsx'))

function Featured() {
  const featured = useApi(async (opts) => {
    const f = await api.featured(opts)
    const analysis = await api.analysis(f.analysis_id, { market: 'SP500', view: 'retrospective' }, opts)
    return { ...f, analysis }
  }, [])
  if (featured.loading) return <Skeleton height={320} label="Caricamento del caso dimostrativo" />
  if (featured.error) {
    return (
      <EmptyState title="Caso dimostrativo non disponibile">
        {featured.error.status === 404
          ? 'Le analisi del catalogo non sono ancora state calcolate su questo server.'
          : featured.error.message}
      </EmptyState>
    )
  }
  const { analysis, analysis_id: id } = featured.data
  const data = analysis.data
  const r1 = data?.outcomes?.returns.find((r) => r.h === 1)
  return (
    <article className="featured" aria-labelledby="featured-title">
      <p className="eyebrow">Caso dimostrativo · {analysis.event.category_label}</p>
      <h2 id="featured-title" className="featured__title">
        {analysis.event.title}
      </h2>
      <p className="featured__meta">
        {formatDate(analysis.event.occurred_on)} · S&amp;P 500 · prima seduta dopo l'evento{' '}
        <strong className={r1?.value >= 0 ? 'tone-up' : 'tone-down'}>{formatPct(r1?.value)}</strong>
      </p>
      {data && (
        <Suspense fallback={<Skeleton height={180} />}>
          <FeaturedPreview data={data} />
        </Suspense>
      )}
      <Link className="button button--large" to={`/analysis/${id}`}>
        Apri il caso dimostrativo
      </Link>
    </article>
  )
}

function EventsList() {
  const events = useApi((opts) => api.events({ page_size: 12 }, opts), [])
  if (events.loading) return <Skeleton height={200} label="Caricamento degli eventi" />
  if (events.error) return <ErrorState error={events.error} />
  if (!events.data.items.length) return <EmptyState title="Nessun evento in archivio" />
  return (
    <>
      <ul className="event-grid">
        {events.data.items.map((e) => (
          <li key={e.id} className="event-card">
            <p className="event-card__meta">
              <span>{e.category_label}</span>
              <time dateTime={e.occurred_on}>{formatDate(e.occurred_on, 'medium')}</time>
            </p>
            {e.analysis_id && e.analysis_status === 'succeeded' ? (
              <Link className="event-card__title" to={`/analysis/${e.analysis_id}`}>
                {e.title}
              </Link>
            ) : (
              <span className="event-card__title">{e.title}</span>
            )}
            <p className="event-card__foot">
              <span>{PRECISION_LABEL[e.time_precision]}</span>
              {e.analysis_status && e.analysis_status !== 'succeeded' && <StatusBadge status={e.analysis_status} />}
            </p>
          </li>
        ))}
      </ul>
      <p>
        <Link to="/archive">Tutti i {events.data.total} eventi nell'archivio →</Link>
      </p>
    </>
  )
}

export default function HomePage({ meta }) {
  return (
    <div className="page home">
      <section className="hero">
        <div className="hero__text">
          <p className="eyebrow">Linked Intelligent Analyst</p>
          <h1 className="hero__title">Che cosa hanno fatto i mercati dopo un evento, e nei casi simili prima di lui.</h1>
          <p className="hero__lead">
            LiA collega un evento documentato a cinque indici azionari, mostra il movimento intorno alla data e lo
            confronta con precedenti storici scelti con regole esplicite. Ogni numero ha fonte, unità e limiti dichiarati.
          </p>
          <div className="hero__actions">
            <Link className="button button--secondary" to="/archive">
              Sfoglia l'archivio
            </Link>
            <Link className="button button--ghost" to="/methodology">
              Come funziona
            </Link>
          </div>
        </div>
        <div className="hero__demo">
          <Featured />
        </div>
      </section>

      <section className="section" aria-labelledby="method-title">
        <h2 id="method-title" className="section__title">
          Il metodo in tre passi
        </h2>
        <ol className="steps">
          <li>
            <strong>Evento e seduta base.</strong> Per ogni indice si individua l'ultima chiusura avvenuta prima
            dell'evento, tenendo conto di orario e fuso. Da lì partono i rendimenti.
          </li>
          <li>
            <strong>Precedenti osservabili.</strong> Si scelgono eventi della stessa categoria o con etichette comuni, ma
            solo se il loro esito era già noto alla seduta base: nessuna informazione dal futuro.
          </li>
          <li>
            <strong>Statistiche descrittive.</strong> Mediana, quartili e frequenza dei rialzi descrivono il campione,
            dichiarandone la numerosità. Non sono probabilità.{' '}
            <Link to="/methodology">Leggi la metodologia</Link>
          </li>
        </ol>
      </section>

      <section className="section" aria-labelledby="events-title">
        <h2 id="events-title" className="section__title">
          Eventi disponibili
        </h2>
        <EventsList />
      </section>

      <section className="section section--muted" aria-labelledby="create-title">
        <h2 id="create-title" className="section__title">
          Analizzare un nuovo evento
        </h2>
        {meta?.features?.create ? (
          <p>
            Gli analisti autorizzati possono inserire un evento con data, orario e fonti: il calcolo usa solo dati di
            mercato gratuiti. <Link to="/new">Crea una nuova analisi</Link>
          </p>
        ) : (
          <p>
            La creazione di nuove analisi non è attiva su questo server. Tutte le analisi dell'archivio sono consultabili
            liberamente.
          </p>
        )}
      </section>
    </div>
  )
}
