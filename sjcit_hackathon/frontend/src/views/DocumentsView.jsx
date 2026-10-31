import React, { useState, useEffect, useCallback } from 'react'
import { Upload, FileText, RefreshCw, FileUp, Edit3, Eye, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { api, isAdminRole } from '../services/http'
import Banner from '../components/Banner'
import PdfUploader from '../components/PdfUploader'
import TransparencyViewer from '../components/TransparencyViewer'

const injectionWarning = n => `${n} chunk(s) identified as potential prompt-injection text and excluded.`

export default function DocumentsView({ token, user, setSuccess, setError }) {
  const [warning, setWarning] = useState('')
  const [docs, setDocs] = useState([])
  const [uploadMode, setUploadMode] = useState('pdf') // 'pdf' or 'manual'
  const [title, setTitle] = useState('')
  const [filename, setFilename] = useState('')
  const [content, setContent] = useState('')
  const [replacingDocId, setReplacingDocId] = useState(null)
  const [replaceContent, setReplaceContent] = useState('')
  const [inspectDocId, setInspectDocId] = useState(null)

  const isAdmin = isAdminRole(user?.role)

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
      setSuccess('Document uploaded and version 1 activated.')
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
      setSuccess('New version activated. Previous version superseded.')
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
        {/* Upload Column - Restricted to Administrator Role */}
        {isAdmin ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Toggle Mode */}
            <div style={{ display: 'flex', background: 'var(--bg-sidebar)', padding: '3px', borderRadius: '4px', border: '1px solid var(--border-warm)' }}>
              <button
                type="button"
                onClick={() => setUploadMode('pdf')}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem',
                  padding: '0.45rem',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  fontFamily: 'var(--font-headings)',
                  borderRadius: '3px',
                  border: 'none',
                  cursor: 'pointer',
                  background: uploadMode === 'pdf' ? 'var(--btn-active)' : 'transparent',
                  color: uploadMode === 'pdf' ? '#FFFCF6' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                <FileUp size={14} />
                <span>Upload Document (Auto-Parse)</span>
              </button>
              <button
                type="button"
                onClick={() => setUploadMode('manual')}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem',
                  padding: '0.45rem',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  fontFamily: 'var(--font-headings)',
                  borderRadius: '3px',
                  border: 'none',
                  cursor: 'pointer',
                  background: uploadMode === 'manual' ? 'var(--btn-active)' : 'transparent',
                  color: uploadMode === 'manual' ? '#FFFCF6' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                <Edit3 size={14} />
                <span>Paste Raw Text</span>
              </button>
            </div>

            {/* PDF Uploader Component */}
            {uploadMode === 'pdf' ? (
              <PdfUploader
                token={token}
                user={user}
                onSuccess={(msg) => {
                  setSuccess(msg)
                  fetchDocs()
                }}
                onError={setError}
              />
            ) : (
              <div className="card-panel">
                <h2 className="panel-title">
                  <Upload size={18} color="var(--accent-primary)" />
                  <span>Paste Text Document</span>
                </h2>
                <p className="panel-subtitle">Ingests text policies, computes SHA-256 digest, and activates version 1.</p>

                <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginTop: '1rem' }}>
                  <div>
                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, fontFamily: 'var(--font-headings)' }}>Document Title</label>
                    <input required className="input-field" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Vendor Invoicing Standard 2026" />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, fontFamily: 'var(--font-headings)' }}>Filename</label>
                    <input className="input-field" value={filename} onChange={e => setFilename(e.target.value)} placeholder="e.g. invoice_policy_v1.txt" />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, fontFamily: 'var(--font-headings)' }}>Document Text Content</label>
                    <textarea required rows={8} className="textarea-field" value={content} onChange={e => setContent(e.target.value)} placeholder="Paste SOP, policies, or contract text here..." />
                  </div>

                  <button type="submit" className="btn-primary">
                    <Upload size={14} />
                    <span>Ingest Document</span>
                  </button>
                </form>
              </div>
            )}
          </div>
        ) : (
          <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <FileText size={20} color="var(--accent-primary)" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--accent-primary)', margin: 0, fontFamily: 'var(--font-headings)' }}>
                Authorized Knowledge Base
              </h3>
            </div>
            <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              You have active query and search access to verified Standard Operating Procedures (SOPs) authorized for your organization.
            </p>
            <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem', fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem', fontFamily: 'var(--font-headings)' }}>
                <ShieldCheck size={14} color="var(--accent-secondary)" />
                <span>Administrator Governance</span>
              </div>
              <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                Document ingestion, vector embeddings telemetry, and version management are governed by organization administrators.
              </p>
            </div>
            <div style={{ background: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)', borderRadius: '4px', padding: '0.75rem', fontSize: '0.78rem', color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <CheckCircle2 size={14} />
              <span>Active SOP: <b>SOP 01 Northstar Retail Returns</b> (Verified & Grounded)</span>
            </div>
          </div>
        )}

        {/* Document Library */}
        <div className="card-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 className="panel-title">
              <FileText size={18} color="var(--accent-primary)" />
              <span>Document Library ({docs.length})</span>
            </h2>
            <button onClick={fetchDocs} aria-label="Refresh document list" className="btn-secondary" style={{ padding: '0.35rem 0.65rem' }}>
              <RefreshCw size={13} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', maxHeight: '560px', overflowY: 'auto' }}>
            {docs.length === 0 && <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No documents uploaded yet.</p>}
            {docs.map(doc => (
              <div key={doc.id} style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <b style={{ color: 'var(--accent-primary)', fontSize: '0.92rem', fontFamily: 'var(--font-headings)' }}>{doc.title}</b>
                  <span className="spec-badge">Active v{doc.current_version}</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>File: {doc.original_filename}</p>
                <div style={{ marginTop: '0.4rem', fontSize: '0.74rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Content Digest: </span>
                  <span className="hash-code">{doc.current_digest?.slice(0, 32)}...</span>
                </div>

                {/* Version History List */}
                <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'var(--bg-workspace)', border: '1px solid var(--border-warm)', borderRadius: '4px' }}>
                  <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: 'var(--font-headings)' }}>
                    Version History:
                  </span>
                  {doc.versions?.map(v => (
                    <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', marginTop: '0.3rem' }}>
                      <span>Version {v.version_num} ({v.created_at?.slice(0, 10)})</span>
                      <span style={{
                        padding: '0.12rem 0.4rem',
                        borderRadius: '3px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        background: v.status === 'active' ? 'var(--status-success-bg)' : 'var(--bg-sidebar)',
                        color: v.status === 'active' ? 'var(--status-success)' : 'var(--text-secondary)',
                        border: `1px solid ${v.status === 'active' ? 'var(--status-success-border)' : 'var(--border-warm)'}`
                      }}>
                        {v.status}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Admin Transparency Telemetry Inspection */}
                {isAdmin && (
                  <div style={{ marginTop: '0.75rem' }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{
                        width: '100%',
                        fontSize: '0.76rem',
                        justifyContent: 'center',
                        background: inspectDocId === doc.id ? 'var(--bg-sidebar)' : 'var(--bg-workspace)',
                        borderColor: inspectDocId === doc.id ? 'var(--accent-secondary)' : 'var(--border-warm)',
                        color: inspectDocId === doc.id ? 'var(--accent-primary)' : 'var(--text-primary)'
                      }}
                      onClick={() => setInspectDocId(inspectDocId === doc.id ? null : doc.id)}
                    >
                      <Eye size={13} color="var(--accent-secondary)" />
                      <span>{inspectDocId === doc.id ? 'Close Transparency Inspection' : 'Inspect Processing & Embeddings (Admin)'}</span>
                    </button>

                    {inspectDocId === doc.id && (
                      <div style={{ marginTop: '0.75rem' }}>
                        <TransparencyViewer
                          docId={doc.id}
                          token={token}
                          onClose={() => setInspectDocId(null)}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Replace Version Trigger - Admin Only */}
                {isAdmin && (
                  replacingDocId === doc.id ? (
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
                      style={{ marginTop: '0.6rem', width: '100%', fontSize: '0.78rem', justifyContent: 'center' }}
                      onClick={() => { setReplacingDocId(doc.id); setReplaceContent('') }}
                    >
                      <RefreshCw size={13} />
                      <span>Upload Replacement Version</span>
                    </button>
                  )
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
