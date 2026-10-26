// Definizioni brevi richiamate vicino a grafici e metriche; la pagina Metodologia le approfondisce.
// Le chiavi coincidono con gli id restituiti dall'API e con le ancore della Metodologia.

export const GLOSSARY = {
  base: {
    term: 'Seduta base (s = 0)',
    text: "Ultima seduta del mercato chiusa prima dell'evento. Se l'orario è sconosciuto, è l'ultima seduta con data precedente al giorno dell'evento. Rendimenti e base 100 partono dalla sua chiusura.",
  },
  sessions: {
    term: 'Sedute (s)',
    text: 'Posizione rispetto alla seduta base contando solo i giorni di borsa: s = +1 è la prima seduta che può riflettere l’evento.',
  },
  index100: {
    term: 'Base 100',
    text: 'Chiusura divisa per la chiusura della seduta base e moltiplicata per 100: rende confrontabili indici e periodi con livelli diversi.',
  },
  as_of: {
    term: 'Vista al cutoff',
    text: 'Mostra solo ciò che era disponibile alla chiusura della seduta base: serie, indicatori e precedenti. Gli esiti successivi sono nascosti.',
  },
  horizon: {
    term: 'Orizzonte',
    text: 'Numero di sedute dopo la base su cui si misura il rendimento: chiusura di s = h rispetto alla chiusura di s = 0.',
  },
  precedents: {
    term: 'Precedenti',
    text: 'Eventi del catalogo della stessa categoria o con almeno due etichette in comune, il cui esito a 20 sedute era già osservabile alla seduta base.',
  },
  observed_frequency: {
    term: 'Frequenza osservata',
    text: 'Quota di precedenti con rendimento positivo. Descrive il campione: non è una probabilità e non è una previsione.',
  },
  median: {
    term: 'Mediana e quartili',
    text: 'Calcolati solo con almeno 3 casi (mediana) e 5 casi (quartili). Descrivono la dispersione del campione, non un intervallo di confidenza.',
  },
  ret_1: { term: 'Rendimento ultima seduta', text: 'Variazione della chiusura base rispetto alla seduta precedente.' },
  ret_5: { term: 'Rendimento 5 sedute', text: 'Variazione della chiusura base rispetto a 5 sedute prima.' },
  vol_20: {
    term: 'Volatilità realizzata 20 sedute',
    text: 'Deviazione standard dei rendimenti logaritmici giornalieri delle ultime 20 sedute, annualizzata con √252.',
  },
  drawdown_60: {
    term: 'Distanza dal massimo a 60 sedute',
    text: 'Variazione della chiusura base rispetto alla chiusura più alta delle ultime 60 sedute.',
  },
  zscore_20: {
    term: 'Z-score a 20 sedute',
    text: 'Distanza della chiusura base dalla media delle ultime 20 chiusure, in deviazioni standard.',
  },
  range_1: {
    term: 'Escursione seduta base',
    text: '(Massimo − minimo) della seduta base rispetto alla chiusura precedente.',
  },
  min_after: {
    term: 'Minimo nelle 20 sedute successive',
    text: 'Chiusura più bassa tra s = +1 e s = +20 rispetto alla base: è un esito, non un dato disponibile al cutoff.',
  },
}
