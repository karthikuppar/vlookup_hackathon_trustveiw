import { OFFLINE_QUESTION_BANK, getOfflineQuestionById, getOfflineQuestionByTopicId } from '@/data/State/offlineQuestionBank'
import { saveQuestions, getQuestionsByTopic, getQuestionById } from '@/utils/indexedDB'
import { buildQuestionFromTopicContext } from '@/utils/syllabusPractice'

let seedPromise = null

export async function ensureOfflineQuestionBank() {
  if (!seedPromise) {
    seedPromise = (async () => {
      await saveQuestions(OFFLINE_QUESTION_BANK)
      return OFFLINE_QUESTION_BANK
    })()
  }

  return seedPromise
}

export async function getQuestionForTopic(topicId, topicContext = null) {
  await ensureOfflineQuestionBank()

  const storedQuestions = await getQuestionsByTopic(topicId)
  if (storedQuestions.length > 0) {
    return storedQuestions[0]
  }

  const staticQuestion = getOfflineQuestionByTopicId(topicId)
  if (staticQuestion) {
    return staticQuestion
  }

  if (!topicContext) {
    return null
  }

  const generatedQuestion = buildQuestionFromTopicContext({
    ...topicContext,
    topicId,
  })
  await saveQuestions([generatedQuestion])
  return generatedQuestion
}

export async function getQuestionForId(questionId) {
  await ensureOfflineQuestionBank()

  const storedQuestion = await getQuestionById(questionId)
  if (storedQuestion) {
    return storedQuestion
  }

  return getOfflineQuestionById(questionId)
}
