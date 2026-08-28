import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type ResolvedRule, type CandidateRule } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { GitBranch, Loader, CheckCircle2, ArrowRight } from 'lucide-react'

const PROCESSES = ['all', 'refund_handling', 'incident_triage', 'pricing_exceptions']

function Score({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const cls = pct >= 70 ? 'text-risk-low' : pct >= 50 ? 'text-risk-medium' : 'text-risk-high'
  return <span className={`font-mono text-sm font-bold ${cls}`}>{pct}%</span>
}

export default function Conflicts() {
  const qc = useQueryClient()
  const [process, setProcess] = useState('all')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [note, setNote] = useState('')

  const { data: conflicts = [], isLoading, error, refetch } = useQuery({
    queryKey: ['conflicts', process],
    queryFn: () =>
      api.conflicts.list({ process: process === 'all' ? undefined : process }),
    refetchInterval: 30_000,
  })

  const { data: detail } = useQuery({
    queryKey: ['conflict', selectedId],
    queryFn: () => api.conflicts.get(selectedId!),
    enabled: selectedId !== null,
  })

  const resolveMut = useMutation({
    mutationFn: () =>
      api.conflicts.resolve(selectedId!, { resolution_note: note || 'Resolved by reviewer', resolved_by: 'human' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conflicts'] })
      setSelectedId(null)
      setNote('')
    },
  })

  const runResolverMut = useMutation({
    mutationFn: (p: string) => api.conflicts.runResolver(p === 'all' ? 'refund_handling' : p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conflicts'] }),
  })

  if (error) return <ErrorState error={error as Error} title="Could not load conflicts" onRetry={refetch} />

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <GitBranch style={{ width: 22, height: 22, color: '#D9641E' }} />
            Conflicts
          </h1>
          <p className="page-subtitle">
            Rule conflicts detected during extraction — how the weighted-scoring resolver settled them.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <select
            className="select"
            style={{ width: 176, paddingBlock: '0.4375rem', fontSize: '0.8125rem' }}
            value={process}
            onChange={(e) => setProcess(e.target.value)}
          >
            {PROCESSES.map((p) => <option key={p} value={p}>{p === 'all' ? 'All processes' : p.replace(/_/g, ' ')}</option>)}
          </select>
          <button
            className="btn-secondary"
            onClick={() => runResolverMut.mutate(process)}
            disabled={runResolverMut.isPending}
            id="run-resolver-btn"
          >
            {runResolverMut.isPending
              ? <><Loader style={{ width: 14, height: 14 }} className="animate-spin" />Running…</>
              : <>Run Resolver</>}
          </button>
        </div>
      </div>

      {runResolverMut.data && (
        <div className="flex items-center gap-3 px-5 py-3.5 rounded-2xl border" style={{ background: 'rgba(220,252,231,0.70)', border: '1px solid rgba(134,239,172,0.50)', color: '#1D6B3E' }}>
          <CheckCircle2 style={{ width: 15, height: 15, flexShrink: 0 }} />
          <span style={{ fontSize: '0.875rem' }}>
            Resolver complete — {(runResolverMut.data as { resolved?: number }).resolved ?? 0} resolved,{' '}
            {(runResolverMut.data as { flagged?: number }).flagged ?? 0} flagged.
          </span>
        </div>
      )}

      <div className="grid grid-cols-5 gap-5">
        {/* List */}
        <div className="col-span-2 card overflow-hidden">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => <div key={i} className="skeleton h-20" />)}
            </div>
          ) : conflicts.length === 0 ? (
            <EmptyState
              icon={GitBranch}
              title="No unresolved conflicts"
              message="Run the resolver to detect and process rule conflicts."
            />
          ) : (
            <div className="divide-y divide-canvas-border">
              {conflicts.map((c: ResolvedRule) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedId(c.id)}
                  className={`w-full text-left px-4 py-4 hover:bg-canvas-warm/60 transition-colors ${
                    selectedId === c.id ? 'bg-canvas-warm border-l-2 border-ink-800' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="badge badge-gray text-2xs capitalize">
                      {c.process.replace(/_/g, ' ')}
                    </span>
                    <span className="badge badge-yellow text-2xs ml-auto">unresolved</span>
                  </div>
                  <div className="text-xs text-ink-700 font-medium line-clamp-2">
                    {c.trigger_text || 'No trigger text'}
                  </div>
                  <div className="text-2xs text-ink-400 mt-1 flex items-center gap-1">
                    Score: <Score value={c.score ?? 0} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail */}
        <div className="col-span-3">
          {detail ? (
            <div className="space-y-4">
              {/* Winning rule */}
              <div className="card p-5 space-y-3">
                <div className="section-title">Conflict Rule</div>
                <div className="space-y-2">
                  <div>
                    <div className="label">Trigger</div>
                    <div className="text-sm text-ink-700">{detail.trigger_text || '—'}</div>
                  </div>
                  <div>
                    <div className="label">Action</div>
                    <div className="text-sm text-ink-700">{detail.action || '—'}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="label">Score</div>
                      <Score value={detail.score ?? 0} />
                    </div>
                    <div>
                      <div className="label">Temporal</div>
                      <span className="badge badge-gray text-2xs">{detail.temporal_scope || '—'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Competing rules */}
              {detail.competing_rules && detail.competing_rules.length > 0 && (
                <div className="card overflow-hidden">
                  <div className="px-5 py-4 border-b border-canvas-border">
                    <div className="section-title">Competing Rules ({detail.competing_rules.length})</div>
                  </div>
                  <div className="divide-y divide-canvas-border">
                    {detail.competing_rules.map((r: CandidateRule) => (
                      <div key={r.id} className="px-5 py-3 flex items-start gap-3">
                        <ArrowRight className="w-3.5 h-3.5 text-ink-300 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-ink-700 font-medium">{r.trigger_text || '—'}</div>
                          <div className="text-2xs text-ink-400 mt-0.5">{r.action}</div>
                        </div>
                        <span className="font-mono text-xs text-ink-400 flex-shrink-0">
                          {Math.round((r.confidence ?? 0) * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resolve */}
              <div className="card p-5 space-y-3">
                <div className="section-title">Human Resolution</div>
                <div>
                  <label className="label">Resolution Note</label>
                  <textarea
                    className="input h-20 resize-none"
                    placeholder="Explain which rule should take precedence and why…"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </div>
                {resolveMut.error && (
                  <div className="text-xs text-risk-high bg-red-50 rounded-xl p-2 border border-red-200">
                    {(resolveMut.error as Error).message}
                  </div>
                )}
                <button
                  id={`resolve-btn-${selectedId}`}
                  className="btn-primary"
                  onClick={() => resolveMut.mutate()}
                  disabled={resolveMut.isPending}
                >
                  {resolveMut.isPending
                    ? <><Loader className="w-4 h-4 animate-spin" /> Resolving…</>
                    : <><CheckCircle2 className="w-4 h-4" /> Mark Resolved</>}
                </button>
              </div>
            </div>
          ) : (
            <div className="card h-full">
              <EmptyState
                icon={GitBranch}
                title="Select a conflict"
                message="Choose a conflict to see competing rules and resolve it."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
