import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EmptyState, ErrorState, Notice, Segmented, Skeleton, TabPanel, Tabs } from '../../components/ui.jsx'
import { api } from '../../lib/api.js'
import { useAuth } from '../../lib/auth.jsx'
import { formatDateTime, STATUS_LABEL } from '../../lib/format.js'
import { useUrlState } from '../../lib/useUrlState.js'
import MarketChart from './MarketChart.jsx'
import OutcomesPanel from './OutcomesPanel.jsx'
import { EventHeader, IndicatorsPanel, KeyFigures, OutcomeMin, QualityPanel, Warnings } from './panels.jsx'
import PrecedentsPanel from './PrecedentsPanel.jsx'
import SummaryPanel from './SummaryPanel.jsx'
import { useAnalysis } from './useAnalysis.js'

const TABS = ['market', 'precedents', 'outcomes', 'quality', 'summary']
const WINDOWS = ['10', '20', '60']

function RerunAction({ eventId, canCreate }) {
  const navigate = useNavigate()
  const auth = useAuth()
  const [error, setError] = useState(null)
  if (!canCreate || !auth.authenticated) {
    return <p className="small">L'operatore autenticato può avviare di nuovo il calcolo.</p>
  }
  return (
    <>
      <button
        type="button"
        className="button button--secondary"
        onClick={async () => {
          try {
            const res = await api.rerun(eventId)
            navigate(`/analysis/${res.analysis_id}`)
          } catch (err) {
            if (err.status === 401) auth.expired()
            setError(err)
          }
        }}
      >
        Ricalcola l'analisi
      </button>
      {error && <p className="small">{error.message}</p>}
    </>
  )
}

