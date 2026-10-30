const STOP_WORDS = new Set([
  'a',
  'an',
  'and',
  'at',
  'by',
  'for',
  'from',
  'in',
  'into',
  'of',
  'on',
  'or',
  'the',
  'to',
  'with',
  'unit',
  'chapter',
  'lesson',
  'part',
])

const SUBJECT_FAMILY_RULES = [
  {
    id: 'mathematics',
    match: /\b(math|maths|mathematics|algebra|geometry|arithmetic|calculus|probability|trigonometry)\b/i,
    buildText: (reference) => `In ${reference}, explain the method or pattern involved and describe one step you would use to solve a problem from this topic.`,
    hint: 'Name the method first, then explain why that method fits the problem.',
    conceptSummary: (reference) => `the method used in ${reference.toLowerCase()}, the steps involved, and why the method works`,
    expectedConcepts: ['method', 'step', 'why'],
    offTrackKeywords: ['history', 'scientist', 'inventor'],
    formulaSignals: ['=', 'formula', 'equation', 'solve'],
  },
  {
    id: 'physics',
    match: /\b(physics|motion|force|energy|gravity|electric|magnet|wave|light)\b/i,
    buildText: (reference) => `Explain the core idea behind ${reference} and describe what changes, moves, or interacts in this topic.`,
    hint: 'Focus on the physical quantity involved and the reason the change happens.',
    conceptSummary: (reference) => `the physical relationship in ${reference.toLowerCase()} and why the effect happens`,
    expectedConcepts: ['cause', 'change', 'because'],
    offTrackKeywords: ['grammar', 'history', 'poem'],
    formulaSignals: ['=', 'formula', 'velocity', 'force'],
  },
  {
    id: 'chemistry',
    match: /\b(chemistry|chemical|atom|molecule|reaction|acid|base|bond)\b/i,
    buildText: (reference) => `Explain the main idea in ${reference} and describe how the particles, substances, or reactions behave.`,
    hint: 'Talk about structure or interaction first, then explain the result.',
    conceptSummary: (reference) => `how substances behave in ${reference.toLowerCase()} and the reason that behaviour occurs`,
    expectedConcepts: ['particle', 'reaction', 'because'],
    offTrackKeywords: ['grammar', 'history', 'story'],
    formulaSignals: ['=', 'equation', 'formula', 'reaction'],
  },
  {
    id: 'biology',
    match: /\b(biology|cell|plant|animal|human|organ|organism|ecosystem|genetics)\b/i,
    buildText: (reference) => `Explain the process or role involved in ${reference} and why it matters in the living system being studied.`,
    hint: 'Describe the function first, then explain its effect on the organism or system.',
    conceptSummary: (reference) => `the biological role in ${reference.toLowerCase()} and how it supports life`,
    expectedConcepts: ['function', 'process', 'because'],
    offTrackKeywords: ['voltage', 'equation', 'network'],
    formulaSignals: ['equation', '=', 'formula'],
  },
  {
    id: 'computer-science',
    match: /\b(computer|program|algorithm|coding|database|network|software|logic)\b/i,
    buildText: (reference) => `In ${reference}, explain the concept clearly and describe what it changes inside a program, system, or algorithm.`,
    hint: 'Use one simple example and explain the effect of using the concept correctly.',
    conceptSummary: (reference) => `how the core idea in ${reference.toLowerCase()} works and what effect it has in a system`,
    expectedConcepts: ['example', 'logic', 'effect'],
    offTrackKeywords: ['poem', 'biology', 'grammar'],
    formulaSignals: ['=', 'code', 'syntax', 'loop'],
  },
  {
    id: 'electronics',
    match: /\b(electronics|circuit|semiconductor|signal|transistor|current|voltage)\b/i,
    buildText: (reference) => `Explain the main idea in ${reference} and what happens in the circuit or signal path when the condition changes.`,
    hint: 'Name the component or signal first, then explain the circuit response.',
    conceptSummary: (reference) => `how the component or signal behaves in ${reference.toLowerCase()} and why the circuit responds that way`,
    expectedConcepts: ['signal', 'current', 'because'],
    offTrackKeywords: ['ecosystem', 'grammar', 'history'],
    formulaSignals: ['=', 'voltage', 'current', 'formula'],
  },
  {
    id: 'social-science',
    match: /\b(social|history|geography|civics|economics|political|democracy|society)\b/i,
    buildText: (reference) => `Explain the main idea of ${reference} and describe one cause, effect, or example connected to it.`,
    hint: 'State the idea first, then connect it to one real example or outcome.',
    conceptSummary: (reference) => `the main idea in ${reference.toLowerCase()} and one cause, effect, or real-world example`,
    expectedConcepts: ['example', 'cause', 'effect'],
    offTrackKeywords: ['formula', 'equation', 'voltage'],
    formulaSignals: ['percentage', 'graph'],
  },
  {
    id: 'languages',
    match: /\b(english|hindi|kannada|sanskrit|language|grammar|poem|story|reading|writing|literature)\b/i,
    buildText: (reference) => `Explain ${reference} in your own words and use one simple example sentence, idea, or passage reference.`,
    hint: 'Say what it means first, then show how it is used in context.',
    conceptSummary: (reference) => `how ${reference.toLowerCase()} works in language and how it changes meaning`,
    expectedConcepts: ['meaning', 'example', 'use'],
    offTrackKeywords: ['force', 'equation', 'voltage'],
    formulaSignals: ['grammar rule', 'sentence'],
  },
  {
    id: 'science',
    match: /\b(science)\b/i,
    buildText: (reference) => `Explain the core idea in ${reference} and describe the key process, interaction, or observation involved.`,
    hint: 'Identify the concept first, then explain what happens and why.',
    conceptSummary: (reference) => `the scientific idea in ${reference.toLowerCase()} and the reason the process or effect occurs`,
    expectedConcepts: ['concept', 'process', 'because'],
    offTrackKeywords: ['poem', 'story', 'grammar'],
    formulaSignals: ['=', 'equation', 'formula'],
  },
]

