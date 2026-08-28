import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api, type AuditEvent } from '../lib/api'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { BarChart2, Play, Loader, Trophy, Clock, CheckCircle2 } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

type EvalSummary = Record<string, {
  n: number
  accuracy: number
  confidence_pass_rate: number
  escalation_accuracy: number
}>

function timeStr(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function Evaluation() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const runMut = useMutation({
    mutationFn: () => api.evaluation.run(),
    onSuccess: (data) => setResult(data),
  })

  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ['evaluation-runs'],
    queryFn: () => api.evaluation.runs(20),
  })

  const summary = result?.summary as EvalSummary | undefined
  const chartData = summary
    ? Object.entries(summary).map(([strategy, m]) => ({
        name: strategy.replace(/baseline_/g, '').replace(/_/g, ' '),
        Accuracy:       Math.round(m.accuracy * 100),
        'Conf. Pass':   Math.round(m.confidence_pass_rate * 100),
        'Escalation':   Math.round(m.escalation_accuracy * 100),
      }))
    : []

  const bestStrategy = summary
    ? Object.entries(summary).sort((a, b) => b[1].accuracy - a[1].accuracy)[0]
    : null

  return (
    <div className="space-y-6 fade-in-up">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <BarChart2 style={{ width: 22, height: 22, color: '#D9641E' }} />
            Evaluation
          </h1>
          <p className="page-subtitle">
            Benchmark OKI against evaluation fixtures and compare baseline strategies.
          </p>
        </div>
        <button
          className="btn-gold"
          id="run-evaluation-btn"
          onClick={() => { setResult(null); runMut.mutate() }}
          disabled={runMut.isPending}
        >
          {runMut.isPending
            ? <><Loader style={{ width: 14, height: 14 }} className="animate-spin" />Running…</>
            : <><Play style={{ width: 14, height: 14 }} />Run Evaluation</>}
        </button>
      </div>

      {/* In-progress */}
      {runMut.isPending && (
        <div className="card p-8 text-center space-y-3">
          <Loader style={{ width: 28, height: 28, color: '#D9641E', margin: '0 auto' }} className="animate-spin" />
          <div className="font-display font-semibold text-ink-700" style={{ fontSize: '0.9375rem' }}>Running agent against evaluation fixtures…</div>
          <div className="text-ink-400" style={{ fontSize: '0.8125rem' }}>This may take 30–60 seconds depending on the LLM.</div>
        </div>
      )}

      {/* Error */}
      {runMut.error && !runMut.isPending && (
        <ErrorState
          error={runMut.error as Error}
          title="Evaluation failed"
          onRetry={() => runMut.mutate()}
        />
      )}

      {/* Results */}
      {result && !runMut.isPending && (
        <div className="space-y-5">
          {/* Best strategy banner */}
          {bestStrategy && (
            <div className="card p-5 border border-amber-200 bg-amber-50/30 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
                <Trophy className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <div className="text-sm font-semibold text-ink-800">Best: {bestStrategy[0]}</div>
                <div className="text-xs text-ink-500 mt-0.5">
                  Accuracy {(bestStrategy[1].accuracy * 100).toFixed(0)}% ·
                  Confidence pass {(bestStrategy[1].confidence_pass_rate * 100).toFixed(0)}% ·
                  Escalation accuracy {(bestStrategy[1].escalation_accuracy * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          )}

          {/* Bar chart */}
          {chartData.length > 0 && (
            <div className="card p-5">
              <div className="section-title mb-4">Strategy Comparison (%)</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData} margin={{ left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E0D6" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: '#9E8E82', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#9E8E82', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: '#EDE7DE',
                      border: '1px solid #D6CEC4',
                      borderRadius: 12,
                      fontSize: 12,
                      boxShadow: '0 4px 16px rgba(44,41,38,0.10)',
                    }}
                    formatter={(v: number) => [`${v}%`]}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#9E8E82' }} />
                  <Bar dataKey="Accuracy"    fill="#2D7A4F" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Conf. Pass"  fill="#C97040" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Escalation"  fill="#1C5C8B" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Summary table */}
          {summary && (
            <div className="card overflow-hidden">
              <div className="px-5 py-4 border-b border-canvas-border section-title">Per-Strategy Results</div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Strategy</th>
                      <th>N</th>
                      <th>Accuracy</th>
                      <th>Confidence Pass</th>
                      <th>Escalation Acc.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(summary).map(([strategy, m]) => (
                      <tr key={strategy}>
                        <td className="font-mono text-xs text-ink-600">{strategy}</td>
                        <td className="font-mono text-ink-400">{m.n}</td>
                        <td>
                          <span className={`badge text-2xs ${
                            m.accuracy >= 0.7 ? 'badge-green' : m.accuracy >= 0.5 ? 'badge-yellow' : 'badge-red'
                          }`}>
                            {(m.accuracy * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="font-mono text-xs text-ink-600">{(m.confidence_pass_rate * 100).toFixed(0)}%</td>
                        <td className="font-mono text-xs text-ink-600">{(m.escalation_accuracy * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !runMut.isPending && !runMut.error && (
        <div className="card">
          <EmptyState
            icon={BarChart2}
            title="No evaluation run yet"
            message='Click "Run Evaluation" to benchmark the agent against the dev fixtures.'
          />
        </div>
      )}

      {/* Past runs */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-canvas-border section-title">Past Evaluation Runs</div>
        {runsLoading ? (
          <div className="p-4 space-y-2">
            {[1, 2].map((i) => <div key={i} className="skeleton h-10" />)}
          </div>
        ) : runs.length === 0 ? (
          <div className="px-5 py-8 text-center text-xs text-ink-400">No past runs found.</div>
        ) : (
          <div className="divide-y divide-canvas-border">
            {runs.map((r: AuditEvent) => (
              <div key={r.id} className="px-5 py-3 flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-risk-low flex-shrink-0" />
                <div className="flex-1 text-xs text-ink-600 font-mono truncate">
                  {r.event_type} · {r.actor || 'system'}
                </div>
                <div className="flex items-center gap-1 text-2xs text-ink-400 flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  {timeStr(r.created_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
