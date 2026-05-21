/**
 * Tracker — View 2 (/tracker).
 *
 * Displays all jobs the user has marked as applied.
 * Each row has a status dropdown; changes are async-written to Google Sheets
 * with localStorage as a fallback.
 */

import { useTracker } from '../context/TrackerContext.jsx'
import StatusDropdown from '../components/StatusDropdown.jsx'

export default function Tracker() {
  const { applications, updateStatus, sheetsOk, loading } = useTracker()

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Application Tracker</h1>
        <p className="text-sm text-gray-400 mt-1">
          {applications.length} application{applications.length !== 1 ? 's' : ''} tracked
        </p>
      </div>

      {/* Sheets warning banner */}
      {!sheetsOk && (
        <div className="mb-5 flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-yellow-800 text-sm">
          <span className="text-base">⚠️</span>
          <span>
            Google Sheets is unavailable. Your data is saved in your browser's local storage only —
            it won't sync across devices until Sheets is restored.
          </span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <p className="text-gray-400 text-sm">Loading tracker…</p>
      )}

      {/* Empty state */}
      {!loading && applications.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <p className="text-4xl mb-3">📋</p>
          <p className="text-sm font-medium">No applications tracked yet.</p>
          <p className="text-xs mt-1">
            Go to{' '}
            <a href="#/" className="text-blue-500 hover:underline">
              Job Browser
            </a>{' '}
            and click <strong>"Mark as Applied"</strong> on a listing.
          </p>
        </div>
      )}

      {/* Application rows */}
      {!loading && applications.length > 0 && (
        <div className="space-y-2">
          {/* Table header */}
          <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto] gap-4 px-4 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wide">
            <span>Job</span>
            <span>Applied</span>
            <span>Link</span>
            <span>Status</span>
          </div>

          {applications.map((app, i) => (
            <div
              key={app.url || i}
              className="bg-white rounded-lg border border-gray-200 px-4 py-3 grid sm:grid-cols-[1fr_auto_auto_auto] gap-3 sm:gap-4 items-center hover:border-gray-300 transition-colors"
            >
              {/* Job info */}
              <div className="min-w-0">
                <p className="font-medium text-gray-900 text-sm truncate">{app.title}</p>
                <p className="text-gray-500 text-xs mt-0.5">{app.company}</p>
              </div>

              {/* Date applied */}
              <span className="text-xs text-gray-400 whitespace-nowrap">
                {app.date_applied}
              </span>

              {/* Link */}
              {app.url ? (
                <a
                  href={app.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline whitespace-nowrap"
                  title={app.url}
                >
                  View →
                </a>
              ) : (
                <span className="text-xs text-gray-300">—</span>
              )}

              {/* Status dropdown */}
              <StatusDropdown
                value={app.status}
                onChange={status => updateStatus(app.url, status)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
