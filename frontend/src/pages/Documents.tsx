import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Document } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { FileText, ChevronRight, ExternalLink } from 'lucide-react'

export default function Documents() {
  const [selected, setSelected] = useState<number | null>(null)
  const [sourceType, setSourceType] = useState('')

  const { data: docs = [], isLoading, error, refetch } = useQuery({
    queryKey: ['documents', sourceType],
    queryFn: () => api.documents.list({ source_type: sourceType || undefined, limit: 100 }),
    refetchInterval: 5_000,
  })

  const { data: fullDoc } = useQuery({
    queryKey: ['document', selected],
    queryFn: () => api.documents.get(selected!),
    enabled: selected !== null,
    refetchInterval: 5_000,
  })

  const SOURCE_TYPES = ['', 'github', 'notion', 'slack', 'synthetic']

  if (error) return <ErrorState error={error as Error} title="Could not load documents" onRetry={refetch} />

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <FileText style={{ width: 22, height: 22, color: '#D9641E' }} />
            Documents
          </h1>
          <p className="page-subtitle">All ingested unstructured knowledge from connected sources.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <label className="font-display text-xs font-medium text-ink-400">Source Type:</label>
          <select className="select" style={{ width: 148, paddingBlock: '0.4375rem', fontSize: '0.8125rem' }} value={sourceType} onChange={e => setSourceType(e.target.value)}>
            {SOURCE_TYPES.map(t => <option key={t} value={t}>{t ? t.toUpperCase() : 'All types'}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-5">
        {/* List */}
        <div className="col-span-2 card overflow-hidden">
          {isLoading ? (
            <div className="p-4 space-y-2">{[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-14" />)}</div>
          ) : docs.length === 0 ? (
            <EmptyState icon={FileText} title="No documents found" message="Sync a source first to ingest documents." />
          ) : (
            <div className="divide-y divide-canvas-border max-h-[600px] overflow-y-auto">
              {docs.map((d: Document) => (
                <button
                  key={d.id}
                  onClick={() => setSelected(d.id)}
                  className={`w-full text-left px-4 py-3.5 hover:bg-canvas-warm/60 transition-colors flex items-center justify-between ${
                    selected === d.id ? 'bg-canvas-warm border-l-2 border-ink-800' : ''
                  }`}
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-display font-medium text-sm text-ink-800 truncate">{d.title || d.author_handle || `Document #${d.id}`}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="badge badge-gray text-2xs uppercase">{d.source_type}</span>
                      <span className="text-2xs text-ink-400">{new Date(d.timestamp).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <ChevronRight style={{ width: 14, height: 14, color: '#C2B8A8' }} />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail Viewer */}
        <div className="col-span-3">
          {fullDoc ? (
            <div className="card p-6 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="section-title text-base">{fullDoc.title || `Document #${fullDoc.id}`}</h2>
                  <div className="flex items-center gap-2 mt-1 text-2xs text-ink-400">
                    <span>Source: <strong className="text-ink-700 uppercase">{fullDoc.source_type}</strong></span>
                    <span>•</span>
                    <span>Author: <strong className="text-ink-700">{fullDoc.author_role || fullDoc.author_handle || 'Unknown'}</strong></span>
                  </div>
                </div>
                {fullDoc.url && (
                  <a href={fullDoc.url} target="_blank" rel="noreferrer" className="btn-secondary btn-xs gap-1">
                    Open <ExternalLink style={{ width: 11, height: 11 }} />
                  </a>
                )}
              </div>

              <div className="p-4 rounded-xl border border-canvas-border bg-canvas-warm/40 font-mono text-xs text-ink-800 whitespace-pre-wrap max-h-[460px] overflow-y-auto leading-relaxed">
                {fullDoc.raw_content || fullDoc.text || 'No content available.'}
              </div>
            </div>
          ) : (
            <div className="card h-full">
              <EmptyState icon={FileText} title="Select a document" message="Click any document from the list to view its full content and metadata." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
