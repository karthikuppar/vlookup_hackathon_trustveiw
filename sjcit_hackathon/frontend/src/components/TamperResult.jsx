import React from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'

// Detection result of a tamper SIMULATION (run on a copy of the ledger, never the real one).
export default function TamperResult({ result }) {
  const v = result?.verification
  if (!v) return null
  const detected = v.valid === false
  return (
    <div
      role="status"
      aria-live="polite"
      className={`banner ${detected ? 'banner-warning' : 'banner-success'}`}
      style={{ alignItems: 'center', marginTop: '0.75rem' }}
    >
      {detected ? <XCircle size={20} /> : <CheckCircle2 size={20} />}
      <div style={{ flex: 1 }}>
        <b>Simulation on a copy of the ledger: {detected ? 'tampering detected' : 'not detected'}</b>
        <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
          Tampered sequence #{v.tampered_sequence ?? result.tampered_sequence}
          {v.error_type ? ` · ${v.error_type}` : ''}
          {v.reason ? ` · ${v.reason}` : ''}
        </div>
        <div style={{ fontSize: '0.74rem', marginTop: '0.2rem', opacity: 0.9 }}>
          {result.real_ledger_modified === false ? 'The real ledger was not modified.' : 'Simulation result.'}
        </div>
      </div>
    </div>
  )
}
