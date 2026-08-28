interface Props {
  level: string  // 'low' | 'medium' | 'high'
  size?: 'sm' | 'md'
}

const CONFIG: Record<string, { label: string; dot: string; bg: string; border: string; text: string }> = {
  low:    { label: 'Low Risk',    dot: '#1D6B3E', bg: 'rgba(220,252,231,0.80)', border: 'rgba(134,239,172,0.50)', text: '#1D6B3E' },
  medium: { label: 'Med Risk',   dot: '#856305', bg: 'rgba(254,243,199,0.80)', border: 'rgba(253,211,77,0.50)',  text: '#856305' },
  high:   { label: 'High Risk',  dot: '#8B1616', bg: 'rgba(254,226,226,0.80)', border: 'rgba(252,165,165,0.50)', text: '#8B1616' },
}

export default function RiskBadge({ level, size = 'md' }: Props) {
  const cfg = CONFIG[level?.toLowerCase()] ?? CONFIG.medium
  const fontSize = size === 'sm' ? '0.625rem' : '0.6875rem'
  const dotSize  = size === 'sm' ? 5 : 6

  return (
    <span
      className="inline-flex items-center gap-1.5 font-display font-semibold"
      style={{
        padding: size === 'sm' ? '0.125rem 0.5rem' : '0.1875rem 0.625rem',
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 999,
        color: cfg.text,
        fontSize,
        letterSpacing: '0.01em',
        fontFamily: "'Outfit', sans-serif",
      }}
    >
      <span style={{ width: dotSize, height: dotSize, borderRadius: '50%', background: cfg.dot, flexShrink: 0, display: 'inline-block' }} />
      {cfg.label}
    </span>
  )
}
