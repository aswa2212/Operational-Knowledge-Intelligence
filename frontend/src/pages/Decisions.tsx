import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Case } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { FileText, Search, Filter } from 'lucide-react'

const PROCESSES = ['all', 'refund_handling', 'incident_triage', 'pricing_exceptions']
const OUTCOMES  = ['all', 'auto', 'escalated', 'pending']

function outcomeOf(c: Case): 'auto' | 'escalated' | 'pending' {
  if (!c.decision) return 'pending'
  return c.decision.escalated ? 'escalated' : 'auto'
}

const OUTCOME_LABELS = {
  auto:      'Auto-Executed',
  escalated: 'Escalated',
  pending:   'Pending',
}

export default function Decisions() {
  const [process, setProcess] = useState('all')
  const [outcome, setOutcome] = useState('all')
  const [search, setSearch] = useState('')

  const { data: cases = [], isLoading, error, refetch } = useQuery({
    queryKey: ['cases', 'decisions-log', process],
    queryFn: () =>
      api.cases.list({
        process: process === 'all' ? undefined : process,
        limit: 200,
      }),
    refetchInterval: 30_000,
  })

  // Client-side filter on outcome + search
  const filtered = cases.filter((c) => {
    if (outcome !== 'all' && outcomeOf(c) !== outcome) return false
    if (search && !`${c.id} ${c.process} ${c.decision?.decision ?? ''}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  if (error) {
    return <ErrorState error={error as Error} title="Could not load decisions" onRetry={refetch} />
  }

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <FileText style={{ width: 22, height: 22, color: '#D9641E' }} />
            Decisions
          </h1>
          <p className="page-subtitle">Decision log across all cases — filterable by process and outcome.</p>
        </div>
        <span className="font-display font-medium text-ink-400" style={{ fontSize: '0.8125rem' }}>
          {filtered.length} {filtered.length === 1 ? 'record' : 'records'}
        </span>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" style={{ width: 13, height: 13 }} />
          <input
            className="input pl-9"
            style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem' }}
            placeholder="Search case ID or decision…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter style={{ width: 13, height: 13, color: '#A0917F' }} />
          <select className="select" style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem', width: 176 }} value={process} onChange={(e) => setProcess(e.target.value)}>
            {PROCESSES.map((p) => <option key={p} value={p}>{p === 'all' ? 'All processes' : p.replace(/_/g, ' ')}</option>)}
          </select>
          <select className="select" style={{ paddingBlock: '0.4375rem', fontSize: '0.8125rem', width: 148 }} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {OUTCOMES.map((o) => <option key={o} value={o}>{o === 'all' ? 'All outcomes' : o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="card p-6 space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton h-12" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <EmptyState icon={FileText} title="No matching decisions" message="Adjust filters or submit a case to generate decisions." />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Case #</th>
                  <th>Process</th>
                  <th>Decision</th>
                  <th>Outcome</th>
                  <th>Confidence</th>
                  <th>Risk</th>
                  <th>Rule</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => {
                  const oc = outcomeOf(c)
                  return (
                    <tr key={c.id} onClick={() => window.location.assign(`/cases/${c.id}`)}>
                      <td className="font-mono text-ink-400 text-xs">#{c.id}</td>
                      <td>
                        <span className="badge badge-gray text-2xs">
                          {c.process.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="max-w-xs">
                        <span className="text-xs font-medium text-ink-700 truncate block">
                          {c.decision?.decision ?? <span className="text-ink-300">No decision</span>}
                        </span>
                      </td>
                      <td>
                        <span className="inline-flex items-center font-display font-semibold" style={{
                          padding: '0.125rem 0.5rem',
                          background: oc === 'auto' ? 'rgba(220,252,231,0.80)' : oc === 'escalated' ? 'rgba(254,243,199,0.80)' : 'rgba(219,234,254,0.80)',
                          border: oc === 'auto' ? '1px solid rgba(134,239,172,0.50)' : oc === 'escalated' ? '1px solid rgba(253,211,77,0.50)' : '1px solid rgba(147,197,253,0.50)',
                          borderRadius: 999, fontSize: '0.625rem', letterSpacing: '0.01em',
                          color: oc === 'auto' ? '#1D6B3E' : oc === 'escalated' ? '#856305' : '#1A4D7A',
                          fontFamily: "'Outfit', sans-serif",
                        }}>
                          {OUTCOME_LABELS[oc]}
                        </span>
                      </td>
                      <td className="w-36">
                        {c.decision ? (
                          <ConfidenceBar value={c.decision.confidence} size="sm" />
                        ) : (
                          <span className="text-ink-300 text-xs">—</span>
                        )}
                      </td>
                      <td>
                        {c.decision?.risk_level ? (
                          <RiskBadge level={c.decision.risk_level} size="sm" />
                        ) : (
                          <span className="text-ink-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="font-mono text-ink-400 text-xs">
                        {c.decision?.matched_rule_id ?? '—'}
                      </td>
                      <td className="text-ink-400 text-xs whitespace-nowrap">
                        {new Date(c.created_at).toLocaleDateString(undefined, {
                          month: 'short', day: 'numeric',
                        })}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