const DEFAULT_SUBJECT_FAMILY = {
  id: 'general',
  buildText: (reference) => `Explain the main idea behind ${reference} and describe it in your own words with one clear supporting point.`,
  hint: 'Start with the main idea, then explain one example or effect.',
  conceptSummary: (reference) => `the main idea in ${reference.toLowerCase()} and one supporting explanation`,
  expectedConcepts: ['main idea', 'example', 'because'],
  offTrackKeywords: ['history', 'equation', 'grammar'],
  formulaSignals: ['=', 'formula'],
}

export function buildPracticeTopicId(documentId, nodeId) {
  return `${documentId}--${nodeId}`
}

export function buildPracticeQuestionId(topicId) {
  return `${topicId}--core-question`
}

export function buildSyllabusPracticeTree(document) {
  const sourceNodes = Array.isArray(document?.toc_tree) && document.toc_tree.length > 0
    ? document.toc_tree
    : Array.isArray(document?.toc)
      ? document.toc.filter((entry) => !entry.parent_id)
      : []
  const subjectId = document?.subject?.slug ?? document?.subject_slug ?? slugify(document?.subject_label ?? 'general')
  const subjectLabel = document?.subject?.label ?? document?.subject_label ?? 'General'
  const practiceNodes = sourceNodes.length > 0 ? sourceNodes : buildFallbackTocNodes(document, subjectLabel)

  return practiceNodes.map((node) => mapPracticeNode(node, {
    documentId: document?.document_id,
    documentTitle: document?.document_title,
    classSlug: document?.class_slug,
    classLabel: document?.class_label,
    subjectId,
    subjectLabel,
  }))
}

export function flattenPracticeNodes(nodes) {
  return nodes.flatMap((node) => [node, ...flattenPracticeNodes(node.children ?? [])])
}

export function resolveTopicContext(topicId, locationState = {}, selection = {}) {
  const topicLabel = locationState.topicLabel ?? selection.topicLabel ?? humanizeTopicId(topicId)
  const subjectLabel = locationState.subjectLabel ?? selection.subjectLabel ?? 'General'
  const subjectId = locationState.subjectId ?? selection.subjectId ?? slugify(subjectLabel)

  return {
    classSlug: locationState.classSlug ?? selection.classSlug ?? null,
    classLabel: locationState.classLabel ?? selection.classLabel ?? null,
    subjectId,
    subjectLabel,
    documentId: locationState.documentId ?? selection.documentId ?? null,
    documentTitle: locationState.documentTitle ?? selection.documentTitle ?? null,
    chapterId: locationState.chapterId ?? selection.chapterId ?? null,
    chapterLabel: locationState.chapterLabel ?? selection.chapterLabel ?? topicLabel,
    topicId: locationState.topicId ?? selection.topicId ?? topicId,
    topicLabel,
    topicPath: locationState.topicPath ?? selection.topicPath ?? topicLabel,
    topicPageNumber: locationState.topicPageNumber ?? selection.topicPageNumber ?? null,
    topicLevel: locationState.topicLevel ?? selection.topicLevel ?? null,
  }
}

