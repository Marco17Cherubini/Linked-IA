import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, setCsrfToken } from './api.js'

// Stato della sessione dell'operatore. È solo un'indicazione per l'interfaccia: ogni
// operazione riservata viene autorizzata dal server, che rifiuta le richieste senza sessione.
const AuthContext = createContext({ status: 'loading', authenticated: false })

export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: 'loading', authenticated: false, expiresAt: null })

  const apply = useCallback((data) => {
    setCsrfToken(data?.authenticated ? data.csrf_token : '')
    setState({ status: 'ready', authenticated: Boolean(data?.authenticated), expiresAt: data?.expires_at ?? null })
  }, [])

  const refresh = useCallback(async () => {
    try {
      apply(await api.session())
    } catch {
      apply(null)
    }
  }, [apply])

  useEffect(() => {
    refresh()
  }, [refresh])

  const login = useCallback(
    async (password) => {
      apply(await api.login(password))
      api.forgetAll()
    },
    [apply],
  )

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      apply(null)
      api.forgetAll()
    }
  }, [apply])

  // Una risposta 401 indica che la sessione è scaduta o revocata sul server.
  const expired = useCallback(() => apply(null), [apply])

  return <AuthContext.Provider value={{ ...state, login, logout, refresh, expired }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
