import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import OutcomesPanel from '../features/analysis/OutcomesPanel.jsx'
import { KeyFigures } from '../features/analysis/panels.jsx'

// FIXTURE: struttura dell'API con valori sintetici riconoscibili.
function fixture(n) {
  const items = Array.from({ length: n }, (_, i) => ({
    event_id: `fixture-${i}`,
    title: `FIXTURE precedente ${i}`,
    occurred_on: `2010-01-${String(i + 1).padStart(2, '0')}`,
    returns: { 1: i - 2, 5: i - 2, 20: i - 2 },
  }))
  const values = items.map((it) => it.returns[5]).sort((a, b) => a - b)
  const stats = {
    n,
    values,
    median: n >= 3 ? values[Math.floor(n / 2)] : null,
    q1: n >= 5 ? values[1] : null,
    q3: n >= 5 ? values[n - 2] : null,
    min: values[0] ?? null,
    max: values[n - 1] ?? null,
    up_count: values.filter((v) => v > 0).length,
    small_sample: n < 10,
    notes: [],
  }
  return {
    base: { date: '2020-01-10', close: 100 },
    precedents: { items },
    stats: { 1: stats, 5: stats, 20: stats },
    outcomes: { returns: [{ h: 1, value: 1.5, end_date: '2020-01-13' }, { h: 5, value: -2, end_date: '2020-01-17' }, { h: 20, value: null, end_date: null }] },
  }
}

const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('OutcomesPanel', () => {
  it('etichetta i rialzi come frequenza osservata, non probabilità', () => {
    wrap(<OutcomesPanel data={fixture(5)} view="retrospective" horizon="5" eventTitle="FIXTURE evento" />)
    expect(screen.getByText('Frequenza osservata, non probabilità')).toBeInTheDocument()
    expect(screen.getByText('2 su 5')).toBeInTheDocument()
    expect(screen.queryByText(/probabilità del/i)).toBeNull()
  })

  it('con pochi casi non calcola i quartili e lo dichiara', () => {
    wrap(<OutcomesPanel data={fixture(3)} view="retrospective" horizon="5" eventTitle="E" />)
    expect(screen.getByText('Servono almeno 5 casi')).toBeInTheDocument()
  })

  it('stato esplicito senza precedenti', () => {
    wrap(<OutcomesPanel data={fixture(0)} view="retrospective" horizon="5" eventTitle="E" />)
    expect(screen.getByText('Nessun esito storico disponibile')).toBeInTheDocument()
  })

  it("in vista al cutoff non mostra l'esito dell'evento", () => {
    wrap(<OutcomesPanel data={fixture(5)} view="as_of" horizon="5" eventTitle="E" />)
    expect(screen.queryByText(/Evento analizzato:/)).toBeNull()
  })
})

describe('KeyFigures', () => {
  const market = { currency: 'USD' }
  it('nasconde gli esiti nella vista al cutoff', () => {
    wrap(<KeyFigures data={fixture(5)} view="as_of" horizon="5" market={market} />)
    expect(screen.getByText('Nascosta')).toBeInTheDocument()
    expect(screen.getByText('Nascosto')).toBeInTheDocument()
  })

  it("mostra per prima la data dell'evento, non quella della seduta base", () => {
    const data = { ...fixture(5), event_time: { occurred_on: '2020-01-11' } }
    wrap(<KeyFigures data={data} view="retrospective" horizon="5" market={market} />)
    expect(screen.getByText('Evento')).toBeInTheDocument()
    expect(screen.getByText('11 gen 2020')).toBeInTheDocument()
    expect(screen.getByText(/Riferimento: chiusura del 10 gen 2020/)).toBeInTheDocument()
  })

  it('orizzonte non ancora osservabile', () => {
    wrap(<KeyFigures data={fixture(5)} view="retrospective" horizon="20" market={market} />)
    expect(screen.getByText('Non ancora osservabile')).toBeInTheDocument()
  })
})
