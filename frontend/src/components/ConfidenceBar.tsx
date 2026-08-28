interface Props {
  value: number  // 0–1
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

function colorForValue(v: number) {
  if (v >= 0.80) return { fill: '#1D6B3E', glow: 'rgba(29,107,62,0.20)' }
  if (v >= 0.55) return { fill: '#856305', glow: 'rgba(133,99,5,0.18)' }
  return                { fill: '#8B1616', glow: 'rgba(139,22,22,0.18)' }
}

export default function ConfidenceBar({ value, size = 'md', showLabel = false }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  const { fill, glow } = colorForValue(value)
  const height = size === 'sm' ? '3px' : size === 'lg' ? '6px' : '4px'

  return (
    <div className="flex items-center gap-2 w-full">
      <div className="confidence-bar-track flex-1" style={{ height }}>
        <div
          className="confidence-bar-fill"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${fill}CC, ${fill})`,
            boxShadow: `0 0 6px ${glow}`,
          }}
        />
      </div>
      {(showLabel || size !== 'sm') && (
        <span
          className="flex-shrink-0 font-mono font-medium tabular-nums"
          style={{ fontSize: '0.6875rem', color: fill, minWidth: '2.25rem', textAlign: 'right' }}
        >
          {pct}%
        </span>
      )}
    </div>
  )
}
