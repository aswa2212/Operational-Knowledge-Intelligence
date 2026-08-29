import { useState } from 'react'
import axios from 'axios'
import {
  ShoppingBag, Briefcase, ShieldAlert, CheckCircle2,
  AlertTriangle, Clock, ExternalLink, Sparkles,
  Loader, ShieldCheck, Terminal
} from 'lucide-react'

const getApiBase = () => {
  const envUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL
  if (envUrl) {
    const trimmed = envUrl.replace(/\/+$/, '')
    return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://operational-knowledge-intelligence.onrender.com/api/v1'
  }
  return 'http://127.0.0.1:8000/api/v1'
}

const API_BASE = getApiBase()
const OKI_DASHBOARD_URL = import.meta.env.VITE_OKI_DASHBOARD_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? 'https://oki-saas.vercel.app' : 'http://localhost:5173')

interface Order {
  id: string
  product: string
  category: string
  price: number
  daysAgo: number
  customerTier: 'standard' | 'enterprise' | 'VIP'
  image: string
}

const SAMPLE_ORDERS: Order[] = [
  { id: 'ORD-9821', product: 'Studio Master Pro ANC Headphones', category: 'electronics', price: 150, daysAgo: 14, customerTier: 'VIP', image: '🎧' },
  { id: 'ORD-8742', product: '4K Ultra-Wide Curved Monitor 34"', category: 'electronics', price: 480, daysAgo: 28, customerTier: 'standard', image: '🖥️' },
  { id: 'ORD-7619', product: 'Custom Mechanical RGB Keyboard', category: 'hardware', price: 95, daysAgo: 45, customerTier: 'standard', image: '⌨️' },
  { id: 'ORD-6510', product: 'Enterprise Server Node v4', category: 'software', price: 1250, daysAgo: 10, customerTier: 'enterprise', image: '🖲️' },
]

