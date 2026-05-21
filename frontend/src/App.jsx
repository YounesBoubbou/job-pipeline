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
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-6 sticky top-0 z-10 shadow-sm">
          <span className="font-bold text-blue-700 text-base tracking-tight">
            🔍 Job Pipeline
          </span>

          <div className="flex gap-1">
            <NavLink href="#/" active={page === 'browser'}>
              Job Browser
            </NavLink>
            <NavLink href="#/tracker" active={page === 'tracker'}>
              Application Tracker
            </NavLink>
          </div>
        </nav>

        {/* ── Page content ── */}
        {page === 'browser' ? <JobBrowser /> : <Tracker />}
      </div>
    </TrackerProvider>
  )
}

function NavLink({ href, active, children }) {
  return (
    <a
      href={href}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        active
          ? 'bg-blue-50 text-blue-700'
          : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
      }`}
    >
      {children}
    </a>
  )
}
