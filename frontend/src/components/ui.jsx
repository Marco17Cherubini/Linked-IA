// Componenti di interfaccia condivisi: stati, controlli, definizioni.
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { GLOSSARY } from '../content/glossary.js'
import { STATUS_LABEL } from '../lib/format.js'

export function InfoTip({ term, anchor }) {
  // Definizione apribile con clic o tastiera; Esc la chiude. Collegata alla Metodologia.
  const entry = GLOSSARY[term]
  const [open, setOpen] = useState(false)
  const id = useId()
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    const onClick = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onClick)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('mousedown', onClick)
    }
  }, [open])
  if (!entry) return null
  return (
    <span className="infotip" ref={ref}>
      <button
        type="button"
        className="infotip__button"
        aria-expanded={open}
        aria-controls={id}
        aria-label={`Definizione: ${entry.term}`}
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <span role="note" id={id} className="infotip__panel">
          <strong>{entry.term}</strong>
          <span>{entry.text}</span>
          <Link to={`/methodology#${anchor || term}`}>Approfondisci nella metodologia</Link>
        </span>
      )}
    </span>
  )
}

export function Segmented({ label, help, value, options, onChange, name }) {
  // Gruppo di radio con aspetto a pulsanti: frecce da tastiera native.
  const helpId = useId()
  return (
    <fieldset className="segmented">
      <legend className="control-label">{label}</legend>
      <div className="segmented__options">
        {options.map((opt) => (
          <label key={opt.value} className={`segmented__option${opt.disabled ? ' is-disabled' : ''}`} title={opt.title}>
            <input
              type="radio"
              name={name}
              value={opt.value}
              checked={value === opt.value}
              disabled={opt.disabled}
              onChange={() => onChange(opt.value)}
              aria-describedby={help ? helpId : undefined}
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      {help && (
        <p className="control-help" id={helpId}>
          {help}
        </p>
      )}
    </fieldset>
  )
}

export function Tabs({ tabs, active, onChange, label }) {
  const refs = useRef({})
  const onKeyDown = (e, index) => {
    const delta = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    let next = null
    if (delta) next = tabs[(index + delta + tabs.length) % tabs.length]
    if (e.key === 'Home') next = tabs[0]
    if (e.key === 'End') next = tabs[tabs.length - 1]
    if (next) {
      e.preventDefault()
      onChange(next.id)
      refs.current[next.id]?.focus()
    }
  }
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((tab, i) => (
        <button
          key={tab.id}
          ref={(el) => (refs.current[tab.id] = el)}
          role="tab"
          type="button"
          id={`tab-${tab.id}`}
          aria-selected={active === tab.id}
          aria-controls={`panel-${tab.id}`}
          tabIndex={active === tab.id ? 0 : -1}
          className="tabs__tab"
          onClick={() => onChange(tab.id)}
          onKeyDown={(e) => onKeyDown(e, i)}
        >
          {tab.label}
          {tab.badge !== undefined && <span className="tabs__badge">{tab.badge}</span>}
        </button>
      ))}
    </div>
  )
}

export function TabPanel({ id, children }) {
  return (
    <section role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} className="tabpanel" tabIndex={0}>
      {children}
    </section>
  )
}

export function StatusBadge({ status }) {
  return <span className={`badge badge--${status}`}>{STATUS_LABEL[status] || status}</span>
}

export function Notice({ tone = 'info', title, children }) {
  return (
    <div className={`notice notice--${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      {title && <strong className="notice__title">{title}</strong>}
      <div>{children}</div>
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {children && <div className="empty__text">{children}</div>}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <Notice tone="error" title="Impossibile caricare i dati">
      <p>{error?.message || 'Errore inatteso.'}</p>
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Riprova
        </button>
      )}
    </Notice>
  )
}

export function Skeleton({ height = 16, width = '100%', label = 'Caricamento…' }) {
  return <span className="skeleton" style={{ height, width }} role="status" aria-label={label} />
}

export function DataTable({ caption, columns, rows, summary = 'Mostra i dati in tabella' }) {
  // Alternativa testuale ai grafici: tabella completa, apribile.
  return (
    <details className="data-table">
      <summary>{summary}</summary>
      <div className="table-scroll">
        <table>
          <caption>{caption}</caption>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col" className={c.numeric ? 'num' : undefined}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.key ?? i}>
                {columns.map((c) => (
                  <td key={c.key} className={c.numeric ? 'num' : undefined}>
                    {row[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export function Stat({ label, value, detail, tone, term }) {
  return (
    <div className="stat">
      <div className="stat__label">
        {label}
        {term && <InfoTip term={term} />}
      </div>
      <div className={`stat__value${tone ? ` tone-${tone}` : ''}`}>{value}</div>
      {detail && <div className="stat__detail">{detail}</div>}
    </div>
  )
}