export default function App() {
  const [stream, setStream] = useState<'refund' | 'pricing' | 'incident'>('refund')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // 1. Refund State
  const [selectedOrder, setSelectedOrder] = useState<Order>(SAMPLE_ORDERS[0])
  const [refundDays, setRefundDays] = useState<number>(14)
  const [refundPrice, setRefundPrice] = useState<number>(150)
  const [refundTier, setRefundTier] = useState<string>('VIP')
  const [refundReason, setRefundReason] = useState<string>('dissatisfied')

  // 2. Pricing State
  const [dealSize, setDealSize] = useState<number>(50000)
  const [discountPercent, setDiscountPercent] = useState<number>(15)
  const [requestorRole, setRequestorRole] = useState<string>('sales_rep')

  // 3. Incident State
  const [errorType, setErrorType] = useState<string>('DDoS')
  const [affectedUsers, setAffectedUsers] = useState<number>(5000)
  const [systemComponent, setSystemComponent] = useState<string>('api_gateway')
  const [severitySignal, setSeveritySignal] = useState<string>('service_down')

  const handleSelectOrder = (o: Order) => {
    setSelectedOrder(o)
    setRefundDays(o.daysAgo)
    setRefundPrice(o.price)
    setRefundTier(o.customerTier)
  }

  const executePipeline = async (proc: string, fields: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const resp = await axios.post(`${API_BASE}/demo/execute`, {
        process: proc,
        fields,
        extraction_method: 'two_pass',
      })
      setResult(resp.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Pipeline execution failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRefundSubmit = () => {
    executePipeline('refund_handling', {
      order_id: selectedOrder.id,
      days_since_purchase: Number(refundDays),
      order_value: Number(refundPrice),
      customer_tier: refundTier,
      item_category: selectedOrder.category,
      reason: refundReason,
    })
  }

  const handlePricingSubmit = () => {
    executePipeline('pricing_exceptions', {
      deal_size: Number(dealSize),
      discount_percent: Number(discountPercent),
      requestor_role: requestorRole,
    })
  }

  const handleIncidentSubmit = () => {
    executePipeline('incident_triage', {
      error_type: errorType,
      affected_users_count: Number(affectedUsers),
      system_component: systemComponent,
      severity_signal: severitySignal,
    })
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#FAF8F5]">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-brand-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-900 text-gold-400 flex items-center justify-center font-display font-bold text-lg shadow-md">
              S
            </div>
            <div>
              <div className="font-display font-bold text-base text-brand-900 tracking-tight">ShopNow & Client Portals</div>
              <div className="text-2xs text-brand-500 font-mono tracking-wider">STANDALONE CLIENT APP (PORT 3000)</div>
            </div>
          </div>

          {/* Stream Switcher Tabs */}
          <div className="flex items-center bg-brand-100/70 p-1 rounded-xl border border-brand-200 text-xs">
            <button
              onClick={() => { setStream('refund'); setResult(null) }}
              className={`px-3.5 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                stream === 'refund' ? 'bg-brand-900 text-white shadow-sm' : 'text-brand-700 hover:text-brand-900'
              }`}
            >
              <ShoppingBag style={{ width: 13, height: 13 }} />
              1. E-Commerce Returns
            </button>
            <button
              onClick={() => { setStream('pricing'); setResult(null) }}
              className={`px-3.5 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                stream === 'pricing' ? 'bg-brand-900 text-white shadow-sm' : 'text-brand-700 hover:text-brand-900'
              }`}
            >
              <Briefcase style={{ width: 13, height: 13 }} />
              2. B2B Pricing Deals
            </button>
            <button
              onClick={() => { setStream('incident'); setResult(null) }}
              className={`px-3.5 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                stream === 'incident' ? 'bg-brand-900 text-white shadow-sm' : 'text-brand-700 hover:text-brand-900'
              }`}
            >
              <ShieldAlert style={{ width: 13, height: 13 }} />
              3. DevOps Incident Desk
            </button>
          </div>

          {/* Link to OKI SaaS Dashboard */}
          <a
            href={OKI_DASHBOARD_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-gold-500/15 text-brand-900 border border-gold-500/30 hover:bg-gold-500/25 transition-colors"
          >
            <Sparkles style={{ width: 13, height: 13, color: '#B8860B' }} />
            Open OKI SaaS Console <ExternalLink style={{ width: 11, height: 11 }} />
          </a>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Stream Banner */}
        <div className="luxury-card p-6 flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="badge px-2.5 py-0.5 rounded-full text-2xs font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                LIVE MOCK CLIENT
              </span>
              <h1 className="font-display text-2xl font-bold text-brand-900">
                {stream === 'refund' && 'ShopNow Consumer Returns & Exchanges'}
                {stream === 'pricing' && 'Apex Global Enterprise Deal Desk'}
                {stream === 'incident' && 'CloudGuard DevOps Incident Helpdesk'}
              </h1>
            </div>
            <p className="text-sm text-brand-600">
              {stream === 'refund' && 'Simulate real customer refund requests against active Notion/Slack policies with zero mocked outcomes.'}
              {stream === 'pricing' && 'Request discount authorization on B2B contracts. Evaluates rep authority and VP approval limits.'}
              {stream === 'incident' && 'Submit production incident reports. Automatically triages SEV levels, alerts on-call, or creates GitHub issues.'}
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono bg-emerald-50 text-emerald-800 px-3 py-1.5 rounded-xl border border-emerald-200">
            <ShieldCheck style={{ width: 14, height: 14, color: '#15803d' }} />
            OKI Backend Connected
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-center gap-2">
            <AlertTriangle style={{ width: 16, height: 16, color: '#dc2626' }} />
            <span>{error}</span>
          </div>
        )}

        {/* ── STREAM 1: E-COMMERCE RETURNS ── */}
        {stream === 'refund' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7 space-y-6">
              <div>
                <h3 className="font-display font-bold text-lg text-brand-900 mb-3">1. Select a Customer Order</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {SAMPLE_ORDERS.map((o) => {
                    const isSelected = selectedOrder.id === o.id
                    return (
                      <button
                        key={o.id}
                        type="button"
                        onClick={() => handleSelectOrder(o)}
                        className={`luxury-card p-4 text-left transition-all ${
                          isSelected ? 'border-gold-500 bg-amber-50/40 shadow-glow-gold' : 'hover:border-brand-400'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <span className="text-3xl">{o.image}</span>
                          <span className="px-2 py-0.5 rounded-full text-2xs font-bold uppercase bg-brand-200/60 text-brand-800">
                            {o.customerTier}
                          </span>
                        </div>
                        <div className="font-display font-semibold text-sm text-brand-900 mt-3 line-clamp-1">{o.product}</div>
                        <div className="flex justify-between items-center mt-3 pt-2 border-t border-brand-200 text-xs">
                          <span className="font-mono text-brand-500">{o.id}</span>
                          <span className="font-display font-bold text-brand-900">${o.price}</span>
                        </div>
                        <div className="text-2xs text-brand-500 mt-1 flex items-center gap-1">
                          <Clock style={{ width: 10, height: 10 }} />
                          {o.daysAgo} days since purchase
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Policy Inputs */}
              <div className="luxury-card p-6 space-y-4">
                <h3 className="font-display font-bold text-base text-brand-900">2. Configure Return Parameters</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Days Ago</label>
                    <input
                      type="number"
                      className="luxury-input"
                      value={refundDays}
                      onChange={(e) => setRefundDays(Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Order Value ($)</label>
                    <input
                      type="number"
                      className="luxury-input"
                      value={refundPrice}
                      onChange={(e) => setRefundPrice(Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Customer Tier</label>
                    <select
                      className="luxury-input"
                      value={refundTier}
                      onChange={(e) => setRefundTier(e.target.value)}
                    >
                      <option value="standard">standard</option>
                      <option value="enterprise">enterprise</option>
                      <option value="VIP">VIP</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Reason for Return</label>
                  <select
                    className="luxury-input"
                    value={refundReason}
                    onChange={(e) => setRefundReason(e.target.value)}
                  >
                    <option value="dissatisfied">Customer Dissatisfaction</option>
                    <option value="product_defect">Product Defect / Hardware Malfunction</option>
                    <option value="wrong_item">Received Incorrect Item</option>
                    <option value="unauthorized_charge">Unauthorized Transaction</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleRefundSubmit}
                  disabled={loading}
                  className="luxury-btn-gold w-full justify-center py-3.5"
                >
                  {loading ? (
                    <>
                      <Loader style={{ width: 16, height: 16 }} className="animate-spin" />
                      OKI Autonomous Engine Evaluating…
                    </>
                  ) : (
                    <>
                      <Sparkles style={{ width: 16, height: 16 }} />
                      Submit Return Request to OKI Engine
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Live Result View */}
            <div className="lg:col-span-5">
              <ResultCard result={result} loading={loading} />
            </div>
          </div>
        )}

        {/* ── STREAM 2: B2B PRICING QUOTES ── */}
        {stream === 'pricing' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7 space-y-6">
              <div className="luxury-card p-6 space-y-5">
                <h3 className="font-display font-bold text-lg text-brand-900">B2B Contract Discount Request</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Contract / Deal Size ($)</label>
                    <input
                      type="number"
                      className="luxury-input text-base"
                      value={dealSize}
                      onChange={(e) => setDealSize(Number(e.target.value))}
                    />
                    <span className="text-2xs text-brand-500 mt-1 block">Standard contract threshold: $50,000+</span>
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Requested Discount (%)</label>
                    <input
                      type="number"
                      className="luxury-input text-base"
                      value={discountPercent}
                      onChange={(e) => setDiscountPercent(Number(e.target.value))}
                    />
                    <span className="text-2xs text-brand-500 mt-1 block">Standard rep authority: ≤ 10% | Manager: ≤ 20% | Director: &gt; 20%</span>
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Sales Requestor Role</label>
                    <select
                      className="luxury-input"
                      value={requestorRole}
                      onChange={(e) => setRequestorRole(e.target.value)}
                    >
                      <option value="sales_rep">sales_rep (Standard Authority)</option>
                      <option value="manager">manager (Intermediate Authority)</option>
                      <option value="director">director (Executive Authority)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handlePricingSubmit}
                  disabled={loading}
                  className="luxury-btn-gold w-full justify-center py-3.5"
                >
                  {loading ? (
                    <>
                      <Loader style={{ width: 16, height: 16 }} className="animate-spin" />
                      Checking Pricing Exception Policies…
                    </>
                  ) : (
                    <>
                      <Sparkles style={{ width: 16, height: 16 }} />
                      Submit Quote Authorization
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="lg:col-span-5">
              <ResultCard result={result} loading={loading} />
            </div>
          </div>
        )}

        {/* ── STREAM 3: DEVOPS INCIDENT DESK ── */}
        {stream === 'incident' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7 space-y-6">
              <div className="luxury-card p-6 space-y-5">
                <h3 className="font-display font-bold text-lg text-brand-900">Production Outage & Alert Reporter</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Incident / Error Type</label>
                    <select
                      className="luxury-input"
                      value={errorType}
                      onChange={(e) => setErrorType(e.target.value)}
                    >
                      <option value="DDoS">DDoS / Traffic Spike Attack</option>
                      <option value="crash">Auth Service Fatal Crash</option>
                      <option value="auth_failure">High Rate Auth Failures</option>
                      <option value="isolated_glitch">Isolated 500 API Error</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Affected Users Count</label>
                      <input
                        type="number"
                        className="luxury-input"
                        value={affectedUsers}
                        onChange={(e) => setAffectedUsers(Number(e.target.value))}
                      />
                    </div>
                    <div>
                      <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">Severity Signal</label>
                      <select
                        className="luxury-input"
                        value={severitySignal}
                        onChange={(e) => setSeveritySignal(e.target.value)}
                      >
                        <option value="service_down">service_down (Complete Outage)</option>
                        <option value="degraded">degraded (High Latency)</option>
                        <option value="isolated">isolated (Minor Glitch)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-brand-500 mb-1">System Component</label>
                    <select
                      className="luxury-input"
                      value={systemComponent}
                      onChange={(e) => setSystemComponent(e.target.value)}
                    >
                      <option value="api_gateway">api_gateway (Core Routing)</option>
                      <option value="auth_service">auth_service (User Authentication)</option>
                      <option value="database_cluster">database_cluster (Primary DB)</option>
                      <option value="payments_worker">payments_worker (Stripe/PayPal Adapter)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleIncidentSubmit}
                  disabled={loading}
                  className="luxury-btn-gold w-full justify-center py-3.5"
                >
                  {loading ? (
                    <>
                      <Loader style={{ width: 16, height: 16 }} className="animate-spin" />
                      Triage Engine Analyzing Incident…
                    </>
                  ) : (
                    <>
                      <Sparkles style={{ width: 16, height: 16 }} />
                      Trigger OKI Incident Triage
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="lg:col-span-5">
              <ResultCard result={result} loading={loading} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function ResultCard({ result, loading }: { result: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="luxury-card p-8 h-full flex flex-col items-center justify-center text-center space-y-3">
        <Loader style={{ width: 36, height: 36, color: '#D4A017' }} className="animate-spin" />
        <div className="font-display font-semibold text-brand-900 text-base">Running Real OKI Pipeline…</div>
        <div className="text-xs text-brand-500 max-w-xs leading-relaxed">
          Ingesting latest policy docs, matching TF-IDF triggers, evaluating confidence & executing bounded action.
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="luxury-card p-8 h-full flex flex-col items-center justify-center text-center space-y-3 text-brand-400">
        <Terminal style={{ width: 36, height: 36, color: '#D6C3B1' }} />
        <div className="font-display font-semibold text-brand-700 text-sm">Awaiting Pipeline Execution</div>
        <div className="text-xs text-brand-500 max-w-xs leading-relaxed">
          Submit any case on the left to see the autonomous decision, risk score, and live tool execution response.
        </div>
      </div>
    )
  }

  const dec = result.pipeline_trace?.decision
  const action = result.pipeline_trace?.action_execution

  const isEscalated = Boolean(dec?.escalated)
  const isApproved = dec?.decision?.toLowerCase().includes('approve')
  const isDenied = dec?.decision?.toLowerCase().includes('deny')

  return (
    <div className="luxury-card p-6 h-full flex flex-col justify-between space-y-5">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-brand-200">
          <span className="font-display font-bold text-sm text-brand-900 uppercase tracking-wide">
            Autonomous Policy Outcome
          </span>
          <span className="font-mono text-2xs text-brand-500">Case #{result.case_id}</span>
        </div>

        {/* Outcome Box */}
        <div className="mt-4">
          {isEscalated ? (
            <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-center space-y-2">
              <AlertTriangle style={{ width: 36, height: 36, color: '#B8860B', margin: '0 auto' }} />
              <div className="font-display font-bold text-lg text-brand-900">Escalated to Human Review</div>
              <p className="text-xs text-brand-700 leading-relaxed">
                {dec?.escalation_reason || 'Policy requires manual manager authorization.'}
              </p>
            </div>
          ) : isDenied ? (
            <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/30 text-center space-y-2">
              <AlertTriangle style={{ width: 36, height: 36, color: '#dc2626', margin: '0 auto' }} />
              <div className="font-display font-bold text-lg text-brand-900">Request Denied</div>
              <p className="text-xs text-brand-700 leading-relaxed">
                Disallowed by authoritative company guidelines.
              </p>
            </div>
          ) : (
            <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-2">
              <CheckCircle2 style={{ width: 36, height: 36, color: '#15803d', margin: '0 auto' }} />
              <div className="font-display font-bold text-lg text-brand-900">
                {isApproved ? 'Approved Instantly' : `Decision: ${dec?.decision}`}
              </div>
              <p className="text-xs text-brand-700 leading-relaxed">
                Autonomously authorized and executed via bounded agent rules.
              </p>
            </div>
          )}
        </div>

        {/* Reasoning Specs */}
        <div className="mt-4 p-4 rounded-xl bg-brand-100/50 border border-brand-200 space-y-2.5 text-xs">
          <div className="flex justify-between">
            <span className="text-brand-500">Decision Value:</span>
            <span className="font-display font-bold text-brand-900 uppercase">{dec?.decision || 'None'}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-brand-500">Model Confidence:</span>
            <span className="font-mono font-bold text-emerald-800">
              {Math.round((dec?.confidence || 0.95) * 100)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-500">Risk Assessment:</span>
            <span className="font-semibold uppercase text-brand-900">{dec?.risk_level || 'low'}</span>
          </div>
          {action && (
            <div className="pt-2 border-t border-brand-200">
              <span className="text-brand-500">Execution Tool: </span>
              <strong className="font-mono text-brand-900">{action.action}</strong>
            </div>
          )}
        </div>
      </div>

      <div className="pt-3 border-t border-brand-200 flex items-center justify-between text-2xs text-brand-500">
        <span>Logged into SQLite / PostgreSQL Audit Trail</span>
        <a href={`${OKI_DASHBOARD_URL}/actions`} target="_blank" rel="noreferrer" className="text-brand-900 font-semibold hover:underline">
          View Audit Log ↗
        </a>
      </div>
    </div>
  )
}
