/**
 * Misconception Tracker — saves and queries misconception detection results.
 * Uses IndexedDB for offline-first storage.
 */

const DB_NAME = 'pragna-vistara-misconceptions'
const DB_VERSION = 1
const STORE_NAME = 'misconception_results'

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true })
        store.createIndex('topicId', 'topicId', { unique: false })
        store.createIndex('chapterId', 'chapterId', { unique: false })
        store.createIndex('misconceptionId', 'misconceptionId', { unique: false })
        store.createIndex('timestamp', 'timestamp', { unique: false })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Save a misconception probe result */
export async function saveMisconceptionResult({
  chapterId, topicId, misconceptionId, probe, selectedIndex, correctIndex, isCorrect, timestamp,
}) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const record = {
      chapterId, topicId, misconceptionId, probe,
      selectedIndex, correctIndex, isCorrect,
      timestamp: timestamp ?? Date.now(),
    }
    const req = store.add(record)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Get all results for a specific topic */
export async function getResultsByTopic(topicId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const idx = tx.objectStore(STORE_NAME).index('topicId')
    const req = idx.getAll(topicId)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Get all results for a chapter */
export async function getResultsByChapter(chapterId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const idx = tx.objectStore(STORE_NAME).index('chapterId')
    const req = idx.getAll(chapterId)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Get all results */
export async function getAllResults() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const req = tx.objectStore(STORE_NAME).getAll()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Compute summary: most common misconceptions */
export async function getMisconceptionSummary(chapterId) {
  const results = chapterId
    ? await getResultsByChapter(chapterId)
    : await getAllResults()

  const byMisconception = {}
  for (const r of results) {
    if (!byMisconception[r.misconceptionId]) {
      byMisconception[r.misconceptionId] = { total: 0, incorrect: 0, probe: r.probe }
    }
    byMisconception[r.misconceptionId].total++
    if (!r.isCorrect) byMisconception[r.misconceptionId].incorrect++
  }

  return Object.entries(byMisconception)
    .map(([id, data]) => ({
      misconceptionId: id,
      probe: data.probe,
      totalAttempts: data.total,
      incorrectCount: data.incorrect,
      errorRate: data.total > 0 ? data.incorrect / data.total : 0,
    }))
    .sort((a, b) => b.errorRate - a.errorRate)
}
