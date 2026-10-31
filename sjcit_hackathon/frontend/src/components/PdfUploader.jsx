import React, { useState, useEffect, useCallback } from 'react'
import { Upload, FileUp, CheckCircle2, AlertTriangle, User, Loader2 } from 'lucide-react'
import { api, isAdminRole } from '../services/http'
import TransparencyViewer from './TransparencyViewer'

export default function PdfUploader({ token, user, onSuccess, onError }) {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [members, setMembers] = useState([])
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const [loadingMembers, setLoadingMembers] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [ingestResult, setIngestResult] = useState(null)

  const isAdmin = isAdminRole(user?.role)
  const tenantId = user?.tenant_id || 'tenant_a'

  // Load existing employees for the dropdown
  const loadEmployees = useCallback(async () => {
    setLoadingMembers(true)
    try {
      const res = await api(`/api/clients/${tenantId}/members`, token)
      const list = res.members || []
      setMembers(list)
      // Default to current user or first employee
      if (list.length > 0 && !selectedEmployeeId) {
        const found = list.find(m => m.id === user?.id) || list[0]
        setSelectedEmployeeId(found.id)
      }
    } catch {
      // fallback: use current user
      if (user?.id) setSelectedEmployeeId(user.id)
    } finally {
      setLoadingMembers(false)
    }
  }, [tenantId, token, user?.id, selectedEmployeeId])

  useEffect(() => {
    loadEmployees()
  }, [loadEmployees])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      if (!title) {
        // Automatically derive clean title from filename
        const cleanName = f.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')
        setTitle(cleanName.charAt(0).toUpperCase() + cleanName.slice(1))
      }
      setIngestResult(null)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) {
      onError('Please select a PDF or document file to upload.')
      return
    }

    setUploading(true)
    setIngestResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title.trim() || file.name)
      if (selectedEmployeeId) {
        formData.append('employee_id', selectedEmployeeId)
      }

      // Upload via multipart form-data
      const res = await fetch(`/api/clients/${tenantId}/documents`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Failed to parse and ingest document')
      }

      setIngestResult(data)
      const empName = members.find(m => m.id === selectedEmployeeId)?.name || 'Employee'
      onSuccess?.(`Document "${data.title}" successfully ingested for ${empName} (${data.chunks_count} chunks).`)

      // Reset file input
      setFile(null)
      setTitle('')
      const fileInput = document.getElementById('pdf-file-input')
      if (fileInput) fileInput.value = ''
    } catch (err) {
      onError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="card-panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
        <FileUp size={18} color="var(--accent-primary)" />
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-primary)', margin: 0, fontFamily: 'var(--font-headings)' }}>
          Upload & Ingest Document
        </h3>
      </div>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
        Select a document file and assign attribution. The system extracts text, chunks paragraphs, applies guardrails, generates embeddings, and indexes graph nodes automatically.
      </p>

      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Employee Dropdown Selection */}
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '0.35rem', fontFamily: 'var(--font-headings)' }}>
            <User size={13} color="var(--accent-secondary)" />
            <span>Select Employee Attribution:</span>
          </label>
          <select
            value={selectedEmployeeId}
            onChange={e => setSelectedEmployeeId(e.target.value)}
            disabled={uploading || loadingMembers}
            className="select-field"
          >
            {members.length === 0 ? (
              <option value={user?.id || ''}>{user?.name || 'Current Admin'} ({user?.email || 'me'})</option>
            ) : (
              members.map(m => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.email}) — {m.role === 'client_admin' ? 'Admin' : 'Employee'}
                </option>
              ))
            )}
          </select>
        </div>

        {/* File Picker */}
        <div>
          <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '0.35rem', fontFamily: 'var(--font-headings)' }}>
            Choose File:
          </label>
          <div style={{
            border: '1px dashed var(--border-warm)',
            borderRadius: '4px',
            padding: '1.25rem',
            textAlign: 'center',
            background: file ? 'var(--bg-main)' : 'var(--bg-workspace)',
            cursor: 'pointer',
            transition: 'border-color 0.15s ease'
          }}>
            <input
              id="pdf-file-input"
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleFileChange}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            <label htmlFor="pdf-file-input" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
              <Upload size={22} color="var(--accent-secondary)" />
              {file ? (
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--accent-primary)', fontSize: '0.85rem' }}>{file.name}</div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>{(file.size / 1024).toFixed(1)} KB — Ready to parse</div>
                </div>
              ) : (
                <div>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>Click to browse or drop file here</span>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>Supports .pdf, .txt, .md (up to 15 MB)</div>
                </div>
              )}
            </label>
          </div>
        </div>

        {/* Document Title */}
        <div>
          <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '0.35rem', fontFamily: 'var(--font-headings)' }}>
            Document Display Title:
          </label>
          <input
            type="text"
            className="input-field"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Employee Handbook 2026"
            disabled={uploading}
          />
        </div>

        {/* Upload Button */}
        <button
          type="submit"
          className="btn-primary"
          disabled={!file || uploading}
          style={{ width: '100%', marginTop: '0.25rem' }}
        >
          {uploading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              <span>Parsing Document & Embedding...</span>
            </>
          ) : (
            <>
              <FileUp size={15} />
              <span>Ingest & Vectorize Document</span>
            </>
          )}
        </button>
      </form>

      {/* Ingestion Results Feedback */}
      {ingestResult && (
        <div style={{ marginTop: '1rem', padding: '0.85rem', background: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)', borderRadius: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--status-success)', fontWeight: 600, fontSize: '0.85rem' }}>
            <CheckCircle2 size={16} />
            <span>Document Ingestion Complete</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.5rem', marginTop: '0.6rem', fontSize: '0.75rem' }}>
            <div style={{ background: 'var(--bg-workspace)', padding: '0.4rem 0.6rem', borderRadius: '3px', border: '1px solid var(--border-warm)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Status: </span>
              <b style={{ color: 'var(--status-success)' }}>{ingestResult.status}</b>
            </div>
            <div style={{ background: 'var(--bg-workspace)', padding: '0.4rem 0.6rem', borderRadius: '3px', border: '1px solid var(--border-warm)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Chunks: </span>
              <b style={{ color: 'var(--accent-primary)' }}>{ingestResult.chunks_count} chunks</b>
            </div>
            <div style={{ background: 'var(--bg-workspace)', padding: '0.4rem 0.6rem', borderRadius: '3px', border: '1px solid var(--border-warm)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Version: </span>
              <b style={{ color: 'var(--text-primary)' }}>v{ingestResult.version_num}</b>
            </div>
          </div>
          {ingestResult.injection_flagged_chunks > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--status-warning)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
              <AlertTriangle size={14} />
              <span>{ingestResult.injection_flagged_chunks} chunk(s) stripped by prompt injection guardrails.</span>
            </div>
          )}
        </div>
      )}

      {/* Admin Transparency Telemetry Layer - Restricted to Admin Layer */}
      {ingestResult && isAdmin && (
        <TransparencyViewer
          initialData={ingestResult.transparency}
          docId={ingestResult.document_id}
          token={token}
          onClose={() => setIngestResult(null)}
        />
      )}
    </div>
  )
}
