import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Database, Flame, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../services/http'
import TamperResult from '../components/TamperResult'

const CATEGORIES = ['security', 'documents', 'queries', 'sharing', 'admin']
const OK_DECISIONS = new Set(['permitted', 'success', 'grounded_answer', 'allowed'])
const DENY_RE = /denied|blocked|refus|reject|fail|invalid|forbidden|tamper|injection/i

export const isDenied = ev => !!ev.decision && !OK_DECISIONS.has(String(ev.decision).toLowerCase()) && DENY_RE.test(String(ev.decision))

export function categorize(ev) {
  const t = `${ev.event_type || ''} ${ev.action || ''}`.toLowerCase()
  if (isDenied(ev) || /security|tamper|injection|attest|tee|threat|auth|login/.test(t)) return 'security'
  if (/share|grant|revoke/.test(t)) return 'sharing'
  if (/document|ingest|upload|version|chunk/.test(t)) return 'documents'
  if (/query|chat|retriev|answer|search/.test(t)) return 'queries'
  return 'admin'
}

export default function LedgerView({ token, user, setSuccess, setError }) {
  const [events, setEvents] = useState([])
  const [verification, setVerification] = useState(null)
  const [tamperResult, setTamperResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')
  const canTamper = user?.role === 'system_admin'

  const fetchEvents = useCallback(async () => {
    try {
      const data = await api('/api/audit/events?limit=50', token)
      setEvents(data.events || [])
    } catch (err) {
      setError(err.message)
    }
  }, [token, setError])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const verifyLedger = async () => {
    setLoading(true)
    try {
      const res = await api('/api/audit/verify', token, { method: 'POST' })
      setVerification(res)
      if (res.valid) {
        setSuccess(`Verification passed! All ${res.total_events} events cryptographically linked.`)
      } else {
        setError(`Tamper detected at Sequence ${res.tampered_sequence}: ${res.reason}`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const simulateTamper = async () => {
    try {
      const res = await api('/api/audit/tamper-test', token, { method: 'POST', body: JSON.stringify({}) })
      setTamperResult(res)
      setSuccess('Tamper simulation ran on a copy of the ledger. The real ledger was not modified.')
    } catch (err) {
      setError(err.message)
    }
  }

  const counts = useMemo(() => {
    const c = { all: events.length }
    CATEGORIES.forEach(k => { c[k] = 0 })
    events.forEach(ev => { c[categorize(ev)] += 1 })
    return c
  }, [events])

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return events.filter(ev => {
      if (category !== 'all' && categorize(ev) !== category) return false
      if (!q) return true
      return [ev.sequence, ev.event_type, ev.action, ev.actor_id, ev.tenant_id, ev.decision, ev.entry_hash, ev.payload_digest]
        .some(v => v !== undefined && v !== null && String(v).toLowerCase().includes(q))
    })
  }, [events, category, search])

  return (
    <div className="card-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 className="panel-title">
            <Database size={18} color="#6366f1" />
            <span>Blockchain-Lite: Tamper-Evident Audit Ledger (Section 5)</span>
          </h2>
          <p className="panel-subtitle">
            Every security action, ingestion, query, and share grant is canonicalized and chained with SHA-256 hashes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {canTamper ? (
            <button className="btn-secondary" onClick={simulateTamper} style={{ borderColor: 'rgba(244,63,94,0.4)', color: '#fda4af' }}>
              <Flame size={14} />
              <span>Simulate Tamper Attack (on a copy)</span>
            </button>
          ) : (
            <span className="note-muted">Tamper simulation is limited to system administrators.</span>
          )}

          <button className="btn-primary" onClick={verifyLedger} disabled={loading}>
            <CheckCircle2 size={14} />
            <span>Verify Chain Integrity</span>
          </button>
        </div>
      </div>

      <TamperResult result={tamperResult} />

      {verification && (
        <div
          role="status"
          aria-live="polite"
          style={{
            background: verification.valid ? '#D1FAE5' : '#FEE2E2',
            border: `1px solid ${verification.valid ? '#065F46' : '#991B1B'}`,
            padding: '1rem',
            borderRadius: '6px',
            margin: '0.75rem 0 1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.85rem',
          }}
        >
          {verification.valid ? <CheckCircle2 size={24} color="#065F46" /> : <XCircle size={24} color="#991B1B" />}
          <div>
            <b style={{ color: verification.valid ? '#065F46' : '#991B1B', fontSize: '0.95rem', fontWeight: 800 }}>
              {verification.valid ? 'Cryptographic Integrity Intact' : `TAMPER DETECTED at Sequence #${verification.tampered_sequence}`}
            </b>
            <p style={{ fontSize: '0.82rem', color: '#000000', marginTop: '0.2rem', fontWeight: 600 }}>
              {verification.valid ? `Chain head: ${verification.chain_head}` : verification.reason}
              {verification.error_type === 'payload_mismatch' ? ' (payload does not match its recorded digest)' : ''}
            </p>
            {verification.legacy_unverified > 0 && (
              <p style={{ fontSize: '0.78rem', color: '#92400E', marginTop: '0.2rem', fontWeight: 700 }}>
                {verification.legacy_unverified} legacy row(s) were written before payload storage and could not be payload-verified.
              </p>
            )}
          </div>
        </div>
      )}

      <div className="chip-row" role="group" aria-label="Filter events by category">
        {['all', ...CATEGORIES].map(k => (
          <button key={k} type="button" className="chip" aria-pressed={category === k} onClick={() => setCategory(k)}>
            <span style={{ fontWeight: 700 }}>{k}</span>
            <span className="chip-count" style={{ fontWeight: 800, marginLeft: '0.35rem' }}>{counts[k]}</span>
          </button>
        ))}
        <input
          type="search"
          className="input-field ledger-search"
          placeholder="Search loaded events..."
          aria-label="Search loaded audit events"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div style={{ overflowX: 'auto', maxHeight: '550px' }}>
        <table className="ledger-table">
          <thead>
            <tr>
              <th>#Seq</th>
              <th>Timestamp</th>
              <th>Event Type</th>
              <th>Actor (HMAC)</th>
              <th>Organization</th>
              <th>Decision</th>
              <th>Payload Digest</th>
              <th>Entry Hash</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr><td colSpan={8} style={{ color: '#000000', padding: '1rem', fontWeight: 600 }}>No events match the current filter.</td></tr>
            )}
            {visible.map(ev => {
              const denied = isDenied(ev)
              const cls = denied ? 'ledger-row ledger-row-denied' : categorize(ev) === 'security' ? 'ledger-row ledger-row-security' : 'ledger-row'
              return (
                <tr key={ev.sequence} className={cls}>
                  <td style={{ fontWeight: 800, color: '#000000', fontFamily: 'monospace' }}>#{ev.sequence}</td>
                  <td style={{ color: '#000000', fontWeight: 700, fontFamily: 'monospace' }}>{ev.timestamp?.slice(11, 19)}</td>
                  <td><b style={{ color: '#000000', fontWeight: 700 }}>{ev.event_type}</b></td>
                  <td><span className="hash-code" style={{ color: '#000000', fontWeight: 700 }}>{ev.actor_id}</span></td>
                  <td><span className="spec-badge" style={{ color: '#000000', fontWeight: 700 }}>{ev.tenant_id}</span></td>
                  <td>
                    <span className={OK_DECISIONS.has(ev.decision) ? 'decision-ok' : 'decision-bad'} style={{ fontWeight: 800 }}>
                      {denied ? '⛔ ' : ''}{ev.decision}
                    </span>
                  </td>
                  <td><span className="hash-code" style={{ color: '#000000', fontWeight: 700 }}>{ev.payload_digest?.slice(7, 23)}...</span></td>
                  <td><span className="hash-code" style={{ color: '#000000', fontWeight: 700 }}>{ev.entry_hash?.slice(7, 23)}...</span></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
