/**
 * TrackerContext — manages application tracker state.
 *
 * Strategy:
 *  1. Every change (markApplied, updateStatus) is shown at once and also put
 *     in a queue of unsent changes, kept in localStorage.
 *  2. A "sync" then asks the Sheet for its rows (GET /api/tracker). If the
 *     Sheet answers, the queued changes are sent to it in order, and each one
 *     leaves the queue only once the API has accepted it. The list shown is
 *     the Sheet's rows plus anything still unsent.
 *  3. A sync runs on page load and after every change, so changes made while
 *     the Sheet was down are sent the next time it answers.
 *  4. If the Sheet is unreachable (503 / network error), sheetsOk → false and
 *     a warning banner is shown. The list comes from the last copy saved in
 *     localStorage, plus the queue, so the app survives a page refresh.
 *
 * The queue is stored apart from the cached list on purpose: the cached list
 * is replaced by the Sheet's rows on every successful load, and the queue is
 * what makes sure nothing waiting to be sent is lost when that happens.
 */

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { localDate, mergeUnsent, replayQueue } from './trackerQueue'

const TrackerContext = createContext(null)

export function useTracker() {
  return useContext(TrackerContext)
}

const LS_KEY       = 'job_pipeline_tracker_v1'        // last list shown
const LS_QUEUE_KEY = 'job_pipeline_tracker_queue_v1'  // changes not yet in the Sheet

function lsRead(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '[]')
  } catch {
    return []
  }
}

function lsWrite(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // localStorage quota exceeded — silently ignore
  }
}

// The queue is always read from and written to localStorage directly (not
// kept in React state), so a change queued while a sync is running is never
// overwritten by that sync.
function queueAdd(change) {
  lsWrite(LS_QUEUE_KEY, [...lsRead(LS_QUEUE_KEY), change])
}

function queueRemove(id) {
  lsWrite(LS_QUEUE_KEY, lsRead(LS_QUEUE_KEY).filter(c => c.id !== id))
}

// A unique enough id, to remove the right change once it is sent.
function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

// Send one change to the API; throws if the Sheet refuses it.
async function sendChange(change) {
  const res = change.type === 'add'
    ? await fetch('/api/tracker', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(change.entry),
      })
    : await fetch('/api/tracker/status', {
        method:  'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ url: change.url, status: change.status }),
      })
  if (!res.ok) throw new Error(await res.text())
}

export function TrackerProvider({ children }) {
  const [applications, setApplications] = useState([])
  const [sheetsOk, setSheetsOk]         = useState(true)  // optimistic
  const [loading, setLoading]           = useState(true)

  // Only one sync runs at a time; otherwise two syncs could send the same
  // queued add and create a duplicate row. A sync asked for while one is
  // running sets `syncAgain`, and the running one goes round once more.
  const syncing   = useRef(false)
  const syncAgain = useRef(false)

  // Show a list and keep a copy in localStorage for the next offline load.
  const show = useCallback((list) => {
    setApplications(list)
    lsWrite(LS_KEY, list)
  }, [])

  const syncOnce = useCallback(async () => {
    const queue = lsRead(LS_QUEUE_KEY)
    try {
      const res = await fetch('/api/tracker')
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const rows = await res.json()
      const allSent = await replayQueue(queue, rows, sendChange, queueRemove)
      // `rows` predates what was just sent, so lay the whole queue (sent and
      // unsent) over it, plus anything queued while this sync was running.
      show(mergeUnsent(mergeUnsent(rows, queue), lsRead(LS_QUEUE_KEY)))
      setSheetsOk(allSent)
    } catch {
      // Sheets unavailable — fall back to localStorage
      show(mergeUnsent(lsRead(LS_KEY), queue))
      setSheetsOk(false)
    }
  }, [show])

  const sync = useCallback(async () => {
    if (syncing.current) {
      syncAgain.current = true
      return
    }
    syncing.current = true
    try {
      do {
        syncAgain.current = false
        await syncOnce()
      } while (syncAgain.current)
    } finally {
      syncing.current = false
      setLoading(false)
    }
  }, [syncOnce])

  // ── Load on mount ─────────────────────────────────────────────────────────
  useEffect(() => {
    sync()
  }, [sync])

  // Queue a change, show it at once, then try to send it.
  const record = useCallback((change) => {
    queueAdd(change)
    setApplications(prev => {
      const next = mergeUnsent(prev, [change])
      lsWrite(LS_KEY, next)
      return next
    })
    sync()
  }, [sync])

  // ── Mark a job as applied ─────────────────────────────────────────────────
  const markApplied = useCallback(async (job) => {
    record({
      id:   newId(),
      type: 'add',
      entry: {
        title:        job.title   || '',
        company:      job.company || '',
        url:          job.url     || '',
        date_applied: localDate(),
        status:       'Applied',
      },
    })
  }, [record])

  // ── Update status for a tracked application ───────────────────────────────
  const updateStatus = useCallback(async (url, status) => {
    record({ id: newId(), type: 'status', url, status })
  }, [record])

  // Set of URLs already in the tracker — used by JobBrowser to hide applied jobs
  const trackedUrls = new Set(applications.map(a => a.url).filter(Boolean))

  return (
    <TrackerContext.Provider
      value={{ applications, trackedUrls, markApplied, updateStatus, sheetsOk, loading }}
    >
      {children}
    </TrackerContext.Provider>
  )
}
