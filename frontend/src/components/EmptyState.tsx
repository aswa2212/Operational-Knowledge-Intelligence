import { type LucideIcon } from 'lucide-react'

interface Props {
  icon?: LucideIcon
  title: string
  message?: string
  action?: React.ReactNode
}

export default function EmptyState({ icon: Icon, title, message, action }: Props) {
  return (
    <div className="empty-state fade-in">
      {Icon && (
        <div className="empty-state-icon">
          <Icon style={{ width: 20, height: 20 }} />
        </div>
      )}
      <div className="space-y-1">
        <p className="font-display font-semibold text-ink-700" style={{ fontSize: '0.9375rem', letterSpacing: '-0.02em' }}>
          {title}
        </p>
        {message && (
          <p className="text-ink-400 text-sm leading-relaxed max-w-xs mx-auto">{message}</p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
