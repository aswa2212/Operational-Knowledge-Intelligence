import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type AuditEvent } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import {
  Zap, Clock, User, CheckCircle2, XCircle, ArrowRight, ExternalLink,
  Github, MessageSquare, CreditCard, ShieldCheck, Filter, Search, Terminal,
  AlertTriangle, FileText,
} from 'lucide-react'

interface ActionItem extends AuditEvent {
  parsedPayload: Record<string, any>
  toolName: string
  isSuccess: boolean
}

export default function Actions() {
  const [toolFilter, setToolFilter] = useState('all')
  const [search, setSearch] = useState('')

  const { data: actions = [], isLoading, error, refetch } = useQuery({
    queryKey: ['actions'],
    queryFn: () => api.actions.list(100),
    refetchInterval: 2_000,
  })

  if (error) return <ErrorState error={error as Error} title="Could not load execution actions" onRetry={refetch} />

  // Enrich parsed action payload
  const parsedActions: ActionItem[] = actions.map((a: AuditEvent) => {
    let payload: Record<string, any> = a.payload || {}
    if ((!payload || Object.keys(payload).length === 0) && a.payload_json) {
      try { payload = JSON.parse(a.payload_json) } catch { payload = {} }
    }
    const toolName: string = String(payload.tool_name || 'unknown_tool')
    const isSuccess: boolean = a.event_type === 'action_executed' && !payload.error
    return { ...a, parsedPayload: payload, toolName, isSuccess }
  })

  const filtered = parsedActions.filter(a => {
    if (toolFilter !== 'all') {
      if (toolFilter === 'github' && !a.toolName.includes('github')) return false
      if (toolFilter === 'slack' && !a.toolName.includes('slack')) return false
      if (toolFilter === 'payment' && !a.toolName.includes('payment') && !a.toolName.includes('refund')) return false
      if (toolFilter === 'notion' && !a.toolName.includes('notion')) return false
    }
    if (search) {
      const q = search.toLowerCase()
      const text = `${a.id} ${a.toolName} ${a.actor} ${JSON.stringify(a.parsedPayload)}`.toLowerCase()
      if (!text.includes(q)) return false
    }
    return true
  })

  const totalExecutions = parsedActions.length
  const githubCount = parsedActions.filter(a => a.toolName.includes('github')).length
  const slackCount = parsedActions.filter(a => a.toolName.includes('slack')).length
  const paymentCount = parsedActions.filter(a => a.toolName.includes('refund') || a.toolName.includes('payment')).length

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <Zap style={{ width: 22, height: 22, color: '#D9641E' }} />
            Execution Arm
          </h1>
          <p className="page-subtitle">
            Live external tool executions & bounded autonomous actions (GitHub Issues, Slack Alerts, Mock Payments).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge badge-green font-mono" style={{ padding: '0.25rem 0.75rem' }}>
            <ShieldCheck style={{ width: 13, height: 13, marginRight: 4 }} />
            Active Bounded Agent
          </span>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <span className="stat-label">Total Executions</span>
            <Zap style={{ width: 14, height: 14, color: '#D9641E' }} />
          </div>
          <div className="stat-value">{totalExecutions}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <span className="stat-label">GitHub Actions</span>
            <Github style={{ width: 14, height: 14, color: '#6A5A48' }} />
          </div>
          <div className="stat-value">{githubCount}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <span className="stat-label">Slack Notifications</span>
            <MessageSquare style={{ width: 14, height: 14, color: '#D4A017' }} />
          </div>
          <div className="stat-value">{slackCount}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <span className="stat-label">Payment Diffs</span>
            <CreditCard style={{ width: 14, height: 14, color: '#1D6B3E' }} />
          </div>
          <div className="stat-value" style={{ color: '#1D6B3E' }}>{paymentCount}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-300" />
          <input
            className="input pl-9 py-1.5 text-xs"
            placeholder="Search executions by tool, case ID, or payload..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-ink-400" />
          <select
            className="select text-xs py-1.5 w-44"
            value={toolFilter}
            onChange={e => setToolFilter(e.target.value)}
          >
            <option value="all">All Tools ({totalExecutions})</option>
            <option value="github">GitHub Issues ({githubCount})</option>
            <option value="slack">Slack Alerts ({slackCount})</option>
            <option value="payment">Payment Mocks ({paymentCount})</option>
          </select>
        </div>
      </div>

      {/* Executions List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="skeleton h-24 rounded-2xl" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Zap}
            title="No actions executed yet"
            message="When OKI makes autonomous decisions or when approvals are confirmed, live external actions appear here with state diffs."
          />
        ) : (
          filtered.map(a => {
            const p = a.parsedPayload
            const beforeState = p.before_state || {}
            const afterState = p.after_state || {}
            const isGithub = a.toolName.includes('github')
            const isSlack = a.toolName.includes('slack')
            const isRefund = a.toolName.includes('refund') || a.toolName.includes('payment')
            const isNotion = a.toolName.includes('notion')
            const externalUrl = p.result?.url || p.result?.label_url
            const payloadMessage = p.args?.message || p.args?.body

            return (
              <div key={a.id} className="card p-5 hover:border-ink-300 transition-all space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      isGithub ? 'bg-slate-900 text-white' :
                      isSlack ? 'bg-purple-600 text-white' :
                      isNotion ? 'bg-stone-800 text-white' :
                      'bg-emerald-600 text-white'
                    }`}>
                      {isGithub ? <Github className="w-5 h-5" /> :
                       isSlack ? <MessageSquare className="w-5 h-5" /> :
                       isNotion ? <FileText className="w-5 h-5" /> :
                       <CreditCard className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-ink-800 font-mono">
                          {a.toolName}
                        </span>
                        <span className={`badge text-2xs ${a.isSuccess ? 'badge-green' : 'badge-red'}`}>
                          {a.isSuccess ? (
                            <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> EXECUTED</span>
                          ) : (
                            <span className="flex items-center gap-1"><XCircle className="w-3 h-3" /> FAILED</span>
                          )}
                        </span>
                        {p.approval_id && (
                          <span className="badge badge-amber text-2xs">Human Approved (#{String(p.approval_id)})</span>
                        )}
                      </div>
                      <div className="text-xs text-ink-400 mt-0.5 flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" /> Actor: <strong className="text-ink-600">{String(a.actor || 'system_agent')}</strong>
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {new Date(a.created_at).toLocaleString()}
                        </span>
                        <span>•</span>
                        <span>Event <strong className="font-mono text-ink-600">#{a.id}</strong></span>
                      </div>
                    </div>
                  </div>

                  {externalUrl && (
                    <a
                      href={String(externalUrl)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary btn-sm flex items-center gap-1.5 text-xs text-terra-600 hover:text-terra-700"
                    >
                      <span>View on {isGithub ? 'GitHub' : isSlack ? 'Slack' : 'External'}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>

                {/* Error Banner if action failed */}
                {p.error && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-800 flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-red-900">Execution Error:</div>
                      <div className="font-mono text-2xs mt-0.5 whitespace-pre-wrap">{String(p.error)}</div>
                    </div>
                  </div>
                )}

                {/* State Diff / Payload Box */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  {/* Before State */}
                  <div className="bg-canvas-warm/70 border border-canvas-border rounded-xl p-3 text-xs">
                    <div className="text-2xs font-semibold uppercase tracking-wider text-ink-400 mb-1">
                      Before State
                    </div>
                    {isRefund ? (
                      <div className="flex items-center justify-between font-mono">
                        <span className="text-ink-500">Refund Status:</span>
                        <span className="badge badge-gray text-2xs">{String(beforeState.refund_status || 'PENDING')}</span>
                      </div>
                    ) : isSlack ? (
                      <div className="text-2xs text-ink-500 space-y-1">
                        <div>Channel: <code className="text-ink-700">{String(p.args?.channel || '#ops-alerts')}</code></div>
                        <div>Status: <span className="badge badge-gray text-2xs">UNNOTIFIED</span></div>
                      </div>
                    ) : (
                      <pre className="text-ink-600 font-mono text-2xs overflow-x-auto">
                        {JSON.stringify(beforeState, null, 2)}
                      </pre>
                    )}
                  </div>

                  {/* After State */}
                  <div className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-3 text-xs">
                    <div className="text-2xs font-semibold uppercase tracking-wider text-emerald-800 mb-1 flex items-center gap-1">
                      <ArrowRight className="w-3 h-3 text-emerald-600" /> After State (Live Change)
                    </div>
                    {isRefund ? (
                      <div className="space-y-1 font-mono">
                        <div className="flex items-center justify-between">
                          <span className="text-emerald-700">Refund Status:</span>
                          <span className="badge badge-green text-2xs font-bold">{String(p.result?.after_state || 'REFUNDED')}</span>
                        </div>
                        {p.result?.refund_id && (
                          <div className="flex items-center justify-between text-2xs text-emerald-600">
                            <span>Tx ID:</span>
                            <span>{String(p.result.refund_id)}</span>
                          </div>
                        )}
                      </div>
                    ) : isSlack ? (
                      <div className="text-2xs text-emerald-800 space-y-1">
                        <div className="flex items-center justify-between">
                          <span>Slack Status:</span>
                          <span className="badge badge-green text-2xs">POSTED LIVE</span>
                        </div>
                        {p.result?.ts && (
                          <div className="text-2xs text-emerald-600 font-mono">
                            Message TS: {String(p.result.ts)}
                          </div>
                        )}
                      </div>
                    ) : (
                      <pre className="text-emerald-900 font-mono text-2xs overflow-x-auto">
                        {JSON.stringify(p.result || afterState, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>

                {/* Execution Args / Body preview */}
                {payloadMessage && (
                  <div className="bg-canvas-warm rounded-xl p-3 border border-canvas-border text-xs">
                    <div className="text-2xs font-semibold uppercase tracking-wider text-ink-400 mb-1 flex items-center gap-1">
                      <Terminal className="w-3 h-3" /> Executed Payload Message
                    </div>
                    <p className="text-ink-700 font-mono whitespace-pre-wrap text-2xs bg-white/60 p-2.5 rounded-lg border border-canvas-border">
                      {String(payloadMessage)}
                    </p>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
