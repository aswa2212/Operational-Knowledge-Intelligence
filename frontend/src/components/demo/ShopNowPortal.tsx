import { useState } from 'react'
import {
  ShoppingBag, Package, CheckCircle2, AlertTriangle,
  Clock, ShieldCheck, Sparkles, Loader
} from 'lucide-react'
import RiskBadge from '../RiskBadge'
import ConfidenceBar from '../ConfidenceBar'

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
  {
    id: 'ORD-9821',
    product: 'Studio Master Pro ANC Headphones',
    category: 'electronics',
    price: 150,
    daysAgo: 14,
    customerTier: 'VIP',
    image: '🎧',
  },
  {
    id: 'ORD-8742',
    product: '4K Ultra-Wide Curved Monitor 34"',
    category: 'electronics',
    price: 480,
    daysAgo: 28,
    customerTier: 'standard',
    image: '🖥️',
  },
  {
    id: 'ORD-7619',
    product: 'Custom Mechanical RGB Keyboard',
    category: 'hardware',
    price: 95,
    daysAgo: 45,
    customerTier: 'standard',
    image: '⌨️',
  },
  {
    id: 'ORD-6510',
    product: 'Enterprise Server Node v4',
    category: 'software',
    price: 1250,
    daysAgo: 10,
    customerTier: 'enterprise',
    image: '🖲️',
  },
]

interface Props {
  onRunDemo: (fields: Record<string, unknown>) => void
  isRunning: boolean
  lastResult: any
}

