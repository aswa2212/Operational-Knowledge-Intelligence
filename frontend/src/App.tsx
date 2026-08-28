import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Cases from './pages/Cases'
import CaseDetail from './pages/CaseDetail'
import Decisions from './pages/Decisions'
import Approvals from './pages/Approvals'
import Conflicts from './pages/Conflicts'
import Evaluation from './pages/Evaluation'
import Connectors from './pages/Connectors'
import Settings from './pages/Settings'

// Secondary views (accessible directly or via deep links)
import Documents from './pages/Documents'
import Skills from './pages/Skills'
import Actions from './pages/Actions'
import Audit from './pages/Audit'
import DemoShowcase from './pages/DemoShowcase'

export default function App() {
  return (
    <Layout>
      <Routes>
        {/* Showcase Demo */}
        <Route path="/demo" element={<DemoShowcase />} />

        {/* 9 Main Pages */}
        <Route path="/" element={<Overview />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/:id" element={<CaseDetail />} />
        <Route path="/decisions" element={<Decisions />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/conflicts" element={<Conflicts />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/connectors" element={<Connectors />} />
        <Route path="/settings" element={<Settings />} />

        {/* Supporting Pages & Aliases */}
        <Route path="/sources" element={<Navigate to="/connectors" replace />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/actions" element={<Actions />} />
        <Route path="/audit" element={<Audit />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
