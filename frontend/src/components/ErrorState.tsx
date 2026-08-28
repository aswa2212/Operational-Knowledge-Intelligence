import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  error: Error
  title?: string
  onRetry?: () => void
}

export default function ErrorState({ error, title = 'Something went wrong', onRetry }: Props) {
  return (
    <div className="empty-state fade-in">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl"
        style={{ background: 'rgba(254,226,226,0.80)', border: '1px solid rgba(252,165,165,0.50)' }}>
        <AlertTriangle className="text-risk-high" style={{ width: 20, height: 20 }} />
      </div>
      <div className="space-y-1 text-center">
        <p className="font-display font-semibold text-ink-900" style={{ fontSize: '0.9375rem', letterSpacing: '-0.02em' }}>
          {title}
        </p>
        <p className="text-ink-400 text-sm max-w-xs mx-auto leading-relaxed">{error.message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary btn-sm mt-1 gap-2">
          <RefreshCw style={{ width: 12, height: 12 }} />
          Try again
        </button>
      )}
    </div>
  )
}
