import { Link } from 'react-router-dom'
import { Notice } from '../components/ui.jsx'

export const POLICY_UPDATED = '28 ottobre 2026'

export function Controller({ legal }) {
  if (!legal?.controller_name || !legal?.controller_email) {
    return (
      <Notice tone="warning" title="Informativa in completamento">
        I dati identificativi e di contatto del titolare non sono ancora configurati su questo server: fino al loro
        inserimento questa informativa non è definitiva.
      </Notice>
    )
  }
  return (
    <p>
      Titolare del trattamento: <strong>{legal.controller_name}</strong>. Contatto per ogni richiesta relativa ai dati
      personali: <a href={`mailto:${legal.controller_email}`}>{legal.controller_email}</a>.
    </p>
  )
}

export default function PrivacyPage({ meta }) {
  const legal = meta?.legal
  const hours = legal?.session_hours ?? 8
  return (
    <div className="page prose-page legal">
      <header className="page-header">
        <h1>Informativa privacy</h1>
        <p className="page-header__lead">
          Come LiA tratta i dati personali, ai sensi degli articoli 13 e 14 del Regolamento (UE) 2016/679 (GDPR).
          Aggiornata al {POLICY_UPDATED}.
        </p>
      </header>

      <h2>1. Titolare</h2>
      <Controller legal={legal} />

      <h2>2. Che cosa fa il sito</h2>
      <p>
        LiA è uno strumento di ricerca che mostra casi storici: eventi documentati e movimenti degli indici azionari. La
        consultazione è libera e non richiede registrazione. Non ci sono moduli pubblici, account per i visitatori,
        newsletter, pubblicità, strumenti di analisi statistica o di profilazione. Le funzioni che contattano servizi
        esterni (nuove analisi e sintesi IA) sono riservate a un unico operatore autenticato.
      </p>

      <h2>3. Dati trattati</h2>
      <h3>Visitatori</h3>
      <p>
        Per consegnare le pagine, l'infrastruttura di hosting registra per ogni richiesta HTTP: indirizzo IP, data e ora,
        metodo, percorso richiesto, host, codice di risposta, dimensioni, tempi e user agent del browser. L'applicazione
        non scrive nei propri registri indirizzi IP, password o contenuti delle richieste.
      </p>
      <h3>Operatore</h3>
      <ul>
        <li>
          Sessione di accesso: un cookie tecnico con un identificativo casuale; sul server se ne conserva solo
          un'impronta crittografica, con scadenza e token anti-falsificazione (CSRF).
        </li>
        <li>
          Tentativi di accesso: esito, data e ora e un'impronta non reversibile dell'indirizzo IP (HMAC con un segreto del
          server), usata solo per limitare i tentativi. L'indirizzo in chiaro non viene salvato.
        </li>
        <li>
          Contenuti inseriti: titolo, descrizione, data ed eventuali fonti degli eventi analizzati, con i risultati
          calcolati. Questi testi non devono contenere dati personali di terzi.
        </li>
        <li>
          Ricerche di notizie: data o intervallo, filtri scelti dall'operatore, query inviate al motore di ricerca e, per
          ogni risultato, URL, titolo, editore, date di pubblicazione e un estratto breve. Non si conserva il testo
          integrale degli articoli. Gli articoli possono citare persone note: sono informazioni già pubblicate dalle fonti.
        </li>
      </ul>

      <h2>4. Finalità e basi giuridiche</h2>
      <ul>
        <li>
          Erogare il sito e proteggerlo da abusi (registri HTTP, limiti ai tentativi di accesso): legittimo interesse del
          titolare alla sicurezza e al funzionamento del servizio (art. 6, par. 1, lett. f GDPR).
        </li>
        <li>
          Riservare all'operatore le funzioni che generano costi o contattano servizi esterni (sessione di accesso):
          legittimo interesse a impedire usi non autorizzati e spese non controllate (art. 6, par. 1, lett. f).
        </li>
      </ul>
      <p>Il sito non usa il consenso come base giuridica perché non svolge trattamenti che lo richiedano.</p>

      <h2>5. Fornitori e destinatari</h2>
      <ul>
        <li>
          <strong>Railway</strong> (hosting): esegue l'applicazione e conserva database e registri. L'esecuzione è
          configurata nella regione Europe West (Amsterdam); il traffico può transitare da nodi di rete del fornitore
          vicini al visitatore e il fornitore, con sede negli Stati Uniti, può accedere ai dati per gestire il servizio.
        </li>
        <li>
          <strong>Perplexity</strong> (Perplexity AI, Inc., Stati Uniti): motore di ricerca usato dalla ricerca delle
          notizie avviata dall'operatore. Riceve le query generate da LiA (date, argomento e area scelti dall'operatore),
          mai dati dei visitatori.
        </li>
        <li>
          <strong>DeepSeek</strong> (Hangzhou DeepSeek Artificial Intelligence Co., Ltd., Cina): genera le sintesi IA e,
          se configurato, organizza i risultati della ricerca in schede evento, solo su azione dell'operatore. Riceve i
          dati strutturati dell'analisi o titoli ed estratti pubblici degli articoli trovati, mai dati dei visitatori.
        </li>
        <li>
          <strong>Yahoo Finance</strong>: il server scarica da qui i prezzi storici degli indici. Le richieste partono dal
          server e non contengono dati dei visitatori.
        </li>
        <li>
          <strong>Hostinger</strong>: registrar del dominio e gestore dei DNS, che traducono il nome del sito nell'indirizzo
          del server. Non riceve i contenuti delle pagine.
        </li>
      </ul>
      <p>Il browser del visitatore non carica risorse da altri siti: caratteri, script e immagini sono serviti dal sito.</p>

      <h2>6. Trasferimenti fuori dall'Unione europea</h2>
      <p>
        Railway ha sede negli Stati Uniti: l'eventuale accesso del fornitore avviene secondo le garanzie del suo accordo
        sul trattamento dei dati (<a href="https://railway.com/legal/dpa" rel="noopener noreferrer">DPA di Railway</a>).
        La Cina non è oggetto di una decisione di adeguatezza della Commissione europea: per questo a DeepSeek non sono
        inviati dati dei visitatori né, per regola d'uso, dati personali. Anche Perplexity ha sede negli Stati Uniti e
        riceve solo le query di ricerca formulate da LiA.
      </p>

      <h2>7. Conservazione</h2>
      <ul>
        <li>Registri HTTP dell'hosting: secondo il piano Railway attivo (7 giorni con il piano Hobby, 30 con il piano Pro).</li>
        <li>
          Sessione dell'operatore: al massimo {hours} ore; viene eliminata all'uscita, alla scadenza (i residui sono
          rimossi al successivo accesso o riavvio) oppure quando l'operatore revoca tutte le sessioni.
        </li>
        <li>Tentativi di accesso: 24 ore.</li>
        <li>
          Ricerche di notizie: 90 giorni; restano più a lungo solo quelle da cui è nato un evento analizzato, finché esiste
          l'evento.
        </li>
        <li>
          Casi e analisi: finché utili alla documentazione del progetto; le copie di sicurezza del database seguono le
          rotazioni descritte nella documentazione tecnica (ultime 7 copie locali e i backup programmati dell'hosting).
        </li>
      </ul>

      <h2>8. Sintesi generate dall'intelligenza artificiale</h2>
      <p>
        Le sintesi sono testi prodotti da un modello linguistico a partire dai dati già calcolati e sono sempre indicate
        come «Testo generato da IA», con il modello usato. Possono contenere errori. Non producono decisioni che
        riguardano persone: il sito non effettua decisioni automatizzate ai sensi dell'art. 22 GDPR.
      </p>

      <h2>9. Diritti</h2>
      <p>
        Chi è interessato può chiedere al titolare accesso, rettifica, cancellazione, limitazione e opposizione al
        trattamento (artt. 15–22 GDPR) usando il contatto indicato al punto 1. Per i dati presenti solo nei registri del
        fornitore di hosting il titolare inoltra la richiesta a Railway, nei limiti di quanto il fornitore consente. È
        sempre possibile proporre reclamo al Garante per la protezione dei dati personali (
        <a href="https://www.garanteprivacy.it" rel="noopener noreferrer">garanteprivacy.it</a>) o all'autorità del
        proprio Paese di residenza.
      </p>

      <h2>10. Sicurezza</h2>
      <p>
        Il sito usa HTTPS, password conservata solo come hash Argon2id, sessioni revocabili lato server, protezione CSRF e
        limiti ai tentativi di accesso. Nessuna misura elimina del tutto i rischi.
      </p>

      <p className="muted small">
        Cookie e altre memorie del browser sono descritti nella <Link to="/cookie">cookie policy</Link>.
      </p>
    </div>
  )
}
