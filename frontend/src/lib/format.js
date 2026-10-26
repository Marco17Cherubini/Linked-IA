// Formattazione coerente di numeri e date (locale italiano). I valori mancanti restano "—".

export const MISSING = '—'

const numberFmt = (digits) => new Intl.NumberFormat('it-IT', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return MISSING
  return numberFmt(digits).format(value)
}

// I rendimenti arrivano in punti percentuali (1.5 = +1,5%).
export function formatPct(value, digits = 2, { sign = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return MISSING
  const text = numberFmt(digits).format(Math.abs(value))
  const prefix = value < 0 ? '−' : sign && value > 0 ? '+' : ''
  return `${prefix}${text}%`
}

export function formatValue(value, unit, digits = 2) {
  if (value === null || value === undefined) return MISSING
  if (unit === '%') return formatPct(value, digits)
  if (unit === '% annua') return `${formatNumber(value, 1)}% annuo`
  if (unit === 'σ') return `${value < 0 ? '−' : ''}${formatNumber(Math.abs(value), 2)} σ`
  return formatNumber(value, digits)
}

export function parseDate(iso) {
  // Le date "YYYY-MM-DD" sono giorni di calendario: niente conversioni di fuso.
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

export function formatDate(iso, style = 'long') {
  if (!iso) return MISSING
  const options =
    style === 'short'
      ? { day: 'numeric', month: 'short', timeZone: 'UTC' }
      : style === 'medium'
        ? { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }
        : { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }
  return new Intl.DateTimeFormat('it-IT', options).format(parseDate(iso))
}

// Orario dell'evento nel fuso in cui è stato registrato, con l'offset esplicito.
export function formatEventTime(occurredAt) {
  if (!occurredAt) return null
  const match = occurredAt.match(/T(\d{2}):(\d{2})(?::\d{2})?([+-]\d{2}:\d{2}|Z)$/)
  if (!match) return null
  const [, hh, mm, offset] = match
  const utc = offset === 'Z' || offset === '+00:00' ? 'UTC' : `UTC${offset.replace(':00', '').replace(/^([+-])0/, '$1')}`
  return `${hh}:${mm} (${utc})`
}

export function formatDateTime(iso) {
  if (!iso) return MISSING
  return new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso))
}

export const PRECISION_LABEL = {
  exact: 'orario documentato',
  approximate: 'orario approssimato',
  unknown: 'orario sconosciuto',
}

export const STATUS_LABEL = {
  queued: 'In coda',
  running: 'In calcolo',
  succeeded: 'Completata',
  failed: 'Non riuscita',
}

export function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`
}
