const MASTERY_BASELINE = {
  'Concept misunderstanding': 34,
  'Wrong logic application': 46,
  'Language misunderstanding': 56,
  'Rote memorization': 62,
  'Partial understanding': 74,
}

const SEVERITY_LABEL = {
  high: 'Needs attention',
  medium: 'Improving',
  low: 'Settling in',
}

export function getMasteryScore({ isCorrect, misconceptionType, confidence = 0 }) {
  if (typeof isCorrect === 'boolean') {
    return isCorrect ? 100 : Math.max(18, Math.round(32 - confidence * 12))
  }

  const baseline = MASTERY_BASELINE[misconceptionType] ?? 52
  const confidencePenalty = Math.round(confidence * 18)
  return Math.max(12, Math.min(96, baseline + (18 - confidencePenalty)))
}

export function buildProgressSnapshot(events) {
  const sortedEvents = [...events].sort((a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0))
  const attempted = sortedEvents.length
  const misconceptionCounts = new Map()
  const topicMap = new Map()

  const timeline = sortedEvents.map((event, index) => {
    const masteryScore = event.masteryScore ?? getMasteryScore(event)
    const misconceptionType = event.misconceptionType ?? 'Unclassified'

    misconceptionCounts.set(
      misconceptionType,
      (misconceptionCounts.get(misconceptionType) ?? 0) + 1,
    )

    const topicKey = event.topicId ?? event.topicLabel ?? 'general'
    const currentTopic = topicMap.get(topicKey) ?? {
      key: topicKey,
      topicLabel: event.topicLabel ?? 'General practice',
      subjectLabel: event.subjectLabel ?? 'Mixed subjects',
      attempts: 0,
      totalMastery: 0,
      misconceptions: new Map(),
      lastPracticedAt: 0,
    }

    currentTopic.attempts += 1
    currentTopic.totalMastery += masteryScore
    currentTopic.lastPracticedAt = Math.max(currentTopic.lastPracticedAt, event.createdAt ?? 0)
    currentTopic.misconceptions.set(
      misconceptionType,
      (currentTopic.misconceptions.get(misconceptionType) ?? 0) + 1,
    )
    topicMap.set(topicKey, currentTopic)

    return {
      id: event.id ?? `${topicKey}-${index}`,
      label: formatShortDate(event.createdAt),
      masteryScore,
      misconceptionType,
      topicLabel: event.topicLabel ?? 'General practice',
      createdAt: event.createdAt ?? 0,
      confidenceLevel: event.confidenceLevel ?? 'low',
    }
  })

  const recentTimeline = timeline.slice(-8)
  const averageMastery = attempted > 0
    ? Math.round(timeline.reduce((sum, event) => sum + event.masteryScore, 0) / attempted)
    : 0

  const improvement = recentTimeline.length >= 2
    ? recentTimeline[recentTimeline.length - 1].masteryScore - recentTimeline[0].masteryScore
    : 0

  const misconceptionBreakdown = [...misconceptionCounts.entries()]
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)

  const weakAreas = [...topicMap.values()]
    .map((topic) => {
      const averageScore = Math.round(topic.totalMastery / topic.attempts)
      const topMisconception = [...topic.misconceptions.entries()]
        .sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Unclassified'

      return {
        key: topic.key,
        topicLabel: topic.topicLabel,
        subjectLabel: topic.subjectLabel,
        attempts: topic.attempts,
        averageScore,
        topMisconception,
        severity: averageScore < 45 ? 'high' : averageScore < 70 ? 'medium' : 'low',
        lastPracticedAt: topic.lastPracticedAt,
      }
    })
    .sort((a, b) => a.averageScore - b.averageScore || b.attempts - a.attempts)

  return {
    attempted,
    averageMastery,
    improvement,
    prediction: buildPrediction(timeline, weakAreas),
    recentTimeline,
    misconceptionBreakdown,
    weakAreas,
    topMisconception: misconceptionBreakdown[0]?.type ?? 'No data yet',
  }
}

export function getSeverityLabel(severity) {
  return SEVERITY_LABEL[severity] ?? 'Review'
}

function formatShortDate(timestamp) {
  if (!timestamp) return 'Now'

  return new Intl.DateTimeFormat('en-IN', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(timestamp))
}

function buildPrediction(timeline, weakAreas) {
  if (timeline.length === 0) {
    return {
      nextMastery: 0,
      trend: 'No attempts yet',
      risk: 'Unknown',
      riskLevel: 'medium',
      confidence: 0,
      recommendation: 'Complete a quiz or misconception check to start the prediction model.',
      forecast: [],
    }
  }

  const recent = timeline.slice(-6)
  const scores = recent.map((event) => event.masteryScore)
  const first = scores[0]
  const last = scores[scores.length - 1]
  const slope = scores.length > 1 ? (last - first) / (scores.length - 1) : 0
  const nextMastery = clamp(Math.round(last + slope), 0, 100)
  const lowRecent = scores.filter((score) => score < 55).length
  const weakHigh = weakAreas.filter((area) => area.severity === 'high').length
  const riskLevel = nextMastery < 45 || weakHigh >= 2 ? 'high' : nextMastery < 70 || lowRecent >= 2 ? 'medium' : 'low'
  const trend = slope > 4 ? 'Rising' : slope < -4 ? 'Dropping' : 'Stable'
  const focusArea = weakAreas[0]

  return {
    nextMastery,
    trend,
    risk: riskLevel === 'high' ? 'High revision need' : riskLevel === 'medium' ? 'Moderate revision need' : 'On track',
    riskLevel,
    confidence: Math.min(95, Math.max(35, 45 + recent.length * 8)),
    recommendation: focusArea
      ? `Practice ${focusArea.topicLabel} next; it has ${focusArea.averageScore}% average mastery and ${focusArea.attempts} attempt${focusArea.attempts === 1 ? '' : 's'}.`
      : 'Keep practicing new topics to improve the prediction quality.',
    forecast: Array.from({ length: 4 }).map((_, index) => ({
      label: `Next ${index + 1}`,
      score: clamp(Math.round(last + slope * (index + 1)), 0, 100),
    })),
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}
