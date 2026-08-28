import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type SkillVersion } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { Layers, Plus, Loader, Code } from 'lucide-react'

const PROCESSES = ['refund_handling', 'incident_triage', 'pricing_exceptions']

export default function Skills() {
  const qc = useQueryClient()
  const [selectedProcess, setSelectedProcess] = useState('refund_handling')
  const [showRaw, setShowRaw] = useState(false)

  const { data: versions = [], isLoading: versionsLoading, error, refetch } = useQuery({
    queryKey: ['skill-versions'],
    queryFn: () => api.skills.list(),
  })

  const { data: active } = useQuery({
    queryKey: ['skill-active', selectedProcess],
    queryFn: () => api.skills.getActive(selectedProcess),
    retry: false,
  })

  const buildMut = useMutation({
    mutationFn: () => api.skills.build(selectedProcess),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['skill-versions'] })
      qc.invalidateQueries({ queryKey: ['skill-active'] })
    },
  })

  const rules = (active as { rules?: { id: number; trigger_text: string; action: string; score: number; temporal_scope: string }[] })?.rules || []

  if (error) return <ErrorState error={error as Error} title="Could not load skill versions" onRetry={refetch} />

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <Layers style={{ width: 22, height: 22, color: '#D9641E' }} />
            Skills Browser
          </h1>
          <p className="page-subtitle">Versioned executable rule packages — the agent's authoritative domain knowledge.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <select
            className="select"
            style={{ width: 176, paddingBlock: '0.4375rem', fontSize: '0.8125rem' }}
            value={selectedProcess}
            onChange={e => setSelectedProcess(e.target.value)}
          >
            {PROCESSES.map(p => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
          </select>
          <button className="btn-gold" onClick={() => buildMut.mutate()} disabled={buildMut.isPending}>
            {buildMut.isPending ? <Loader style={{ width: 14, height: 14 }} className="animate-spin" /> : <Plus style={{ width: 14, height: 14 }} />}
            Build New Version
          </button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-5">
        {/* Versions sidebar */}
        <div className="col-span-2 card overflow-hidden">
          <div className="px-5 py-4 border-b border-canvas-border section-title">Versions Log</div>
          {versionsLoading ? (
            <div className="p-4 space-y-2">{[1, 2, 3].map(i => <div key={i} className="skeleton h-14" />)}</div>
          ) : versions.length === 0 ? (
            <EmptyState icon={Layers} title="No versions yet" message="Click 'Build New Version' to compile candidate rules." />
          ) : (
            <div className="divide-y divide-canvas-border max-h-[550px] overflow-y-auto">
              {versions.map((v: SkillVersion) => (
                <div key={v.id} className="p-4 hover:bg-canvas-warm/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="font-display font-semibold text-sm text-ink-900">{v.version}</span>
                    <span className="badge badge-gray text-2xs uppercase">{v.process.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="text-2xs text-ink-400 mt-1 flex items-center gap-1.5">
                    <span>{v.rules_count ?? v.rule_count ?? 0} rules</span>
                    <span>•</span>
                    <span>{new Date(v.created_at || v.generated_at || Date.now()).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Skill Details */}
        <div className="col-span-3">
          {active ? (
            <div className="card p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="section-title text-base">Active Skill: {(active as { version?: string }).version || 'vCurrent'}</h2>
                  <div className="text-2xs text-ink-400 mt-0.5">Compiled rules currently driving agent decisions</div>
                </div>
                <button className="btn-secondary btn-xs gap-1.5" onClick={() => setShowRaw(!showRaw)}>
                  <Code style={{ width: 12, height: 12 }} />
                  {showRaw ? 'Show Rules' : 'Show Raw YAML'}
                </button>
              </div>

              {showRaw ? (
                <pre className="p-4 rounded-xl border border-canvas-border bg-canvas-warm/40 font-mono text-xs text-ink-800 whitespace-pre-wrap max-h-[460px] overflow-y-auto">
                  {typeof (active as { content?: string }).content === 'string' ? (active as { content?: string }).content : JSON.stringify(active, null, 2)}
                </pre>
              ) : (
                <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                  {rules.length === 0 ? (
                    <div className="text-xs text-ink-400 text-center py-8">No resolved rules in this version.</div>
                  ) : (
                    rules.map(r => (
                      <div key={r.id} className="p-4 rounded-xl border border-canvas-border bg-canvas-warm/30 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono text-ink-400">Rule #{r.id}</span>
                          <span className="badge badge-gold text-2xs">Score: {Math.round((r.score ?? 1) * 100)}%</span>
                        </div>
                        <div className="text-sm font-medium text-ink-800">{r.trigger_text}</div>
                        <div className="text-xs text-ink-600">Action: <strong className="text-ink-800 font-semibold">{r.action}</strong></div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="card h-full">
              <EmptyState icon={Layers} title="No active skill compiled" message="Click 'Build New Version' to compile and activate the latest rules." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
