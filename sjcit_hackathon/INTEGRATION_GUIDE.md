# Integration Guide: Using Multi-Student System in Existing Pages

This guide shows how to integrate the multi-student system into existing pages and components.

## Quick Start

### 1. Get Current Student Info

```javascript
import { useStudent } from '@/context/StudentContext'

export default function MyPage() {
  const { currentStudent } = useStudent()
  
  if (!currentStudent) {
    return <div>Not logged in</div>
  }
  
  return (
    <div>
      <h1>Welcome, {currentStudent.name}</h1>
      <p>Class {currentStudent.class}</p>
    </div>
  )
}
```

### 2. Record Student Quiz Attempts

**OLD WAY (before multi-student):**
```javascript
import { saveResponse } from '@/utils/indexedDB'

await saveResponse({
  questionId: 'q_123',
  topicId: 'topic_45',
  selectedIndex: 2,
  isCorrect: true,
  timestamp: Date.now()
})
```

**NEW WAY (with multi-student):**
```javascript
import { recordStudentAttempt } from '@/services/studentManagement'
import { getCurrentStudentId } from '@/utils/indexedDB'

// Get current student
const studentId = await getCurrentStudentId()

// Record attempt (automatically tracks student)
await recordStudentAttempt(studentId, {
  questionId: 'q_123',
  topicId: 'topic_45',
  isCorrect: true,
  misconception: null,
  answerText: 'Selected option B',
  subjectLabel: 'Mathematics'
})
```

### 3. Get Student-Specific Progress

**OLD WAY:**
```javascript
import { getResponsesByTopic } from '@/utils/indexedDB'

const responses = await getResponsesByTopic('topic_45')
// Returns all responses from all students!
```

**NEW WAY:**
```javascript
import { getStudentResponsesByTopic } from '@/utils/indexedDB'
import { getCurrentStudentId } from '@/utils/indexedDB'

const studentId = await getCurrentStudentId()
const responses = await getStudentResponsesByTopic(studentId, 'topic_45')
// Returns only this student's responses
```

### 4. Update Progress Dashboard

```javascript
import { useStudent } from '@/context/StudentContext'
import { getStudentProgressSummary } from '@/services/studentManagement'
import { useEffect, useState } from 'react'

export default function ProgressDashboard() {
  const { currentStudent } = useStudent()
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    if (!currentStudent) return

    const loadProgress = async () => {
      const prog = await getStudentProgressSummary(currentStudent.id)
      setProgress(prog)
    }

    loadProgress()
  }, [currentStudent])

  if (!progress) return <div>Loading...</div>

  return (
    <div>
      <h2>{currentStudent.name}'s Progress</h2>
      <p>Total Attempts: {progress.total_attempts}</p>
      <p>Accuracy: {progress.accuracy}%</p>
      <p>Correct: {progress.correct_answers}</p>
    </div>
  )
}
```

## Common Integration Patterns

### Pattern 1: Protected Route (Check if Student is Logged In)

```javascript
import { Navigate } from 'react-router-dom'
import { useStudent } from '@/context/StudentContext'

export default function LearningPage() {
  const { currentStudent, isLoadingStudent } = useStudent()

  if (isLoadingStudent) {
    return <div>Loading...</div>
  }

  if (!currentStudent) {
    return <Navigate to="/login" replace />
  }

  // Render page content
  return <div>Learning Page for {currentStudent.name}</div>
}
```

### Pattern 2: Form with Student Context

```javascript
import { useStudent } from '@/context/StudentContext'
import { recordStudentAttempt } from '@/services/studentManagement'

export default function QuizPage() {
  const { currentStudent } = useStudent()
  const [answer, setAnswer] = useState('')

  const handleSubmit = async () => {
    if (!currentStudent) {
      alert('Please login first')
      return
    }

    await recordStudentAttempt(currentStudent.id, {
      questionId: 'q_123',
      topicId: 'topic_45',
      isCorrect: answer === 'correct',
      misconception: null,
      answerText: answer
    })

    // Show result...
  }

  return (
    <div>
      <p>Student: {currentStudent.name}</p>
      <input value={answer} onChange={(e) => setAnswer(e.target.value)} />
      <button onClick={handleSubmit}>Submit</button>
    </div>
  )
}
```

### Pattern 3: Multi-Student Statistics

```javascript
import { getDeviceStatistics } from '@/services/studentManagement'
import { useEffect, useState } from 'react'

export default function DeviceStatsPage() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const loadStats = async () => {
      const deviceStats = await getDeviceStatistics()
      setStats(deviceStats)
    }
    loadStats()
  }, [])

  if (!stats) return <div>Loading...</div>

  return (
    <div>
      <h2>Device Statistics</h2>
      <p>Total Students: {stats.totalStudents}</p>
      <p>Total Attempts: {stats.totalAttempts}</p>
      <p>Average Accuracy: {stats.avgAccuracy}%</p>
    </div>
  )
}
```

## Updating Existing Pages

### SelectionPage
Add student name to header:
```javascript
import { useStudent } from '@/context/StudentContext'

export default function SelectionPage() {
  const { currentStudent } = useStudent()

  return (
    <div>
      <h1>Hello, {currentStudent?.name}! 👋</h1>
      {/* existing content */}
    </div>
  )
}
```

### LearningPage
Filter responses by student:
```javascript
// In your learning component
const studentId = await getCurrentStudentId()
const myResponses = await getStudentResponsesByTopic(studentId, topicId)
```

