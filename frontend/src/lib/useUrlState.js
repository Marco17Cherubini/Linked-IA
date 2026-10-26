import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

// Stato di visualizzazione conservato nell'URL: una vista si può ricaricare o condividere.
// `schema` definisce per ogni chiave il valore predefinito e (facoltativo) i valori ammessi.
export function useUrlState(schema) {
  const [params, setParams] = useSearchParams()

  const state = useMemo(() => {
    const out = {}
    for (const [key, { default: def, allowed, list }] of Object.entries(schema)) {
      const raw = params.get(key)
      if (list) {
        out[key] = raw ? raw.split(',').filter(Boolean) : def
      } else if (raw === null || (allowed && !allowed.includes(raw))) {
        out[key] = def
      } else {
        out[key] = raw
      }
    }
    return out
    // lo schema è statico per ogni pagina
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const update = useCallback(
    (changes, { replace = true } = {}) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(changes)) {
            const def = schema[key]?.default
            const isList = schema[key]?.list
            const serialized = isList ? (value || []).join(',') : value
            if (serialized === undefined || serialized === null || serialized === '' || serialized === def) next.delete(key)
            else next.set(key, serialized)
          }
          return next
        },
        { replace },
      )
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setParams],
  )

  return [state, update]
}
