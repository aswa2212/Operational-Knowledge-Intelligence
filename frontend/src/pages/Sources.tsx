import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Database, Plus, RefreshCw, Loader } from 'lucide-react'

const PROCESS_OPTIONS = ['refund_handling', 'incident_triage', 'pricing_exceptions']

export default function Sources() {
  const qc = useQueryClient()
  const { data: sources = [], isLoading } = useQuery({ queryKey: ['sources'], queryFn: api.sources.list })

  const [form, setForm] = useState({ type: 'synthetic', name: '', process: 'refund_handling' })
  const [syncId, setSyncId] = useState<number | null>(null)

  const createMut = useMutation({
    mutationFn: () => api.sources.create({ type: form.type, name: form.name, config: { process: form.process } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })

  const syncMut = useMutation({
    mutationFn: (id: number) => { setSyncId(id); return api.sources.sync(id) },
    onSuccess: () => { setSyncId(null); qc.invalidateQueries({ queryKey: ['sources'] }) },
    onError: () => setSyncId(null),
  })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Database className="w-5 h-5 text-brand-400" /> Sources
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">Register data sources and trigger sync.</p>
      </div>

      {/* Add source form */}
      <div className="glass-card p-4 space-y-3">
        <div className="label">Register New Source</div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Type</label>
            <select className="select" value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
              <option value="synthetic">Synthetic (demo)</option>
              <option value="github">GitHub</option>
              <option value="notion">Notion</option>
              <option value="slack">Slack</option>
            </select>
          </div>
          <div>
            <label className="label">Name</label>
            <input className="input" placeholder="e.g. refund_handling" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
          {form.type === 'synthetic' && (
            <div>
              <label className="label">Process</label>
              <select className="select" value={form.process} onChange={e => setForm(f => ({ ...f, process: e.target.value }))}>
                {PROCESS_OPTIONS.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          )}
        </div>
        <button className="btn-primary" onClick={() => createMut.mutate()} disabled={!form.name || createMut.isPending}>
          {createMut.isPending ? <Loader className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Register Source
        </button>
      </div>

      {/* Sources list */}
      {isLoading ? (
        <div className="glass-card p-6 space-y-2">
          {[1,2,3].map(i => <div key={i} className="skeleton h-10" />)}
        </div>
      ) : sources.length === 0 ? (
        <div className="glass-card p-10 text-center text-slate-600">
          <Database className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <div>No sources yet. Register one above.</div>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="data-table">
            <thead>
              <tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th><th>Registered</th><th></th></tr>
            </thead>
            <tbody>
              {sources.map(s => (
                <tr key={s.id}>
                  <td className="text-slate-600 font-mono text-xs">{s.id}</td>
                  <td className="font-medium text-slate-200">{s.name}</td>
                  <td><span className="badge badge-blue">{s.type}</span></td>
                  <td>
                    <span className={`badge ${s.enabled ? 'badge-green' : 'badge-gray'}`}>
                      {s.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="text-slate-500 text-xs">{new Date(s.created_at).toLocaleString()}</td>
                  <td>
                    <button className="btn-secondary text-xs py-1 px-2"
                      onClick={() => syncMut.mutate(s.id)}
                      disabled={syncId === s.id}>
                      {syncId === s.id
                        ? <><Loader className="w-3 h-3 animate-spin" /> Syncing...</>
                        : <><RefreshCw className="w-3 h-3" /> Sync</>}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
