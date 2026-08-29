/**
 * lib/api.ts — Typed Axios API client for OKI backend.
 *
 * Single Axios instance with baseURL from VITE_API_BASE_URL env var.
 * All endpoints are accessed through this module — no raw URLs elsewhere.
 */

import axios, { type AxiosError } from 'axios'

// ── Axios instance ─────────────────────────────────────────────────────────

function getBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)
    || (import.meta.env.VITE_API_URL as string | undefined)

  if (envUrl && envUrl.trim()) {
    let clean = envUrl.trim().replace(/\/+$/, '')
    if (clean.endsWith('/v1')) {
      clean = clean.slice(0, -3)
    }
    if (!clean.endsWith('/api')) {
      clean = `${clean}/api`
    }
    return clean
  }

  // Fallback for local development
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return 'http://127.0.0.1:8000/api'
  }

  // Fallback for production (e.g. Vercel) to direct to Render backend
  return 'https://operational-knowledge-intelligence.onrender.com/api'
}

export const axiosInstance = axios.create({
  baseURL: getBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000, // 60s — LLM extraction can be slow
})

// Normalize FastAPI error responses so React Query always sees a real Error
axiosInstance.interceptors.response.use(
  (res) => res,
  (err: AxiosError<{ detail?: string }>) => {
    const detail = err.response?.data?.detail ?? err.message ?? 'Unknown error'
    return Promise.reject(new Error(String(detail)))
  },
)

const get = <T>(path: string, params?: Record<string, unknown>) =>
  axiosInstance.get<T>(path, { params }).then((r) => r.data)

const post = <T>(path: string, body?: unknown) =>
  axiosInstance.post<T>(path, body).then((r) => r.data)

// ── Types ──────────────────────────────────────────────────────────────────

export interface Source {
  id: number
  type: string
  name: string
  config_json: string
  enabled: number
  created_at: string
}

export interface Document {
  id: number
  source_id: number
  source_type: string
  author_handle: string
  channel_or_space: string
  timestamp: string
  title: string
  url: string
  text?: string
  raw_content?: string
  author_role?: string
}

export interface CandidateRule {
  id: number
  process: string
  trigger_text: string
  action: string
  confidence: number
  extraction_method: string
  status: string
  temporal_scope: string
}

export interface ResolvedRule {
  id: number
  process: string
  trigger_text: string
  action: string
  score: number
  status: string
  temporal_scope: string
  created_at: string
  provenance_json: string
}

export interface SkillVersion {
  id: number
  process: string
  version: number
  status: string
  generated_at: string
  artifact_path: string
  rules_count?: number
  rule_count?: number
  created_at?: string
}

export interface Decision {
  id: number
  case_id: number
  decision: string
  confidence: number
  matched_rule_id: number
  risk_level: string // low | medium | high
  escalated: number  // 0 | 1
  reason: string
  trace_json: string
  trace?: Record<string, unknown>
  created_at: string
}

export interface Case {
  id: number
  process: string
  source: string
  status: string
  created_at: string
  payload_json: string
  decision?: Decision
}

export interface Approval {
  id: number
  decision_id: number
  type: string
  status: string // pending | approved | rejected
  requested_action_json: string
  reason: string
  requested_at: string
  resolved_at: string
  resolved_by: string
  // joined fields
  decision?: string
  confidence?: number
  risk_level?: string
  escalation_reason?: string
  requested_action?: Record<string, unknown>
  summary_card?: Record<string, string>
  case_fields?: Record<string, unknown>
  process?: string
}

export interface AuditEvent {
  id: number
  entity_type: string
  entity_id: string
  event_type: string
  actor: string
  payload_json: string
  created_at: string
  payload?: Record<string, unknown>
}

export interface HealthResponse {
  status: string
  service: string
  version: string
}

