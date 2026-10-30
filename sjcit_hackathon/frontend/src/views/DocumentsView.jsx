import React, { useState, useEffect, useCallback } from 'react'
import { Upload, FileText, RefreshCw } from 'lucide-react'
import { api } from '../services/http'
import Banner from '../components/Banner'

const injectionWarning = n => `${n} chunk(s) look like prompt-injection text and will be excluded from answers.`

export default function DocumentsView({ token, user, setSuccess, setError }) {
  const [warning, setWarning] = useState('')
  const [docs, setDocs] = useState([])
  const [title, setTitle] = useState('')
  const [filename, setFilename] = useState('')
  const [content, setContent] = useState('')
  const [replacingDocId, setReplacingDocId] = useState(null)
  const [replaceContent, setReplaceContent] = useState('')

  const fetchDocs = useCallback(async () => {
    try {
      const data = await api(`/api/clients/${user?.tenant_id}/documents`, token)
      setDocs(data.documents || [])
    } catch (err) {
      setError(err.message)
    }
  }, [token, user?.tenant_id, setError])

  useEffect(() => {
    fetchDocs()
  }, [fetchDocs])

  const handleUpload = async e => {
    e.preventDefault()
    setWarning('')
    try {
      const res = await api(`/api/clients/${user?.tenant_id}/documents`, token, {
        method: 'POST',
        body: JSON.stringify({ title, filename: filename || `${title.toLowerCase().replace(/\s+/g, '_')}.txt`, content }),
      })
      if (res?.injection_flagged_chunks > 0) setWarning(injectionWarning(res.injection_flagged_chunks))
      setSuccess('Document uploaded and version 1 activated!')
      setTitle('')
      setFilename('')
      setContent('')
      fetchDocs()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleReplaceVersion = async docId => {
    setWarning('')
    try {
      const res = await api(`/api/documents/${docId}/versions`, token, {
        method: 'POST',
        body: JSON.stringify({ filename: 'replacement_version.txt', content: replaceContent }),
      })
      if (res?.injection_flagged_chunks > 0) setWarning(injectionWarning(res.injection_flagged_chunks))
      setSuccess('New version activated! Previous version atomically superseded.')
      setReplacingDocId(null)
      setReplaceContent('')
      fetchDocs()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
    <Banner kind="warning" onClose={() => setWarning('')}>{warning}</Banner>
    <div className="grid-2col">
      {/* Upload Panel */}
      <div className="card-panel">
        <h2 className="panel-title">
          <Upload size={18} color="#6366f1" />
          <span>Upload Document (Initial Version)</span>
        </h2>
        <p className="panel-subtitle">Ingests text or policies, computes content SHA-256 digest, and creates version 1.</p>

        <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginTop: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Document Title</label>
            <input required className="input-field" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Vendor Invoicing Standard 2026" />
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Filename</label>
            <input className="input-field" value={filename} onChange={e => setFilename(e.target.value)} placeholder="e.g. invoice_policy_v1.txt" />
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Document Text Content</label>
            <textarea required rows={8} className="textarea-field" value={content} onChange={e => setContent(e.target.value)} placeholder="Paste SOP, policies, or contract text here..." />
          </div>

          <button type="submit" className="btn-primary">
            <Upload size={14} />
            <span>Ingest Document</span>
          </button>
        </form>
      </div>

      {/* Document Library & Version Timeline */}
      <div className="card-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 className="panel-title">
            <FileText size={18} color="#6366f1" />
            <span>Tenant Document Library ({docs.length})</span>
          </h2>
          <button onClick={fetchDocs} aria-label="Refresh document list" className="btn-secondary" style={{ padding: '0.35rem 0.65rem' }}>
            <RefreshCw size={13} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '560px', overflowY: 'auto' }}>
          {docs.length === 0 && <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No documents uploaded yet for this tenant.</p>}
          {docs.map(doc => (
            <div key={doc.id} style={{ background: 'rgba(9, 13, 22, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <b style={{ color: '#fff', fontSize: '0.95rem' }}>{doc.title}</b>
                <span className="spec-badge">Active v{doc.current_version}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.25rem' }}>File: {doc.original_filename}</p>
              <div style={{ marginTop: '0.5rem', fontSize: '0.74rem' }}>
                <span style={{ color: '#64748b' }}>Active Content Digest: </span>
                <span className="hash-code">{doc.current_digest?.slice(0, 32)}...</span>
              </div>

              {/* Version History List */}
              <div style={{ marginTop: '0.75rem', padding: '0.65rem', background: 'rgba(0,0,0,0.25)', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Version History (Audit Kept):</span>
                {doc.versions?.map(v => (
                  <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', marginTop: '0.35rem' }}>
                    <span>Version {v.version_num} ({v.created_at?.slice(0, 10)})</span>
                    <span style={{
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      background: v.status === 'active' ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.2)',
                      color: v.status === 'active' ? '#34d399' : '#94a3b8',
                    }}>
                      {v.status}
                    </span>
                  </div>
                ))}
              </div>

              {/* Replace Version Trigger */}
              {replacingDocId === doc.id ? (
                <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <textarea
                    rows={4}
                    className="textarea-field"
                    value={replaceContent}
                    onChange={e => setReplaceContent(e.target.value)}
                    placeholder="Enter revised document text for next version..."
                  />
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn-primary" style={{ flex: 1 }} onClick={() => handleReplaceVersion(doc.id)}>
                      Activate Next Version
                    </button>
                    <button className="btn-secondary" onClick={() => setReplacingDocId(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <button
                  className="btn-secondary"
                  style={{ marginTop: '0.75rem', width: '100%', fontSize: '0.8rem', justifyContent: 'center' }}
                  onClick={() => { setReplacingDocId(doc.id); setReplaceContent('') }}
                >
                  <RefreshCw size={13} />
                  <span>Upload Replacement Version</span>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
    </div>
  )
}
