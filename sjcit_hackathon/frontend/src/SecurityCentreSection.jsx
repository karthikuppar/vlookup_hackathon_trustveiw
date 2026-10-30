import React, { useState, useEffect, useCallback } from 'react'
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Play,
  RotateCcw,
  Download,
  AlertCircle,
  Sliders,
  Filter,
  Terminal,
  ChevronDown,
  ChevronUp,
  FileText,
  Check,
  Bug,
  Wrench,
  ExternalLink,
  Zap,
} from 'lucide-react'

// --- API Helper matching App.jsx ---
const api = async (path, token, options = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  }
  const res = await fetch(path, { ...options, headers })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Request failed (${res.status})`)
  }
  return data
}

export default function SecurityCentreSection({ token, user, setSuccess, setError }) {
  // State
  const [stats, setStats] = useState(null)
  const [categories, setCategories] = useState([])
  const [scans, setScans] = useState([])
  const [activeScanId, setActiveScanId] = useState(null)
  const [activeScanDetails, setActiveScanDetails] = useState(null)
  const [findings, setFindings] = useState([])
  const [selectedFinding, setSelectedFinding] = useState(null)

  // Selection & Filters
  const [selectedCategories, setSelectedCategories] = useState([])
  const [scopeAccordionOpen, setScopeAccordionOpen] = useState(false)
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')

  // Execution states
  const [scanning, setScanning] = useState(false)
  const [remediatingId, setRemediatingId] = useState(null)
  const [verifyingId, setVerifyingId] = useState(null)
  const [rollingBackId, setRollingBackId] = useState(null)
  const [exportingReport, setExportingReport] = useState(false)

  // Load initial posture and categories
  const loadData = useCallback(async () => {
    try {
      const [statsData, catData, scansData] = await Promise.all([
        api('/api/admin/security/stats', token),
        api('/api/admin/security/categories', token),
        api('/api/admin/security/scans', token),
      ])
      setStats(statsData)
      setCategories(catData)
      setScans(scansData)

      if (scansData && scansData.length > 0) {
        const latestId = scansData[0].id
        setActiveScanId(latestId)
        const scanDetail = await api(`/api/admin/security/scans/${latestId}`, token)
        setActiveScanDetails(scanDetail)
        setFindings(scanDetail.findings || [])
      } else {
        const findingsData = await api('/api/admin/security/findings', token)
        setFindings(findingsData)
      }
    } catch (err) {
      setError(err.message)
    }
  }, [token, setError])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Select scan to inspect
  const handleSelectScan = async (scanId) => {
    try {
      setActiveScanId(scanId)
      const scanDetail = await api(`/api/admin/security/scans/${scanId}`, token)
      setActiveScanDetails(scanDetail)
      setFindings(scanDetail.findings || [])
    } catch (err) {
      setError(err.message)
    }
  }

  // Trigger real security scan
  const handleRunScan = async (useTargeted = false) => {
    setScanning(true)
    setError('')
    try {
      const payload = useTargeted && selectedCategories.length > 0 ? { scope: selectedCategories } : {}
      const res = await api('/api/admin/security/scans', token, {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setSuccess(`✅ Security assessment completed in ${res.duration_seconds}s! Evaluated ${res.total_tests} test categories.`)
      await loadData()
      if (res.id) {
        handleSelectScan(res.id)
      }
    } catch (err) {
      setError(`Security scan failed: ${err.message}`)
    } finally {
      setScanning(false)
    }
  }

  // Toggle category in custom scope
  const toggleCategory = (key) => {
    setSelectedCategories(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  const selectAllCategories = () => {
    setSelectedCategories(categories.map(c => c.key))
  }

  const clearAllCategories = () => {
    setSelectedCategories([])
  }

  // Apply proposed remediation
  const handleApplyRemediation = async (finding) => {
    setRemediatingId(finding.id)
    try {
      const res = await api(`/api/admin/security/findings/${finding.id}/remediate`, token, { method: 'POST' })
      setSuccess(`Applied automated patch for: ${finding.title}. Verification is ready.`)

      // Update finding status locally
      setFindings(prev => prev.map(f => f.id === finding.id ? { ...f, status: 'IN_REMEDIATION', remediation_id: res.remediation_id, remediation_status: 'APPLIED' } : f))
      if (selectedFinding && selectedFinding.id === finding.id) {
        setSelectedFinding(prev => ({ ...prev, status: 'IN_REMEDIATION', remediation_id: res.remediation_id, remediation_status: 'APPLIED' }))
      }
      loadData()
    } catch (err) {
      setError(`Failed to apply remediation: ${err.message}`)
    } finally {
      setRemediatingId(null)
    }
  }

  // Verify remediation with automated re-test
  const handleVerifyRemediation = async (remId, findingId) => {
    if (!remId) return
    setVerifyingId(remId)
    try {
      const res = await api(`/api/admin/security/remediations/${remId}/verify`, token, { method: 'POST' })
      if (res.verification_outcome === 'PASS') {
        setSuccess(`✅ Post-remediation verification PASSED! Vulnerability is fixed.`)
        setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: 'FIXED', remediation_status: 'VERIFIED' } : f))
        if (selectedFinding && selectedFinding.id === findingId) {
          setSelectedFinding(prev => ({ ...prev, status: 'FIXED', remediation_status: 'VERIFIED' }))
        }
      } else {
        setError(`⚠️ Post-remediation verification failed: ${res.error || 'Test still detected vulnerability.'}`)
        setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: 'VERIFICATION_FAILED', remediation_status: 'FAILED' } : f))
      }
      loadData()
    } catch (err) {
      setError(`Verification request failed: ${err.message}`)
    } finally {
      setVerifyingId(null)
    }
  }

  // Rollback remediation
  const handleRollbackRemediation = async (remId, findingId) => {
    if (!remId) return
    setRollingBackId(remId)
    try {
      const res = await api(`/api/admin/security/remediations/${remId}/rollback`, token, { method: 'POST' })
      setSuccess(`Rolled back patch for remediation ${remId}. Vulnerability status reset to OPEN.`)
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: 'OPEN', remediation_status: 'ROLLED_BACK' } : f))
      if (selectedFinding && selectedFinding.id === findingId) {
        setSelectedFinding(prev => ({ ...prev, status: 'OPEN', remediation_status: 'ROLLED_BACK' }))
      }
      loadData()
    } catch (err) {
      setError(`Rollback failed: ${err.message}`)
    } finally {
      setRollingBackId(null)
    }
  }

  // Export JSON Report
  const handleExportReport = async () => {
    if (!activeScanId) return
    setExportingReport(true)
    try {
      const report = await api(`/api/admin/security/reports/${activeScanId}/export`, token)
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Security_Assessment_Report_${activeScanId}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setSuccess(`Exported report ${report.report_id} conforming to CVSS v3.1 and zero-egress standards.`)
    } catch (err) {
      setError(`Failed to export report: ${err.message}`)
    } finally {
      setExportingReport(false)
    }
  }

  // Filter findings
  const filteredFindings = findings.filter(f => {
    if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false
    if (statusFilter !== 'ALL' && f.status !== statusFilter) return false
    return true
  })

  const postureScore = stats?.posture_score ?? 100
  const postureRating = stats?.posture_rating ?? 'EXCELLENT'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner: Security Posture Score & Controls */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        borderRadius: '16px',
        padding: '1.5rem',
        backdropFilter: 'blur(10px)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.25rem' }}>
          {/* Posture Score Display */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{
              width: '84px',
              height: '84px',
              borderRadius: '50%',
              background: `conic-gradient(#10b981 ${postureScore * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(16, 185, 129, 0.25)',
            }}>
              <div style={{
                width: '68px',
                height: '68px',
                borderRadius: '50%',
                background: '#0f172a',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <span style={{ fontSize: '1.35rem', fontWeight: 800, color: '#f8fafc', lineHeight: 1 }}>
                  {postureScore}
                </span>
                <span style={{ fontSize: '0.62rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  / 100
                </span>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
                  Security Assessment Posture
                </h3>
                <span style={{
                  background: postureScore >= 80 ? 'rgba(16,185,129,0.18)' : postureScore >= 60 ? 'rgba(245,158,11,0.18)' : 'rgba(244,63,94,0.18)',
                  color: postureScore >= 80 ? '#34d399' : postureScore >= 60 ? '#fbbf24' : '#fb7185',
                  padding: '3px 10px',
                  borderRadius: '12px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  letterSpacing: '0.03em',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}>
                  {postureRating}
                </span>
              </div>
              <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: 0 }}>
                Continuous automated vulnerability assessment across 20 mandatory security categories with atomic remediation.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              onClick={() => handleRunScan(false)}
              disabled={scanning}
              className="btn-primary"
              style={{
                background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                padding: '0.65rem 1.25rem',
                fontSize: '0.85rem',
                fontWeight: 700,
                boxShadow: '0 4px 15px rgba(124, 58, 237, 0.35)',
              }}
            >
              {scanning ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Scanning Application...</span>
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  <span>Run Full Security Assessment</span>
                </>
              )}
            </button>

            <button
              onClick={handleExportReport}
              disabled={!activeScanId || exportingReport}
              className="btn-secondary"
              style={{ padding: '0.65rem 1rem', fontSize: '0.85rem' }}
              title="Download Full Audit Report in JSON format"
            >
              <Download size={15} />
              <span>{exportingReport ? 'Generating...' : 'Export Audit Report'}</span>
            </button>
          </div>
        </div>

        {/* Severity Metrics Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginTop: '1.25rem' }}>
          <div style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#fb7185', fontWeight: 700, textTransform: 'uppercase' }}>Critical</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#f43f5e' }}>{stats?.counts?.critical || 0}</div>
          </div>
          <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#fbbf24', fontWeight: 700, textTransform: 'uppercase' }}>High</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#f59e0b' }}>{stats?.counts?.high || 0}</div>
          </div>
          <div style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#22d3ee', fontWeight: 700, textTransform: 'uppercase' }}>Medium</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#06b6d4' }}>{stats?.counts?.medium || 0}</div>
          </div>
          <div style={{ background: 'rgba(100,116,139,0.08)', border: '1px solid rgba(100,116,139,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Low</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#cbd5e1' }}>{stats?.counts?.low || 0}</div>
          </div>
          <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 700, textTransform: 'uppercase' }}>Fixed / Verified</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#10b981' }}>{stats?.counts?.fixed || 0}</div>
          </div>
          <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '10px', padding: '0.75rem 1rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#818cf8', fontWeight: 700, textTransform: 'uppercase' }}>Total Scans</div>
            <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#a5b4fc' }}>{stats?.total_scans || 0}</div>
          </div>
        </div>
      </div>

      {/* Accordion: Targeted Category Scanner */}
      <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '12px' }}>
        <div
          onClick={() => setScopeAccordionOpen(!scopeAccordionOpen)}
          style={{
            padding: '0.9rem 1.25rem',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            userSelect: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Sliders size={18} color="#818cf8" />
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
              Targeted Scope Selector ({selectedCategories.length === 0 ? 'Full Scope: All 20 Categories' : `${selectedCategories.length} Categories Selected`})
            </span>
          </div>
          {scopeAccordionOpen ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
        </div>

        {scopeAccordionOpen && (
          <div style={{ padding: '0.75rem 1.25rem 1.25rem', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Select specific categories to execute targeted security audits:
              </span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn-secondary" onClick={selectAllCategories} style={{ padding: '2px 8px', fontSize: '0.72rem' }}>
                  Select All
                </button>
                <button className="btn-secondary" onClick={clearAllCategories} style={{ padding: '2px 8px', fontSize: '0.72rem' }}>
                  Clear
                </button>
                {selectedCategories.length > 0 && (
                  <button
                    className="btn-primary"
                    onClick={() => handleRunScan(true)}
                    disabled={scanning}
                    style={{ padding: '3px 10px', fontSize: '0.74rem' }}
                  >
                    Run Targeted ({selectedCategories.length})
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.5rem' }}>
              {categories.map(cat => {
                const isSelected = selectedCategories.includes(cat.key)
                return (
                  <label
                    key={cat.key}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.55rem',
                      padding: '0.45rem 0.65rem',
                      borderRadius: '8px',
                      background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isSelected ? 'rgba(99, 102, 241, 0.4)' : 'rgba(255, 255, 255, 0.05)'}`,
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleCategory(cat.key)}
                      style={{ marginTop: '3px' }}
                    />
                    <div style={{ fontSize: '0.76rem' }}>
                      <div style={{ fontWeight: 600, color: isSelected ? '#a5b4fc' : '#e2e8f0' }}>{cat.name}</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>{cat.description}</div>
                    </div>
                  </label>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Main Grid: Scan History & Live Logs (Left) + Vulnerability Explorer (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.25rem' }}>
        {/* Left Column: Scan History & Live Terminal */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Past Scans Box */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', margin: '0 0 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={15} color="#818cf8" />
              <span>Scan History</span>
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', maxHeight: '200px', overflowY: 'auto' }}>
              {scans.length === 0 ? (
                <div style={{ fontSize: '0.76rem', color: '#64748b', fontStyle: 'italic', padding: '0.5rem' }}>
                  No scans executed yet. Click "Run Full Security Assessment" to start.
                </div>
              ) : (
                scans.map(s => {
                  const isActive = s.id === activeScanId
                  return (
                    <div
                      key={s.id}
                      onClick={() => handleSelectScan(s.id)}
                      style={{
                        padding: '0.55rem 0.75rem',
                        borderRadius: '8px',
                        background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'rgba(255, 255, 255, 0.02)',
                        border: `1px solid ${isActive ? 'rgba(99, 102, 241, 0.5)' : 'rgba(255, 255, 255, 0.05)'}`,
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: isActive ? '#a5b4fc' : '#e2e8f0' }}>
                          {s.id}
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>
                          {s.started_at?.slice(0, 19).replace('T', ' ')} • {s.duration_seconds}s
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {s.critical_count > 0 && (
                          <span style={{ background: '#f43f5e', color: '#fff', fontSize: '0.65rem', padding: '1px 5px', borderRadius: '4px', fontWeight: 800 }}>
                            {s.critical_count}C
                          </span>
                        )}
                        {s.high_count > 0 && (
                          <span style={{ background: '#f59e0b', color: '#000', fontSize: '0.65rem', padding: '1px 5px', borderRadius: '4px', fontWeight: 800 }}>
                            {s.high_count}H
                          </span>
                        )}
                        {s.passed_tests > 0 && (
                          <span style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399', fontSize: '0.65rem', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>
                            {s.passed_tests} PASS
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* Execution Log Console */}
          <div style={{ background: '#090d16', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Terminal size={14} color="#34d399" />
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#34d399', letterSpacing: '0.04em' }}>
                  SECURITY AUDIT CONSOLE
                </span>
              </div>
              <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                {activeScanDetails ? activeScanDetails.id : 'Live Engine Output'}
              </span>
            </div>
            <div style={{
              fontFamily: 'monospace',
              fontSize: '0.72rem',
              color: '#a7f3d0',
              background: '#040711',
              padding: '0.75rem',
              borderRadius: '8px',
              height: '240px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.45',
              border: '1px solid rgba(52, 211, 153, 0.15)',
            }}>
              {activeScanDetails?.execution_log || 'System ready. Trigger an assessment to monitor real-time security execution.'}
            </div>
          </div>
        </div>

        {/* Right Column: Vulnerability Explorer & Remediation Studio */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Findings Filter Bar */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '0.85rem 1.1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Bug size={16} color="#fb7185" />
              <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
                Detected Vulnerabilities ({filteredFindings.length})
              </span>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <Filter size={13} color="#94a3b8" />
              <select
                value={severityFilter}
                onChange={e => setSeverityFilter(e.target.value)}
                style={{ background: '#1e293b', color: '#e2e8f0', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '3px 8px', fontSize: '0.74rem' }}
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                style={{ background: '#1e293b', color: '#e2e8f0', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '3px 8px', fontSize: '0.74rem' }}
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="IN_REMEDIATION">In Remediation</option>
                <option value="FIXED">Fixed</option>
              </select>
            </div>
          </div>

          {/* Findings List Table */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: '12px', overflow: 'hidden' }}>
            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: '#94a3b8' }}>
                    <th style={{ padding: '0.65rem 0.85rem' }}>Severity</th>
                    <th style={{ padding: '0.65rem 0.85rem' }}>Vulnerability Title & Root Cause</th>
                    <th style={{ padding: '0.65rem 0.85rem' }}>Component</th>
                    <th style={{ padding: '0.65rem 0.85rem' }}>Status</th>
                    <th style={{ padding: '0.65rem 0.85rem', textAlign: 'right' }}>Remediation Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontStyle: 'italic' }}>
                        {findings.length === 0 ? 'No vulnerabilities detected. All security checks passed!' : 'No findings match the active filters.'}
                      </td>
                    </tr>
                  ) : (
                    filteredFindings.map(f => {
                      const sevColor = f.severity === 'CRITICAL' ? '#f43f5e' : f.severity === 'HIGH' ? '#f59e0b' : f.severity === 'MEDIUM' ? '#06b6d4' : '#94a3b8'
                      const sevBg = f.severity === 'CRITICAL' ? 'rgba(244,63,94,0.15)' : f.severity === 'HIGH' ? 'rgba(245,158,11,0.15)' : f.severity === 'MEDIUM' ? 'rgba(6,182,212,0.15)' : 'rgba(100,116,139,0.15)'

                      return (
                        <tr
                          key={f.id}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                            background: selectedFinding?.id === f.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                            cursor: 'pointer',
                          }}
                          onClick={() => setSelectedFinding(f)}
                        >
                          <td style={{ padding: '0.65rem 0.85rem' }}>
                            <span style={{ background: sevBg, color: sevColor, padding: '2px 7px', borderRadius: '4px', fontWeight: 800, fontSize: '0.68rem' }}>
                              {f.severity}
                            </span>
                          </td>
                          <td style={{ padding: '0.65rem 0.85rem' }}>
                            <div style={{ fontWeight: 700, color: '#f8fafc' }}>{f.title}</div>
                            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{f.category} • {f.test_case_id}</div>
                          </td>
                          <td style={{ padding: '0.65rem 0.85rem', color: '#94a3b8' }}>
                            <code style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.05)', padding: '2px 5px', borderRadius: '4px' }}>
                              {f.affected_component || 'Core API'}
                            </code>
                          </td>
                          <td style={{ padding: '0.65rem 0.85rem' }}>
                            <span style={{
                              padding: '2px 7px',
                              borderRadius: '12px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: f.status === 'FIXED' ? 'rgba(16,185,129,0.2)' : f.status === 'IN_REMEDIATION' ? 'rgba(245,158,11,0.2)' : 'rgba(244,63,94,0.15)',
                              color: f.status === 'FIXED' ? '#34d399' : f.status === 'IN_REMEDIATION' ? '#fbbf24' : '#fb7185',
                            }}>
                              {f.status}
                            </span>
                          </td>
                          <td style={{ padding: '0.65rem 0.85rem', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                            {f.status === 'OPEN' && (
                              <button
                                className="btn-primary"
                                onClick={() => handleApplyRemediation(f)}
                                disabled={remediatingId === f.id}
                                style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                              >
                                {remediatingId === f.id ? 'Patching...' : '⚡ Apply Fix'}
                              </button>
                            )}
                            {f.status === 'IN_REMEDIATION' && (
                              <button
                                className="btn-secondary"
                                onClick={() => handleVerifyRemediation(f.remediation_id, f.id)}
                                disabled={verifyingId === f.remediation_id}
                                style={{ padding: '3px 8px', fontSize: '0.7rem', color: '#38bdf8' }}
                              >
                                {verifyingId === f.remediation_id ? 'Verifying...' : '🔍 Verify Fix'}
                              </button>
                            )}
                            {f.status === 'FIXED' && (
                              <div style={{ display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
                                <span style={{ color: '#34d399', fontSize: '0.72rem', fontWeight: 700 }}>Fixed & Verified ✅</span>
                                <button
                                  className="btn-secondary"
                                  onClick={() => handleRollbackRemediation(f.remediation_id, f.id)}
                                  disabled={rollingBackId === f.remediation_id}
                                  style={{ padding: '2px 6px', fontSize: '0.65rem', color: '#fb7185' }}
                                  title="Rollback remediation patch"
                                >
                                  Rollback
                                </button>
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
          </div>
        </div>
      </div>

      {/* Finding Details & Remediation Modal / Studio Drawer */}
      {selectedFinding && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          zIndex: 1000,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '1rem',
        }}>
          <div style={{
            background: '#0f172a',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '740px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '1.5rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span style={{
                    background: selectedFinding.severity === 'CRITICAL' ? 'rgba(244,63,94,0.2)' : 'rgba(245,158,11,0.2)',
                    color: selectedFinding.severity === 'CRITICAL' ? '#f43f5e' : '#f59e0b',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 800,
                    fontSize: '0.72rem',
                  }}>
                    {selectedFinding.severity}
                  </span>
                  <span style={{ fontSize: '0.76rem', color: '#94a3b8' }}>
                    Risk Score: {selectedFinding.risk_score} / 10.0 • CVSS v3.1
                  </span>
                </div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
                  {selectedFinding.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.25rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Root Cause & Impact */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.25rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '0.85rem' }}>
                <span style={{ fontSize: '0.72rem', color: '#818cf8', fontWeight: 700, textTransform: 'uppercase' }}>
                  Root Cause Explanation
                </span>
                <p style={{ fontSize: '0.82rem', color: '#cbd5e1', margin: '0.35rem 0 0', lineHeight: '1.45' }}>
                  {selectedFinding.root_cause}
                </p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '0.85rem' }}>
                <span style={{ fontSize: '0.72rem', color: '#fb7185', fontWeight: 700, textTransform: 'uppercase' }}>
                  Potential Impact
                </span>
                <p style={{ fontSize: '0.82rem', color: '#cbd5e1', margin: '0.35rem 0 0', lineHeight: '1.45' }}>
                  {selectedFinding.potential_impact}
                </p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '0.85rem' }}>
                <span style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 700, textTransform: 'uppercase' }}>
                  Automated Proposed Remediation
                </span>
                <p style={{ fontSize: '0.82rem', color: '#cbd5e1', margin: '0.35rem 0 0', lineHeight: '1.45' }}>
                  {selectedFinding.recommended_remediation}
                </p>
                {selectedFinding.proposed_patch && (
                  <pre style={{
                    marginTop: '0.65rem',
                    background: '#040711',
                    border: '1px solid rgba(52, 211, 153, 0.2)',
                    padding: '0.65rem',
                    borderRadius: '6px',
                    color: '#6ee7b7',
                    fontSize: '0.74rem',
                    overflowX: 'auto',
                  }}>
                    {selectedFinding.proposed_patch}
                  </pre>
                )}
              </div>
            </div>

            {/* Modal Action Controls */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
              <button className="btn-secondary" onClick={() => setSelectedFinding(null)}>
                Close
              </button>

              {selectedFinding.status === 'OPEN' && (
                <button
                  className="btn-primary"
                  onClick={() => handleApplyRemediation(selectedFinding)}
                  disabled={remediatingId === selectedFinding.id}
                >
                  <Wrench size={14} />
                  <span>{remediatingId === selectedFinding.id ? 'Applying Patch...' : 'Apply Safe Automated Fix'}</span>
                </button>
              )}

              {selectedFinding.status === 'IN_REMEDIATION' && (
                <button
                  className="btn-primary"
                  style={{ background: '#0284c7' }}
                  onClick={() => handleVerifyRemediation(selectedFinding.remediation_id, selectedFinding.id)}
                  disabled={verifyingId === selectedFinding.remediation_id}
                >
                  <CheckCircle2 size={14} />
                  <span>{verifyingId === selectedFinding.remediation_id ? 'Verifying...' : 'Run Post-Fix Verification'}</span>
                </button>
              )}

              {selectedFinding.status === 'FIXED' && (
                <button
                  className="btn-secondary"
                  style={{ color: '#fb7185', borderColor: 'rgba(244,63,94,0.3)' }}
                  onClick={() => handleRollbackRemediation(selectedFinding.remediation_id, selectedFinding.id)}
                  disabled={rollingBackId === selectedFinding.remediation_id}
                >
                  <RotateCcw size={14} />
                  <span>{rollingBackId === selectedFinding.remediation_id ? 'Rolling back...' : 'Rollback Remediation'}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
