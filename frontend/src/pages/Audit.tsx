import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type AuditEvent } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { ClipboardList, Clock, Filter, User } from 'lucide-react'

const ENTITY_TYPES = ['', 'sync', 'extraction', 'decision', 'approval', 'action', 'evaluation']

export default function Audit() {
  const [entityType, setEntityType] = useState('')

  const { data: events = [], isLoading, error, refetch } = useQuery({
    queryKey: ['audit', entityType],
    queryFn: () => api.audit.list({ entity_type: entityType || undefined, limit: 100 }),
    refetchInterval: 30_000,
  })

  if (error) return <ErrorState error={error as Error} title="Could not load audit log" onRetry={refetch} />

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <ClipboardList style={{ width: 22, height: 22, color: '#D9641E' }} />
            Audit Log
          </h1>
          <p className="page-subtitle">Immutable chronological timeline of all system events and actor interventions.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <Filter style={{ width: 13, height: 13, color: '#A0917F' }} />
          <select className="select" style={{ width: 176, paddingBlock: '0.4375rem', fontSize: '0.8125rem' }} value={entityType} onChange={e => setEntityType(e.target.value)}>
            {ENTITY_TYPES.map(t => <option key={t} value={t}>{t ? t.toUpperCase() : 'All entity types'}</option>)}
          </select>
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3, 4, 5].map(i => <div key={i} className="skeleton h-12" />)}
          </div>
        ) : events.length === 0 ? (
          <EmptyState icon={ClipboardList} title="No audit events found" message="Events will be recorded as the platform operates." />
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Entity Type</th>
                  <th>Event Type</th>
                  <th>Actor</th>
                  <th>Entity ID</th>
                  <th>Payload</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev: AuditEvent) => (
                  <tr key={ev.id}>
                    <td className="font-mono text-ink-400 text-xs">#{ev.id}</td>
                    <td>
                      <span className="badge badge-gray text-2xs uppercase">{ev.entity_type}</span>
                    </td>
                    <td className="text-xs font-semibold text-ink-800">{ev.event_type}</td>
                    <td>
                      <div className="flex items-center gap-1.5 text-xs text-ink-600">
                        <User className="w-3 h-3 text-ink-400" />
                        {ev.actor || 'system'}
                      </div>
                    </td>
                    <td className="font-mono text-xs text-ink-500">{ev.entity_id || '—'}</td>
                    <td className="max-w-xs truncate text-xs font-mono text-ink-600">
                      {JSON.stringify(ev.payload || ev.payload_json)}
                    </td>
                    <td className="text-2xs text-ink-400 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(ev.created_at).toLocaleString()}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
