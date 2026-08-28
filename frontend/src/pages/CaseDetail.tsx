import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import ErrorState from '../components/ErrorState'
import {
  ArrowLeft, FileText, Brain, CheckCircle2, AlertTriangle, Clock,
  Hash, ChevronRight,
} from 'lucide-react'

function timeStr(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

interface TimelineStep {
  icon: React.ReactNode
  label: string
  sub?: string
  done: boolean
  extra?: React.ReactNode
}

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const caseId = parseInt(id ?? '0', 10)

  const { data: c, isLoading, error, refetch } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => api.cases.get(caseId),
    enabled: caseId > 0,
  })

  if (isLoading) {
    return (
      <div className="space-y-6 fade-in-up">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton h-64 w-full" />
        <div className="skeleton h-48 w-full" />
      </div>
    )
  }

  if (error || !c) {
    return <ErrorState error={error as Error} title="Case not found" onRetry={refetch} />
  }

  const payload = (() => {
    try { return JSON.parse(c.payload_json) } catch { return {} }
  })()

  const decision = c.decision
  const trace = decision?.trace ?? (() => {
    try { return JSON.parse(decision?.trace_json ?? '{}') } catch { return {} }
  })()

  const isEscalated = Boolean(decision?.escalated)
  const decisionLabel = isEscalated ? 'Escalated' : decision ? 'Auto-Executed' : 'Pending'
  const decisionIcon = isEscalated
    ? <AlertTriangle style={{ width: 15, height: 15, color: '#856305' }} />
    : decision
    ? <CheckCircle2 style={{ width: 15, height: 15, color: '#1D6B3E' }} />
    : <Clock style={{ width: 15, height: 15, color: '#1A4D7A' }} />

  const steps: TimelineStep[] = [
    {
      icon: <FileText style={{ width: 15, height: 15, color: '#A0917F' }} />,
      label: 'Case submitted',
      sub: `Process: ${c.process.replace(/_/g, ' ')} · Source: ${c.source ?? 'api'}`,
      done: true,
      extra: (
        <div className="mt-2 bg-canvas-warm/60 rounded-xl border border-canvas-border p-3.5">
          <div className="label mb-1.5">Fields</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {Object.entries(payload).map(([k, v]) => (
              <div key={k} className="flex gap-2 text-xs">
                <span className="text-ink-400 capitalize">{k.replace(/_/g, ' ')}:</span>
                <span className="text-ink-800 font-medium">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      icon: <Brain style={{ width: 15, height: 15, color: '#D9641E' }} />,
      label: 'Rules matched & decision made',
      sub: decision
        ? `Rule #${decision.matched_rule_id ?? '—'} matched · ${new Date(decision.created_at).toLocaleString()}`
        : 'No decision yet',
      done: !!decision,
      extra: decision ? (
        <div className="mt-2 space-y-2">
          <div className="bg-canvas-warm/60 rounded-xl border border-canvas-border p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="label">Decision</span>
              <span className="font-display font-semibold text-ink-900 text-sm">{decision.decision || '—'}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="label">Confidence</span>
              <div style={{ width: 160 }}><ConfidenceBar value={decision.confidence} showLabel /></div>
            </div>
            <div className="flex items-center justify-between">
              <span className="label">Risk Level</span>
              <RiskBadge level={decision.risk_level} />
            </div>
            {decision.reason && (
              <div>
                <div className="label mb-0.5">Reason</div>
                <div className="text-xs text-ink-600 leading-relaxed">{decision.reason}</div>
              </div>
            )}
          </div>
        </div>
      ) : null,
    },
    {
      icon: decisionIcon,
      label: decisionLabel,
      sub: isEscalated ? 'Routed to human approval queue' : decision ? 'Action executed automatically via bounded execution agent' : 'Waiting for decision',
      done: !!decision,
      extra: decision && !isEscalated ? (
        <div className="mt-2 rounded-xl p-3.5 text-xs space-y-1.5 border" style={{
          background: 'rgba(220,252,231,0.60)', border: '1px solid rgba(134,239,172,0.50)', color: '#1D6B3E'
        }}>
          <div className="flex items-center justify-between">
            <span className="font-semibold flex items-center gap-1.5">
              <CheckCircle2 style={{ width: 13, height: 13 }} />
              Autonomous Action Executed Live
            </span>
            <Link to="/actions" className="text-2xs font-semibold hover:underline" style={{ color: '#D9641E' }}>
              View Action Ledger →
            </Link>
          </div>
          <div className="text-2xs text-ink-700">
            Action for decision <strong>"{decision.decision}"</strong> was executed and committed to the audit ledger.
          </div>
        </div>
      ) : null,
    },
  ]

  const hasTrace = trace && Object.keys(trace).length > 0

  return (
    <div className="space-y-6 fade-in-up max-w-4xl">
      {/* Back */}
      <Link to="/cases" className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-700 transition-colors font-medium">
        <ArrowLeft style={{ width: 14, height: 14 }} />
        Back to Cases
      </Link>

      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Hash style={{ width: 14, height: 14, color: '#A0917F' }} />
            <span className="font-mono text-ink-400 text-sm font-semibold">{c.id}</span>
            <ChevronRight style={{ width: 13, height: 13, color: '#C2B8A8' }} />
            <span className="badge badge-gray capitalize">
              {c.process.replace(/_/g, ' ')}
            </span>
          </div>
          <h1 className="page-title">Case Detail</h1>
          <p className="page-subtitle">Submitted {timeStr(c.created_at)}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 mt-1">
          {decision?.risk_level && <RiskBadge level={decision.risk_level} />}
          <span className={`badge ${
            isEscalated ? 'badge-escalated' : decision ? 'badge-auto' : 'badge-pending'
          }`}>
            {decisionLabel}
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="card p-6">
        <h2 className="section-title mb-5">Case Timeline</h2>
        <div className="space-y-6">
          {steps.map((step, idx) => (
            <div key={idx} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  step.done ? 'bg-canvas-warm border border-canvas-border' : 'bg-canvas-muted'
                }`}>
                  {step.icon}
                </div>
                {idx < steps.length - 1 && (
                  <div className={`w-px flex-1 mt-2 ${step.done ? 'bg-canvas-border' : 'bg-canvas-muted'}`} />
                )}
              </div>
              <div className="flex-1 pb-6">
                <div className="flex items-center gap-2">
                  <span className={`font-display text-sm font-semibold ${step.done ? 'text-ink-800' : 'text-ink-400'}`}>
                    {step.label}
                  </span>
                  {!step.done && <span className="badge badge-pending text-2xs">Waiting</span>}
                </div>
                {step.sub && <div className="text-xs text-ink-400 mt-0.5">{step.sub}</div>}
                {step.extra}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Decision trace */}
      {hasTrace && (
        <div className="card overflow-hidden">
          <div className="px-6 py-4 border-b border-canvas-border">
            <h2 className="section-title">Resolver Trace</h2>
          </div>
          <div className="p-5">
            <pre className="text-xs text-ink-700 font-mono overflow-x-auto bg-canvas-warm/50 rounded-xl p-4 border border-canvas-border leading-relaxed">
              {JSON.stringify(trace, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Escalation link */}
      {isEscalated && (
        <div className="card-gold p-5">
          <div className="flex items-center gap-3">
            <AlertTriangle style={{ width: 18, height: 18, color: '#856305', flexShrink: 0 }} />
            <div className="flex-1">
              <div className="font-display text-sm font-semibold text-ink-900">Escalated for human review</div>
              <div className="text-xs text-ink-600 mt-0.5">{decision?.reason ?? 'Routed to approval queue'}</div>
            </div>
            <Link to="/approvals" className="btn-gold btn-sm">
              View Approvals →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
