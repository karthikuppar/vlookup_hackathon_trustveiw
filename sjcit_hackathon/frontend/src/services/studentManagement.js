/**
 * studentManagement.js
 * Comprehensive multi-student management for offline mode.
 * 
 * Features:
 * - Create/edit/delete students
 * - PIN-based authentication
 * - Student session tracking
 * - Export/import student data (backup & restore)
 * - Progress tracking per student
 */

import {
  createStudent,
  getAllStudents,
  getStudentById,
  authenticateStudent,
  deleteStudent,
  updateStudent,
  getCurrentStudentId,
  setCurrentStudent,
  clearCurrentStudent,
  getStudentProgress,
  updateStudentProgress,
  getResponsesByStudent,
  saveResponseWithStudent,
} from '@/utils/indexedDB'

// ─── Student Management ────────────────────────────────────────────────────────

/**
 * Creates a new student on this device.
 * @param {Object} studentData - { name, class, pin, language }
 * @returns {Promise<Object>} created student with id
 */
export async function registerStudent(studentData) {
  if (!studentData.name || !studentData.class || !studentData.pin) {
    throw new Error('Name, class, and PIN are required')
  }
  
  if (studentData.pin.length < 4) {
    throw new Error('PIN must be at least 4 digits')
  }
  
  const studentId = await createStudent({
    name: studentData.name,
    class: studentData.class,
    pin: studentData.pin,
    language: studentData.language || 'en',
  })
  
  return {
    id: studentId,
    name: studentData.name,
    class: studentData.class,
    language: studentData.language || 'en',
    createdAt: Date.now(),
  }
}

/**
 * Lists all students available on this device.
 * @returns {Promise<Object[]>}
 */
export async function listStudents() {
  const students = await getAllStudents()
  return students.map(s => ({
    id: s.id,
    name: s.name,
    class: s.class,
    language: s.language,
    anon_id: s.anon_id,
    lastAccessedAt: s.lastAccessedAt,
    createdAt: s.createdAt,
  }))
}

/**
 * Authenticates a student with PIN and logs them in.
 * @param {string} studentId
 * @param {string} pin
 * @returns {Promise<Object>} authenticated student
 */
export async function loginStudent(studentId, pin) {
  const isValid = await authenticateStudent(studentId, pin)
  
  if (!isValid) {
    throw new Error('Invalid PIN')
  }
  
  await setCurrentStudent(studentId)
  const student = await getStudentById(studentId)
  
  return {
    id: student.id,
    name: student.name,
    class: student.class,
    language: student.language,
    anon_id: student.anon_id,
  }
}

/**
 * Starts a student session without PIN verification.
 * Used by the app login screen so local/offline entry always works.
 * @param {string} studentId
 * @returns {Promise<Object>} active student
 */
export async function forceLoginStudent(studentId) {
  await setCurrentStudent(studentId)
  const student = await getStudentById(studentId)

  if (!student) {
    throw new Error('Student not found')
  }

  return {
    id: student.id,
    name: student.name,
    class: student.class,
    language: student.language,
    anon_id: student.anon_id,
  }
}

/**
 * Gets the currently logged-in student.
 * @returns {Promise<Object|null>}
 */
export async function getCurrentStudent() {
  const studentId = await getCurrentStudentId()
  
  if (!studentId) {
    return null
  }
  
  const student = await getStudentById(studentId)
  if (!student) {
    await clearCurrentStudent()
    return null
  }
  
  return {
    id: student.id,
    name: student.name,
    class: student.class,
    language: student.language,
    anon_id: student.anon_id,
  }
}

/**
 * Switches to a different student (for shared devices).
 * @param {string} studentId
 * @param {string} pin - Student's PIN for security
 * @returns {Promise<Object>} switched student
 */
export async function switchStudent(studentId, pin) {
  return loginStudent(studentId, pin)
}

/**
 * Logs out the current student.
 * @returns {Promise<void>}
 */
export async function logoutStudent() {
  await clearCurrentStudent()
}

/**
 * Updates student info (name, class, language).
 * Note: Does NOT change PIN through this method (see updateStudentPin).
 * @param {string} studentId
 * @param {Object} updates - { name?, class?, language? }
 */
export async function editStudent(studentId, updates) {
  const student = await getStudentById(studentId)
  
  if (!student) {
    throw new Error('Student not found')
  }
  
  await updateStudent(studentId, updates)
  
  return {
    id: student.id,
    name: updates.name || student.name,
    class: updates.class || student.class,
    language: updates.language || student.language,
  }
}

