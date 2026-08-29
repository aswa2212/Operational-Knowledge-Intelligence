import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import {
  Brain, LayoutDashboard, Play, CheckCircle, GitBranch,
  BarChart2, Plug, Settings, FileText, Files, Layers, Zap, ChevronRight,
  ShoppingBag, ExternalLink,
} from 'lucide-react'

const PRIMARY_NAV = [
  { to: '/',            icon: LayoutDashboard, label: 'Overview'      },
  { to: '/documents',   icon: Files,           label: 'Documents'     },
  { to: '/skills',      icon: Layers,          label: 'Skills'        },
  { to: '/cases',       icon: Play,            label: 'Cases'         },
  { to: '/decisions',   icon: FileText,        label: 'Decisions'     },
  { to: '/actions',     icon: Zap,             label: 'Actions'       },
  { to: '/conflicts',   icon: GitBranch,       label: 'Conflicts'     },
  { to: '/approvals',   icon: CheckCircle,     label: 'Approvals'     },
  { to: '/evaluation',  icon: BarChart2,       label: 'Evaluation'    },
  { to: '/connectors',  icon: Plug,            label: 'Connectors'    },
  { to: '/settings',    icon: Settings,        label: 'Settings'      },
]

interface Props { children: React.ReactNode }

export default function Layout({ children }: Props) {
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const el = document.getElementById('main-scroll')
    if (!el) return
    const handler = () => setScrolled(el.scrollTop > 24)
    el.addEventListener('scroll', handler, { passive: true })
    return () => el.removeEventListener('scroll', handler)
  }, [])

  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30_000,
    retry: 1,
  })

  const { data: pendingApprovals = [] } = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: () => api.approvals.list('pending'),
    refetchInterval: 30_000,
  })

  const pendingCount = pendingApprovals.length

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#FAF8F4' }}>

      {/* ── Floating Nav ──────────────────────────────────────────────── */}
      <nav className={`floating-nav ${scrolled ? 'scrolled' : ''}`}>
        <div className="flex items-center h-14 px-4 gap-3">

          {/* Logo mark */}
          <NavLink to="/" className="flex items-center gap-2.5 flex-shrink-0 mr-1 group">
            <div className="relative w-8 h-8 flex-shrink-0">
              {/* Outer ring */}
              <div className="absolute inset-0 rounded-xl border border-ink-200/60 bg-gradient-to-br from-ink-800 to-ink-950 shadow-md group-hover:shadow-lg transition-shadow duration-300" />
              {/* Inner glow */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-gold-400/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <Brain className="absolute inset-0 m-auto text-canvas" style={{ width: 16, height: 16 }} />
            </div>
            <div className="leading-none">
              <div className="font-display text-sm font-700 text-ink-900 tracking-tight" style={{ fontWeight: 700 }}>OKI</div>
              <div className="text-2xs text-ink-400 font-medium tracking-wide" style={{ fontSize: '0.6rem', letterSpacing: '0.06em' }}>INTELLIGENCE</div>
            </div>
          </NavLink>

          {/* Vertical divider */}
          <div className="h-5 w-px flex-shrink-0" style={{ background: 'linear-gradient(to bottom, transparent, rgba(212,203,191,0.70), transparent)' }} />

          {/* Nav links */}
          <div className="flex items-center gap-0.5 flex-1 overflow-x-auto no-scrollbar">
            {PRIMARY_NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `top-nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon className="flex-shrink-0" style={{ width: 13, height: 13 }} />
                {label}
                {label === 'Approvals' && pendingCount > 0 && (
                  <span className="ml-0.5 inline-flex items-center justify-center rounded-full text-white font-bold"
                    style={{ minWidth: 16, height: 16, fontSize: '0.5625rem', backgroundColor: '#D9641E', paddingInline: 4 }}>
                    {pendingCount > 9 ? '9+' : pendingCount}
                  </span>
                )}
              </NavLink>
            ))}
          </div>

          {/* Vertical divider */}
          <div className="h-5 w-px flex-shrink-0" style={{ background: 'linear-gradient(to bottom, transparent, rgba(212,203,191,0.70), transparent)' }} />

          {/* Right Action buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Mock Client Website Button */}
            <a
              href={import.meta.env.VITE_MOCK_CLIENT_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? 'https://oki-mock-website.vercel.app' : 'http://localhost:3000')}
              target="_blank"
              rel="noreferrer"
              className="btn-gold btn-xs gap-1.5 font-display font-semibold hidden md:inline-flex"
              title="Open Standalone Mock Client Website (ShopNow / B2B Quotes / DevOps Incident Desk)"
            >
              <ShoppingBag style={{ width: 12, height: 12 }} />
              Mock Client
              <ExternalLink style={{ width: 10, height: 10 }} />
            </a>

            {/* System health */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full" style={{ background: 'rgba(238,234,225,0.70)', border: '1px solid rgba(212,203,191,0.55)' }}>
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                isError ? 'bg-risk-high' : health ? 'bg-risk-low animate-pulse-soft' : 'bg-canvas-subtle'
              }`} />
              <span className="hidden sm:inline font-display font-semibold text-ink-400" style={{ fontSize: '0.625rem', letterSpacing: '0.06em' }}>
                {isError ? 'OFFLINE' : health ? 'LIVE' : 'CONNECTING'}
              </span>
            </div>
          </div>
        </div>

        {/* Breadcrumb for deep routes */}
        {location.pathname.includes('/cases/') && (
          <div className="px-4 pb-2.5 flex items-center gap-1.5" style={{ fontSize: '0.6875rem', color: '#A0917F' }}>
            <NavLink to="/cases" className="hover:text-ink-700 transition-colors font-medium">Cases</NavLink>
            <ChevronRight style={{ width: 11, height: 11 }} />
            <span className="text-ink-700 font-semibold">Detail</span>
          </div>
        )}
      </nav>

      {/* ── Main scroll area ──────────────────────────────────────────── */}
      <div id="main-scroll" className="h-screen overflow-y-auto pt-[4.5rem] scroll-area">
        <div className="max-w-7xl mx-auto px-6 py-8 fade-in-up">
          {children}
        </div>
        <div className="h-16" />
      </div>
    </div>
  )
}
