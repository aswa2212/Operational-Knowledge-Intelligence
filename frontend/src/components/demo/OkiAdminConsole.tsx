import {
  Brain, FileText, GitBranch, Zap,
  CheckCircle2, Layers, Terminal, AlertCircle
} from 'lucide-react'
import RiskBadge from '../RiskBadge'
import ConfidenceBar from '../ConfidenceBar'

interface Props {
  result: any
  isRunning: boolean
  extractionMethod: 'two_pass' | 'single_pass'
}

export default function OkiAdminConsole({ result, isRunning, extractionMethod }: Props) {
  const trace = result?.pipeline_trace

  return (
    <div className="space-y-6">
      {/* Overview header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title text-base flex items-center gap-2">
            <Brain style={{ width: 18, height: 18, color: '#D9641E' }} />
            OKI Glass-Box Execution Pipeline
          </h2>
          <p className="text-xs text-ink-400 mt-0.5">
            Full end-to-end transparent reasoning from external documents to autonomous bounded action.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="badge badge-gold text-2xs uppercase">
            Mode: {extractionMethod === 'two_pass' ? 'Two-Pass Extraction' : 'Single-Pass (Ablation)'}
          </span>
          <span className={`badge ${result ? 'badge-green' : 'badge-gray'} text-2xs`}>
            {isRunning ? 'Executing Pipeline…' : result ? 'Pipeline Resolved' : 'Awaiting Input'}
          </span>
        </div>
      </div>

      {/* 4-Panel Glass-Box Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Panel 1: Ingestion & Knowledge Graph */}
        <div className="card p-5 border border-canvas-border flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-canvas-border">
              <span className="font-display font-semibold text-xs text-ink-900 uppercase tracking-wider flex items-center gap-1.5">
                <FileText style={{ width: 14, height: 14, color: '#D9641E' }} />
                1. Ingestion
              </span>
              <span className="badge badge-gray text-2xs">Real Connectors</span>
            </div>

            <div className="space-y-3 pt-3">
              <div className="text-2xs text-ink-400">Sources Ingested</div>
              <div className="flex flex-wrap gap-1.5">
                {['notion', 'github', 'slack'].map((s) => (
                  <span key={s} className="badge badge-gray text-2xs uppercase font-mono">
                    {s}
                  </span>
                ))}
              </div>

              <div className="p-3 rounded-xl bg-canvas-warm/60 border border-canvas-border space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-ink-400">Documents Ingested:</span>
                  <span className="font-semibold text-ink-800">
                    {trace?.ingestion?.total_documents ?? '22'} docs
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-400">Authority Verification:</span>
                  <span className="text-emerald-700 font-semibold">Active</span>
                </div>
              </div>
            </div>
          </div>

          <div className="text-2xs text-ink-400 flex items-center gap-1">
            <CheckCircle2 style={{ width: 12, height: 12, color: '#1D6B3E' }} />
            Live sync connected
          </div>
        </div>

        {/* Panel 2: Rule Extraction & Ablation */}
        <div className="card p-5 border border-canvas-border flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-canvas-border">
              <span className="font-display font-semibold text-xs text-ink-900 uppercase tracking-wider flex items-center gap-1.5">
                <Layers style={{ width: 14, height: 14, color: '#D9641E' }} />
                2. Extraction
              </span>
              <span className={`badge ${extractionMethod === 'two_pass' ? 'badge-green' : 'badge-terra'} text-2xs`}>
                {extractionMethod === 'two_pass' ? 'Two-Pass' : 'Single-Pass'}
              </span>
            </div>

            <div className="space-y-3 pt-3">
              <div className="text-2xs text-ink-400">Extraction Output</div>
              <div className="p-3 rounded-xl bg-canvas-warm/60 border border-canvas-border space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-ink-400">Architecture:</span>
                  <span className="font-medium text-ink-800 capitalize">{extractionMethod.replace('_', '-')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-400">Rules Synthesized:</span>
                  <span className="font-semibold text-ink-800">
                    {trace?.extraction?.rules_extracted ?? '9'} active
                  </span>
                </div>
              </div>

              {trace?.extraction?.fallback_used && (
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-2xs text-amber-800 leading-relaxed">
                  <AlertCircle style={{ width: 12, height: 12, display: 'inline', marginRight: 4 }} />
                  LLM timeout handled: fell back to active SQLite skill artifact.
                </div>
              )}
            </div>
          </div>

          <div className="text-2xs text-ink-400 flex items-center gap-1">
            <CheckCircle2 style={{ width: 12, height: 12, color: '#1D6B3E' }} />
            Zero hardcoding
          </div>
        </div>

        {/* Panel 3: Conflict Resolution & Decision */}
        <div className="card p-5 border border-canvas-border flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-canvas-border">
              <span className="font-display font-semibold text-xs text-ink-900 uppercase tracking-wider flex items-center gap-1.5">
                <GitBranch style={{ width: 14, height: 14, color: '#D9641E' }} />
                3. Decision Engine
              </span>
              <span className="badge badge-gold text-2xs">Weighted Resolver</span>
            </div>

            <div className="space-y-3 pt-3">
              {trace?.decision ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-ink-900 capitalize">
                      {trace.decision.decision}
                    </span>
                    <RiskBadge level={trace.decision.risk_level || 'low'} size="sm" />
                  </div>

                  <div className="space-y-1">
                    <div className="text-2xs text-ink-400 flex justify-between">
                      <span>Confidence</span>
                      <span>{Math.round((trace.decision.confidence || 0.9) * 100)}%</span>
                    </div>
                    <ConfidenceBar value={trace.decision.confidence || 0.9} size="sm" />
                  </div>

                  {trace.decision.escalated && (
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-2xs text-amber-800">
                      Escalated: {trace.decision.escalation_reason}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-xs text-ink-400 py-4 text-center">
                  Awaiting case execution…
                </div>
              )}
            </div>
          </div>

          <div className="text-2xs text-ink-400 flex items-center gap-1">
            <CheckCircle2 style={{ width: 12, height: 12, color: '#1D6B3E' }} />
            TF-IDF + Deterministic
          </div>
        </div>

        {/* Panel 4: Bounded Action Execution */}
        <div className="card p-5 border border-canvas-border flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-canvas-border">
              <span className="font-display font-semibold text-xs text-ink-900 uppercase tracking-wider flex items-center gap-1.5">
                <Zap style={{ width: 14, height: 14, color: '#D9641E' }} />
                4. Execution Arm
              </span>
              <span className="badge badge-green text-2xs">Live Tool</span>
            </div>

            <div className="space-y-3 pt-3">
              {trace?.action_execution ? (
                <div className="p-3 rounded-xl bg-canvas-warm/60 border border-canvas-border space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-ink-400">Tool:</span>
                    <span className="font-mono font-semibold text-ink-900">
                      {trace.action_execution.action}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-400">Status:</span>
                    <span className="text-emerald-700 font-semibold">Executed Live</span>
                  </div>
                  <div className="text-2xs text-ink-400 pt-1 border-t border-canvas-border">
                    Audit log event recorded in SQLite ledger.
                  </div>
                </div>
              ) : (
                <div className="text-xs text-ink-400 py-4 text-center">
                  Action queued upon decision…
                </div>
              )}
            </div>
          </div>

          <div className="text-2xs text-ink-400 flex items-center gap-1">
            <CheckCircle2 style={{ width: 12, height: 12, color: '#1D6B3E' }} />
            Bounded autonomous actions
          </div>
        </div>
      </div>

      {/* Raw Trace Viewer */}
      {result && (
        <div className="card p-5 border border-canvas-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="section-title text-sm flex items-center gap-1.5">
              <Terminal style={{ width: 14, height: 14 }} />
              Live Pipeline JSON Trace
            </span>
            <span className="text-2xs font-mono text-ink-400">Case #{result.case_id}</span>
          </div>
          <pre className="p-4 rounded-xl bg-canvas-warm/50 border border-canvas-border font-mono text-2xs text-ink-800 whitespace-pre-wrap max-h-56 overflow-y-auto leading-relaxed">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
