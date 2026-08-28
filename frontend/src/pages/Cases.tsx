import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, type Case } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import {
  Play, Search, Filter, Plus, X, Loader, ChevronRight,
  CheckCircle2, AlertTriangle, Clock,
} from 'lucide-react'

const PROCESSES = ['refund_handling', 'incident_triage', 'pricing_exceptions']
const PROCESS_FIELDS: Record<string, { key: string; label: string; type: string; placeholder: string }[]> = {
  refund_handling: [
    { key: 'days_since_purchase', label: 'Days Since Purchase', type: 'number', placeholder: '30' },
    { key: 'order_value',         label: 'Order Value ($)',     type: 'number', placeholder: '150' },
    { key: 'customer_tier',       label: 'Customer Tier',       type: 'text',   placeholder: 'standard | enterprise | VIP' },
    { key: 'item_category',       label: 'Item Category',       type: 'text',   placeholder: 'electronics | software | hardware' },
    { key: 'reason',              label: 'Reason',              type: 'text',   placeholder: 'dissatisfied | product_defect | wrong_item' },
  ],
  incident_triage: [
    { key: 'error_type',           label: 'Error Type',       type: 'text',   placeholder: 'DDoS | auth_failure | crash' },
    { key: 'affected_users_count', label: 'Affected Users',   type: 'number', placeholder: '1000' },
    { key: 'system_component',     label: 'System Component', type: 'text',   placeholder: 'api_gateway | auth_service' },
    { key: 'severity_signal',      label: 'Severity Signal',  type: 'text',   placeholder: 'service_down | isolated | degraded' },
  ],
  pricing_exceptions: [
    { key: 'discount_percent', label: 'Discount %',      type: 'number', placeholder: '15' },
    { key: 'deal_size',        label: 'Deal Size ($)',   type: 'number', placeholder: '5000' },
    { key: 'requestor_role',   label: 'Requestor Role', type: 'text',   placeholder: 'sales_rep | manager | director' },
  ],
}

function outcomeOf(c: Case): 'auto' | 'escalated' | 'pending' {
  if (!c.decision) return 'pending'
  return c.decision.escalated ? 'escalated' : 'auto'
}

const OUTCOME_CONFIG = {
  auto:      { icon: <CheckCircle2 style={{ width: 11, height: 11 }} />, label: 'Auto-Executed', bg: 'rgba(220,252,231,0.80)', border: 'rgba(134,239,172,0.50)', color: '#1D6B3E' },
  escalated: { icon: <AlertTriangle style={{ width: 11, height: 11 }} />, label: 'Escalated',     bg: 'rgba(254,243,199,0.80)', border: 'rgba(253,211,77,0.50)',  color: '#856305' },
  pending:   { icon: <Clock style={{ width: 11, height: 11 }} />,         label: 'Pending',       bg: 'rgba(219,234,254,0.80)', border: 'rgba(147,197,253,0.50)', color: '#1A4D7A' },
}

function OutcomePill({ outcome }: { outcome: 'auto' | 'escalated' | 'pending' }) {
  const cfg = OUTCOME_CONFIG[outcome]
  return (
    <span className="inline-flex items-center gap-1 font-display font-semibold" style={{
      padding: '0.125rem 0.5rem', background: cfg.bg, border: `1px solid ${cfg.border}`,
      borderRadius: 999, color: cfg.color, fontSize: '0.625rem', letterSpacing: '0.01em', fontFamily: "'Outfit', sans-serif",
    }}>
      {cfg.icon}{cfg.label}
    </span>
  )
}

type SubmitResult = {
  case_id: number; decision: string; confidence: number
  escalated: boolean; escalation_reason?: string
}

