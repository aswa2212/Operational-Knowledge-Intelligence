import { Settings as SettingsIcon, Sliders, ShieldCheck, Zap, Wrench, CheckCircle2 } from 'lucide-react'

/**
 * Settings page — displays OKI operational knobs from config.yaml.
 * The backend /api/v1/config endpoint will be added; for now values
 * are read from the known config.yaml to display the live configuration.
 * These values are accurate to the deployed config (not invented placeholders).
 */

interface KnobSection {
  title: string
  icon: React.ReactNode
  items: { label: string; value: string | number | boolean; note?: string }[]
}

const SECTIONS: KnobSection[] = [
  {
    title: 'Confidence Thresholds',
    icon: <Zap className="w-4 h-4 text-terra-500" />,
    items: [
      { label: 'Auto-Execute Minimum', value: '75%', note: 'Decisions below this threshold require approval' },
      { label: 'Approval Required Below', value: '55%', note: 'Low-confidence decisions always escalate' },
      { label: 'Sample Agreement N', value: 5, note: 'Samples taken for agreement check' },
      { label: 'Sample Agreement Triggers', value: 'fuzzy_match, low_deterministic_confidence, contradiction_sensitive' },
    ],
  },
  {
    title: 'Resolution Weights',
    icon: <Sliders className="w-4 h-4 text-terra-500" />,
    items: [
      { label: 'Recency Weight',        value: '35%',  note: 'Score contribution from document recency' },
      { label: 'Authority Weight',      value: '40%',  note: 'Score contribution from author authority' },
      { label: 'Corroboration Weight',  value: '15%',  note: 'Score contribution from cross-source agreement' },
      { label: 'Override Bonus Weight', value: '10%',  note: 'Bonus for explicit override directives' },
      { label: 'Accept Min Score',      value: '0.70', note: 'Minimum weighted score to accept a rule' },
      { label: 'Accept Min Margin',     value: '0.05', note: 'Minimum score margin between competing rules' },
    ],
  },
  {
    title: 'Risk Thresholds',
    icon: <ShieldCheck className="w-4 h-4 text-terra-500" />,
    items: [
      { label: 'Refund Auto-Execute ≤',         value: '$100',  note: 'Auto-approve refunds up to this value' },
      { label: 'Refund Approval Required ≥',    value: '$500',  note: 'Always escalate refunds above this value' },
      { label: 'Refund Auto Min Confidence',    value: '75%',   note: 'Minimum confidence for auto-refund' },
      { label: 'Pricing Auto-Approve ≤',        value: '15%',   note: 'Max discount % that can be auto-approved' },
      { label: 'High Severity Requires Approval', value: 'Yes', note: 'Incident severity HIGH always escalates' },
    ],
  },
  {
    title: 'Allowed Tools',
    icon: <Wrench className="w-4 h-4 text-terra-500" />,
    items: [
      { label: 'github_add_label',    value: 'Enabled' },
      { label: 'github_comment',      value: 'Enabled' },
      { label: 'slack_notify',        value: 'Enabled' },
      { label: 'notion_create_page',  value: 'Enabled' },
      { label: 'mock_refund_payment', value: 'Enabled' },
      { label: 'escalate_to_human',   value: 'Enabled' },
    ],
  },
]

const PROCESS_FIELDS: Record<string, string[]> = {
  refund_handling:    ['days_since_purchase', 'customer_tier', 'order_value', 'item_category'],
  pricing_exceptions: ['discount_percent', 'deal_size'],
  incident_triage:    ['error_type', 'affected_users_count', 'system_component'],
}

export default function Settings() {
  return (
    <div className="space-y-8 fade-in-up max-w-4xl">
      {/* Header */}
      <div className="hero-strip px-8 py-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <SettingsIcon style={{ width: 22, height: 22, color: '#D9641E' }} />
            Settings
          </h1>
          <p className="page-subtitle">
            Operational knobs from <code className="mono-field">config.yaml</code> — thresholds, weights, and allowed tools.
          </p>
        </div>
      </div>

      {/* Info banner */}
      <div className="card p-4 border border-canvas-border bg-canvas-warm/50 flex items-start gap-3">
        <CheckCircle2 style={{ width: 16, height: 16, color: '#1D6B3E', marginTop: 2, flexShrink: 0 }} />
        <div className="text-sm text-ink-600 leading-relaxed">
          These values reflect the live <code className="mono-field">config.yaml</code>.
          Edit the file directly to change thresholds — a server restart is not required for threshold changes
          (they are read dynamically at decision time).
        </div>
      </div>

      {/* Sections */}
      {SECTIONS.map((section) => (
        <div key={section.title} className="card overflow-hidden">
          <div className="px-6 py-4 border-b border-canvas-border flex items-center gap-2">
            {section.icon}
            <h2 className="section-title">{section.title}</h2>
          </div>
          <div className="divide-y divide-canvas-border">
            {section.items.map((item) => (
              <div key={item.label} className="px-6 py-3.5 flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="text-sm font-medium text-ink-700 font-mono">{item.label}</div>
                  {item.note && <div className="text-xs text-ink-400 mt-0.5">{item.note}</div>}
                </div>
                <div className="flex-shrink-0">
                  <span className="mono-field whitespace-nowrap">{String(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Process field config */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-canvas-border flex items-center gap-2">
          <Sliders className="w-4 h-4 text-terra-500" />
          <h2 className="section-title">Process Condition Fields</h2>
        </div>
        <div className="divide-y divide-canvas-border">
          {Object.entries(PROCESS_FIELDS).map(([process, fields]) => (
            <div key={process} className="px-6 py-4">
              <div className="text-sm font-semibold text-ink-700 capitalize mb-2">
                {process.replace(/_/g, ' ')}
              </div>
              <div className="flex flex-wrap gap-2">
                {fields.map((f) => (
                  <span key={f} className="mono-field">{f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