export default function ShopNowPortal({ onRunDemo, isRunning, lastResult }: Props) {
  const [selectedOrder, setSelectedOrder] = useState<Order>(SAMPLE_ORDERS[0])
  const [reason, setReason] = useState('dissatisfied')
  const [customDays, setCustomDays] = useState<number>(selectedOrder.daysAgo)
  const [customPrice, setCustomPrice] = useState<number>(selectedOrder.price)
  const [customTier, setCustomTier] = useState<string>(selectedOrder.customerTier)

  const handleSelectOrder = (o: Order) => {
    setSelectedOrder(o)
    setCustomDays(o.daysAgo)
    setCustomPrice(o.price)
    setCustomTier(o.customerTier)
  }

  const handleSubmit = () => {
    onRunDemo({
      order_id: selectedOrder.id,
      days_since_purchase: Number(customDays),
      order_value: Number(customPrice),
      customer_tier: customTier,
      item_category: selectedOrder.category,
      reason,
    })
  }

  return (
    <div className="space-y-6">
      {/* Store Header */}
      <div className="card p-6 bg-gradient-to-r from-canvas-warm via-canvas-card to-canvas-warm border border-canvas-border flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-ink-900 text-gold-400 flex items-center justify-center shadow-card-md text-xl">
            <ShoppingBag style={{ width: 22, height: 22 }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-xl font-bold text-ink-900">ShopNow Retail</h2>
              <span className="badge badge-gold text-2xs">Live E-Commerce Demo</span>
            </div>
            <p className="text-xs text-ink-400 mt-0.5">
              Customer self-service returns portal powered autonomously by OKI intelligence.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="badge badge-green text-xs font-mono">
            <ShieldCheck style={{ width: 12, height: 12, marginRight: 4 }} />
            Policy Engine Connected
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Orders Column */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="section-title">Select Customer Order</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {SAMPLE_ORDERS.map((o) => {
              const isSelected = selectedOrder.id === o.id
              return (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => handleSelectOrder(o)}
                  className={`card p-4 text-left transition-all relative overflow-hidden ${
                    isSelected
                      ? 'border-gold-500/80 bg-canvas-warm shadow-glow-gold'
                      : 'hover:border-ink-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <span className="text-2xl">{o.image}</span>
                    <span className={`badge ${
                      o.customerTier === 'VIP' ? 'badge-gold' : o.customerTier === 'enterprise' ? 'badge-terra' : 'badge-gray'
                    } text-2xs uppercase`}>
                      {o.customerTier}
                    </span>
                  </div>

                  <div className="font-display font-semibold text-sm text-ink-900 mt-2 line-clamp-1">
                    {o.product}
                  </div>

                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-canvas-border text-xs">
                    <span className="font-mono text-ink-400">{o.id}</span>
                    <span className="font-display font-bold text-ink-900">${o.price}</span>
                  </div>

                  <div className="text-2xs text-ink-400 mt-1 flex items-center gap-1">
                    <Clock style={{ width: 11, height: 11 }} />
                    {o.daysAgo} days since purchase
                  </div>
                </button>
              )
            })}
          </div>

          {/* Return Form Details */}
          <div className="card p-5 border border-canvas-border space-y-4">
            <h4 className="section-title text-sm">Fine-Tune Policy Parameters for Evaluation</h4>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label">Days Ago</label>
                <input
                  type="number"
                  className="input text-xs"
                  value={customDays}
                  onChange={(e) => setCustomDays(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="label">Order Value ($)</label>
                <input
                  type="number"
                  className="input text-xs"
                  value={customPrice}
                  onChange={(e) => setCustomPrice(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="label">Customer Tier</label>
                <select
                  className="select text-xs"
                  value={customTier}
                  onChange={(e) => setCustomTier(e.target.value)}
                >
                  <option value="standard">standard</option>
                  <option value="enterprise">enterprise</option>
                  <option value="VIP">VIP</option>
                </select>
              </div>
            </div>

            <div>
              <label className="label">Return Reason</label>
              <select
                className="select text-xs"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              >
                <option value="dissatisfied">Customer Dissatisfaction</option>
                <option value="product_defect">Product Defect / Broken</option>
                <option value="wrong_item">Received Wrong Item</option>
                <option value="unauthorized_charge">Unauthorized Charge</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isRunning}
              className="btn-gold w-full justify-center py-3 text-sm gap-2"
            >
              {isRunning ? (
                <>
                  <Loader style={{ width: 15, height: 15 }} className="animate-spin" />
                  OKI Engine Evaluating Policies…
                </>
              ) : (
                <>
                  <Sparkles style={{ width: 15, height: 15 }} />
                  Submit Return Request to OKI
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Execution Result Column */}
        <div className="lg:col-span-5">
          <div className="card p-6 h-full flex flex-col justify-between border border-canvas-border space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-canvas-border">
                <span className="font-display font-semibold text-sm text-ink-900">Customer Response</span>
                <span className="badge badge-gray text-2xs">Real-Time Outcome</span>
              </div>

              {lastResult ? (
                <div className="space-y-4 pt-4">
                  {lastResult.pipeline_trace?.decision?.escalated ? (
                    <div className="text-center p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                      <AlertTriangle style={{ width: 40, height: 40, color: '#856305', margin: '0 auto' }} />
                      <div className="font-display font-bold text-lg text-ink-900">
                        Under Human Review
                      </div>
                      <p className="text-xs text-ink-600 leading-relaxed">
                        Your request exceeds autonomous risk limits. Our operations team is reviewing it.
                      </p>
                      <div className="badge badge-escalated mt-2">
                        Reason: {lastResult.pipeline_trace.decision.escalation_reason || 'Policy Threshold Triggered'}
                      </div>
                    </div>
                  ) : lastResult.pipeline_trace?.decision?.decision?.toLowerCase().includes('deny') ? (
                    <div className="text-center p-6 rounded-2xl bg-red-500/10 border border-red-500/30 space-y-2">
                      <AlertTriangle style={{ width: 40, height: 40, color: '#8B1616', margin: '0 auto' }} />
                      <div className="font-display font-bold text-lg text-ink-900">
                        Refund Request Denied
                      </div>
                      <p className="text-xs text-ink-600 leading-relaxed">
                        This order falls outside the allowable refund window based on authoritative company policy.
                      </p>
                    </div>
                  ) : (
                    <div className="text-center p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                      <CheckCircle2 style={{ width: 40, height: 40, color: '#1D6B3E', margin: '0 auto' }} />
                      <div className="font-display font-bold text-lg text-ink-900">
                        Refund Approved Instantly
                      </div>
                      <p className="text-xs text-ink-600 leading-relaxed">
                        Your return has been processed automatically by OKI autonomous policy rules.
                      </p>
                    </div>
                  )}

                  {/* Execution Ledger Details */}
                  <div className="p-4 rounded-xl bg-canvas-warm/60 border border-canvas-border space-y-2.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-ink-400">Decision</span>
                      <span className="font-semibold text-ink-900 uppercase">
                        {lastResult.pipeline_trace?.decision?.decision || 'Approved'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-ink-400">Engine Confidence</span>
                      <div style={{ width: 120 }}>
                        <ConfidenceBar value={lastResult.pipeline_trace?.decision?.confidence ?? 0.95} showLabel />
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-400">Risk Assessment</span>
                      <RiskBadge level={lastResult.pipeline_trace?.decision?.risk_level ?? 'low'} size="sm" />
                    </div>
                    {lastResult.pipeline_trace?.action_execution && (
                      <div className="pt-2 border-t border-canvas-border text-2xs text-ink-600">
                        <span>Live Tool Action: </span>
                        <strong className="text-ink-800 font-mono">
                          {lastResult.pipeline_trace.action_execution.action || 'mock_refund_payment'}
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-ink-400 space-y-2">
                  <Package style={{ width: 36, height: 36, margin: '0 auto', color: '#C2B8A8' }} />
                  <p className="text-xs">Submit an order request to see the live policy outcome.</p>
                </div>
              )}
            </div>

            <div className="text-2xs text-ink-400 text-center border-t border-canvas-border pt-3">
              Switch to <strong>OKI Glass-Box Admin</strong> tab above to see the underlying 4-panel knowledge pipeline.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
