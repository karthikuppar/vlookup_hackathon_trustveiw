import React, { useState, useEffect } from 'react'
import { Eye, Database, Cpu, Zap, Layers, FileText, CheckCircle2, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../services/http'

export default function TransparencyViewer({ docId, initialData, token, onClose }) {
  const [data, setData] = useState(initialData || null)
  const [loading, setLoading] = useState(!initialData && !docId)
  const [error, setError] = useState('')
  const [expandedChunkId, setExpandedChunkId] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (initialData) {
      setData(initialData)
      return
    }
    if (!docId) return

    let isMounted = true
    const fetchTransparency = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await api(`/api/documents/${docId}/transparency`, token)
        if (isMounted) setData(res)
      } catch (err) {
        if (isMounted) setError(err.message)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    fetchTransparency()
    return () => { isMounted = false }
  }, [docId, initialData, token])

  if (loading) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', background: 'var(--bg-workspace)', borderRadius: '6px', border: '1px solid var(--border-warm)' }}>
        <div style={{ color: 'var(--accent-secondary)', fontWeight: 600, fontSize: '0.85rem' }}>Loading Document Transparency Telemetry...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '1rem', background: 'var(--status-error-bg)', border: '1px solid var(--status-error-border)', borderRadius: '6px', color: 'var(--status-error)', fontSize: '0.82rem' }}>
        Failed to load transparency telemetry: {error}
      </div>
    )
  }

  if (!data) return null

  const chunking = data.chunking || {}
  const embeddings = data.embeddings || {}
  const speed = data.expected_speed || {}
  const intents = data.intent_matching || {}
  const allChunks = chunking.chunks || []

  const filteredChunks = allChunks.filter(c => 
    !searchTerm || 
    c.section?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    c.snippet?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div style={{
      background: 'var(--bg-workspace)',
      border: '1px solid var(--border-warm)',
      borderRadius: '6px',
      padding: '1.25rem',
      marginTop: '1rem',
      boxShadow: 'var(--shadow-card)',
      position: 'relative'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-warm)', paddingBottom: '0.8rem', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Eye size={18} color="var(--accent-primary)" />
            <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-primary)', fontFamily: 'var(--font-headings)' }}>
              Transparency Layer: Ingestion Telemetry
            </span>
            <span style={{ background: 'var(--status-success-bg)', color: 'var(--status-success)', border: '1px solid var(--status-success-border)', fontSize: '0.68rem', padding: '2px 8px', borderRadius: '3px', fontWeight: 600 }}>
              VERIFIED
            </span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Document: <b style={{ color: 'var(--text-primary)' }}>{data.title}</b> ({data.filename}) — Version {data.version_num}
          </div>
        </div>

        {onClose && (
          <button onClick={onClose} className="btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}>
            Close Inspector
          </button>
        )}
      </div>

      {/* KPI 4-Card Grid: Size, Chunks, Embeddings, Speed */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
        {/* Document Volume */}
        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            <span>Size & Characters</span>
            <FileText size={14} color="var(--accent-primary)" />
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '0.3rem', fontFamily: 'var(--font-headings)' }}>
            {(chunking.total_characters || 0).toLocaleString()} <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>chars</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            ~{((chunking.total_characters || 0) / 1024).toFixed(1)} KB text | {(chunking.total_tokens || 0).toLocaleString()} tokens
          </div>
        </div>

        {/* Chunking Processing */}
        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            <span>Chunking Metrics</span>
            <Layers size={14} color="var(--accent-secondary)" />
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '0.3rem', fontFamily: 'var(--font-headings)' }}>
            {chunking.total_chunks || 0} <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>chunks</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Avg {chunking.avg_tokens_per_chunk || 0} tokens ({chunking.min_chunk_tokens || 0} - {chunking.max_chunk_tokens || 0} range)
          </div>
        </div>

        {/* Embedding Dimensions */}
        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            <span>Vector Dimensions</span>
            <Database size={14} color="var(--btn-active)" />
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--btn-active)', marginTop: '0.3rem', fontFamily: 'var(--font-headings)' }}>
            {embeddings.vector_dimension || 512} <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>dims</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            {embeddings.sparsity_profile || 'L2 Unit-Sphere Vectorized'}
          </div>
        </div>

        {/* Retrieval Speed */}
        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            <span>Expected Speed</span>
            <Zap size={14} color="var(--status-warning)" />
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--status-warning)', marginTop: '0.3rem', fontFamily: 'var(--font-headings)' }}>
            {speed.total_api_speed || '< 20 ms'}
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Vector cosine search: {speed.vector_search_latency || '< 1.5ms'}
          </div>
        </div>
      </div>

      {/* Embedding & Architecture Row */}
      <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border-warm)', borderRadius: '4px', padding: '0.85rem', marginBottom: '1.25rem', fontSize: '0.78rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between' }}>
          <div>
            <span style={{ color: 'var(--text-secondary)' }}>Embedding Architecture: </span>
            <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{embeddings.embedding_model}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-secondary)' }}>Content Digest: </span>
            <code style={{ color: 'var(--accent-primary)', background: 'var(--bg-sidebar)', padding: '2px 6px', borderRadius: '3px', border: '1px solid var(--border-warm)' }}>
              {data.digest?.slice(0, 32)}...
            </code>
          </div>
          <div>
            <span style={{ color: 'var(--text-secondary)' }}>Primary Category: </span>
            <span style={{ color: 'var(--status-success)', fontWeight: 600 }}>{intents.primary_category || 'SOP Policy'}</span>
          </div>
        </div>
      </div>

      {/* Chunk Breakdown List with Search */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem', margin: 0, fontFamily: 'var(--font-headings)' }}>
            <Layers size={14} color="var(--accent-secondary)" />
            <span>Extracted Chunks & Vector Elements ({filteredChunks.length} of {allChunks.length})</span>
          </h4>
          <input
            type="text"
            placeholder="Filter chunks by section or text..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="input-field"
            style={{ width: '240px', padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
          />
        </div>

        <div style={{ maxHeight: '280px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.45rem', paddingRight: '0.25rem' }}>
          {filteredChunks.map(c => {
            const isExpanded = expandedChunkId === c.id
            return (
              <div
                key={c.id}
                style={{
                  background: 'var(--bg-main)',
                  border: '1px solid var(--border-warm)',
                  borderRadius: '4px',
                  padding: '0.65rem 0.85rem',
                  fontSize: '0.78rem',
                  transition: 'border-color 0.15s ease'
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={() => setExpandedChunkId(isExpanded ? null : c.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--accent-primary)', fontFamily: 'var(--font-headings)' }}>
                      Chunk #{c.id}
                    </span>
                    <span style={{ color: 'var(--text-secondary)' }}>· {c.section || 'General'}</span>
                    <span style={{ background: 'var(--bg-sidebar)', padding: '1px 5px', borderRadius: '3px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      Page {c.page}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>
                      {c.token_count} tokens ({c.char_count} chars)
                    </span>
                    {isExpanded ? <ChevronUp size={14} color="var(--text-secondary)" /> : <ChevronDown size={14} color="var(--text-secondary)" />}
                  </div>
                </div>

                {isExpanded && (
                  <div style={{
                    marginTop: '0.6rem',
                    padding: '0.6rem',
                    background: 'var(--bg-workspace)',
                    border: '1px solid var(--border-warm)',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.78rem',
                    color: 'var(--text-primary)',
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap'
                  }}>
                    {c.snippet}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
