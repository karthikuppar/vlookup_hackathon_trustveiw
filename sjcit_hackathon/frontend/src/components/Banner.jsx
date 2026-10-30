import React from 'react'

const ROLE = { error: 'alert', warning: 'alert', success: 'status' }

export default function Banner({ kind = 'error', onClose, children }) {
  if (!children) return null
  return (
    <div className={`banner banner-${kind}`} role={ROLE[kind]} aria-live={kind === 'success' ? 'polite' : 'assertive'}>
      <span>{children}</span>
      {onClose && (
        <button className="banner-close" onClick={onClose} aria-label="Dismiss message">
          ✕
        </button>
      )}
    </div>
  )
}
