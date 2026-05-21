/**
 * JobCard — displays a single job listing with badges, snippet, and actions.
 */

export default function JobCard({ job, onApply }) {
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
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-xs text-gray-400">
          Found {job.date_found || '—'}
        </span>

        <div className="flex items-center gap-2">
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
    </article>
  )
}

function Badge({ className, children }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${className}`}>
      {children}
    </span>
  )
}
