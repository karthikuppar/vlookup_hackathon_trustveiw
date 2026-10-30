import React, { useState, useEffect, useCallback } from 'react'
import { Share2, Lock, RefreshCw } from 'lucide-react'
import { api } from '../services/http'

export default function SharingView({ token, setSuccess, setError }) {
  const [shares, setShares] = useState({ outgoing: [], incoming: [] })
  const [recipient, setRecipient] = useState('tenant_b')
  const [reason, setReason] = useState('Joint cross-client compliance audit')

  const fetchShares = useCallback(async () => {
    try {
      const data = await api('/api/knowledge-bases/shares', token)
      setShares(data)
    } catch (err) {
      setError(err.message)
    }
  }, [token, setError])

  useEffect(() => {
    fetchShares()
  }, [fetchShares])

  const handleCreateShare = async e => {
    e.preventDefault()
    try {
      await api('/api/knowledge-bases/default/shares', token, {
        method: 'POST',
        body: JSON.stringify({ recipient_tenant_id: recipient, reason, permission: 'read' }),
      })
      setSuccess(`Knowledge share granted to ${recipient}!`)
      fetchShares()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRevokeShare = async shareId => {
    try {
      await api(`/api/knowledge-bases/default/shares/${shareId}`, token, {
        method: 'DELETE',
      })
      setSuccess('Share grant revoked! Access is immediately denied on future queries.')
      fetchShares()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="grid-2col">
      {/* Create Share Grant */}
      <div className="card-panel">
        <h2 className="panel-title">
          <Share2 size={18} color="#6366f1" />
          <span>Grant Knowledge Base Share (Section 4)</span>
        </h2>
        <p className="panel-subtitle">
          Default is NO sharing. Create an explicit, audited grant to allow another client tenant read-only search access.
        </p>

        <form onSubmit={handleCreateShare} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.25rem' }}>
          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Recipient Client Tenant ID</label>
            <select className="select-field" value={recipient} onChange={e => setRecipient(e.target.value)}>
              <option value="tenant_a">tenant_a (AcroCorp Technologies)</option>
              <option value="tenant_b">tenant_b (BetaShield Security)</option>
              <option value="tenant_c">tenant_c (Gamma Logistics)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Business Justification / Reason</label>
            <input required className="input-field" value={reason} onChange={e => setReason(e.target.value)} />
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Permission Level</label>
            <input disabled className="input-field" value="Read (Enforced default)" style={{ opacity: 0.7 }} />
          </div>

          <button type="submit" className="btn-primary">
            <Share2 size={14} />
            <span>Create Share Grant</span>
          </button>
        </form>
      </div>

      {/* Active Shares Console */}
      <div className="card-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 className="panel-title">
            <Lock size={18} color="#6366f1" />
            <span>Active & Historic Shares</span>
          </h2>
          <button onClick={fetchShares} aria-label="Refresh shares" className="btn-secondary" style={{ padding: '0.35rem 0.65rem' }}>
            <RefreshCw size={13} />
          </button>
        </div>

        <h3 style={{ fontSize: '0.85rem', color: '#c7d2fe', marginBottom: '0.5rem' }}>Outgoing Grants from Your Tenant:</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1.5rem' }}>
          {shares.outgoing.length === 0 && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No outgoing shares created.</p>}
          {shares.outgoing.map(s => (
            <div key={s.id} style={{ background: 'rgba(9, 13, 22, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <b style={{ color: '#fff', fontSize: '0.85rem' }}>Recipient: {s.recipient_tenant_id}</b>
                <p style={{ fontSize: '0.74rem', color: '#94a3b8' }}>Reason: {s.reason}</p>
                <small style={{ color: '#64748b' }}>Created: {s.created_at?.slice(0, 19)}</small>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  background: s.status === 'active' ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)',
                  color: s.status === 'active' ? '#34d399' : '#fb7185',
                }}>
                  {s.status.toUpperCase()}
                </span>
                {s.status === 'active' && (
                  <button onClick={() => handleRevokeShare(s.id)} className="btn-danger" style={{ padding: '0.3rem 0.65rem', fontSize: '0.74rem' }}>
                    Revoke Now
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <h3 style={{ fontSize: '0.85rem', color: '#c7d2fe', marginBottom: '0.5rem' }}>Incoming Knowledge Bases Permitted to You:</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {shares.incoming.length === 0 && <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No external tenants have shared documents with you.</p>}
          {shares.incoming.map(s => (
            <div key={s.id} style={{ background: 'rgba(9, 13, 22, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.65rem', fontSize: '0.8rem' }}>
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>Source: {s.source_tenant_id}</span>
              <span style={{ color: '#64748b', marginLeft: '0.5rem' }}>({s.status})</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
