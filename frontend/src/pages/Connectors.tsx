import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Source, type AuditEvent } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import {
  Plug, RefreshCw, Github, FileText, Hash, Plus, Loader,
  CheckCircle2, Clock, AlertCircle
} from 'lucide-react'

const PROCESS_OPTIONS = ['refund_handling', 'incident_triage', 'pricing_exceptions']

function sourceIcon(type: string) {
  if (type === 'github') return <Github className="w-5 h-5 text-ink-700" />
  if (type === 'notion') return <FileText className="w-5 h-5 text-ink-700" />
  if (type === 'slack')  return <Hash className="w-5 h-5 text-ink-700" />
  return <Plug className="w-5 h-5 text-terra-600" />
}

function timeStr(iso?: string | null) {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function Connectors() {
  const qc = useQueryClient()
  const [syncingId, setSyncingId] = useState<number | null>(null)
  const [selectedSource, setSelectedSource] = useState<Source | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [form, setForm] = useState({ type: 'github', name: '', process: 'refund_handling' })
  const [feedbackMsg, setFeedbackMsg] = useState<{ id: number; msg: string; type: 'success' | 'error' } | null>(null)

  const { data: sources = [], isLoading, error, refetch } = useQuery({
    queryKey: ['sources'],
    queryFn: api.sources.list,
    refetchInterval: 3_000,
  })

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ['source-history', selectedSource?.id],
    queryFn: () => api.sources.syncHistory(selectedSource!.id),
    enabled: !!selectedSource,
  })

  const createMut = useMutation({
    mutationFn: () => api.sources.create({
      type: form.type,
      name: form.name,
      config: { process: form.process }
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] })
      setShowAddForm(false)
      setForm({ type: 'github', name: '', process: 'refund_handling' })
    }
  })

  const syncMut = useMutation({
    mutationFn: async (id: number) => {
      setSyncingId(id)
      setFeedbackMsg(null)
      return api.sources.sync(id)
    },
    onSuccess: (data, id) => {
      setSyncingId(null)
      setFeedbackMsg({
        id,
        msg: `Sync successful (${(data as { inserted?: number }).inserted ?? 0} docs processed)`,
        type: 'success'
      })
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['source-history', id] })
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (err: Error, id) => {
      setSyncingId(null)
      setFeedbackMsg({
        id,
        msg: `Sync failed: ${err.message}`,
        type: 'error'
      })
    }
  })

  if (error) return <ErrorState error={error as Error} title="Could not load connectors" onRetry={refetch} />

  return (
    <div className="space-y-8 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <Plug style={{ width: 22, height: 22, color: '#D9641E' }} />
            Connectors
          </h1>
          <p className="page-subtitle">
            External ingestion connectors (GitHub, Notion, Slack, Synthetic) with live sync capability.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus style={{ width: 14, height: 14 }} />
          {showAddForm ? 'Close Form' : 'Add Source'}
        </button>
      </div>

      {/* Add Source Card */}
      {showAddForm && (
        <div className="card p-6 border-2 border-terra-200 bg-terra-50/20 space-y-4">
          <div className="section-title">Register External Source</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="label">Type</label>
              <select
                className="select"
                value={form.type}
                onChange={(e) => setForm(f => ({ ...f, type: e.target.value }))}
              >
                <option value="github">GitHub</option>
                <option value="notion">Notion</option>
                <option value="slack">Slack</option>
                <option value="synthetic">Synthetic (Demo)</option>
              </select>
            </div>
            <div>
              <label className="label">Name</label>
              <input
                className="input"
                placeholder="e.g. org-policy-repo"
                value={form.name}
                onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Target Process</label>
              <select
                className="select"
                value={form.process}
                onChange={(e) => setForm(f => ({ ...f, process: e.target.value }))}
              >
                {PROCESS_OPTIONS.map(p => (
                  <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
            <button
              className="btn-primary"
              onClick={() => createMut.mutate()}
              disabled={!form.name || createMut.isPending}
            >
              {createMut.isPending ? <Loader className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              Save Source
            </button>
          </div>
        </div>
      )}

      {/* Connector Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-48" />)}
        </div>
      ) : sources.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Plug}
            title="No connectors registered"
            message="Add a GitHub, Notion, Slack or demo source to begin ingesting documents."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {sources.map((s: Source) => {
            const isSyncing = syncingId === s.id
            const isSelected = selectedSource?.id === s.id
            const feedback = feedbackMsg?.id === s.id ? feedbackMsg : null

            return (
              <div
                key={s.id}
                className={`card p-5 flex flex-col justify-between transition-all duration-200 ${
                  isSelected ? 'ring-2 ring-ink-800' : 'hover:shadow-card-md'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-canvas-warm border border-canvas-border flex items-center justify-center">
                        {sourceIcon(s.type)}
                      </div>
                      <div>
                        <div className="font-semibold text-ink-900 text-sm">{s.name}</div>
                        <span className="badge badge-gray text-2xs uppercase tracking-wider">{s.type}</span>
                      </div>
                    </div>
                    <span className={`badge text-2xs ${s.enabled ? 'badge-green' : 'badge-gray'}`}>
                      {s.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>

                  <div className="text-2xs text-ink-400 space-y-1 bg-canvas-warm p-2.5 rounded-xl border border-canvas-border">
                    <div className="flex justify-between">
                      <span>Source ID:</span>
                      <span className="font-mono text-ink-700">#{s.id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Registered:</span>
                      <span className="text-ink-700">{timeStr(s.created_at)}</span>
                    </div>
                  </div>

                  {feedback && (
                    <div className={`p-2.5 rounded-xl text-2xs flex items-center gap-2 ${
                      feedback.type === 'success'
                        ? 'bg-green-50 text-risk-low border border-green-200'
                        : 'bg-red-50 text-risk-high border border-red-200'
                    }`}>
                      {feedback.type === 'success'
                        ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                        : <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />}
                      <span className="truncate">{feedback.msg}</span>
                    </div>
                  )}
                </div>

                <div className="pt-4 mt-4 border-t border-canvas-border flex items-center gap-2">
                  <button
                    className="btn-secondary btn-sm flex-1 justify-center"
                    onClick={() => setSelectedSource(isSelected ? null : s)}
                  >
                    <Clock className="w-3 h-3" />
                    {isSelected ? 'Hide Logs' : 'History'}
                  </button>
                  <button
                    id={`sync-source-${s.id}`}
                    className="btn-primary btn-sm flex-1 justify-center"
                    onClick={() => syncMut.mutate(s.id)}
                    disabled={isSyncing}
                  >
                    {isSyncing ? (
                      <>
                        <Loader className="w-3 h-3 animate-spin" />
                        Syncing…
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-3 h-3" />
                        Re-sync
                      </>
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Sync History Drawer/Panel */}
      {selectedSource && (
        <div className="card overflow-hidden fade-in-up">
          <div className="px-6 py-4 border-b border-canvas-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-terra-500" />
              <h2 className="section-title">Sync Audit History — {selectedSource.name}</h2>
            </div>
            <button
              className="text-xs text-ink-400 hover:text-ink-700"
              onClick={() => setSelectedSource(null)}
            >
              Close
            </button>
          </div>

          {historyLoading ? (
            <div className="p-5 space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="skeleton h-10" />)}
            </div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center text-xs text-ink-400">
              No previous sync history events found for this connector.
            </div>
          ) : (
            <div className="divide-y divide-canvas-border max-h-72 overflow-y-auto">
              {history.map((ev: AuditEvent) => (
                <div key={ev.id} className="px-6 py-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-blue text-2xs">{ev.event_type}</span>
                    <span className="text-ink-700">{ev.actor || 'system'}</span>
                  </div>
                  <div className="text-ink-400 font-mono text-2xs">{timeStr(ev.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
