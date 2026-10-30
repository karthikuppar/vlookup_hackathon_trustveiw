import React, { useState, useEffect } from 'react'
import { Cpu, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../services/http'

export default function TeeView({ token, setSuccess, setError }) {
  const [teeStatus, setTeeStatus] = useState(null)
  const [attestationRes, setAttestationRes] = useState(null)

  useEffect(() => {
    if (!token) return
    api('/api/security/tee-status', token)
      .then(setTeeStatus)
      .catch(err => setError(err.message))
  }, [token, setError])

  const testAttestation = async simulateInvalid => {
    try {
      const res = await api('/api/security/tee-verify', token, {
        method: 'POST',
        body: JSON.stringify({ simulate_invalid: simulateInvalid }),
      })
      setAttestationRes(res)
      if (res.verified) {
        setSuccess('Attestation verified! Mock encryption secret released.')
      } else {
        setError(`Attestation rejected: ${res.reason}`)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="card-panel">
      <h2 className="panel-title">
        <Cpu size={18} color="#6366f1" />
        <span>Confidential Computing & TEE Simulation (Section 6)</span>
      </h2>
      <p className="panel-subtitle">
        Per Section 6.2 of the specification, the application truthfully discloses deployment status as a SIMULATION unless compatible confidential hardware (Intel TDX / AMD SEV-SNP) is present.
      </p>

      <div style={{ marginTop: '1.25rem', background: 'rgba(9, 13, 22, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span className="indicator-dot dot-cyan" />
          <b style={{ color: '#22d3ee' }}>Deployment Mode: {teeStatus?.mode?.toUpperCase()}</b>
        </div>
        <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.5rem', lineHeight: 1.5 }}>
          {teeStatus?.status_description}
        </p>

        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Expected MRENCLAVE:</span>
            <div className="hash-code" style={{ marginTop: '0.25rem' }}>{teeStatus?.attestation_policy?.expected_mrenclave}</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Expected MRSIGNER:</span>
            <div className="hash-code" style={{ marginTop: '0.25rem' }}>{teeStatus?.attestation_policy?.expected_mrsigner}</div>
          </div>
        </div>
      </div>

      {/* Attestation Verification Playground */}
      <div style={{ marginTop: '1.5rem' }}>
        <h3 style={{ fontSize: '0.92rem', color: '#fff', marginBottom: '0.5rem' }}>Attestation Policy Verification Simulator</h3>
        <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '1rem' }}>
          Demonstrate that secrets are released ONLY when attestation measurements match approved policy.
        </p>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn-primary" onClick={() => testAttestation(false)}>
            <CheckCircle2 size={14} />
            <span>Test Valid Attestation Quote</span>
          </button>

          <button className="btn-secondary" style={{ borderColor: 'rgba(244,63,94,0.4)', color: '#fb7185' }} onClick={() => testAttestation(true)}>
            <XCircle size={14} />
            <span>Test Tampered Quote (Should Reject)</span>
          </button>
        </div>

        {attestationRes && (
          <div style={{
            marginTop: '1.25rem',
            padding: '1rem',
            borderRadius: '8px',
            background: attestationRes.verified ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
            border: `1px solid ${attestationRes.verified ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`,
          }}>
            <b style={{ color: attestationRes.verified ? '#34d399' : '#fb7185' }}>
              Attestation Result: {attestationRes.status}
            </b>
            <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
              Secret Released: {attestationRes.secret_released ? `Yes [${attestationRes.released_secret}]` : 'Denied (0 secrets released)'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