// ── API namespace ──────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => get<HealthResponse>('/v1/health'),

  // Sources / Connectors
  sources: {
    list: () => get<Source[]>('/v1/sources'),
    create: (body: { type: string; name: string; config: Record<string, unknown> }) =>
      post<{ id: number }>('/v1/sources', body),
    sync: (id: number) => post<{ inserted: number }>(`/v1/sources/${id}/sync`),
    syncHistory: (id: number) => get<AuditEvent[]>(`/v1/sources/${id}/sync-history`),
  },

  // Documents
  documents: {
    list: (params?: { source_type?: string; limit?: number; offset?: number }) =>
      get<Document[]>('/v1/documents', params as Record<string, unknown>),
    get: (id: number) => get<Document>(`/v1/documents/${id}`),
  },

  // Extraction
  extraction: {
    run: (process: string, method = 'two_pass') =>
      post<Record<string, unknown>>('/v1/extraction/run', { process, method }),
    runs: (limit = 50) => get<AuditEvent[]>('/v1/extraction/runs', { limit }),
    candidateRules: (params?: { process?: string; method?: string; limit?: number }) =>
      get<CandidateRule[]>('/v1/candidate-rules', params as Record<string, unknown>),
  },

  // Conflicts
  conflicts: {
    list: (params?: { process?: string; status?: string }) =>
      get<ResolvedRule[]>('/v1/conflicts', {
        status: 'conflict_unresolved',
        ...params,
      }),
    get: (id: number) =>
      get<ResolvedRule & { competing_rules: CandidateRule[] }>(`/v1/conflicts/${id}`),
    resolve: (id: number, body: { resolution_note: string; resolved_by?: string }) =>
      post<{ status: string }>(`/v1/conflicts/${id}/resolve`, body),
    runResolver: (process: string) =>
      post<{ resolved: number; flagged: number }>('/v1/conflicts/resolve-run', { process }),
  },

  // Skills
  skills: {
    list: (params?: { process?: string }) =>
      get<SkillVersion[]>('/v1/skills', params as Record<string, unknown>),
    getActive: (process: string) =>
      get<Record<string, unknown>>(`/v1/skills/${process}`),
    build: (process: string) =>
      post<{ version: number; rule_count: number }>('/v1/skills/build', { process }),
  },

  // Cases
  cases: {
    submit: (process: string, fields: Record<string, unknown>, source = 'dashboard') =>
      post<{
        case_id: number
        decision: string
        confidence: number
        escalated: boolean
        escalation_reason?: string
        matched_rule_id?: number
      }>('/v1/cases', { process, fields, source }),
    list: (params?: { process?: string; status?: string; limit?: number }) =>
      get<Case[]>('/v1/cases', params as Record<string, unknown>),
    get: (id: number) => get<Case>(`/v1/cases/${id}`),
    decide: (id: number) =>
      post<{ case_id: number; decision: string; confidence: number; escalated: boolean }>(
        `/v1/cases/${id}/decide`,
      ),
  },

  // Approvals
  approvals: {
    list: (status = 'pending') => get<Approval[]>('/v1/approvals', { status }),
    get: (id: number) => get<Approval>(`/v1/approvals/${id}`),
    approve: (id: number, resolved_by = 'human') =>
      post<{ status: string }>(`/v1/approvals/${id}/approve`, { resolved_by }),
    reject: (id: number, reason: string, resolved_by = 'human') =>
      post<{ status: string }>(`/v1/approvals/${id}/reject`, { reason, resolved_by }),
  },

  // Actions
  actions: {
    list: (limit = 100) => get<AuditEvent[]>('/v1/actions', { limit }),
    get: (id: number) => get<AuditEvent>(`/v1/actions/${id}`),
  },

  // Evaluation
  evaluation: {
    run: (fixture_file = 'eval_cases.json') =>
      post<Record<string, unknown>>('/v1/evaluation/run', { fixture_file }),
    runs: (limit = 20) => get<AuditEvent[]>('/v1/evaluation/runs', { limit }),
  },

  // Audit
  audit: {
    list: (params?: { entity_type?: string; limit?: number; offset?: number }) =>
      get<AuditEvent[]>('/v1/audit', params as Record<string, unknown>),
  },

  // Config
  config: {
    get: () => get<Record<string, unknown>>('/v1/config'),
  },

  // Demo Showcase
  demo: {
    execute: (body: { process: string; fields: Record<string, unknown>; extraction_method?: string; sync_live?: boolean }) =>
      post<{
        success: boolean
        case_id: number
        process: string
        input_fields: Record<string, unknown>
        pipeline_trace: {
          ingestion: { total_documents: number; sources_active: string[] }
          extraction: { method: string; documents_processed: number; rules_extracted: number; error?: string; fallback_used: boolean }
          skills: { active_version: string; rules_count: number }
          decision: { decision: string; confidence: number; risk_level: string; matched_rule_id?: number; escalated: boolean; escalation_reason?: string }
          action_execution?: Record<string, unknown>
        }
      }>('/v1/demo/execute', body),
    state: () => get<Record<string, { has_skill: boolean; skill_version?: string; cases_count: number }>>('/v1/demo/state'),
    reset: () => post<{ status: string; message: string }>('/v1/demo/reset'),
  },
}
