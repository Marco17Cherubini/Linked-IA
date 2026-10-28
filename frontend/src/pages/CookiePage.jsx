import { Link } from 'react-router-dom'
import { Controller, POLICY_UPDATED } from './PrivacyPage.jsx'

export default function CookiePage({ meta }) {
  const legal = meta?.legal
  const hours = legal?.session_hours ?? 8
  const owner = legal?.controller_name || 'Titolare del sito (prima parte)'
  return (
    <div className="page prose-page legal">
      <header className="page-header">
        <h1>Cookie policy</h1>
        <p className="page-header__lead">Cookie e altre memorie del browser usati da LiA. Aggiornata al {POLICY_UPDATED}.</p>
      </header>

      <Controller legal={legal} />

      <h2>In breve</h2>
      <p>
        I visitatori non ricevono alcun cookie. Un solo cookie tecnico viene impostato quando l'operatore accede all'area
        riservata. Non ci sono cookie di terze parti, di analisi statistica, di profilazione o pubblicitari, né pixel o
        altri strumenti di tracciamento. Per questo il sito non mostra un banner di consenso: i cookie tecnici
        strettamente necessari non lo richiedono (art. 122 del Codice privacy e Linee guida del Garante sui cookie del 10
        giugno 2021).
      </p>

      <h2>Cookie</h2>
      <div className="table-scroll">
        <table className="legal-table">
          <thead>
            <tr>
              <th scope="col">Nome</th>
              <th scope="col">Finalità</th>
              <th scope="col">Categoria</th>
              <th scope="col">Durata</th>
              <th scope="col">Gestito da</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>__Host-lia_session</code>
              </td>
              <td>Mantiene l'accesso dell'operatore alle funzioni riservate. Attributi Secure, HttpOnly, SameSite=Strict.</td>
              <td>Tecnico, strettamente necessario</td>
              <td>Fino a {hours} ore, o fino all'uscita</td>
              <td>{owner}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2>Altre memorie del browser</h2>
      <div className="table-scroll">
        <table className="legal-table">
          <thead>
            <tr>
              <th scope="col">Memoria</th>
              <th scope="col">Uso</th>
              <th scope="col">Durata</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>localStorage, sessionStorage, IndexedDB</td>
              <td>Non usati.</td>
              <td>—</td>
            </tr>
            <tr>
              <td>Memoria della pagina (JavaScript)</td>
              <td>
                Token anti-falsificazione della sessione dell'operatore e copia temporanea delle analisi già aperte, per non
                ripetere le richieste.
              </td>
              <td>Fino alla chiusura o al ricaricamento della scheda</td>
            </tr>
            <tr>
              <td>Cache HTTP del browser</td>
              <td>File statici del sito (script e fogli di stile con nome versionato).</td>
              <td>Gestita dal browser, al massimo un anno</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2>Come gestirli</h2>
      <p>
        Il cookie di sessione si cancella con il pulsante «Esci» o dalle impostazioni del browser. Bloccarlo impedisce solo
        l'accesso all'area riservata: la consultazione dei casi resta possibile.
      </p>
      <p className="muted small">
        Per gli altri trattamenti vedi l'<Link to="/privacy">informativa privacy</Link>.
      </p>
    </div>
  )
}
