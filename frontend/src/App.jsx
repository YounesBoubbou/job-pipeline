import { useState, useEffect } from 'react'
import { TrackerProvider } from './context/TrackerContext.jsx'
import JobBrowser from './pages/JobBrowser.jsx'
import Tracker from './pages/Tracker.jsx'

/** Derive current page from URL hash: #/ → browser, #/tracker → tracker */
function getPage() {
  return window.location.hash === '#/tracker' ? 'tracker' : 'browser'
}

export default function App() {
  const [page, setPage] = useState(getPage)

  useEffect(() => {
    const onHashChange = () => setPage(getPage())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return (
    <TrackerProvider>
      <div className="min-h-screen bg-gray-50 text-gray-900">
        {/* ── Nav bar ── */}
        {/* Phones get shorter labels, so the bar fits on one line at 375px */}
        <nav className="bg-white border-b border-gray-200 px-4 sm:px-6 py-1.5 sm:py-3 flex items-center gap-3 sm:gap-6 sticky top-0 z-10 shadow-sm">
          <span className="font-bold text-blue-700 text-base tracking-tight whitespace-nowrap">
            🔍 Job Pipeline
          </span>

          <div className="flex gap-1 min-w-0">
            <NavLink href="#/" active={page === 'browser'} short="Jobs">
              Job Browser
            </NavLink>
            <NavLink href="#/tracker" active={page === 'tracker'} short="Tracker">
              Application Tracker
            </NavLink>
          </div>
        </nav>

        <LastRunStatus />

        {/* ── Page content ── */}
        {page === 'browser' ? <JobBrowser /> : <Tracker />}
      </div>
    </TrackerProvider>
  )
}

function NavLink({ href, active, short, children }) {
  return (
    <a
      href={href}
      className={`px-3 py-2.5 sm:py-1.5 whitespace-nowrap rounded-md text-sm font-medium transition-colors ${
        active
          ? 'bg-blue-50 text-blue-700'
          : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
      }`}
    >
      <span className="sm:hidden">{short}</span>
      <span className="hidden sm:inline">{children}</span>
    </a>
  )
}

/** "3 hours ago" style text for a past date */
function timeAgo(date) {
  const minutes = Math.round((Date.now() - date.getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  return `${Math.round(hours / 24)} days ago`
}

/** When the pipeline last ran and how many boards failed (W8), from /api/last-run */
function LastRunStatus() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/api/last-run')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch((err) =>
        setData({ found: false, message: `Could not load the last run status: ${err.message}` })
      )
  }, [])

  if (!data) return null

  if (!data.found) {
    return (
      <div className="px-4 sm:px-6 py-2 text-sm bg-yellow-50 border-b border-yellow-200 text-yellow-800">
        {data.message}
      </div>
    )
  }

  const run = data.summary
  const finished = new Date(run.finished_at)
  const failed = run.failed || []
  const crashed = run.status === 'crashed'

  return (
    <div
      className={`px-4 sm:px-6 py-2 text-sm border-b ${
        crashed || failed.length
          ? 'bg-yellow-50 border-yellow-200 text-yellow-900'
          : 'bg-white border-gray-200 text-gray-600'
      }`}
    >
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        <span>
          Last run:{' '}
          <span className="font-medium">
            {finished.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
          </span>{' '}
          ({timeAgo(finished)})
        </span>
        {crashed && (
          <span className="font-medium text-red-700">Crashed: {run.error}</span>
        )}
        <span>
          {failed.length} board{failed.length === 1 ? '' : 's'} failed
        </span>
      </div>

      {failed.length > 0 && (
        <details className="mt-1">
          <summary className="cursor-pointer text-blue-700 py-2 sm:py-0">Show failed boards</summary>
          <ul className="mt-1 space-y-1">
            {failed.map((board) => (
              <li key={`${board.source}:${board.name}`} className="break-words">
                <span className="font-medium">{board.name}</span>{' '}
                <span className="text-gray-500">({board.source})</span>: {board.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
