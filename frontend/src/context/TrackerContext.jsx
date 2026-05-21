/**
 * TrackerContext — manages application tracker state.
 *
 * Strategy:
 *  1. On mount, fetch tracked applications from GET /api/tracker (Google Sheets).
 *  2. All writes (markApplied, updateStatus) are optimistic — state updates
 *     immediately, then an async request goes to the backend.
 *  3. If the backend is unreachable (503 / network error), sheetsOk → false
 *     and the data lives in localStorage only. A warning banner is shown.
 *  4. localStorage is always kept in sync so the app survives a page refresh
 *     even when Sheets is down.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const TrackerContext = createContext(null)

export function useTracker() {
  return useContext(TrackerContext)
}

const LS_KEY = 'job_pipeline_tracker_v1'

function lsLoad() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]')
  } catch {
    return []
  }
}

function lsSave(entries) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(entries))
  } catch {
    // localStorage quota exceeded — silently ignore
  }
}

export function TrackerProvider({ children }) {
  const [applications, setApplications] = useState([])
  const [sheetsOk, setSheetsOk]         = useState(true)  // optimistic
  const [loading, setLoading]           = useState(true)

  // ── Load on mount ─────────────────────────────────────────────────────────
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/tracker')
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        const data = await res.json()
        setApplications(data)
        lsSave(data)   // keep LS in sync with Sheets
        setSheetsOk(true)
      } catch {
        // Sheets unavailable — fall back to localStorage
        setApplications(lsLoad())
        setSheetsOk(false)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // ── Mark a job as applied ─────────────────────────────────────────────────
  const markApplied = useCallback(async (job) => {
    const entry = {
      title:        job.title        || '',
      company:      job.company      || '',
      url:          job.url          || '',
      date_applied: new Date().toISOString().slice(0, 10),
      status:       'Applied',
    }

    // Optimistic update — UI responds instantly
    setApplications(prev => {
      const next = [...prev, entry]
      lsSave(next)
      return next
    })

    // Fire-and-forget async write to Sheets
    ;(async () => {
      try {
        const res = await fetch('/api/tracker', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(entry),
        })
        if (!res.ok) throw new Error(await res.text())
        setSheetsOk(true)
      } catch {
        setSheetsOk(false)
      }
    })()
  }, [])

  // ── Update status for a tracked application ───────────────────────────────
  const updateStatus = useCallback(async (url, status) => {
    // Optimistic update
    setApplications(prev => {
      const next = prev.map(a => (a.url === url ? { ...a, status } : a))
      lsSave(next)
      return next
    })

    // Fire-and-forget async write to Sheets
    ;(async () => {
      try {
        const res = await fetch('/api/tracker/status', {
          method:  'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ url, status }),
        })
        if (!res.ok) throw new Error(await res.text())
        setSheetsOk(true)
      } catch {
        setSheetsOk(false)
      }
    })()
  }, [])

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
