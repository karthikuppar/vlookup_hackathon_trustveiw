// Lightweight Markdown renderer (no external dep).
// Safety: &, < and > are escaped FIRST, before any tags are added. All emitted
// attributes are static CSS classes (no inline styles, no user data in attributes),
// so output is safe for dangerouslySetInnerHTML under a strict CSP.
export const renderMarkdown = (text) => {
  if (!text) return ''
  const html = String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<![*])\*(.+?)\*(?![*])/g, '<em>$1</em>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    .replace(/^(\d+[.)]\s+.+)$/gm, '<div class="md-num">&nbsp;&nbsp;$1</div>')
    .replace(/^-\s+(.+)$/gm, '<div class="md-bullet">&#8226;&nbsp;$1</div>')
    .replace(/^(SECTION\s+\d+:.+)$/gm, '<div class="md-section">$1</div>')
    .replace(/^---$/gm, '<hr class="md-hr">')
    .replace(/\n\n/g, '</p><p class="md-p">')
    .replace(/\n/g, '<br/>')
  return `<p class="md-p0">${html}</p>`
}
