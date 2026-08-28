import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Approval } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import {
  ShieldCheck, CheckCircle2, XCircle, Loader, AlertTriangle,
  Clock, Brain, Zap,
} from 'lucide-react'

function timeStr(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function Approvals() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [rejectReason, setRejectReason] = useState('')
  const [justApproved, setJustApproved] = useState(false)
  const aggressiveRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: approvals = [], isLoading, error, refetch } = useQuery({
    queryKey: ['approvals', statusFilter],
    queryFn: () => api.approvals.list(statusFilter),
    refetchInterval: 20_000,
  })

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['approval', selected],
    queryFn: () => api.approvals.get(selected!),
    enabled: selected !== null,
    refetchInterval: (query): number | false => {
      const d = query.state.data as Approval | undefined
      return d && Object.keys(d.summary_card ?? {}).length > 0 ? false : 5_000
    },
  })

  const approveMut = useMutation({
    mutationFn: () => api.approvals.approve(selected!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['actions'] })
      setSelected(null)
      setJustApproved(true)
      let ticks = 0
      aggressiveRefreshRef.current = setInterval(() => {
        qc.invalidateQueries({ queryKey: ['actions'] })
        ticks++
        if (ticks >= 12) {
          clearInterval(aggressiveRefreshRef.current!)
          aggressiveRefreshRef.current = null
          setJustApproved(false)
        }
      }, 1500)
    },
  })

  useEffect(() => () => { if (aggressiveRefreshRef.current) clearInterval(aggressiveRefreshRef.current) }, [])

  const rejectMut = useMutation({
    mutationFn: () => api.approvals.reject(selected!, rejectReason || 'Rejected by reviewer'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['actions'] })
      setSelected(null)
      setRejectReason('')
    },
  })

  if (error) return <ErrorState error={error as Error} title="Could not load approvals" onRetry={refetch} />

  const isPending = statusFilter === 'pending'
  const isActing = approveMut.isPending || rejectMut.isPending

  return (
    <div className="space-y-6 fade-in-up">

      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <ShieldCheck style={{ width: 22, height: 22, color: '#D9641E' }} />
            Approvals
          </h1>
          <p className="page-subtitle">High-risk decisions and knowledge conflicts requiring human review.</p>
        </div>
        <select
          className="select"
          style={{ width: 148, paddingBlock: '0.4375rem', fontSize: '0.8125rem' }}
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setSelected(null) }}
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {/* Execution banner */}
      {justApproved && (
        <div className="flex items-center gap-3 px-5 py-3.5 rounded-2xl border" style={{
          background: 'rgba(220,252,231,0.70)', border: '1px solid rgba(134,239,172,0.50)', color: '#1D6B3E',
        }}>
          <Zap style={{ width: 15, height: 15, flexShrink: 0 }} />
          <span className="text-sm font-medium">
            <strong>Action queued!</strong> Executing in the background — check the <strong>Execution Arm</strong> tab for live results.
          </span>
          <Loader style={{ width: 15, height: 15, flexShrink: 0, marginLeft: 'auto' }} className="animate-spin" />
        </div>
      )}

      <div className="grid grid-cols-5 gap-5">
        {/* List */}
        <div className="col-span-2 card overflow-hidden">
          {isLoading ? (
            <div className="p-4 space-y-3">{[1, 2, 3].map((i) => <div key={i} className="skeleton h-20" />)}</div>
          ) : approvals.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title={`No ${statusFilter} approvals`}
              message={isPending ? 'All caught up — no actions waiting for review.' : undefined}
            />
          ) : (
            <div className="divide-y divide-canvas-border">
              {approvals.map((a: Approval) => (
                <button
                  key={a.id}
                  id={`approval-${a.id}`}
                  onClick={() => setSelected(a.id)}
                  className={`w-full text-left px-4 py-4 transition-colors ${
                    selected === a.id
                      ? 'border-l-2 border-ink-800'
                      : 'hover:bg-canvas-warm/60'
                  }`}
                  style={selected === a.id ? { background: 'rgba(245,240,230,0.60)' } : {}}
                >
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className={`badge text-2xs ${a.type === 'knowledge' ? 'badge-terra' : 'badge-yellow'}`}>{a.type}</span>
                    {a.risk_level && <RiskBadge level={a.risk_level} size="sm" />}
                    <span className="font-mono text-2xs text-ink-400 ml-auto">#{a.id}</span>
                  </div>
                  <div className="text-ink-700 truncate font-medium" style={{ fontSize: '0.8125rem' }}>
                    {a.reason || a.escalation_reason || 'Review required'}
                  </div>
                  <div className="text-ink-400 mt-1 flex items-center gap-1" style={{ fontSize: '0.6875rem' }}>
                    <Clock style={{ width: 10, height: 10 }} />
                    {timeStr(a.requested_at)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail */}
        <div className="col-span-3">
          {detailLoading ? (
            <div className="space-y-3">
              <div className="skeleton h-32" />
              <div className="skeleton h-48" />
            </div>
          ) : detail ? (
            <div className="space-y-4">
              {/* AI summary */}
              {detail.summary_card && Object.keys(detail.summary_card).length > 0 && (
                <div className="card-gold p-5 space-y-3">
                  <div className="flex items-center gap-2">
                    <Brain style={{ width: 15, height: 15, color: '#78590A' }} />
                    <div className="label" style={{ color: '#78590A' }}>AI Review Summary</div>
                  </div>
                  {detail.summary_card.headline && (
                    <div className="font-display font-semibold text-ink-800" style={{ fontSize: '0.9375rem', letterSpacing: '-0.02em' }}>
                      {detail.summary_card.headline}
                    </div>
                  )}
                  {detail.summary_card.situation && (
                    <div className="text-ink-600" style={{ fontSize: '0.8125rem' }}>{detail.summary_card.situation}</div>
                  )}
                  {(detail.summary_card.approve_consequence || detail.summary_card.reject_consequence) && (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl p-3 border" style={{ background: 'rgba(220,252,231,0.70)', border: '1px solid rgba(134,239,172,0.50)', fontSize: '0.75rem' }}>
                        <div className="font-semibold text-risk-low mb-1">If approved</div>
                        <div className="text-ink-600">{detail.summary_card.approve_consequence}</div>
                      </div>
                      <div className="rounded-xl p-3 border" style={{ background: 'rgba(254,226,226,0.70)', border: '1px solid rgba(252,165,165,0.50)', fontSize: '0.75rem' }}>
                        <div className="font-semibold text-risk-high mb-1">If rejected</div>
                        <div className="text-ink-600">{detail.summary_card.reject_consequence}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Decision info */}
              <div className="card p-5 space-y-3">
                <div className="section-title">Decision Details</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                  {[['Process', detail.process ?? '—'], ['Decision', detail.decision ?? '—']].map(([k, v]) => (
                    <div key={k}>
                      <div className="label">{k}</div>
                      <div className="text-ink-800 font-medium" style={{ fontSize: '0.875rem' }}>{v}</div>
                    </div>
                  ))}
                  <div>
                    <div className="label">Confidence</div>
                    <div className="mt-1">
                      {detail.confidence ? <ConfidenceBar value={detail.confidence} showLabel /> : <span className="text-ink-300 text-xs">—</span>}
                    </div>
                  </div>
                  <div>
                    <div className="label">Risk Level</div>
                    <div className="mt-1">
                      {detail.risk_level ? <RiskBadge level={detail.risk_level} /> : <span className="text-ink-300 text-xs">—</span>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Case fields */}
              {detail.case_fields && Object.keys(detail.case_fields).length > 0 && (
                <div className="card p-5">
                  <div className="section-title mb-3">Case Fields</div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                    {Object.entries(detail.case_fields).map(([k, v]) => (
                      <div key={k}>
                        <div className="label">{k.replace(/_/g, ' ')}</div>
                        <div className="text-ink-700 font-medium" style={{ fontSize: '0.875rem' }}>{String(v)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              {isPending && (
                <div className="space-y-2.5">
                  {rejectMut.isIdle && (
                    <div className="flex gap-2.5">
                      <button
                        id={`approve-btn-${selected}`}
                        className="btn-success flex-1 justify-center"
                        onClick={() => approveMut.mutate()}
                        disabled={isActing}
                      >
                        {approveMut.isPending
                          ? <Loader style={{ width: 14, height: 14 }} className="animate-spin" />
                          : <CheckCircle2 style={{ width: 14, height: 14 }} />}
                        Approve & Execute
                      </button>
                      <button
                        id={`reject-btn-${selected}`}
                        className="btn-danger flex-1 justify-center"
                        onClick={() => rejectMut.mutate()}
                        disabled={isActing}
                      >
                        {rejectMut.isPending
                          ? <Loader style={{ width: 14, height: 14 }} className="animate-spin" />
                          : <XCircle style={{ width: 14, height: 14 }} />}
                        Reject
                      </button>
                    </div>
                  )}
                  {(approveMut.error || rejectMut.error) && (
                    <div className="rounded-xl p-3 border" style={{ fontSize: '0.75rem', background: 'rgba(254,226,226,0.70)', border: '1px solid rgba(252,165,165,0.50)', color: '#8B1616' }}>
                      {((approveMut.error || rejectMut.error) as Error).message}
                    </div>
                  )}
                </div>
              )}

              {/* Resolved state */}
              {!isPending && detail.status && (
                <div className={`card p-4 flex items-center gap-3`}
                  style={detail.status === 'approved'
                    ? { background: 'rgba(220,252,231,0.50)', border: '1px solid rgba(134,239,172,0.50)' }
                    : { background: 'rgba(254,226,226,0.50)', border: '1px solid rgba(252,165,165,0.50)' }}>
                  {detail.status === 'approved'
                    ? <CheckCircle2 style={{ width: 18, height: 18, color: '#1D6B3E' }} />
                    : <XCircle style={{ width: 18, height: 18, color: '#8B1616' }} />}
                  <div>
                    <div className="font-display font-semibold text-ink-800 capitalize" style={{ fontSize: '0.875rem' }}>{detail.status}</div>
                    {detail.resolved_at && (
                      <div className="text-ink-400" style={{ fontSize: '0.75rem' }}>{timeStr(detail.resolved_at)} by {detail.resolved_by || 'human'}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card h-full">
              <EmptyState icon={AlertTriangle} title="Select an approval" message="Choose an item from the queue to review its details and take action." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
