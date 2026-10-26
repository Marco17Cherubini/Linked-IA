import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api.js'

const PENDING = ['queued', 'running']

// Carica un'analisi per mercato e vista. Se il job (o la sintesi IA) è in corso, ripete la
// richiesta con intervallo crescente: lo stato vive nel server e sopravvive al ricaricamento.
export function useAnalysis(id, market, view) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [nonce, setNonce] = useState(0)
  const timer = useRef(null)

  const refresh = useCallback(() => {
    api.forgetAnalysis(id)
    setNonce((n) => n + 1)
  }, [id])

  useEffect(() => {
    const controller = new AbortController()
    let delay = 1500
    let cancelled = false

    const load = async () => {
      try {
        const data = await api.analysis(id, { market, view }, { signal: controller.signal })
        if (cancelled) return
        setState({ data, error: null, loading: false })
        const pending = PENDING.includes(data.status) || PENDING.includes(data.summary?.status)
        if (pending) {
          timer.current = setTimeout(load, delay)
          delay = Math.min(delay * 1.5, 10000)
        }
      } catch (error) {
        if (error.name !== 'AbortError' && !cancelled) setState((s) => ({ ...s, error, loading: false }))
      }
    }
    setState((s) => ({ ...s, loading: true, error: null }))
    load()
    return () => {
      cancelled = true
      controller.abort()
      clearTimeout(timer.current)
    }
  }, [id, market, view, nonce])

  return { ...state, refresh }
}
