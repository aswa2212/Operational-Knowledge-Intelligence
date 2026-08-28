import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import ShopNowPortal from '../components/demo/ShopNowPortal'
import OkiAdminConsole from '../components/demo/OkiAdminConsole'
import AblationPanel from '../components/demo/AblationPanel'
import {
  Sparkles, ShoppingBag, Brain, RotateCcw, AlertTriangle,
} from 'lucide-react'

export default function DemoShowcase() {
  const qc = useQueryClient()
  const [role, setRole] = useState<'shopnow' | 'admin'>('shopnow')
  const [process, setProcess] = useState<string>('refund_handling')
  const [extractionMethod, setExtractionMethod] = useState<'two_pass' | 'single_pass'>('two_pass')
  const [lastResult, setLastResult] = useState<any>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const executeMut = useMutation({
    mutationFn: async (fields: Record<string, unknown>) => {
      setErrorMessage(null)
      return api.demo.execute({
        process,
        fields,
        extraction_method: extractionMethod,
      })
    },
    onSuccess: (data) => {
      setLastResult(data)
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['actions'] })
      qc.invalidateQueries({ queryKey: ['approvals'] })
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || 'Pipeline execution encountered an error.')
    },
  })

  const resetMut = useMutation({
    mutationFn: () => api.demo.reset(),
    onSuccess: () => {
      setLastResult(null)
      setErrorMessage(null)
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['actions'] })
    },
  })

  return (
    <div className="space-y-8 fade-in-up">
      {/* Top Banner & Role Switcher */}
      <div className="hero-strip px-8 py-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Sparkles style={{ width: 22, height: 22, color: '#D4A017' }} />
            <h1 className="page-title">Live Demo Showcase</h1>
            <span className="badge badge-gold text-2xs uppercase">Evaluator Mode</span>
          </div>
          <p className="page-subtitle">
            Demonstrating OKI's real autonomous knowledge ingestion, conflict resolution, and bounded execution.
          </p>
        </div>

        {/* Role & Process Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            className="select text-xs py-1.5"
            style={{ width: 170 }}
            value={process}
            onChange={(e) => setProcess(e.target.value)}
          >
            <option value="refund_handling">Refund Handling</option>
            <option value="pricing_exceptions">Pricing Exceptions</option>
            <option value="incident_triage">Incident Triage</option>
          </select>

          <div className="pill-tabs">
            <button
              type="button"
              onClick={() => setRole('shopnow')}
              className={`pill-tab flex items-center gap-1.5 ${role === 'shopnow' ? 'active' : ''}`}
            >
              <ShoppingBag style={{ width: 14, height: 14 }} />
              ShopNow Customer Portal
            </button>
            <button
              type="button"
              onClick={() => setRole('admin')}
              className={`pill-tab flex items-center gap-1.5 ${role === 'admin' ? 'active' : ''}`}
            >
              <Brain style={{ width: 14, height: 14 }} />
              OKI Glass-Box Admin
            </button>
          </div>

          <button
            type="button"
            onClick={() => resetMut.mutate()}
            disabled={resetMut.isPending}
            className="btn-secondary btn-sm gap-1"
            title="Reset runtime cases & decisions"
          >
            <RotateCcw style={{ width: 12, height: 12 }} />
            Reset
          </button>
        </div>
      </div>

      {/* Error alert if any */}
      {errorMessage && (
        <div className="card p-4 border border-red-500/30 bg-red-500/10 flex items-center gap-3 text-xs text-red-800">
          <AlertTriangle style={{ width: 16, height: 16, color: '#8B1616', flexShrink: 0 }} />
          <span><strong>Execution Note:</strong> {errorMessage}</span>
        </div>
      )}

      {/* Ablation Control Bar */}
      <AblationPanel
        method={extractionMethod}
        onChange={setExtractionMethod}
        disabled={executeMut.isPending}
      />

      {/* Main View Toggle */}
      {role === 'shopnow' ? (
        <ShopNowPortal
          onRunDemo={(fields) => executeMut.mutate(fields)}
          isRunning={executeMut.isPending}
          lastResult={lastResult}
        />
      ) : (
        <OkiAdminConsole
          result={lastResult}
          isRunning={executeMut.isPending}
          extractionMethod={extractionMethod}
        />
      )}
    </div>
  )
}