/**
 * Removes a student and all their data from the device.
 * @param {string} studentId
 * @param {string} pin - Requires PIN for security
 */
export async function removeStudent(studentId, pin) {
  const isValid = await authenticateStudent(studentId, pin)
  
  if (!isValid) {
    throw new Error('Invalid PIN. Student not deleted.')
  }
  
  // If this was the current student, logout
  const currentId = await getCurrentStudentId()
  if (currentId === studentId) {
    await clearCurrentStudent()
  }
  
  await deleteStudent(studentId)
}

// ─── Student Progress ─────────────────────────────────────────────────────────

/**
 * Gets a student's progress summary.
 * @param {string} studentId
 * @returns {Promise<Object>}
 */
export async function getStudentProgressSummary(studentId) {
  const progress = await getStudentProgress(studentId)
  
  if (!progress) {
    return {
      student_id: studentId,
      topics_completed: [],
      weak_areas: [],
      accuracy: 0,
      total_attempts: 0,
      correct_answers: 0,
    }
  }
  
  return {
    student_id: progress.student_id,
    topics_completed: progress.topics_completed || [],
    weak_areas: progress.weak_areas || [],
    accuracy: progress.accuracy || 0,
    total_attempts: progress.total_attempts || 0,
    correct_answers: progress.correct_answers || 0,
  }
}

/**
 * Records a quiz attempt for a student and updates progress.
 * @param {string} studentId
 * @param {Object} attemptData - { questionId, topicId, subjectId, isCorrect, ... }
 */
export async function recordStudentAttempt(studentId, attemptData) {
  // Save response with student_id
  const responseId = await saveResponseWithStudent({
    student_id: studentId,
    ...attemptData,
  })
  
  // Update student progress
  const progress = await getStudentProgress(studentId)
  const newAttempts = (progress.total_attempts || 0) + 1
  const newCorrect = (progress.correct_answers || 0) + (attemptData.isCorrect ? 1 : 0)
  const newAccuracy = Math.round((newCorrect / newAttempts) * 100)
  
  // Add to weak_areas if incorrect
  let weakAreas = progress.weak_areas || []
  if (!attemptData.isCorrect && attemptData.misconception) {
    if (!weakAreas.includes(attemptData.misconception)) {
      weakAreas = [...weakAreas, attemptData.misconception]
    }
  }
  
  await updateStudentProgress(studentId, {
    total_attempts: newAttempts,
    correct_answers: newCorrect,
    accuracy: newAccuracy,
    weak_areas: weakAreas,
  })
  
  return responseId
}

// ─── Export/Import (Backup & Restore) ──────────────────────────────────────────

/**
 * Exports a single student's data as JSON (for backup).
 * @param {string} studentId
 * @param {string} pin - Requires PIN for security
 * @returns {Promise<Object>} exportable data
 */
export async function exportStudentData(studentId, pin) {
  const isValid = await authenticateStudent(studentId, pin)
  
  if (!isValid) {
    throw new Error('Invalid PIN. Export cancelled.')
  }
  
  const student = await getStudentById(studentId)
  const progress = await getStudentProgress(studentId)
  const responses = await getResponsesByStudent(studentId)
  
  return {
    exportVersion: '1.0',
    exportedAt: new Date().toISOString(),
    student: {
      id: student.id,
      name: student.name,
      class: student.class,
      language: student.language,
      createdAt: student.createdAt,
    },
    progress,
    responses: responses.map(r => ({
      ...r,
      // Don't export sensitive data
      student_id: undefined,
    })),
    metadata: {
      totalResponses: responses.length,
      accuracy: progress.accuracy,
      lastStudied: Math.max(...responses.map(r => r.timestamp || 0)),
    },
  }
}

/**
 * Exports ALL students' data as JSON.
 * @returns {Promise<Object>} export with all students
 */
export async function exportAllStudentsData() {
  const students = await getAllStudents()
  const allData = []
  
  for (const student of students) {
    const progress = await getStudentProgress(student.id)
    const responses = await getResponsesByStudent(student.id)
    
    allData.push({
      student: {
        id: student.id,
        name: student.name,
        class: student.class,
        language: student.language,
        createdAt: student.createdAt,
      },
      progress,
      responses: responses.length,
    })
  }
  
  return {
    exportVersion: '1.0',
    exportedAt: new Date().toISOString(),
    totalStudents: students.length,
    students: allData,
  }
}

