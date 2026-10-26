import { Link, NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/archive', label: 'Archivio' },
  { to: '/methodology', label: 'Metodologia' },
]

export default function Layout({ meta }) {
  return (
    <>
      <a className="skip-link" href="#main">
        Vai al contenuto
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <Link to="/" className="brand" aria-label="LiA, pagina iniziale">
            <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
              <rect width="32" height="32" rx="6" fill="var(--accent)" />
              <path d="M6 22 L12 16 L17 19 L26 9" fill="none" stroke="var(--on-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="17" cy="19" r="2.6" fill="var(--event)" />
            </svg>
            <span className="brand__name">LiA</span>
            <span className="brand__tag">Linked Intelligent Analyst</span>
          </Link>
          <nav aria-label="Principale">
            <ul className="nav">
              {NAV.map((item) => (
                <li key={item.to}>
                  <NavLink to={item.to} className="nav__link">
                    {item.label}
                  </NavLink>
                </li>
              ))}
              {meta?.features?.create && (
                <li>
                  <NavLink to="/new" className="nav__link nav__link--cta">
                    Nuova analisi
                  </NavLink>
                </li>
              )}
            </ul>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="site-footer__inner">
          <p>
            LiA è uno strumento di ricerca: descrive ciò che è accaduto in casi storici selezionati e non fornisce
            previsioni né consigli di investimento.
          </p>
          <p className="muted">
            Prezzi: Yahoo Finance (endpoint pubblico). Metodo v{meta?.method_version ?? '—'} ·{' '}
            <Link to="/methodology">come funziona</Link>
          </p>
        </div>
      </footer>
    </>
  )
}
