import { getExplanationTemplate } from '@/data/State/offlineExplanationTemplates'
import { getOfflineQuestionById, getOfflineQuestionByTopicId } from '@/data/State/offlineQuestionBank'
import { buildQuestionFromTopicContext } from '@/utils/syllabusPractice'

const CATEGORY = {
  CONCEPT: 'Concept misunderstanding',
  PARTIAL: 'Partial understanding',
  LOGIC: 'Wrong logic application',
  ROTE: 'Rote memorization',
  LANGUAGE: 'Language misunderstanding',
}

const GUIDANCE = {
  [CATEGORY.CONCEPT]: 'Revisit the core idea first, then explain why it applies in this exact situation.',
  [CATEGORY.PARTIAL]: 'Keep the correct part and add the missing concept or reasoning step that completes the answer.',
  [CATEGORY.LOGIC]: 'Identify the right condition before applying a formula, rule, or procedure.',
  [CATEGORY.ROTE]: 'Explain the idea in one full sentence instead of stopping at a memorized phrase or symbol.',
  [CATEGORY.LANGUAGE]: 'Restate the question in simpler words before answering so the target idea stays clear.',
}

export function buildExplanationCacheId(responseId, questionId, topicId) {
  return `explanation:${responseId ?? questionId ?? topicId ?? 'entry'}`
}

