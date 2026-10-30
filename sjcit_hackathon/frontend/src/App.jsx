import React, { useState } from 'react'
import { Shield, MessageSquare, FileText, Share2, Database, Cpu, LogOut, User, ShieldCheck, Wrench } from 'lucide-react'
import { getSession, saveSession, clearSession } from './services/session'
import { isAdminRole } from './services/http'
import Banner from './components/Banner'
import AuthScreen from './views/AuthScreen'
import ChatView from './views/ChatView'
import DocumentsView from './views/DocumentsView'
import SharingView from './views/SharingView'
import LedgerView from './views/LedgerView'
import TeeView from './views/TeeView'
import AdminSecurityView from './views/AdminSecurityView'
import SecurityCentreSection from './SecurityCentreSection'

export default function App() {
  const [session, setSession] = useState(() => getSession())
  const [activeTab, setActiveTab] = useState('chat')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const token = session?.access_token

  const handleLogout = () => {
    clearSession()
    setSession(null)
  }

  const handleLoginSuccess = data => {
    saveSession(data)
    setSession(data)
    setErrorMsg('')
  }

  if (!session) {
    return <AuthScreen onLogin={handleLoginSuccess} />
  }

  const isAdmin = isAdminRole(session.user?.role)
  const roleLabel = isAdmin ? 'Main Admin' : 'Employee'

  const tabs = [
    { id: 'chat', label: 'Grounded Chat', icon: MessageSquare },
    { id: 'documents', label: 'Documents & Versioning', icon: FileText },
    { id: 'sharing', label: 'Knowledge Sharing', icon: Share2 },
    { id: 'ledger', label: 'Audit Ledger', icon: Database },
    { id: 'tee', label: 'TEE Simulation', icon: Cpu },
    ...(isAdmin ? [
      { id: 'admin_security', label: 'Admin & Security Hub', icon: ShieldCheck },
      { id: 'security_centre', label: 'Security & Remediation Centre', icon: Wrench },
    ] : []),
  ]
  const tab = tabs.some(t => t.id === activeTab) ? activeTab : 'chat'

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand-section">
          <div className="brand-logo">
            <Shield size={20} />
          </div>
          <div>
            <span className="brand-title">AegisKB</span>
            <span className="spec-badge" style={{ marginLeft: '0.6rem' }}>SOP ASSISTANT</span>
          </div>
        </div>

        <div className="nav-controls">
          <div className="indicator-pill">
            <span className="indicator-dot dot-green" />
            <span>Offline Zero-Egress</span>
          </div>

          <div className="indicator-pill">
            <span className="indicator-dot dot-cyan" />
            <span>TEE: Simulated</span>
          </div>

          <div className="user-badge">
            <User size={14} color="#94a3b8" />
            <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>{session.user?.name}</span>
            <span className="role-tag">({roleLabel})</span>
          </div>

          <button onClick={handleLogout} className="btn-secondary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.78rem' }}>
            <LogOut size={13} />
            <span>Sign out</span>
          </button>
        </div>
      </header>

      <nav className="tabs-bar" aria-label="Main sections">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`tab-btn ${tab === id ? 'active' : ''}`}
            aria-current={tab === id ? 'page' : undefined}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <main className="main-content">
        <Banner kind="error" onClose={() => setErrorMsg('')}>{errorMsg}</Banner>
        <Banner kind="success" onClose={() => setSuccessMsg('')}>{successMsg}</Banner>

        {tab === 'chat' && <ChatView token={token} user={session.user} />}
        {tab === 'documents' && <DocumentsView token={token} user={session.user} setSuccess={setSuccessMsg} setError={setErrorMsg} />}
        {tab === 'sharing' && <SharingView token={token} setSuccess={setSuccessMsg} setError={setErrorMsg} />}
        {tab === 'ledger' && <LedgerView token={token} user={session.user} setSuccess={setSuccessMsg} setError={setErrorMsg} />}
        {tab === 'tee' && <TeeView token={token} setSuccess={setSuccessMsg} setError={setErrorMsg} />}
        {tab === 'admin_security' && isAdmin && (
          <AdminSecurityView token={token} user={session.user} setSuccess={setSuccessMsg} setError={setErrorMsg} />
        )}
        {tab === 'security_centre' && isAdmin && (
          <SecurityCentreSection token={token} user={session.user} setSuccess={setSuccessMsg} setError={setErrorMsg} />
        )}
      </main>
    </div>
  )
}
