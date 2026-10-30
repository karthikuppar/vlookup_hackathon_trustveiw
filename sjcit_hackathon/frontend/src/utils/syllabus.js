import {
  Atom,
  Binary,
  BookOpenText,
  BookText,
  Calculator,
  CircuitBoard,
  Dna,
  FlaskConical,
  Globe2,
  Landmark,
  Languages,
  Leaf,
  NotebookPen,
  ScrollText,
} from 'lucide-react'

const LEVELS = [
  { id: 'primary', label: 'Primary', range: [1, 5], accent: 'text-primary-300', badge: 'badge-primary' },
  { id: 'higher-primary', label: 'Higher Primary', range: [6, 8], accent: 'text-accent-teal', badge: 'badge-teal' },
  { id: 'secondary', label: 'Secondary', range: [9, 10], accent: 'text-accent-amber', badge: 'badge-amber' },
  { id: 'higher-secondary', label: 'Higher Secondary', range: [11, 12], accent: 'text-accent-rose', badge: 'badge-rose' },
]

const SUBJECT_VISUALS = [
  { match: /math/, Icon: Calculator, accent: 'text-primary-300', bg: 'bg-surface-card', border: 'border-primary-500' },
  { match: /physics/, Icon: Atom, accent: 'text-accent-amber', bg: 'bg-accent-amber/10', border: 'border-accent-amber/30' },
  { match: /chemistry|science/, Icon: FlaskConical, accent: 'text-accent-teal', bg: 'bg-accent-teal/10', border: 'border-accent-teal/30' },
  { match: /biology/, Icon: Dna, accent: 'text-emerald-300', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  { match: /english|hindi|kannada|sanskrit|language/, Icon: Languages, accent: 'text-sky-300', bg: 'bg-sky-500/10', border: 'border-sky-500/30' },
  { match: /computer/, Icon: Binary, accent: 'text-indigo-300', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30' },
  { match: /electronics/, Icon: CircuitBoard, accent: 'text-fuchsia-300', bg: 'bg-fuchsia-500/10', border: 'border-fuchsia-500/30' },
  { match: /social|history|geography|civics/, Icon: Globe2, accent: 'text-orange-300', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  { match: /physical education/, Icon: Leaf, accent: 'text-lime-300', bg: 'bg-lime-500/10', border: 'border-lime-500/30' },
  { match: /workbook/, Icon: NotebookPen, accent: 'text-violet-300', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
  { match: /reader/, Icon: ScrollText, accent: 'text-cyan-300', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30' },
  { match: /textbook/, Icon: BookText, accent: 'text-surface-muted', bg: 'bg-surface-border/30', border: 'border-surface-border' },
]

const DEFAULT_VISUAL = {
  Icon: BookOpenText,
  accent: 'text-primary-300',
  bg: 'bg-surface-card',
  border: 'border-primary-500',
}

export function getClassNumber(value) {
  const match = String(value ?? '').match(/(\d+)/)
  if (match) return Number(match[1])

  const romanMatch = String(value ?? '').match(/\b(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)\b/i)
  if (!romanMatch) return null

  return romanToInt(romanMatch[1])
}

export function getLevelMeta(value) {
  const classNumber = getClassNumber(value)
  if (classNumber == null) return LEVELS[0]
  return LEVELS.find((level) => classNumber >= level.range[0] && classNumber <= level.range[1]) ?? LEVELS[0]
}

export function groupClassesByLevel(classes) {
  return LEVELS.map((level) => ({
    ...level,
    classes: classes.filter((classItem) => {
      const classNumber = getClassNumber(classItem.class_label ?? classItem.classLabel ?? classItem.class_slug)
      return classNumber != null && classNumber >= level.range[0] && classNumber <= level.range[1]
    }),
  }))
}

export function getSubjectVisual(subjectSlug = '', subjectLabel = '') {
  const needle = `${subjectSlug} ${subjectLabel}`.toLowerCase()
  return SUBJECT_VISUALS.find((entry) => entry.match.test(needle)) ?? DEFAULT_VISUAL
}

export function formatCompactNumber(value) {
  return new Intl.NumberFormat('en-IN', {
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value ?? 0)
}

export function formatFileSize(bytes) {
  const value = Number(bytes ?? 0)
  if (value < 1024) return `${value} B`

  const units = ['KB', 'MB', 'GB', 'TB']
  let size = value / 1024
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }

  return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[unitIndex]}`
}

export function getTocNodes(document) {
  if (Array.isArray(document?.toc_tree) && document.toc_tree.length > 0) {
    return document.toc_tree
  }

  if (Array.isArray(document?.toc)) {
    return document.toc.filter((entry) => !entry.parent_id)
  }

  return []
}

export function getTopLevelTocEntries(document) {
  const toc = Array.isArray(document?.toc) ? document.toc : []
  return toc.filter((entry) => !entry.parent_id)
}

export function calculateDocumentCoverage(entryCount, pageCount) {
  if (!pageCount) return 0
  return Math.min(100, Math.round((entryCount / pageCount) * 100 * 4))
}

function romanToInt(value) {
  const numerals = { i: 1, v: 5, x: 10 }
  let total = 0
  let previous = 0

  for (const character of value.toLowerCase().split('').reverse()) {
    const current = numerals[character] ?? 0
    if (current < previous) {
      total -= current
    } else {
      total += current
      previous = current
    }
  }

  return total
}
