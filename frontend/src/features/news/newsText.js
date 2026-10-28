// Testi della ricerca notizie: stati, errori ed etichette. Gli errori restano distinti dai risultati vuoti.

export const STAGE_LABEL = {
  queued: 'In coda',
  searching: 'Ricerca delle fonti',
  extracting: 'Organizzazione degli eventi',
  done: 'Completata',
  failed: 'Interrotta',
}

export const ERROR_TEXT = {
  provider_not_configured: 'La ricerca automatica non è configurata su questo server (manca la chiave del servizio di ricerca).',
  provider_auth: 'Il servizio di ricerca ha rifiutato le credenziali configurate. Nessun risultato è stato scartato: la ricerca non è avvenuta.',
  provider_timeout: 'Il servizio di ricerca non ha risposto in tempo. Il costo prudenziale resta conteggiato finché l’esito non è noto.',
  provider_rate_limited: 'Il servizio di ricerca ha raggiunto il proprio limite di richieste. Riprova tra qualche minuto.',
  provider_no_credit: 'Il credito del servizio di ricerca è esaurito.',
  provider_unavailable: 'Il servizio di ricerca non è disponibile in questo momento.',
  provider_invalid_response: 'Il servizio di ricerca ha restituito una risposta non leggibile.',
  provider_rejected: 'Il servizio di ricerca ha rifiutato la richiesta.',
  budget_blocked: 'Budget delle chiamate a pagamento esaurito o in pausa: nessuna richiesta è partita.',
  budget_exceeded: 'La ricerca supera il budget complessivo configurato.',
  busy: 'È già in corso un’altra operazione esterna. Riprova tra qualche minuto.',
  interrupted: 'La ricerca è stata interrotta da un riavvio del server. Avviala di nuovo.',
  unauthorized: 'La sessione è scaduta prima dell’esecuzione. Accedi di nuovo.',
}

export const EXCLUDED_TEXT = {
  invalid_url: 'indirizzo non valido',
  missing_title: 'senza titolo',
  missing_publication_date: 'senza data di pubblicazione (fonti dell’epoca)',
  outside_window: 'pubblicati fuori dalla finestra dell’epoca',
  published_before_event: 'pubblicati prima dell’evento',
  duplicate_url: 'duplicati',
  index_page: 'pagine indice o cronologie (non sono eventi)',
  other_language: 'in lingue diverse da italiano e inglese',
}

export const DATE_BASIS_TEXT = {
  searched_day: 'giorno cercato',
  first_publication: 'stimata dalla prima pubblicazione',
  extracted: 'indicata nelle fonti',
}

export const MODES = [
  { id: 'auto', label: 'Fonti dell’epoca e ricostruzioni successive' },
  { id: 'contemporary', label: 'Solo fonti dell’epoca' },
  { id: 'retrospective', label: 'Solo ricostruzioni successive' },
]

export function errorText(code, fallback) {
  return ERROR_TEXT[code] || fallback || 'La ricerca non è riuscita.'
}

// Solo link http(s): gli URL arrivano da fonti esterne e non devono mai eseguire codice.
export function safeHref(url) {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : undefined
  } catch {
    return undefined
  }
}
