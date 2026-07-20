/**
 * JobCard — displays a single job listing with badges, snippet, and actions.
 */

import { useState } from 'react'

// Generation calls the Claude API and can take a while — no client-side timeout.
async function generateDocument(endpoint, url) {
  const res = await fetch(endpoint, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ url }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

function download(filename, content) {
  const blob = new Blob([content], { type: 'text/plain' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

export default function JobCard({ job, onApply }) {
  const [cvState, setCvState] = useState({ status: 'idle' })       // idle | loading | done | error
  const [letterState, setLetterState] = useState({ status: 'idle' })

  async function handleGenerateCv() {
    setCvState({ status: 'loading' })
    try {
      const { filename, tex } = await generateDocument('/api/jobs/generate-cv', job.url)
      setCvState({ status: 'done', filename, content: tex })
    } catch (err) {
      setCvState({ status: 'error', message: err.message })
    }
  }

  async function handleGenerateCoverLetter() {
    setLetterState({ status: 'loading' })
    try {
      const { filename, letter } = await generateDocument('/api/jobs/generate-cover-letter', job.url)
      setLetterState({ status: 'done', filename, content: letter })
    } catch (err) {
      setLetterState({ status: 'error', message: err.message })
    }
  }

  const indColor = {
    Yes:     'bg-green-100 text-green-700 border-green-200',
    No:      'bg-red-100  text-red-700   border-red-200',
    Unknown: 'bg-gray-100 text-gray-500  border-gray-200',
  }[job.ind_sponsor] ?? 'bg-gray-100 text-gray-500 border-gray-200'

  // Werkzoeken / Indeed → blue; company career pages → purple
  const isJobBoard = ['Indeed', 'Werkzoeken'].some(s =>
    (job.source || '').includes(s)
  )
  const sourceColor = isJobBoard
    ? 'bg-blue-100 text-blue-700 border-blue-200'
    : 'bg-purple-100 text-purple-700 border-purple-200'

  return (
    <article className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow group">
      {/* ── Header row ── */}
      <div className="flex items-start gap-3">
        {/* Title + company */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 leading-snug truncate" title={job.title}>
            {job.title}
          </h3>
          <p className="text-sm text-gray-500 mt-0.5 truncate">
            {[job.company, job.location].filter(Boolean).join(' · ')}
          </p>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-1.5 shrink-0 flex-wrap justify-end">
          <Badge className={indColor}>
            IND {job.ind_sponsor || 'Unknown'}
          </Badge>
          {job.source && (
            <Badge className={sourceColor}>{job.source}</Badge>
          )}
        </div>
      </div>

      {/* ── Description snippet ── */}
      {job.description_snippet && (
        <p className="mt-2.5 text-sm text-gray-500 line-clamp-2 leading-relaxed">
          {job.description_snippet}
        </p>
      )}

      {/* ── Footer row ── */}
      <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
        <span className="text-xs text-gray-400">
          Found {job.date_found || '—'}
        </span>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          <GenerateButton
            label="Tailor CV"
            state={cvState}
            onClick={handleGenerateCv}
          />
          <GenerateButton
            label="Cover Letter"
            state={letterState}
            onClick={handleGenerateCoverLetter}
          />
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium hover:underline"
          >
            Apply →
          </a>
          <button
            onClick={onApply}
            className="text-sm bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white
              px-3 py-1.5 rounded-lg font-medium transition-colors"
          >
            ✓ Mark as Applied
          </button>
        </div>
      </div>

      {/* ── Generated document panels ── */}
      <ResultPanel state={cvState} onClose={() => setCvState({ status: 'idle' })} />
      <ResultPanel state={letterState} onClose={() => setLetterState({ status: 'idle' })} />
    </article>
  )
}

function GenerateButton({ label, state, onClick }) {
  const loading = state.status === 'loading'
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="text-sm bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-700
        px-3 py-1.5 rounded-lg font-medium transition-colors disabled:opacity-60 disabled:cursor-wait"
    >
      {loading ? '⏳ Generating…' : `✨ ${label}`}
    </button>
  )
}

function ResultPanel({ state, onClose }) {
  if (state.status === 'error') {
    return (
      <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm flex items-start justify-between gap-3">
        <span>Generation failed: {state.message}</span>
        <button onClick={onClose} className="text-red-400 hover:text-red-600 shrink-0">✕</button>
      </div>
    )
  }

  if (state.status !== 'done') return null

  return (
    <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-sm font-medium text-gray-700 truncate" title={state.filename}>
          {state.filename}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => navigator.clipboard.writeText(state.content)}
            className="text-xs text-gray-500 hover:text-gray-800 font-medium"
          >
            Copy
          </button>
          <button
            onClick={() => download(state.filename, state.content)}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            Download
          </button>
          <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
        </div>
      </div>
      <pre className="text-xs text-gray-600 bg-white border border-gray-200 rounded p-2 max-h-48 overflow-auto whitespace-pre-wrap">
        {state.content}
      </pre>
    </div>
  )
}

function Badge({ className, children }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${className}`}>
      {children}
    </span>
  )
}