/**
 * Downloads a student's data as JSON file.
 * @param {string} studentId
 * @param {string} pin
 */
export async function downloadStudentDataJSON(studentId, pin) {
  const data = await exportStudentData(studentId, pin)
  const student = await getStudentById(studentId)
  
  const jsonString = JSON.stringify(data, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${student.name}_backup_${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Downloads a student's data as CSV file (responses only).
 * @param {string} studentId
 * @param {string} pin
 */
export async function downloadStudentDataCSV(studentId, pin) {
  const data = await exportStudentData(studentId, pin)
  const student = await getStudentById(studentId)
  
  const responses = data.responses
  if (responses.length === 0) {
    alert('No responses to export')
    return
  }
  
  // Build CSV header
  const headers = [
    'Question ID',
    'Topic ID',
    'Subject',
    'Correct',
    'Answer Text',
    'Misconception',
    'Timestamp',
  ]
  
  // Build CSV rows
  const rows = responses.map(r => [
    r.questionId,
    r.topicId,
    r.subjectLabel || r.subjectId || '',
    r.isCorrect ? 'Yes' : 'No',
    (r.answerText || '').replace(/"/g, '""'),
    r.misconception || '',
    new Date(r.timestamp).toISOString(),
  ])
  
  const csvContent = [
    headers.map(h => `"${h}"`).join(','),
    ...rows.map(r => r.map(cell => `"${cell}"`).join(',')),
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${student.name}_responses_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Imports/restores a student's data from JSON backup.
 * (This is a simplified version; full implementation would restore responses too)
 * @param {Object} importData - exported data object
 * @returns {Promise<string>} imported student ID
 */
export async function importStudentData(importData) {
  if (!importData.student || !importData.progress) {
    throw new Error('Invalid import file format')
  }
  
  // Create student (with new ID, old data preserved)
  const studentId = await createStudent({
    name: importData.student.name,
    class: importData.student.class,
    language: importData.student.language,
    pin: '0000', // Default PIN for imported students
  })
  
  // Restore progress
  await updateStudentProgress(studentId, {
    topics_completed: importData.progress.topics_completed || [],
    weak_areas: importData.progress.weak_areas || [],
    accuracy: importData.progress.accuracy || 0,
    total_attempts: importData.progress.total_attempts || 0,
    correct_answers: importData.progress.correct_answers || 0,
  })
  
  // TODO: Restore responses (more complex, needs mapping)
  
  return studentId
}

/**
 * Handles JSON file upload for import.
 * @param {File} file - JSON file to import
 * @returns {Promise<string>} imported student ID
 */
export async function importStudentDataFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    
    reader.onload = async (e) => {
      try {
        const importData = JSON.parse(e.target.result)
        const studentId = await importStudentData(importData)
        resolve(studentId)
      } catch (error) {
        reject(new Error(`Import failed: ${error.message}`))
      }
    }
    
    reader.onerror = () => {
      reject(new Error('Failed to read file'))
    }
    
    reader.readAsText(file)
  })
}

// ─── Device-Level Statistics ──────────────────────────────────────────────────

/**
 * Gets statistics for all students on this device.
 * @returns {Promise<Object>}
 */
export async function getDeviceStatistics() {
  const students = await getAllStudents()
  let totalAttempts = 0
  let totalCorrect = 0
  let avgAccuracy = 0
  
  for (const student of students) {
    const progress = await getStudentProgress(student.id)
    totalAttempts += progress.total_attempts || 0
    totalCorrect += progress.correct_answers || 0
  }
  
  avgAccuracy = totalAttempts > 0 ? Math.round((totalCorrect / totalAttempts) * 100) : 0
  
  return {
    totalStudents: students.length,
    totalAttempts,
    totalCorrect,
    avgAccuracy,
    lastStudent: students.length > 0 ? students[students.length - 1].name : null,
  }
}

export default {
  registerStudent,
  listStudents,
  loginStudent,
  getCurrentStudent,
  switchStudent,
  logoutStudent,
  editStudent,
  removeStudent,
  getStudentProgressSummary,
  recordStudentAttempt,
  exportStudentData,
  exportAllStudentsData,
  downloadStudentDataJSON,
  downloadStudentDataCSV,
  importStudentData,
  importStudentDataFromFile,
  getDeviceStatistics,
}
