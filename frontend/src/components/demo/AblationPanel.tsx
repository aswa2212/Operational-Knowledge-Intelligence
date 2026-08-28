import { Sliders, Info } from 'lucide-react'

interface Props {
  method: 'two_pass' | 'single_pass'
  onChange: (method: 'two_pass' | 'single_pass') => void
  disabled?: boolean
}

export default function AblationPanel({ method, onChange, disabled }: Props) {
  return (
    <div className="card p-5 border border-canvas-border space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sliders style={{ width: 16, height: 16, color: '#D9641E' }} />
          <h3 className="section-title">Ablation: Extraction Architecture</h3>
        </div>
        <span className="badge badge-gold text-2xs">Ablation 1</span>
      </div>

      <p className="text-xs text-ink-600 leading-relaxed">
        Compare <strong>Single-Pass vs Two-Pass Extraction</strong> across your real connected documents.
      </p>

      {/* Toggle selector */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange('two_pass')}
          className={`p-3.5 rounded-xl text-left border transition-all ${
            method === 'two_pass'
              ? 'border-ink-800 bg-canvas-warm shadow-card-md'
              : 'border-canvas-border bg-canvas/60 hover:bg-canvas-warm/40'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-display font-semibold text-sm text-ink-900">Two-Pass Extraction</span>
            {method === 'two_pass' && <span className="badge badge-green text-2xs">Standard OKI</span>}
          </div>
          <p className="text-2xs text-ink-400 leading-relaxed">
            Pass 1 identifies rule boundaries; Pass 2 structures conditions & actions. High precision.
          </p>
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange('single_pass')}
          className={`p-3.5 rounded-xl text-left border transition-all ${
            method === 'single_pass'
              ? 'border-ink-800 bg-canvas-warm shadow-card-md'
              : 'border-canvas-border bg-canvas/60 hover:bg-canvas-warm/40'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-display font-semibold text-sm text-ink-900">Single-Pass Extraction</span>
            {method === 'single_pass' && <span className="badge badge-terra text-2xs">Ablation Mode</span>}
          </div>
          <p className="text-2xs text-ink-400 leading-relaxed">
            Direct single LLM prompt per document. Faster but lower constraint accuracy.
          </p>
        </button>
      </div>

      <div className="flex items-start gap-2.5 p-3 rounded-xl bg-canvas-warm/50 border border-canvas-border text-2xs text-ink-400 leading-relaxed">
        <Info style={{ width: 14, height: 14, color: '#A0917F', flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>Note:</strong> This toggle evaluates <em>Extraction Method</em>. Conflict resolution strategy ablation (Weighted vs Recency-only / Authority-only) is benchmarked in the Evaluation tab.
        </span>
      </div>
    </div>
  )
}