export default function Cases() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [processFilter, setProcessFilter] = useState('all')
  const [outcomeFilter, setOutcomeFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [modalProcess, setModalProcess] = useState('refund_handling')
  const [fields, setFields] = useState<Record<string, string>>({})
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null)

  const { data: cases = [], isLoading, error, refetch } = useQuery({
    queryKey: ['cases', processFilter],
    queryFn: () => api.cases.list({ process: processFilter === 'all' ? undefined : processFilter, limit: 100 }),
    refetchInterval: 30_000,
  })

  const filtered = cases.filter((c) => {
    if (outcomeFilter !== 'all' && outcomeOf(c) !== outcomeFilter) return false
    if (search && !`${c.id} ${c.process}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const submitMut = useMutation({
    mutationFn: () => {
      const parsed: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(fields)) {
        parsed[k] = isNaN(Number(v)) || v === '' ? v : Number(v)
      }
      return api.cases.submit(modalProcess, parsed)
    },
    onSuccess: (data) => {
      setSubmitResult(data)
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['actions'] })
    },
  })

  function closeModal() {
    setShowModal(false)
    setFields({})
    setSubmitResult(null)
    submitMut.reset()
  }

  if (error) return <ErrorState error={error as Error} title="Could not load cases" onRetry={refetch} />

  return (
    <div className="space-y-6 fade-in-up">

      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <Play style={{ width: 22, height: 22, color: '#D9641E' }} />
            Cases
          </h1>
          <p className="page-subtitle">All submitted cases across the three business processes.</p>
        </div>
        <button className="btn-gold" onClick={() => setShowModal(true)}>
          <Plus style={{ width: 14, height: 14 }} />
          New Case
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" style={{ width: 13, height: 13 }} />
          <input
            className="input pl-9"
            style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem' }}
            placeholder="Search by ID or process…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter style={{ width: 13, height: 13, color: '#A0917F' }} />
          <select className="select" style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem', width: 180 }} value={processFilter} onChange={(e) => setProcessFilter(e.target.value)}>
            <option value="all">All processes</option>
            {PROCESSES.map((p) => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
          </select>
          <select className="select" style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem', width: 148 }} value={outcomeFilter} onChange={(e) => setOutcomeFilter(e.target.value)}>
            <option value="all">All outcomes</option>
            <option value="auto">Auto-Executed</option>
            <option value="escalated">Escalated</option>
            <option value="pending">Pending</option>
          </select>
        </div>
        <span className="font-display font-medium text-ink-400 ml-auto" style={{ fontSize: '0.8125rem' }}>{filtered.length} cases</span>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="card p-6 space-y-3">
          {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton h-12" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <EmptyState icon={Play} title="No cases found" message="Submit a new case or adjust your filters." action={<button className="btn-gold btn-sm" onClick={() => setShowModal(true)}>New Case</button>} />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th><th>Process</th><th>Outcome</th><th>Decision</th>
                  <th>Confidence</th><th>Risk</th><th>Date</th><th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => {
                  const oc = outcomeOf(c)
                  return (
                    <tr key={c.id} onClick={() => navigate(`/cases/${c.id}`)}>
                      <td><span className="font-mono text-ink-400" style={{ fontSize: '0.6875rem' }}>#{c.id}</span></td>
                      <td>
                        <span className="badge badge-gray" style={{ fontSize: '0.625rem' }}>{c.process.replace(/_/g, ' ')}</span>
                      </td>
                      <td><OutcomePill outcome={oc} /></td>
                      <td className="max-w-xs">
                        <span className="text-ink-700 truncate block" style={{ fontSize: '0.8125rem' }}>
                          {c.decision?.decision ?? <span className="text-ink-300">—</span>}
                        </span>
                      </td>
                      <td style={{ minWidth: 128 }}>
                        {c.decision ? <ConfidenceBar value={c.decision.confidence} size="sm" /> : <span className="text-ink-300 text-xs">—</span>}
                      </td>
                      <td>
                        {c.decision?.risk_level ? <RiskBadge level={c.decision.risk_level} size="sm" /> : <span className="text-ink-300 text-xs">—</span>}
                      </td>
                      <td className="text-ink-400 whitespace-nowrap" style={{ fontSize: '0.75rem' }}>
                        {new Date(c.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </td>
                      <td><ChevronRight style={{ width: 14, height: 14, color: '#C2B8A8' }} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* New Case Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(26,21,15,0.35)', backdropFilter: 'blur(8px)' }}>
          <div className="card-elevated w-full max-w-lg scale-in" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="px-6 py-5 border-b border-canvas-border flex items-center justify-between">
              <div>
                <h2 className="section-title" style={{ fontSize: '1.0625rem' }}>Submit New Case</h2>
                <p className="text-ink-400 mt-0.5" style={{ fontSize: '0.8125rem' }}>Run the OKI decision engine on a real case</p>
              </div>
              <button className="w-8 h-8 rounded-xl hover:bg-canvas-muted flex items-center justify-center transition-colors" onClick={closeModal}>
                <X style={{ width: 14, height: 14, color: '#A0917F' }} />
              </button>
            </div>

            {submitResult ? (
              <div className="p-6 space-y-5">
                <div className="text-center py-2">
                  {submitResult.escalated
                    ? <AlertTriangle style={{ width: 48, height: 48, color: '#856305', margin: '0 auto 12px' }} />
                    : <CheckCircle2 style={{ width: 48, height: 48, color: '#1D6B3E', margin: '0 auto 12px' }} />}
                  <div className="font-display font-700 text-ink-900 mb-2" style={{ fontSize: '1.5rem', letterSpacing: '-0.03em', fontWeight: 700 }}>
                    {submitResult.decision || 'Decision made'}
                  </div>
                  {submitResult.escalated && <span className="badge badge-escalated">Escalated to human</span>}
                </div>
                <div className="rounded-2xl p-4 space-y-3 border border-canvas-border" style={{ background: 'rgba(245,240,230,0.60)' }}>
                  <div className="flex justify-between items-center">
                    <span className="text-ink-400" style={{ fontSize: '0.8125rem' }}>Case ID</span>
                    <span className="font-mono text-ink-700" style={{ fontSize: '0.8125rem' }}>#{submitResult.case_id}</span>
                  </div>
                  <div className="flex justify-between items-center gap-4">
                    <span className="text-ink-400" style={{ fontSize: '0.8125rem' }}>Confidence</span>
                    <div style={{ width: 140 }}><ConfidenceBar value={submitResult.confidence} showLabel /></div>
                  </div>
                  {submitResult.escalation_reason && (
                    <div className="rounded-xl p-3 border" style={{ fontSize: '0.75rem', background: 'rgba(254,243,199,0.70)', border: '1px solid rgba(253,211,77,0.40)', color: '#856305' }}>
                      {submitResult.escalation_reason}
                    </div>
                  )}
                </div>
                <div className="flex gap-2.5">
                  <button className="btn-secondary flex-1 justify-center" onClick={closeModal}>Close</button>
                  <button className="btn-primary flex-1 justify-center" onClick={() => { navigate(`/cases/${submitResult.case_id}`); closeModal() }}>
                    View Case <ChevronRight style={{ width: 13, height: 13 }} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6 space-y-4">
                <div>
                  <label className="label">Process</label>
                  <select className="select" value={modalProcess} onChange={(e) => { setModalProcess(e.target.value); setFields({}) }}>
                    {PROCESSES.map((p) => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <div className="space-y-3">
                  {(PROCESS_FIELDS[modalProcess] || []).map((f) => (
                    <div key={f.key}>
                      <label className="label">{f.label}</label>
                      <input
                        type={f.type}
                        className="input"
                        placeholder={f.placeholder}
                        value={fields[f.key] || ''}
                        onChange={(e) => setFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                {submitMut.error && (
                  <div className="rounded-xl p-3 border" style={{ fontSize: '0.75rem', background: 'rgba(254,226,226,0.70)', border: '1px solid rgba(252,165,165,0.50)', color: '#8B1616' }}>
                    {(submitMut.error as Error).message}
                  </div>
                )}
                <button className="btn-primary w-full justify-center" onClick={() => submitMut.mutate()} disabled={submitMut.isPending}>
                  {submitMut.isPending
                    ? <><Loader style={{ width: 14, height: 14 }} className="animate-spin" />Running engine…</>
                    : <><Play style={{ width: 14, height: 14 }} />Run Case</>}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
