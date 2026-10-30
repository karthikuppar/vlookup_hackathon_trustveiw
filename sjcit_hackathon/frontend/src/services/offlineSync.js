import { analyzeResponseOnline, generateExplanationOnline } from '@/services/api'
import { ensureOfflineQuestionBank } from '@/services/offlineContent'
import {
  getPendingResponses,
  saveCachedExplanation,
  updateResponse,
} from '@/utils/indexedDB'
import { buildExplanationCacheId } from '@/utils/offlineEngine'

export const OFFLINE_SYNC_EVENT = 'pragna-vistara:sync-state-changed'


export async function prepareOfflineExperience() {
  await ensureOfflineQuestionBank()
}

export async function getPendingSyncCount() {
  const pendingResponses = await getPendingResponses()
  return pendingResponses.length
}

export async function syncPendingResponses() {
  await ensureOfflineQuestionBank()

  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return { syncedCount: 0, failedCount: 0, pendingCount: await getPendingSyncCount() }
  }

  const pendingResponses = await getPendingResponses()
  let syncedCount = 0
  let failedCount = 0

  for (const response of pendingResponses) {
    if (!response.answerText || !response.questionText) {
      continue
    }

    try {
      const analysisResult = await analyzeResponseOnline({
        question: response.questionText,
        student_answer: response.answerText,
        subject: response.subjectId ?? response.subjectLabel,
        topic_id: response.topicId,
        question_id: response.questionId,
      })

      const explanationResult = await generateExplanationOnline({
        misconception_type: analysisResult.misconception_type,
        topic: response.topicLabel,
        topic_id: response.topicId,
        subject: analysisResult.subject,
        question_id: response.questionId,
        question_text: response.questionText,
        student_answer: response.answerText,
        include_visual: true,
      })

      await saveCachedExplanation({
        id: buildExplanationCacheId(response.id, response.questionId, response.topicId),
        responseId: response.id,
        questionId: response.questionId,
        topicId: response.topicId,
        topicLabel: response.topicLabel,
        subjectLabel: response.subjectLabel,
        analysis: analysisResult,
        explanation: explanationResult,
        source: explanationResult.source,
        syncedAt: Date.now(),
      })

      await updateResponse(response.id, {
        status: 'analyzed',
        syncStatus: 'synced',
        lastSyncedAt: Date.now(),
        lastSyncError: '',
        analysisSource: analysisResult.analysis_method ?? 'backend_offline_rule_engine',
        explanationSource: explanationResult.source,
      })

      syncedCount += 1
    } catch (error) {
      failedCount += 1
      await updateResponse(response.id, {
        syncStatus: 'pending',
        lastSyncError: error.message,
        lastSyncAttemptAt: Date.now(),
      })
    }
  }

  return {
    syncedCount,
    failedCount,
    pendingCount: await getPendingSyncCount(),
  }
}

export function notifyOfflineSyncStateChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(OFFLINE_SYNC_EVENT))
  }
}
