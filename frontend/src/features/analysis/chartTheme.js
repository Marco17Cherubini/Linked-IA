// Colori e stili condivisi dai grafici: usano i token CSS, quindi seguono anche il tema scuro.

export const SERIES_COLORS = [
  'var(--series-1)',
  'var(--series-2)',
  'var(--series-3)',
  'var(--series-4)',
  'var(--series-5)',
  'var(--series-6)',
]

export const AXIS_PROPS = {
  stroke: 'var(--border-strong)',
  tick: { fill: 'var(--text-3)', fontSize: 12 },
  tickLine: { stroke: 'var(--border-strong)' },
}

export const GRID_PROPS = { stroke: 'var(--grid)', strokeDasharray: '0', vertical: false }

export const REDUCED_MOTION =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Animazioni brevi solo per chiarire i cambi di dati; disattivate con movimento ridotto.
export const ANIMATION = { isAnimationActive: !REDUCED_MOTION, animationDuration: 250 }

export function colorFor(index) {
  return SERIES_COLORS[index % SERIES_COLORS.length]
}