export function analyzeResponseOffline(payload) {
  const startedAt = performance.now()
  const questionText = payload.question ?? payload.question_text ?? ''
  const studentAnswer = payload.student_answer ?? payload.answer_text ?? payload.answer ?? ''
  const topicId = payload.topic_id ?? payload.topicId
  const questionId = payload.question_id ?? payload.questionId
  const question = (
    getOfflineQuestionById(questionId) ??
    getOfflineQuestionByTopicId(topicId) ??
    buildQuestionFromTopicContext(buildOfflineTopicContext(payload, topicId))
  )

  const normalizedAnswer = normalizeText(studentAnswer)
  const answerTokens = tokenize(normalizedAnswer)
  const expectedConcepts = question?.expectedConcepts ?? []
  const offTrackKeywords = question?.offTrackKeywords ?? []
  const formulaSignals = question?.formulaSignals ?? []
  const matchedConcepts = expectedConcepts.filter((concept) => contains(normalizedAnswer, concept))
  const missingConcepts = expectedConcepts.filter((concept) => !contains(normalizedAnswer, concept))
  const offTrackHits = offTrackKeywords.filter((keyword) => contains(normalizedAnswer, keyword))
  const formulaHits = formulaSignals.filter((signal) => contains(normalizedAnswer, signal))
  const symbolHeavy = /[=+\-/*^]/.test(studentAnswer) || /\d/.test(studentAnswer)

  let misconceptionType = CATEGORY.CONCEPT
  let confidence = 0.56
  let description = `The answer needs a stronger link to the core idea in ${question?.topicLabel ?? 'this topic'}.`

  if (offTrackHits.length > 0) {
    misconceptionType = CATEGORY.LANGUAGE
    confidence = 0.64 + Math.min(offTrackHits.length, 2) * 0.08
    description = `The answer drifts toward ${offTrackHits.join(', ')} instead of staying with what the question asks in ${question?.topicLabel ?? 'this topic'}.`
  } else if (formulaHits.length > 0 && matchedConcepts.length <= 1) {
    misconceptionType = answerTokens.length < 10 ? CATEGORY.ROTE : CATEGORY.LOGIC
    confidence = answerTokens.length < 10 ? 0.72 : 0.68
    description = `The answer moves too quickly to a remembered rule instead of explaining the condition that matters in ${question?.topicLabel ?? 'this topic'}.`
  } else if (matchedConcepts.length > 0 && missingConcepts.length > 0) {
    misconceptionType = CATEGORY.PARTIAL
    confidence = 0.58 + Math.min(matchedConcepts.length, 2) * 0.08
    description = `The answer contains part of the right idea, but it still misses ${formatList(missingConcepts.slice(0, 3)) || 'one key reasoning step'}.`
  } else if (answerTokens.length < 8 || (symbolHeavy && matchedConcepts.length === 0)) {
    misconceptionType = CATEGORY.ROTE
    confidence = 0.61
    description = `The response is too short or too formula-heavy to show full understanding of ${question?.topicLabel ?? 'this topic'}.`
  } else if (matchedConcepts.length === 0 && expectedConcepts.length > 0) {
    misconceptionType = CATEGORY.CONCEPT
    confidence = 0.67
    description = `The answer does not yet name the key idea for ${question?.topicLabel ?? 'this topic'}: ${question?.conceptSummary ?? 'the central concept and why it works'}.`
  } else {
    misconceptionType = CATEGORY.PARTIAL
    confidence = 0.49
    description = `The answer is close, but it would be stronger with a clearer reasoning step.`
  }

  const confidenceLevel = getConfidenceLevel(confidence)
  const executionMs = roundMs(performance.now() - startedAt)

  return {
    question_id: questionId ?? null,
    subject: question?.subjectId ?? normalizeSubject(payload.subject),
    misconception_type: misconceptionType,
    confidence_level: confidenceLevel,
    confidence,
    misconceptions: [
      {
        type: misconceptionType,
        description,
        confidence,
        confidence_level: confidenceLevel,
        rule_id: 'frontend_offline_engine',
        matched_keywords: matchedConcepts,
        matched_patterns: formulaHits,
        missing_concepts: missingConcepts,
      },
    ],
    corrective_guidance: GUIDANCE[misconceptionType],
    explanation_available: true,
    is_correct: null,
    analysis_method: 'frontend_offline_engine',
    execution_ms: executionMs,
    offline_generated: true,
    question: questionText,
    student_answer: studentAnswer,
  }
}

export function generateExplanationOffline(payload) {
  const topicId = payload.topic_id ?? payload.topicId
  const questionId = payload.question_id ?? payload.questionId
  const misconceptionType = payload.misconception_type ?? CATEGORY.CONCEPT
  const question = (
    getOfflineQuestionById(questionId) ??
    getOfflineQuestionByTopicId(topicId) ??
    buildQuestionFromTopicContext(buildOfflineTopicContext(payload, topicId))
  )
  const template = getExplanationTemplate(misconceptionType)
  const topicLabel = payload.topic ?? question?.topicLabel ?? 'this topic'
  const conceptSummary = question?.conceptSummary ?? 'the core idea, the reasoning step, and the final conclusion'
  const expectedConcepts = question?.expectedConcepts ?? []

  const content = [
    template.contentLead,
    `In ${topicLabel}, focus on ${conceptSummary}.`,
    expectedConcepts.length > 0 ? `A complete answer should mention ${formatList(expectedConcepts.slice(0, 3))}.` : '',
  ].filter(Boolean).join(' ')

  const story = [
    template.storyLead,
    `For ${topicLabel}, the trick is to connect the idea to what changes and why.`,
  ].join(' ')

  return {
    question_id: questionId ?? null,
    type: template.type,
    content,
    diagram: template.diagram,
    story,
    topic: topicLabel,
    misconception_type: misconceptionType,
    source: 'offline_template',
    enhanced_by_ai: false,
    online_used: false,
    ai_provider: null,
    generated_at: Date.now() / 1000,
    offline_generated: true,
  }
}

function normalizeText(text) {
  return (text ?? '').toLowerCase().replace(/\s+/g, ' ').trim()
}

function buildOfflineTopicContext(payload, topicId) {
  return {
    topicId,
    topicLabel: payload.topic ?? payload.topicLabel ?? payload.topic_label,
    subjectId: payload.subject ?? payload.subjectId,
    subjectLabel: payload.subject_label ?? payload.subjectLabel ?? payload.subject,
    chapterLabel: payload.chapter_label ?? payload.chapterLabel,
    documentTitle: payload.document_title ?? payload.documentTitle,
    classLabel: payload.class_label ?? payload.classLabel,
  }
}

function tokenize(text) {
  return text.match(/[a-z0-9]+/g) ?? []
}

function contains(text, phrase) {
  const normalizedPhrase = normalizeText(phrase)
  if (!normalizedPhrase) return false

  if (normalizedPhrase.includes(' ')) {
    return text.includes(normalizedPhrase)
  }

  return new RegExp(`\\b${escapeRegex(normalizedPhrase)}\\b`, 'i').test(text)
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function getConfidenceLevel(confidence) {
  if (confidence >= 0.75) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

function normalizeSubject(subject) {
  return normalizeText(subject).replace(/\s+/g, '-') || 'general'
}

function formatList(items) {
  if (items.length === 0) return ''
  if (items.length === 1) return items[0]
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`
}

function roundMs(value) {
  return Math.round(value * 1000) / 1000
}
