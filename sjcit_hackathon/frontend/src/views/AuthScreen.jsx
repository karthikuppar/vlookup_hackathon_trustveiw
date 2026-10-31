import React, { useState } from 'react'
import { Shield, ChevronRight, RefreshCw } from 'lucide-react'
import { api } from '../services/http'

const DEMO_ACCOUNTS = [
  { name: 'Alice Admin', email: 'admin@acrocorp.com', role: 'Main Admin', dept: 'SOP Governance & Compliance' },
  { name: 'Edward Employee', email: 'employee@acrocorp.com', role: 'Employee', dept: 'Operations & Engineering' },
  { name: 'Sam Employee', email: 'sam@acrocorp.com', role: 'Employee', dept: 'Retail Logistics & Returns' },
]

export default function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('Password123!')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const handleLogin = async (loginEmail, loginPwd) => {
    setLoading(true)
    setError('')
    try {
      const data = await api('/api/auth/login', null, {
        method: 'POST',
        body: JSON.stringify({ email: loginEmail || email, password: loginPwd || password }),
      })
      onLogin(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // No role is sent: the server assigns the employee role itself.
  const handleRegister = async () => {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const data = await api('/api/auth/register', null, {
        method: 'POST',
        body: JSON.stringify({ name, email, password }),
      })
      if (data?.access_token) {
        onLogin(data)
      } else {
        setNotice('Account created. You can now sign in.')
        setMode('login')
      }
    } catch (err) {
      setError(err.status === 403 ? `Registration is unavailable: ${err.message}` : err.message)
    } finally {
      setLoading(false)
    }
  }

  const isRegister = mode === 'register'

  return (
    <div className="auth-wrapper">
      <div className="auth-box">
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div className="brand-logo" style={{ margin: '0 auto 0.75rem', width: '42px', height: '42px' }}>
            <Shield size={22} />
          </div>
          <h1 style={{ fontSize: '1.35rem', fontWeight: 600, color: 'var(--accent-primary)' }}>AegisKB Enterprise</h1>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Document-Grounded Knowledge Management & Audit
          </p>
        </div>

        <div aria-live="assertive" role="alert">
          {error && (
            <div className="banner banner-error" style={{ fontSize: '0.82rem' }}>{error}</div>
          )}
        </div>
        {notice && <div className="banner banner-success" role="status" style={{ fontSize: '0.82rem' }}>{notice}</div>}

        {!isRegister && (
          <div style={{ marginBottom: '1.5rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Instant Demo Logins:
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', marginTop: '0.5rem' }}>
              {DEMO_ACCOUNTS.map(acc => (
                <button
                  key={acc.email}
                  className="btn-secondary"
                  style={{ width: '100%', justifyContent: 'space-between', padding: '0.45rem 0.75rem', fontSize: '0.8rem' }}
                  onClick={() => handleLogin(acc.email, 'Password123!')}
                  disabled={loading}
                  aria-label={`Sign in as ${acc.name}, ${acc.role}`}
                >
                  <span><b>{acc.name}</b> <small style={{ color: 'var(--text-secondary)' }}>({acc.role})</small></span>
                  <ChevronRight size={14} color="var(--accent-secondary)" />
                </button>
              ))}
            </div>
          </div>
        )}

        <form
          onSubmit={e => {
            e.preventDefault()
            if (isRegister) handleRegister()
            else handleLogin()
          }}
          style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
        >
          {isRegister && (
            <div>
              <label htmlFor="reg-name" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Full Name</label>
              <input id="reg-name" required className="input-field" value={name} onChange={e => setName(e.target.value)} />
            </div>
          )}
          <div>
            <label htmlFor="auth-email" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Email Address</label>
            <input id="auth-email" required type="email" className="input-field" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@acrocorp.com" />
          </div>

          <div>
            <label htmlFor="auth-password" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Password</label>
            <input id="auth-password" required type="password" className="input-field" value={password} onChange={e => setPassword(e.target.value)} />
          </div>

          {isRegister && (
            <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              New accounts are created with the Employee role. Registration may be disabled by your administrator.
            </p>
          )}

          <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
            {loading ? <RefreshCw className="animate-spin" size={16} aria-label="Working" /> : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <button
          type="button"
          className="btn-secondary"
          style={{ width: '100%', marginTop: '0.75rem', justifyContent: 'center', fontSize: '0.78rem' }}
          onClick={() => { setMode(isRegister ? 'login' : 'register'); setError(''); setNotice('') }}
        >
          {isRegister ? 'Back to sign in' : 'Create an account'}
        </button>
      </div>
    </div>
  )
}
