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

      <div style={{ marginTop: '1.25rem', background: '#FAF7F0', border: '1px solid #000000', borderRadius: '6px', padding: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span className="indicator-dot dot-cyan" />
          <b style={{ color: '#000000', fontWeight: 800 }}>Deployment Mode: {teeStatus?.mode?.toUpperCase()}</b>
        </div>
        <p style={{ fontSize: '0.85rem', color: '#000000', marginTop: '0.5rem', lineHeight: 1.5, fontWeight: 500 }}>
          {teeStatus?.status_description}
        </p>

        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ background: '#F0E9DD', border: '1px solid #000000', padding: '0.75rem', borderRadius: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: '#000000', textTransform: 'uppercase', fontWeight: 700 }}>Expected MRENCLAVE:</span>
            <div className="hash-code" style={{ marginTop: '0.35rem', display: 'block', wordBreak: 'break-all' }}>{teeStatus?.attestation_policy?.expected_mrenclave}</div>
          </div>
          <div style={{ background: '#F0E9DD', border: '1px solid #000000', padding: '0.75rem', borderRadius: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: '#000000', textTransform: 'uppercase', fontWeight: 700 }}>Expected MRSIGNER:</span>
            <div className="hash-code" style={{ marginTop: '0.35rem', display: 'block', wordBreak: 'break-all' }}>{teeStatus?.attestation_policy?.expected_mrsigner}</div>
          </div>
        </div>
      </div>

      {/* Attestation Verification Playground */}
      <div style={{ marginTop: '1.5rem' }}>
        <h3 style={{ fontSize: '0.92rem', color: '#000000', fontWeight: 800, marginBottom: '0.5rem' }}>Attestation Policy Verification Simulator</h3>
        <p style={{ fontSize: '0.82rem', color: '#000000', marginBottom: '1rem' }}>
          Demonstrate that secrets are released ONLY when attestation measurements match approved policy.
        </p>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn-primary" onClick={() => testAttestation(false)}>
            <CheckCircle2 size={14} />
            <span>Test Valid Attestation Quote</span>
          </button>

          <button className="btn-secondary" style={{ borderColor: '#991B1B', color: '#991B1B' }} onClick={() => testAttestation(true)}>
            <XCircle size={14} />
            <span>Test Tampered Quote (Should Reject)</span>
          </button>
        </div>

        {attestationRes && (
          <div style={{
            marginTop: '1.25rem',
            padding: '1rem',
            borderRadius: '6px',
            background: attestationRes.verified ? '#D1FAE5' : '#FEE2E2',
            border: `1px solid ${attestationRes.verified ? '#065F46' : '#991B1B'}`,
          }}>
            <b style={{ color: attestationRes.verified ? '#065F46' : '#991B1B', fontWeight: 800 }}>
              Attestation Result: {attestationRes.status}
            </b>
            <p style={{ fontSize: '0.82rem', color: '#000000', marginTop: '0.25rem', fontWeight: 600 }}>
              Secret Released: {attestationRes.secret_released ? `Yes [${attestationRes.released_secret}]` : 'Denied (0 secrets released)'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