export function buildQuestionFromTopicContext(context = {}) {
  const topicId = context.topicId ?? context.id ?? slugify(context.topicLabel ?? 'topic')
  const topicLabel = context.topicLabel ?? context.label ?? context.title ?? humanizeTopicId(topicId)
  const subjectLabel = context.subjectLabel ?? 'General'
  const subjectId = context.subjectId ?? slugify(subjectLabel)
  const chapterLabel = context.chapterLabel ?? topicLabel
  const family = getSubjectFamily(subjectId, subjectLabel)
  const reference = chapterLabel && chapterLabel !== topicLabel
    ? `${topicLabel} from ${chapterLabel}`
    : topicLabel
  const topicKeywords = deriveTopicKeywords(topicLabel)
  const estimatedTime = estimatePracticeTime(context.topicLevel)

  return {
    id: buildPracticeQuestionId(topicId),
    subjectId,
    subjectLabel,
    topicId,
    topicLabel,
    chapterId: context.chapterId ?? null,
    chapterLabel,
    classSlug: context.classSlug ?? null,
    classLabel: context.classLabel ?? null,
    documentId: context.documentId ?? null,
    documentTitle: context.documentTitle ?? null,
    topicPageNumber: context.topicPageNumber ?? null,
    topicPath: context.topicPath ?? topicLabel,
    text: family.buildText(reference),
    hint: family.hint,
    estimatedTime,
    conceptSummary: family.conceptSummary(reference),
    expectedConcepts: uniqueValues([...family.expectedConcepts, ...topicKeywords]).slice(0, 4),
    offTrackKeywords: family.offTrackKeywords,
    formulaSignals: family.formulaSignals,
  }
}

export function getSubjectFamily(subjectId = '', subjectLabel = '') {
  const needle = `${subjectId} ${subjectLabel}`.trim()
  return SUBJECT_FAMILY_RULES.find((rule) => rule.match.test(needle)) ?? DEFAULT_SUBJECT_FAMILY
}

function mapPracticeNode(node, baseContext, ancestors = [], chapterRoot = null) {
  const topicId = buildPracticeTopicId(baseContext.documentId, node.id)
  const topicLabel = node.title
  const nextPath = [...ancestors, topicLabel]
  const nextChapterRoot = chapterRoot ?? { chapterId: topicId, chapterLabel: topicLabel }

  return {
    id: topicId,
    sourceNodeId: node.id,
    title: topicLabel,
    topicId,
    topicLabel,
    chapterId: nextChapterRoot.chapterId,
    chapterLabel: nextChapterRoot.chapterLabel,
    classSlug: baseContext.classSlug,
    classLabel: baseContext.classLabel,
    subjectId: baseContext.subjectId,
    subjectLabel: baseContext.subjectLabel,
    documentId: baseContext.documentId,
    documentTitle: baseContext.documentTitle,
    topicPageNumber: node.page_number ?? null,
    topicLevel: node.level ?? nextPath.length,
    topicPath: nextPath.join(' -> '),
    level: node.level ?? nextPath.length,
    page_number: node.page_number ?? null,
    children: (node.children ?? []).map((child) => mapPracticeNode(
      child,
      baseContext,
      nextPath,
      nextChapterRoot,
    )),
  }
}

function buildFallbackTocNodes(document, subjectLabel) {
  const pageCount = Number(document?.page_count ?? document?.pdf?.page_count ?? 0)
  if (!pageCount) return []

  const sectionSize = getFallbackSectionSize(pageCount)
  const sectionCount = Math.max(1, Math.ceil(pageCount / sectionSize))
  const documentTitle = document?.document_title ?? `${subjectLabel} textbook`

  return Array.from({ length: sectionCount }, (_, index) => {
    const startPage = index * sectionSize + 1
    const endPage = Math.min(pageCount, (index + 1) * sectionSize)
    const title = sectionCount === 1
      ? documentTitle
      : `${subjectLabel} section ${index + 1}`

    return {
      id: `inferred-section-${index + 1}`,
      title,
      level: 1,
      parent_id: null,
      page_number: startPage,
      children: [
        {
          id: `inferred-section-${index + 1}-overview`,
          title: `Pages ${startPage}-${endPage} overview`,
          level: 2,
          parent_id: `inferred-section-${index + 1}`,
          page_number: startPage,
          children: [],
        },
      ],
    }
  })
}

function getFallbackSectionSize(pageCount) {
  if (pageCount <= 80) return 20
  if (pageCount <= 180) return 24
  return 32
}

function deriveTopicKeywords(topicLabel) {
  return String(topicLabel ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]+/g, ' ')
    .split(/[\s-]+/)
    .filter((token) => token.length > 3 && !STOP_WORDS.has(token))
    .slice(0, 2)
}

function estimatePracticeTime(topicLevel) {
  if (Number(topicLevel) >= 4) return '7 min'
  if (Number(topicLevel) === 3) return '6 min'
  return '5 min'
}

function uniqueValues(items) {
  return [...new Set(items.filter(Boolean))]
}

function slugify(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'general'
}

function humanizeTopicId(topicId) {
  const value = String(topicId ?? '')
  if (!value) return 'Selected topic'
  const simplified = value.split('--').pop() ?? value
  return simplified
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}
