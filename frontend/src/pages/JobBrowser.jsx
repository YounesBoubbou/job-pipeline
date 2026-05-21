/**
 * JobBrowser — View 1.
 *
 * Fetches all jobs from GET /api/jobs, applies the 5 filter rules
 * simultaneously, hides already-applied jobs, and renders job cards
 * sorted by date_found descending.
 */

import { useState, useEffect, useMemo } from 'react'
import { useTracker } from '../context/TrackerContext.jsx'
import JobCard from '../components/JobCard.jsx'
import FilterBar from '../components/FilterBar.jsx'
import {
  DEFAULT_FILTERS,
  ROLE_MAP,
  SENIORITY_EXCLUDE,
  DUTCH_EXCLUDE,
  EDU_INCLUDE,
} from '../constants/filters.js'

// ── Filter logic ───────────────────────────────────────────────────────────────

function passesFilters(job, filters) {
  const title = (job.title               || '').toLowerCase()
  const desc  = (job.description_snippet || '').toLowerCase()
  const text  = `${title} ${desc}`

  // 1. Role type — ANY selected role must match
  if (filters.roles.length > 0) {
    const matchesRole = filters.roles.some(role =>
      ROLE_MAP[role]?.some(kw => text.includes(kw))
    )
    if (!matchesRole) return false
  }

  // 2. Seniority — exclude if ANY disqualifying keyword found
  if (filters.seniority) {
    if (SENIORITY_EXCLUDE.some(kw => text.includes(kw))) return false
  }

  // 3. Language — exclude if any Dutch-required keyword found
  if (filters.language) {
    if (DUTCH_EXCLUDE.some(kw => text.includes(kw))) return false
  }

  // 4. IND sponsorship — show only confirmed sponsors
  if (filters.indSponsor) {
    if (job.ind_sponsor !== 'Yes') return false
  }

  // 5. Education — show only if a master's-level keyword appears
  if (filters.education) {
    if (!EDU_INCLUDE.some(kw => text.includes(kw))) return false
  }

  return true
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function JobBrowser() {
  const [jobs,    setJobs]    = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)

  const { trackedUrls, markApplied, sheetsOk } = useTracker()

  // Fetch all jobs once on mount
  useEffect(() => {
    fetch('/api/jobs')
      .then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json()
      })
      .then(data => {
        // Sort newest first
        data.sort((a, b) => (b.date_found || '').localeCompare(a.date_found || ''))
        setJobs(data)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  // Apply all filters + hide already-applied jobs
  const filtered = useMemo(() => (
    jobs
      .filter(j => !trackedUrls.has(j.url))
      .filter(j => passesFilters(j, filters))
  ), [jobs, filters, trackedUrls])

  return (
    <div className="flex" style={{ minHeight: 'calc(100vh - 49px)' }}>
      {/* ── Filter sidebar ── */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalShown={filtered.length}
        totalJobs={jobs.length}
      />

      {/* ── Job list ── */}
      <main className="flex-1 p-6 overflow-y-auto">
        {/* Sheets warning */}
        {!sheetsOk && (
          <div className="mb-4 flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-yellow-800 text-sm">
            <span>⚠️</span>
            <span>Google Sheets unavailable — tracker data is saved in your browser's local storage.</span>
          </div>
        )}

        {loading && (
          <p className="text-gray-400 text-sm">Loading jobs…</p>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm">
            Could not load jobs: {error}. Is <code>python api.py</code> running?
          </div>
        )}

        {!loading && !error && (
          <>
            <p className="text-sm text-gray-400 mb-4">
              {filtered.length} of {jobs.length} jobs match your filters
              {trackedUrls.size > 0 && ` (${trackedUrls.size} applied hidden)`}
            </p>

            <div className="grid gap-3">
              {filtered.map(job => (
                <JobCard
                  key={job.url}
                  job={job}
                  onApply={() => markApplied(job)}
                />
              ))}

              {filtered.length === 0 && (
                <div className="text-center py-16 text-gray-400">
                  <p className="text-3xl mb-2">🔍</p>
                  <p className="text-sm">No jobs match the current filters.</p>
                  <p className="text-xs mt-1">Try relaxing some of the filter settings.</p>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
