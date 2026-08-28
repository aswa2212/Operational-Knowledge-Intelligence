const DECISION_CONFIG: Record<string, { bg: string; border: string; text: string; label: string }> = {
  approve:   { bg: 'rgba(220,252,231,0.80)', border: 'rgba(134,239,172,0.50)', text: '#1D6B3E', label: 'Approved'   },
  approved:  { bg: 'rgba(220,252,231,0.80)', border: 'rgba(134,239,172,0.50)', text: '#1D6B3E', label: 'Approved'   },
  deny:      { bg: 'rgba(254,226,226,0.80)', border: 'rgba(252,165,165,0.50)', text: '#8B1616', label: 'Denied'     },
  denied:    { bg: 'rgba(254,226,226,0.80)', border: 'rgba(252,165,165,0.50)', text: '#8B1616', label: 'Denied'     },
  escalate:  { bg: 'rgba(254,243,199,0.80)', border: 'rgba(253,211,77,0.50)',  text: '#856305', label: 'Escalated'  },
  escalated: { bg: 'rgba(254,243,199,0.80)', border: 'rgba(253,211,77,0.50)',  text: '#856305', label: 'Escalated'  },
  pending:   { bg: 'rgba(219,234,254,0.80)', border: 'rgba(147,197,253,0.50)', text: '#1A4D7A', label: 'Pending'    },
  rejected:  { bg: 'rgba(254,226,226,0.80)', border: 'rgba(252,165,165,0.50)', text: '#8B1616', label: 'Rejected'   },
}

interface Props {
  decision: string
  size?: 'sm' | 'md'
}

export default function DecisionBadge({ decision, size = 'md' }: Props) {
  const key = (decision ?? '').toLowerCase()
  const cfg = DECISION_CONFIG[key] ?? { bg: 'rgba(238,234,225,0.90)', border: 'rgba(212,203,191,0.70)', text: '#6A5A48', label: decision }
  const fontSize = size === 'sm' ? '0.625rem' : '0.6875rem'

  return (
    <span
      className="inline-flex items-center font-display font-semibold"
      style={{
        padding: size === 'sm' ? '0.125rem 0.5rem' : '0.1875rem 0.625rem',
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 999,
        color: cfg.text,
        fontSize,
        letterSpacing: '0.01em',
        fontFamily: "'Outfit', sans-serif",
        textTransform: 'capitalize',
      }}
    >
      {cfg.label}
    </span>
  )
}