export default function WorkspacePage({ meta }) {
  const { analysisId } = useParams()
  const horizons = meta.horizons.map(String)
  const schema = useMemo(
    () => ({
      market: { default: meta.default_market, allowed: meta.markets.map((m) => m.id) },
      view: { default: 'retrospective', allowed: ['retrospective', 'as_of'] },
      win: { default: '20', allowed: WINDOWS },
      h: { default: '5', allowed: horizons },
      tab: { default: 'market', allowed: TABS },
      hide: { default: [], list: true },
      sel: { default: '' },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [meta],
  )
  const [ui, setUi] = useUrlState(schema)
  const { data, error, loading, refresh } = useAnalysis(analysisId, ui.market, ui.view)

  useEffect(() => {
    if (data?.event) document.title = `${data.event.title} — LiA`
    return () => {
      document.title = 'LiA — Linked Intelligent Analyst'
    }
  }, [data?.event])

  if (error && !data) {
    return (
      <div className="page">
        {error.status === 404 ? (
          <EmptyState title="Analisi non trovata" action={<Link className="button" to="/archive">Apri l'archivio</Link>}>
            L'analisi richiesta non esiste o è stata rimossa.
          </EmptyState>
        ) : (
          <ErrorState error={error} onRetry={refresh} />
        )}
      </div>
    )
  }
  if (!data) {
    return (
      <div className="page" aria-busy="true">
        <Skeleton height={20} width="30%" />
        <Skeleton height={40} width="70%" />
        <Skeleton height={340} />
      </div>
    )
  }

  const market = meta.markets.find((m) => m.id === ui.market)
  const marketStatus = data.markets.find((m) => m.id === ui.market)
  const pending = ['queued', 'running'].includes(data.status)
  const result = data.data

  return (
    <div className="page workspace">
      <EventHeader event={data.event} analysis={data} />

      {pending && (
        <Notice tone="info" title={STATUS_LABEL[data.status]}>
          <p role="status">
            <span className="spinner" aria-hidden="true" /> Download dei prezzi e calcolo in corso. Puoi lasciare o
            ricaricare la pagina: l'analisi continua sul server.
          </p>
        </Notice>
      )}
      {data.status === 'failed' && (
        <Notice tone="error" title="Analisi non riuscita">
          <p>{data.error?.message}</p>
          <p className="small muted">Terminata il {formatDateTime(data.finished_at)}.</p>
          <RerunAction eventId={data.event.id} canCreate={meta.features.create} />
        </Notice>
      )}

      {data.status === 'succeeded' && (
        <>
          <div className="controls" role="group" aria-label="Controlli della vista">
            <Segmented
              name="market"
              label="Indice"
              help="Cambia mercato: grafici, indicatori, precedenti e statistiche si aggiornano."
              value={ui.market}
              onChange={(market) => setUi({ market, sel: '', hide: [] })}
              options={data.markets.map((m) => ({
                value: m.id,
                label: m.name,
                title: m.status === 'ok' ? `${m.name} (${m.exchange})` : 'Dati non disponibili',
              }))}
            />
            <Segmented
              name="view"
              label="Vista"
              help={
                ui.view === 'as_of'
                  ? 'Solo dati disponibili alla chiusura della seduta base: esiti nascosti.'
                  : 'Mostra anche ciò che è successo dopo l’evento.'
              }
              value={ui.view}
              onChange={(view) => setUi({ view })}
              options={[
                { value: 'retrospective', label: 'Retrospettiva' },
                { value: 'as_of', label: 'Al cutoff' },
              ]}
            />
            <Segmented
              name="window"
              label="Finestra"
              help="Sedute mostrate prima e dopo la base nel grafico del mercato."
              value={ui.win}
              onChange={(win) => setUi({ win })}
              options={WINDOWS.map((w) => ({ value: w, label: `±${w}` }))}
            />
            <Segmented
              name="horizon"
              label="Orizzonte"
              help="Sedute dopo la base su cui si misurano esiti e statistiche."
              value={ui.h}
              onChange={(h) => setUi({ h })}
              options={horizons.map((h) => ({ value: h, label: `${h} sed.` }))}
            />
          </div>

          {!result ? (
            <Notice tone="warning" title={`${market.name}: dati non disponibili`}>
              {marketStatus?.error?.message || 'Il calcolo per questo mercato non ha prodotto risultati.'} Scegli un altro
              indice.
            </Notice>
          ) : result.status !== 'ok' ? (
            <Notice tone="warning" title={`${market.name}: dati insufficienti`}>
              <Warnings warnings={result.warnings} />
            </Notice>
          ) : (
            <>
              <KeyFigures data={result} view={ui.view} horizon={ui.h} market={market} />
              <Tabs
                label="Approfondimenti"
                active={ui.tab}
                onChange={(tab) => setUi({ tab })}
                tabs={[
                  { id: 'market', label: 'Mercato' },
                  { id: 'precedents', label: 'Precedenti', badge: result.precedents.items.length },
                  { id: 'outcomes', label: 'Esiti del campione' },
                  { id: 'quality', label: 'Qualità e fonti', badge: result.warnings.length || undefined },
                  { id: 'summary', label: 'Sintesi IA' },
                ]}
              />
              <TabPanel id={ui.tab}>
                {ui.tab === 'market' && (
                  <div className="split">
                    <div className="split__main">
                      <MarketChart data={result} market={market} view={ui.view} windowSize={Number(ui.win)} />
                    </div>
                    <div className="split__side">
                      <IndicatorsPanel indicators={result.observed.indicators} />
                      {ui.view === 'retrospective' && <OutcomeMin data={result} />}
                      <Warnings warnings={result.warnings.filter((w) => w.severity !== 'info')} />
                    </div>
                  </div>
                )}
                {ui.tab === 'precedents' && (
                  <PrecedentsPanel
                    data={result}
                    view={ui.view}
                    horizon={ui.h}
                    hidden={ui.hide}
                    selected={ui.sel}
                    eventTitle={data.event.title}
                    onToggle={(id) =>
                      setUi({ hide: ui.hide.includes(id) ? ui.hide.filter((x) => x !== id) : [...ui.hide, id] })
                    }
                    onSelect={(sel) => setUi({ sel })}
                  />
                )}
                {ui.tab === 'outcomes' && (
                  <OutcomesPanel data={result} view={ui.view} horizon={ui.h} eventTitle={data.event.title} />
                )}
                {ui.tab === 'quality' && (
                  <QualityPanel
                    data={result}
                    event={data.event}
                    market={market}
                    priceSource={data.price_source}
                    method={data.method_version}
                    marketError={marketStatus?.error}
                  />
                )}
                {ui.tab === 'summary' && (
                  <SummaryPanel
                    analysisId={analysisId}
                    summary={data.summary}
                    aiEnabled={meta.features.ai_summary}
                    onRequested={refresh}
                  />
                )}
              </TabPanel>
            </>
          )}
        </>
      )}
      {loading && data && <span className="sr-only" role="status">Aggiornamento dei dati…</span>}
    </div>
  )
}
