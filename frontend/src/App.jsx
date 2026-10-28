import { lazy, Suspense, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { ErrorState, Skeleton } from './components/ui.jsx'
import { api } from './lib/api.js'
import { AuthProvider } from './lib/auth.jsx'
import { useApi } from './lib/useApi.js'
import HomePage from './pages/HomePage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

// Le pagine con grafici si caricano solo quando servono.
const WorkspacePage = lazy(() => import('./features/analysis/WorkspacePage.jsx'))
const ArchivePage = lazy(() => import('./pages/ArchivePage.jsx'))
const MethodologyPage = lazy(() => import('./pages/MethodologyPage.jsx'))
const NewAnalysisPage = lazy(() => import('./pages/NewAnalysisPage.jsx'))
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'))
const PrivacyPage = lazy(() => import('./pages/PrivacyPage.jsx'))
const CookiePage = lazy(() => import('./pages/CookiePage.jsx'))

function ScrollToHash() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(decodeURIComponent(hash.slice(1)))
      if (el) {
        el.scrollIntoView()
        return
      }
    }
    window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}

export default function App() {
  const meta = useApi((opts) => api.meta(opts), [])

  if (meta.error) {
    return (
      <div className="page">
        <ErrorState error={meta.error} onRetry={() => window.location.reload()} />
      </div>
    )
  }

  return (
    <AuthProvider>
      <ScrollToHash />
      <Suspense
        fallback={
          <div className="page">
            <Skeleton height={32} width="40%" />
          </div>
        }
      >
        <Routes>
          <Route element={<Layout meta={meta.data} />}>
            <Route index element={<HomePage meta={meta.data} />} />
            <Route path="analysis/:analysisId" element={meta.data ? <WorkspacePage meta={meta.data} /> : <Skeleton />} />
            <Route path="archive" element={meta.data ? <ArchivePage meta={meta.data} /> : <Skeleton />} />
            <Route path="methodology" element={<MethodologyPage meta={meta.data} />} />
            <Route path="new" element={meta.data ? <NewAnalysisPage meta={meta.data} /> : <Skeleton />} />
            <Route path="accesso" element={<LoginPage meta={meta.data} />} />
            <Route path="privacy" element={<PrivacyPage meta={meta.data} />} />
            <Route path="cookie" element={<CookiePage meta={meta.data} />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </AuthProvider>
  )
}
