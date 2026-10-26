import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GLOSSARY } from '../content/glossary.js'

const INDICATORS = ['ret_1', 'ret_5', 'vol_20', 'drawdown_60', 'zscore_20', 'range_1', 'min_after']

export default function MethodologyPage({ meta }) {
  const criteria = meta?.precedent_criteria
  const { hash } = useLocation()
  // La pagina è caricata in modo differito: l'ancora va raggiunta dopo il montaggio.
  useEffect(() => {
    if (hash) document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView()
  }, [hash])
  return (
    <div className="page prose-page">
      <header className="page-header">
        <h1>Metodologia</h1>
        <p className="page-header__lead">
          Come LiA collega un evento ai mercati, sceglie i precedenti e calcola le statistiche. Versione del metodo{' '}
          {meta?.method_version ?? '—'}.
        </p>
      </header>

      <nav className="toc" aria-label="In questa pagina">
        <ul>
          <li><a href="#evento">Evento e fonti</a></li>
          <li><a href="#base">Seduta base</a></li>
          <li><a href="#index100">Base 100 e sedute</a></li>
          <li><a href="#as_of">Vista al cutoff</a></li>
          <li><a href="#indicatori">Indicatori</a></li>
          <li><a href="#precedents">Precedenti</a></li>
          <li><a href="#median">Statistiche</a></li>
          <li><a href="#ia">Sintesi IA</a></li>
          <li><a href="#limiti">Limiti</a></li>
        </ul>
      </nav>

      <section id="evento">
        <h2>Evento e fonti</h2>
        <p>
          Un evento ha titolo, descrizione, categoria, etichette, data e, se documentato, orario con fuso e grado di
          precisione (documentato, approssimato, sconosciuto). Ogni evento cita almeno una fonte. Il catalogo iniziale
          usa voci di Wikipedia e comunicati ufficiali verificati alla data indicata: sono fonti di consultazione, non
          notizie originali dell'epoca.
        </p>
      </section>

      <section id="base">
        <h2>{GLOSSARY.base.term}</h2>
        <p>{GLOSSARY.base.text}</p>
        <p>
          Ogni mercato ha fuso e orario di chiusura propri (per esempio New York 16:00, Francoforte 17:30, Tokyo 15:00 e
          15:30 dal 5 novembre 2024). Un evento alle 22:00 di New York cade a Tokyo il giorno dopo, prima della chiusura:
          la seduta base può quindi essere diversa da un indice all'altro. Le chiusure anticipate non sono modellate.
        </p>
        <p>
          Con orario sconosciuto si usa una convenzione prudente: la seduta base non contiene mai la reazione all'evento,
          ma la prima seduta successiva può includere movimenti precedenti all'evento. Se il mercato è rimasto chiuso
          (per esempio dopo l'11 settembre 2001), l'analisi lo segnala.
        </p>
      </section>

      <section id="index100">
        <h2>{GLOSSARY.index100.term} e sedute</h2>
        <p>{GLOSSARY.index100.text}</p>
        <p id="sessions">{GLOSSARY.sessions.text}</p>
        <p id="horizon">{GLOSSARY.horizon.text} Orizzonti disponibili: {meta?.horizons?.join(', ')} sedute.</p>
      </section>

      <section id="as_of">
        <h2>{GLOSSARY.as_of.term}</h2>
        <p>
          {GLOSSARY.as_of.text} Il server separa sempre i dati osservati fino alla seduta base dagli esiti successivi; in
          vista al cutoff questi ultimi non vengono nemmeno trasmessi al browser.
        </p>
      </section>

      <section id="indicatori">
        <h2>Indicatori</h2>
        <p>Gli indicatori al cutoff usano solo sedute fino alla seduta base inclusa.</p>
        <dl className="definition-list">
          {INDICATORS.map((id) => (
            <div key={id} id={id}>
              <dt>{GLOSSARY[id].term}</dt>
              <dd>{GLOSSARY[id].text}</dd>
            </div>
          ))}
        </dl>
        <p>
          Se le sedute disponibili non bastano, l'indicatore resta vuoto con il motivo: un dato mancante non viene mai
          sostituito con zero.
        </p>
      </section>

      <section id="precedents">
        <h2>Selezione dei precedenti</h2>
        <p>{criteria?.description}</p>
        <ul>
          <li>Pertinenza: stessa categoria, oppure almeno {criteria?.min_shared_tags} etichette in comune.</li>
          <li>
            Punteggio: {criteria?.category_weight} × stessa categoria + {criteria?.tags_weight} × indice di Jaccard delle
            etichette (etichette comuni / etichette totali).
          </li>
          <li>Al massimo {criteria?.max_precedents} precedenti, i più pertinenti; a parità di punteggio il più recente.</li>
          <li>
            Cutoff: un precedente entra solo se la sua seduta +20 è anteriore o uguale alla seduta base dell'evento
            analizzato, nello stesso mercato.
          </li>
        </ul>
        <p>
          La selezione dipende dal catalogo disponibile: con pochi eventi simili il campione è piccolo, e l'interfaccia
          lo dichiara.
        </p>
      </section>

      <section id="median">
        <h2>Statistiche del campione</h2>
        <p>{GLOSSARY.median.text}</p>
        <p id="observed_frequency">{GLOSSARY.observed_frequency.text}</p>
        <p>
          Con meno di 12 casi il grafico degli esiti mostra i singoli precedenti; oltre, un istogramma. Non si
          disegnano bande di variabilità come se fossero intervalli di previsione.
        </p>
      </section>

      <section id="ia">
        <h2>Sintesi IA</h2>
        <p>
          La sintesi testuale è facoltativa e a pagamento: parte solo su richiesta esplicita di un analista autorizzato,
          viene salvata e non si rigenera consultando o filtrando l'analisi. Il modello riceve soltanto i dati
          strutturati dell'analisi e deve rispondere con uno schema fisso (titolo, osservazioni, interpretazione,
          limiti), validato prima del salvataggio. Le istruzioni vietano di presentare frequenze come probabilità.
        </p>
      </section>

      <section id="limiti">
        <h2>Limiti</h2>
        <ul>
          <li>Il campione di precedenti è piccolo e scelto da un catalogo curato: non è rappresentativo di tutti gli eventi.</li>
          <li>Un evento non è l'unica causa dei movimenti di mercato osservati nello stesso periodo.</li>
          <li>
            I prezzi provengono dall'endpoint pubblico di Yahoo Finance, non ufficiale: possono contenere errori o lacune,
            che vengono segnalati e mai sostituiti.
          </li>
          <li>Gli orari approssimati possono spostare la seduta base quando l'evento è vicino a una chiusura.</li>
        </ul>
        <p>
          <Link to="/archive">Torna all'archivio</Link>
        </p>
      </section>
    </div>
  )
}
