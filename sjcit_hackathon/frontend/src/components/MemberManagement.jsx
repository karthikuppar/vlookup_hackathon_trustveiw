import React, { useState, useEffect, useCallback } from 'react'
import { Users, UserPlus, Trash2, Key, UserCheck, UserX, Shield, ShieldAlert, RefreshCw, LogOut } from 'lucide-react'
import { api } from '../services/http'

export default function MemberManagement({ token, user, setSuccess, setError }) {
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [resettingUserId, setResettingUserId] = useState(null)
  const [newPasswordInput, setNewPasswordInput] = useState('')

  // New member form state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('client_employee')
  const [submitting, setSubmitting] = useState(false)

  const tenantId = user?.tenant_id || 'tenant_a'

  const loadMembers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api(`/api/clients/${tenantId}/members`, token)
      setMembers(res.members || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [tenantId, token, setError])

  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  const handleAddMember = async (e) => {
    e.preventDefault()
    if (!name.trim() || !email.trim() || !password) return
    setSubmitting(true)
    try {
      await api(`/api/clients/${tenantId}/members`, token, {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), email: email.trim(), password, role })
      })
      setSuccess(`✅ New member "${name}" registered successfully!`)
      setName('')
      setEmail('')
      setPassword('')
      setShowAddModal(false)
      loadMembers()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggleActive = async (member) => {
    const newStatus = member.is_active === 0
    try {
      await api(`/api/clients/${tenantId}/members/${member.id}`, token, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: newStatus })
      })
      setSuccess(`Member "${member.name}" account is now ${newStatus ? 'Activated' : 'Deactivated and sessions revoked'}.`)
      loadMembers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleToggleRole = async (member) => {
    const newRole = member.role === 'client_admin' ? 'client_employee' : 'client_admin'
    try {
      await api(`/api/clients/${tenantId}/members/${member.id}`, token, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole })
      })
      setSuccess(`Member "${member.name}" role updated to ${newRole === 'client_admin' ? 'Administrator' : 'Employee'}.`)
      loadMembers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteMember = async (member) => {
    if (!window.confirm(`Are you sure you want to permanently remove member "${member.name}" (${member.email})? All their sessions will be terminated immediately.`)) {
      return
    }
    try {
      await api(`/api/clients/${tenantId}/members/${member.id}`, token, { method: 'DELETE' })
      setSuccess(`Member "${member.name}" was removed and their access tokens invalidated.`)
      loadMembers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleResetPassword = async (memberId) => {
    if (!newPasswordInput || newPasswordInput.length < 12) {
      setError('Password must be at least 12 characters long according to security policy.')
      return
    }
    try {
      await api(`/api/clients/${tenantId}/members/${memberId}/reset-password`, token, {
        method: 'POST',
        body: JSON.stringify({ new_password: newPasswordInput })
      })
      setSuccess('✅ Password reset successfully. User will be required to change password on next sign-in.')
      setResettingUserId(null)
      setNewPasswordInput('')
      loadMembers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRevokeAllSessions = async () => {
    if (!window.confirm('Revoke all current sessions across all devices for your account? You will need to sign in again.')) {
      return
    }
    try {
      await api('/api/auth/logout-all', token, { method: 'POST' })
      setSuccess('All active sessions revoked. Signing out...')
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={{ background: '#FAF7F0', border: '1px solid #000000', borderRadius: '6px', padding: '1.25rem', marginTop: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#000000', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={18} color="#000000" />
            <span>Admin Member & Credential Lifecycle</span>
          </h3>
          <p style={{ fontSize: '0.8rem', color: '#000000', marginTop: '0.2rem' }}>
            Manage client team membership, enforce credential security policies, and perform immediate token revoking.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <button className="btn-secondary" onClick={handleRevokeAllSessions} style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem' }}>
            <LogOut size={13} />
            <span>Revoke All My Sessions</span>
          </button>
          <button className="btn-secondary" onClick={loadMembers} disabled={loading} style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem' }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ padding: '0.45rem 0.95rem', fontSize: '0.78rem' }}>
            <UserPlus size={14} />
            <span>Add Member</span>
          </button>
        </div>
      </div>

      {/* Add Member Modal / Card */}
      {showAddModal && (
        <form onSubmit={handleAddMember} style={{ background: '#FAF7F0', border: '1px solid #000000', borderRadius: '6px', padding: '1rem', marginBottom: '1.25rem' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#000000', marginBottom: '0.8rem' }}>Onboard New Team Member</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#000000', fontWeight: 700, marginBottom: '0.3rem' }}>Full Name</label>
              <input
                className="input-field"
                type="text"
                placeholder="Jane Doe"
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#000000', fontWeight: 700, marginBottom: '0.3rem' }}>Email Address</label>
              <input
                className="input-field"
                type="email"
                placeholder="jane@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#000000', fontWeight: 700, marginBottom: '0.3rem' }}>Initial Password (12+ chars)</label>
              <input
                className="input-field"
                type="password"
                placeholder="SecurePassword2026!"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#000000', fontWeight: 700, marginBottom: '0.3rem' }}>Role</label>
              <select
                className="select-field"
                value={role}
                onChange={e => setRole(e.target.value)}
              >
                <option value="client_employee">Client Employee</option>
                <option value="client_admin">Client Administrator</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting} style={{ padding: '0.4rem 0.9rem', fontSize: '0.78rem' }}>
              {submitting ? 'Creating...' : 'Create Account'}
            </button>
          </div>
        </form>
      )}

      {/* Members Table */}
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table" style={{ width: '100%', fontSize: '0.82rem' }}>
          <thead>
            <tr>
              <th style={{ padding: '0.6rem 0.8rem' }}>Name & Email</th>
              <th style={{ padding: '0.6rem 0.8rem' }}>Role</th>
              <th style={{ padding: '0.6rem 0.8rem' }}>Status</th>
              <th style={{ padding: '0.6rem 0.8rem' }}>Joined</th>
              <th style={{ padding: '0.6rem 0.8rem', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '1.5rem', textAlign: 'center', color: '#000000', fontWeight: 600 }}>
                  No members found.
                </td>
              </tr>
            ) : (
              members.map(m => {
                const isSelf = m.id === user?.id
                const isSysAdmin = m.role === 'system_admin'
                const isActive = m.is_active !== 0

                return (
                  <tr key={m.id}>
                    <td style={{ padding: '0.65rem 0.8rem' }}>
                      <div style={{ fontWeight: 700, color: '#000000' }}>{m.name} {isSelf && <span style={{ fontSize: '0.72rem', color: '#065F46', fontWeight: 800 }}>(You)</span>}</div>
                      <div style={{ fontSize: '0.72rem', color: '#000000', opacity: 0.85 }}>{m.email}</div>
                    </td>
                    <td style={{ padding: '0.65rem 0.8rem' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        background: m.role === 'client_admin' ? '#E0E7FF' : '#E2E8F0',
                        color: m.role === 'client_admin' ? '#1E1B4B' : '#000000',
                        border: '1px solid #000000'
                      }}>
                        {m.role === 'client_admin' ? <Shield size={11} /> : null}
                        {m.role === 'client_admin' ? 'Admin' : 'Employee'}
                      </span>
                    </td>
                    <td style={{ padding: '0.65rem 0.8rem' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                        background: isActive ? '#D1FAE5' : '#FEE2E2',
                        color: isActive ? '#065F46' : '#991B1B',
                        border: `1px solid ${isActive ? '#065F46' : '#991B1B'}`
                      }}>
                        {isActive ? <UserCheck size={11} /> : <UserX size={11} />}
                        {isActive ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td style={{ padding: '0.65rem 0.8rem', color: '#000000', fontSize: '0.78rem', fontWeight: 600 }}>
                      {m.created_at ? new Date(m.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td style={{ padding: '0.65rem 0.8rem', textAlign: 'right' }}>
                      {!isSysAdmin && (
                        <div style={{ display: 'inline-flex', gap: '0.4rem', alignItems: 'center' }}>
                          {/* Toggle Active / Deactivate */}
                          {!isSelf && (
                            <button
                              onClick={() => handleToggleActive(m)}
                              title={isActive ? 'Deactivate account & revoke all sessions' : 'Activate account'}
                              style={{
                                background: isActive ? 'rgba(244,63,94,0.1)' : 'rgba(16,185,129,0.1)',
                                border: `1px solid ${isActive ? 'rgba(244,63,94,0.3)' : 'rgba(16,185,129,0.3)'}`,
                                color: isActive ? '#fb7185' : '#34d399',
                                borderRadius: '4px',
                                padding: '3px 6px',
                                cursor: 'pointer',
                                fontSize: '0.72rem'
                              }}
                            >
                              {isActive ? 'Disable' : 'Enable'}
                            </button>
                          )}

                          {/* Toggle Role */}
                          {!isSelf && (
                            <button
                              onClick={() => handleToggleRole(m)}
                              title="Promote or demote role"
                              style={{
                                background: 'rgba(99,102,241,0.1)',
                                border: '1px solid rgba(99,102,241,0.3)',
                                color: '#818cf8',
                                borderRadius: '4px',
                                padding: '3px 6px',
                                cursor: 'pointer',
                                fontSize: '0.72rem'
                              }}
                            >
                              {m.role === 'client_admin' ? 'Make Emp' : 'Make Admin'}
                            </button>
                          )}

                          {/* Reset Password */}
                          <button
                            onClick={() => setResettingUserId(resettingUserId === m.id ? null : m.id)}
                            title="Reset password"
                            style={{
                              background: 'rgba(245,158,11,0.1)',
                              border: '1px solid rgba(245,158,11,0.3)',
                              color: '#fbbf24',
                              borderRadius: '4px',
                              padding: '3px 6px',
                              cursor: 'pointer',
                              fontSize: '0.72rem'
                            }}
                          >
                            <Key size={11} />
                          </button>

                          {/* Remove */}
                          {!isSelf && (
                            <button
                              onClick={() => handleDeleteMember(m)}
                              title="Permanently remove member"
                              style={{
                                background: 'rgba(244,63,94,0.1)',
                                border: '1px solid rgba(244,63,94,0.3)',
                                color: '#fb7185',
                                borderRadius: '4px',
                                padding: '3px 6px',
                                cursor: 'pointer',
                                fontSize: '0.72rem'
                              }}
                            >
                              <Trash2 size={11} />
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Inline Reset Password Box */}
      {resettingUserId && (
        <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#fbbf24', fontSize: '0.82rem', fontWeight: 600 }}>
            <ShieldAlert size={14} />
            <span>Reset Temporary Password for Member (must be 12+ characters):</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="password"
              placeholder="Enter new 12+ char temporary password"
              value={newPasswordInput}
              onChange={e => setNewPasswordInput(e.target.value)}
              style={{ flex: 1, padding: '0.4rem 0.6rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', fontSize: '0.8rem' }}
            />
            <button
              className="btn-primary"
              onClick={() => handleResetPassword(resettingUserId)}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
            >
              Confirm Reset
            </button>
            <button
              className="btn-secondary"
              onClick={() => { setResettingUserId(null); setNewPasswordInput('') }}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
