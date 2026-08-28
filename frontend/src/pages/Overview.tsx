import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, type Case, type Source } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import {
  Brain, Play, CheckCircle, Zap,
  RefreshCw, Github, FileText, Hash, ArrowUpRight,
  TrendingUp, Activity, ShieldCheck,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function sourceIcon(type: string) {
  if (type === 'github')    return <Github style={{ width: 14, height: 14 }} />
  if (type === 'notion')    return <FileText style={{ width: 14, height: 14 }} />
  if (type === 'slack')     return <Hash style={{ width: 14, height: 14 }} />
  return <RefreshCw style={{ width: 14, height: 14 }} />
}

function decisionState(c: Case): 'auto' | 'escalated' | 'pending' {
  if (!c.decision) return 'pending'
  return c.decision.escalated ? 'escalated' : 'auto'
}

const STATE_BADGE: Record<string, { bg: string; border: string; text: string; label: string }> = {
  auto:      { bg: 'rgba(220,252,231,0.80)', border: 'rgba(134,239,172,0.50)', text: '#1D6B3E', label: 'Auto-Executed' },
  escalated: { bg: 'rgba(254,243,199,0.80)', border: 'rgba(253,211,77,0.50)',  text: '#856305', label: 'Escalated'     },
  pending:   { bg: 'rgba(219,234,254,0.80)', border: 'rgba(147,197,253,0.50)', text: '#1A4D7A', label: 'Pending'       },
}

function StateBadge({ state }: { state: 'auto' | 'escalated' | 'pending' }) {
  const cfg = STATE_BADGE[state]
  return (
    <span className="inline-flex items-center font-display font-semibold"
      style={{ padding: '0.125rem 0.5rem', background: cfg.bg, border: `1px solid ${cfg.border}`,
               borderRadius: 999, color: cfg.text, fontSize: '0.625rem', letterSpacing: '0.01em', fontFamily: "'Outfit', sans-serif" }}>
      {cfg.label}
    </span>
  )
}

function ProcessLabel({ process }: { process: string }) {
  return (
    <span className="inline-flex items-center font-display font-medium"
      style={{ padding: '0.125rem 0.5625rem', background: 'rgba(238,234,225,0.90)', border: '1px solid rgba(212,203,191,0.65)',
               borderRadius: 999, color: '#6A5A48', fontSize: '0.625rem', letterSpacing: '0.02em', fontFamily: "'Outfit', sans-serif" }}>
      {process.replace(/_/g, ' ')}
    </span>
  )
}

export default function Overview() {
  const {
    data: cases = [],
    isLoading: casesLoading,
    error: casesError,
    refetch: refetchCases,
  } = useQuery({
    queryKey: ['cases', 'overview'],
    queryFn: () => api.cases.list({ limit: 50 }),
    refetchInterval: 60_000,
  })

  const { data: sources = [], isLoading: sourcesLoading } = useQuery({
    queryKey: ['sources'],
    queryFn: api.sources.list,
    refetchInterval: 60_000,
  })

  const { data: pendingApprovals = [] } = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: () => api.approvals.list('pending'),
    refetchInterval: 30_000,
  })

  // Derived stats
  const today = new Date().toDateString()
  const casesToday = cases.filter((c) => new Date(c.created_at).toDateString() === today)
  const autoToday = casesToday.filter((c) => c.decision && !c.decision.escalated).length
  const escalatedToday = casesToday.filter((c) => c.decision?.escalated).length
  const avgConfidence = cases.length
    ? Math.round(cases.filter(c => c.decision).reduce((s, c) => s + (c.decision!.confidence ?? 0), 0) / cases.filter(c => c.decision).length * 100)
    : 0

  const recentCases = cases.slice(0, 10)

  const chartData = cases
    .filter((c) => c.decision)
    .slice(0, 30)
    .reverse()
    .map((c, i) => ({
      i: i + 1,
      confidence: Math.round((c.decision!.confidence ?? 0) * 100),
    }))

  const connectorTypes = ['github', 'notion', 'slack', 'synthetic']
  const connectorStatus = connectorTypes.map((type) => {
    const src = sources.filter((s: Source) => s.type === type)
    return { type, count: src.length, active: src.filter((s: Source) => s.enabled).length }
  })

  if (casesError) {
    return <ErrorState error={casesError as Error} title="Could not load dashboard" onRetry={refetchCases} />
  }

  return (
    <div className="space-y-8 fade-in-up">

      {/* ── Hero strip ────────────────────────────────────────────────── */}
      <div className="hero-strip px-8 py-7 flex items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #302820 0%, #1A150F 100%)', boxShadow: '0 4px 12px rgba(26,21,15,0.20)' }}>
              <Brain style={{ width: 18, height: 18, color: '#FAF8F4' }} />
            </div>
            <h1 className="page-title">Operational Overview</h1>
          </div>
          <p className="page-subtitle">
            Live decisions, active connectors, and system confidence at a glance.
          </p>
        </div>
        <button onClick={() => refetchCases()} className="btn-secondary btn-sm gap-1.5 flex-shrink-0">
          <RefreshCw style={{ width: 12, height: 12 }} />
          Refresh
        </button>
      </div>

      {/* ── Stat cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">

        {/* Total Cases */}
        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(238,234,225,0.80)', border: '1px solid rgba(212,203,191,0.55)' }}>
              <Play style={{ width: 12, height: 12, color: '#6A5A48' }} />
            </div>
            <ArrowUpRight style={{ width: 13, height: 13, color: '#C2B8A8' }} />
          </div>
          {casesLoading ? <div className="skeleton h-9 w-16 mb-0.5" /> : <div className="stat-value">{cases.length}</div>}
          <div className="stat-label">Total Cases</div>
          <div className="stat-trend mt-1">{casesToday.length} today</div>
        </div>

        {/* Pending Approvals */}
        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(254,243,199,0.80)', border: '1px solid rgba(253,211,77,0.40)' }}>
              <CheckCircle style={{ width: 12, height: 12, color: '#856305' }} />
            </div>
            {pendingApprovals.length > 0 && <span className="text-2xs font-semibold font-display" style={{ color: '#D9641E' }}>Action needed</span>}
          </div>
          {casesLoading
            ? <div className="skeleton h-9 w-12 mb-0.5" />
            : <div className="stat-value" style={{ color: pendingApprovals.length > 0 ? '#856305' : undefined }}>{pendingApprovals.length}</div>}
          <div className="stat-label">Pending Approvals</div>
          <div className="stat-trend mt-1">
            <Link to="/approvals" className="hover:underline" style={{ color: '#D4A017' }}>View queue →</Link>
          </div>
        </div>

        {/* Auto-Executed */}
        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(220,252,231,0.80)', border: '1px solid rgba(134,239,172,0.40)' }}>
              <Zap style={{ width: 12, height: 12, color: '#1D6B3E' }} />
            </div>
            <TrendingUp style={{ width: 13, height: 13, color: '#C2B8A8' }} />
          </div>
          {casesLoading ? <div className="skeleton h-9 w-10 mb-0.5" /> : <div className="stat-value" style={{ color: '#1D6B3E' }}>{autoToday}</div>}
          <div className="stat-label">Auto-Executed Today</div>
          <div className="stat-trend mt-1">No human needed</div>
        </div>

        {/* Avg Confidence */}
        <div className="stat-card">
          <div className="flex items-center justify-between mb-1">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(219,234,254,0.80)', border: '1px solid rgba(147,197,253,0.40)' }}>
              <ShieldCheck style={{ width: 12, height: 12, color: '#1A4D7A' }} />
            </div>
            <Activity style={{ width: 13, height: 13, color: '#C2B8A8' }} />
          </div>
          {casesLoading ? <div className="skeleton h-9 w-14 mb-0.5" /> : <div className="stat-value" style={{ color: '#1A4D7A' }}>{avgConfidence ? `${avgConfidence}%` : '—'}</div>}
          <div className="stat-label">Avg Confidence</div>
          <div className="stat-trend mt-1">{escalatedToday > 0 ? `${escalatedToday} escalated` : 'All clean'}</div>
        </div>
      </div>

      {/* ── Main grid ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Recent Decisions table */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="px-6 py-5 border-b border-canvas-border flex items-center justify-between">
            <div>
              <h2 className="section-title">Recent Decisions</h2>
              <p className="text-2xs text-ink-400 mt-0.5">Latest 10 cases processed by the engine</p>
            </div>
            <Link to="/decisions" className="btn-secondary btn-sm gap-1.5">
              View all
              <ArrowUpRight style={{ width: 11, height: 11 }} />
            </Link>
          </div>

          {casesLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton h-12" />)}
            </div>
          ) : recentCases.length === 0 ? (
            <EmptyState
              icon={Play}
              title="No cases yet"
              message="Register a connector and submit a case to see decisions here."
              action={<Link to="/connectors" className="btn-secondary btn-sm">Set up connectors</Link>}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Process</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Risk</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {recentCases.map((c) => {
                    const state = decisionState(c)
                    return (
                      <tr key={c.id} onClick={() => window.location.assign(`/cases/${c.id}`)}>
                        <td>
                          <span className="font-mono text-ink-400" style={{ fontSize: '0.6875rem' }}>#{c.id}</span>
                        </td>
                        <td><ProcessLabel process={c.process} /></td>
                        <td><StateBadge state={state} /></td>
                        <td style={{ minWidth: 120 }}>
                          {c.decision
                            ? <ConfidenceBar value={c.decision.confidence} size="sm" />
                            : <span className="text-ink-300 text-xs">—</span>}
                        </td>
                        <td>
                          {c.decision?.risk_level
                            ? <RiskBadge level={c.decision.risk_level} size="sm" />
                            : <span className="text-ink-300 text-xs">—</span>}
                        </td>
                        <td className="text-ink-400" style={{ fontSize: '0.75rem' }}>{relativeTime(c.created_at)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-5">

          {/* Confidence trend */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="section-title">Confidence Trend</h2>
              <span className="badge badge-gray text-2xs">Last 30</span>
            </div>
            {chartData.length === 0 ? (
              <div className="h-36 flex items-center justify-center text-ink-300 text-xs">No data yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={chartData} margin={{ left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#1D6B3E" stopOpacity={0.22} />
                      <stop offset="95%" stopColor="#1D6B3E" stopOpacity={0}    />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="i" tick={false} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#A0917F', fontSize: 10, fontFamily: 'Inter' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: 'rgba(250,248,244,0.96)', border: '1px solid rgba(212,203,191,0.70)', borderRadius: 12, fontSize: 12, fontFamily: 'Inter' }}
                    formatter={(v: number) => [`${v}%`, 'Confidence']}
                    labelFormatter={() => ''}
                  />
                  <Area type="monotone" dataKey="confidence" stroke="#1D6B3E" strokeWidth={2} fill="url(#confGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Connector status */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-canvas-border flex items-center justify-between">
              <h2 className="section-title">Connectors</h2>
              <Link to="/connectors" className="btn-secondary btn-sm gap-1">
                Manage
                <ArrowUpRight style={{ width: 10, height: 10 }} />
              </Link>
            </div>
            {sourcesLoading ? (
              <div className="p-4 space-y-2">
                {[1, 2, 3].map((i) => <div key={i} className="skeleton h-10" />)}
              </div>
            ) : (
              <div className="divide-y divide-canvas-border">
                {connectorStatus.map(({ type, count, active }) => (
                  <div key={type} className="px-5 py-3.5 flex items-center justify-between group hover:bg-canvas-warm transition-colors">
                    <div className="flex items-center gap-2.5 text-ink-600">
                      {sourceIcon(type)}
                      <span className="font-display font-medium text-sm capitalize" style={{ letterSpacing: '-0.01em' }}>{type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${active > 0 ? 'bg-risk-low animate-pulse-soft' : 'bg-canvas-subtle'}`} />
                      <span className="font-mono text-ink-400" style={{ fontSize: '0.6875rem' }}>
                        {count === 0 ? 'Not configured' : `${active}/${count} active`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
