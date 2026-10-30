import { openDB } from 'idb'

const DB_NAME = 'pragna-vistara-db'
const DB_VERSION = 7
const STORES = {
  SESSIONS: 'sessions',
  STUDENTS: 'students',
}

const IDENTITY_ID = 'anonymous-identity'
const CURRENT_STUDENT_ID = 'current-student'

async function getDB() {
  return openDB(DB_NAME)
}

function createDeviceId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID()
  }

  const bytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function saveIdentity(db, identity) {
  return db.put(STORES.SESSIONS, {
    id: IDENTITY_ID,
    ...identity,
    updatedAt: Date.now(),
  })
}

async function appendAnonIdToCurrentStudent(db, anonId) {
  const session = await db.get(STORES.SESSIONS, CURRENT_STUDENT_ID)
  if (!session?.student_id) return

  const student = await db.get(STORES.STUDENTS, session.student_id)
  if (!student || student.anon_id === anonId) return

  await db.put(STORES.STUDENTS, {
    ...student,
    anon_id: anonId,
    lastAccessedAt: Date.now(),
  })
}

async function fetchAnonId(fingerprint) {
  const response = await fetch('/auth/anon', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fingerprint }),
  })

  if (!response.ok) {
    throw new Error('anon id request failed')
  }

  const data = await response.json()
  return data.anon_id
}

export async function getAnonId() {
  const db = await getDB()
  let identity = await db.get(STORES.SESSIONS, IDENTITY_ID)

  if (identity?.anon_id) {
    await appendAnonIdToCurrentStudent(db, identity.anon_id)
    return identity.anon_id
  }

  if (!identity?.device_id) {
    identity = {
      ...identity,
      id: IDENTITY_ID,
      device_id: createDeviceId(),
      createdAt: identity?.createdAt ?? Date.now(),
    }
    await saveIdentity(db, identity)
  }

  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return identity?.anon_id ?? null
  }

  const fingerprint = btoa(`edu-device:${identity.device_id}`)
  try {
    const anonId = await fetchAnonId(fingerprint)
    await saveIdentity(db, { ...identity, anon_id: anonId })
    await appendAnonIdToCurrentStudent(db, anonId)
    return anonId
  } catch {
    const latestIdentity = await db.get(STORES.SESSIONS, IDENTITY_ID)
    return latestIdentity?.anon_id ?? null
  }
}