### ProgressDashboardPage
Show only current student's progress:
```javascript
const { currentStudent } = useStudent()
const progress = await getStudentProgressSummary(currentStudent.id)
```

## Migration Checklist

When updating existing pages:

- [ ] Import `useStudent` hook
- [ ] Replace `getCurrentSession()` with `useStudent().currentStudent`
- [ ] Update `saveResponse()` → `recordStudentAttempt()`
- [ ] Update response queries → add `student_id` filter
- [ ] Update progress queries → student-specific
- [ ] Test with multiple students
- [ ] Test offline functionality
- [ ] Verify data isolation

## Example: Updating QuestionPage

**Before:**
```javascript
import { saveResponse, getResponsesByTopic } from '@/utils/indexedDB'

export default function QuestionPage() {
  const handleSubmit = async (answer) => {
    // Save without student tracking
    const responseId = await saveResponse({
      questionId,
      topicId,
      selectedIndex: answer,
      isCorrect: answer === correctIndex
    })
    
    // Get all responses (includes other students!)
    const allResponses = await getResponsesByTopic(topicId)
  }
}
```

**After:**
```javascript
import { recordStudentAttempt } from '@/services/studentManagement'
import { getCurrentStudentId } from '@/utils/indexedDB'
import { useStudent } from '@/context/StudentContext'

export default function QuestionPage() {
  const { currentStudent } = useStudent()
  
  const handleSubmit = async (answer) => {
    const studentId = await getCurrentStudentId()
    
    // Save with student tracking
    const responseId = await recordStudentAttempt(studentId, {
      questionId,
      topicId,
      isCorrect: answer === correctIndex,
      misconception: null,
      answerText: question.options[answer]
    })
    
    // Get only this student's responses
    const myResponses = await getStudentResponsesByTopic(studentId, topicId)
  }
}
```

## Testing Multi-Student Functionality

### Test Script
```javascript
// Run in browser console on any page

import {
  registerStudent,
  loginStudent,
  recordStudentAttempt,
  getStudentProgressSummary,
  switchStudent
} from '@/services/studentManagement'

// 1. Create two students
console.log('Creating Student 1...')
const stu1 = await registerStudent({
  name: 'Alice',
  class: 'V',
  pin: '1111',
  language: 'en'
})
console.log('✓ Created:', stu1.id)

console.log('Creating Student 2...')
const stu2 = await registerStudent({
  name: 'Bob',
  class: 'VI',
  pin: '2222',
  language: 'en'
})
console.log('✓ Created:', stu2.id)

// 2. Record attempts for both
console.log('Recording attempts for Alice...')
await recordStudentAttempt(stu1.id, {
  questionId: 'q_1',
  topicId: 't_1',
  isCorrect: true,
  misconception: null
})
await recordStudentAttempt(stu1.id, {
  questionId: 'q_2',
  topicId: 't_1',
  isCorrect: false,
  misconception: 'error_type_1'
})

console.log('Recording attempts for Bob...')
await recordStudentAttempt(stu2.id, {
  questionId: 'q_1',
  topicId: 't_1',
  isCorrect: true,
  misconception: null
})

// 3. Check progress
const prog1 = await getStudentProgressSummary(stu1.id)
const prog2 = await getStudentProgressSummary(stu2.id)

console.log('Alice:', prog1)
console.log('Bob:', prog2)

// 4. Verify data isolation
console.assert(prog1.total_attempts === 2, 'Alice should have 2 attempts')
console.assert(prog2.total_attempts === 1, 'Bob should have 1 attempt')
console.log('✓ Data isolation verified!')
```

## Troubleshooting Integration Issues

### Issue: `useStudent` returns undefined
**Solution:** Ensure `StudentProvider` is in App.jsx wrapper
```javascript
// App.jsx
<StudentProvider>
  {children}
</StudentProvider>
```

### Issue: Student data mixed up
**Solution:** Always filter by `student_id`
```javascript
// Wrong:
const allResponses = await getAllResponses()

// Right:
const studentId = await getCurrentStudentId()
const myResponses = await getResponsesByStudent(studentId)
```

### Issue: PIN not verifying
**Solution:** Check exact value (numeric string, 4-6 digits)
```javascript
// Test pin authentication directly
const valid = await authenticateStudent(studentId, '1234')
console.log(valid) // should be true/false
```

### Issue: Student not persisting after refresh
**Solution:** StudentProvider handles this, but check IndexedDB
```javascript
// In DevTools:
const db = await indexedDB.databases()
console.log(db) // should show 'pragna-vistara-db'
```

## Performance Notes

- ✅ IndexedDB queries are indexed by `student_id` (fast lookups)
- ✅ Student switching is instant (no network calls)
- ✅ Data isolation uses indexed queries (O(n) where n = student's responses)
- ✅ Can handle 100+ students per device without issues

## Production Deployment

1. **Test with real classrooms:**
   - 30 students, 1 tablet
   - Teacher switches between students
   - Verify no data leakage

2. **Enable PIN hashing:**
   ```javascript
   import bcrypt from 'bcryptjs'
   // Update studentManagement.js to hash PINs
   ```

3. **Add device-level security:**
   - Require device unlock
   - Session timeout (30 mins)
   - Clear session on app close

4. **Monitor performance:**
   - Measure IndexedDB query times
   - Alert if responses > 10k per student

5. **Backup strategy:**
   - Auto-export weekly
   - Sync to cloud (optional)
   - Test restore process
