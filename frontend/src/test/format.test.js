import { describe, expect, it } from 'vitest'
import { formatEventTime, formatPct, formatValue, MISSING } from '../lib/format.js'
import { histogramBins, niceScale } from '../features/analysis/OutcomesPanel.jsx'
import { buildPayload, slugify } from '../pages/NewAnalysisPage.jsx'

describe('formattazione', () => {
  it('rendimenti con segno esplicito e mancanti come trattino', () => {
    expect(formatPct(1.4957)).toBe('+1,50%')
    expect(formatPct(-3.959)).toBe('−3,96%')
    expect(formatPct(0)).toBe('0,00%')
    expect(formatPct(null)).toBe(MISSING)
    expect(formatPct(undefined)).toBe(MISSING)
  })

  it('unità degli indicatori', () => {
    expect(formatValue(22.73, '% annua')).toBe('22,7% annuo')
    expect(formatValue(-2.235, 'σ')).toBe('−2,24 σ')
    expect(formatValue(null, '%')).toBe(MISSING)
  })

  it("orario dell'evento con fuso esplicito", () => {
    expect(formatEventTime('2022-02-24T05:00:00+02:00')).toBe('05:00 (UTC+2)')
    expect(formatEventTime('2001-09-11T08:46:00-04:00')).toBe('08:46 (UTC-4)')
    expect(formatEventTime(null)).toBeNull()
  })
})

describe('scale dei grafici', () => {
  it('scala con passo tondo che include gli estremi', () => {
    const { domain, ticks } = niceScale(-17.47, 8.01)
    expect(domain[0]).toBeLessThanOrEqual(-17.47)
    expect(domain[1]).toBeGreaterThanOrEqual(8.01)
    expect(ticks).toContain(0)
    const steps = new Set(ticks.slice(1).map((t, i) => +(t - ticks[i]).toFixed(6)))
    expect(steps.size).toBe(1)
  })

  it('istogramma: ogni valore in una sola classe', () => {
    const values = [-5, -1, 0, 0.5, 2, 3, 3.5, 4, 8, 9, 10, 12]
    const bins = histogramBins(values)
    expect(bins.reduce((n, b) => n + b.count, 0)).toBe(values.length)
  })
})

describe('creazione evento', () => {
  it('identificativo leggibile e stabile', () => {
    expect(slugify("La BNS abbandona il cambio minimo con l'euro", '2015-01-15')).toBe(
      'la-bns-abbandona-il-cambio-minimo-con-l-euro-2015',
    )
  })

  it('senza orario la precisione è sconosciuta e occurred_at assente', () => {
    const payload = buildPayload({
      title: 'Evento',
      description: 'D',
      category: 'trade',
      tags: 'Tariffs, United States',
      date: '2020-01-02',
      time: '',
      offset: '+01:00',
      precision: 'exact',
      sources: [{ url: ' https://example.org ', publisher: '', title: '', kind: 'news' }, { url: '', publisher: '', title: '', kind: 'news' }],
    })
    expect(payload.time_precision).toBe('unknown')
    expect(payload.occurred_at).toBeNull()
    expect(payload.tags).toEqual(['tariffs', 'united-states'])
    expect(payload.sources).toHaveLength(1)
    expect(payload.sources[0].url).toBe('https://example.org')
  })

  it('con orario include il fuso', () => {
    const payload = buildPayload({
      title: 'E', description: 'D', category: 'trade', tags: '', date: '2015-01-15', time: '10:30',
      offset: '+01:00', precision: 'approximate', sources: [],
    })
    expect(payload.occurred_at).toBe('2015-01-15T10:30:00+01:00')
    expect(payload.time_precision).toBe('approximate')
  })
})
