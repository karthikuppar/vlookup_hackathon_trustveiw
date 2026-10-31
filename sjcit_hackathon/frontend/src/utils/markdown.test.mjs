// Run with: node src/utils/markdown.test.mjs
import assert from 'node:assert/strict'
import { renderMarkdown } from './markdown.js'

const payloads = [
  '<img src=x onerror=alert(1)>',
  '<script>alert(1)</script>',
  '"onmouseover="alert(1)',
  '**<b onclick=x>hi</b>**',
]
for (const p of payloads) {
  const out = renderMarkdown(p)
  assert.ok(!/<img|<script|<b /i.test(out), `unescaped tag in: ${out}`)
  assert.ok(!/style=/i.test(out), 'inline style emitted')
  // every remaining tag must be one of our static ones
  const tags = out.match(/<[^>]+>/g) || []
  for (const t of tags) {
    assert.match(t, /^<\/?(p|strong|em|code|div|hr|br)(\s+class="md-[a-z0-9]+")?\s*\/?>$/, `unexpected tag ${t}`)
  }
}
assert.ok(renderMarkdown('<img src=x onerror=alert(1)>').includes('&lt;img src=x onerror=alert(1)&gt;'))
assert.ok(renderMarkdown('<script>').includes('&lt;script&gt;'))
assert.ok(renderMarkdown('a"onmouseover="x').includes('"onmouseover=')) // quote is inert as text node
assert.ok(renderMarkdown('a & b').includes('a &amp; b'))

assert.ok(renderMarkdown('**bold**').includes('<strong>bold</strong>'))
assert.ok(renderMarkdown('use `code`').includes('<code class="md-code">code</code>'))
assert.ok(renderMarkdown('- item').includes('class="md-bullet"'))
assert.ok(renderMarkdown('1. step').includes('class="md-num"'))
assert.ok(renderMarkdown('a\n\nb').includes('</p><p class="md-p">'))
assert.equal(renderMarkdown(''), '')

console.log('markdown tests passed')
