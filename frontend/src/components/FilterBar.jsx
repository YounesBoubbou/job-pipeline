/**
 * FilterBar — sticky left sidebar with all 5 filter controls.
 */

import { DEFAULT_FILTERS, ROLE_MAP } from '../pages/JobBrowser.jsx'

const ROLES = Object.keys(ROLE_MAP)

export default function FilterBar({ filters, onChange, totalShown, totalJobs }) {
  function toggleRole(role) {
    onChange(prev => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter(r => r !== role)
        : [...prev.roles, role],
    }))
  }

  function toggle(key) {
    onChange(prev => ({ ...prev, [key]: !prev[key] }))
  }

  function clearAll() {
    onChange(DEFAULT_FILTERS)
  }

  const activeFilterCount =
    filters.roles.length +
    (filters.seniority  ? 1 : 0) +
    (filters.language   ? 1 : 0) +
    (filters.indSponsor ? 1 : 0) +
    (filters.education  ? 1 : 0)

  return (
    <aside className="w-60 shrink-0 bg-white border-r border-gray-200 p-5 sticky top-[49px] overflow-y-auto"
           style={{ height: 'calc(100vh - 49px)' }}>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-800 text-sm">Filters</h2>
        {activeFilterCount > 0 && (
          <button
            onClick={clearAll}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear ({activeFilterCount})
          </button>
        )}
      </div>

      {/* ── Role type ──────────────────────────────────────────── */}
      <Section label="Role Type">
        <div className="space-y-2">
          {ROLES.map(role => (
            <label key={role} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.roles.includes(role)}
                onChange={() => toggleRole(role)}
                className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-gray-700 group-hover:text-gray-900 leading-tight">
                {role}
              </span>
            </label>
          ))}
        </div>
        {filters.roles.length === 0 && (
          <p className="text-xs text-gray-400 mt-2">All role types shown</p>
        )}
      </Section>

      {/* ── Hard filters (exclude) ──────────────────────────────── */}
      <Section label="Exclude">
        <div className="space-y-3">
          <Toggle
            label="Entry-level only"
            sublabel="Hides senior / lead / manager titles"
            checked={filters.seniority}
            onChange={() => toggle('seniority')}
          />
          <Toggle
            label="No Dutch required"
            sublabel="Hides listings requiring Dutch"
            checked={filters.language}
            onChange={() => toggle('language')}
          />
        </div>
      </Section>

      {/* ── Show-only filters (include) ─────────────────────────── */}
      <Section label="Show Only">
        <div className="space-y-3">
          <Toggle
            label="IND sponsors"
            sublabel="Only visa-sponsoring companies"
            checked={filters.indSponsor}
            onChange={() => toggle('indSponsor')}
          />
          <Toggle
            label="MSc-friendly"
            sublabel="Mentions master's / MSc degree"
            checked={filters.education}
            onChange={() => toggle('education')}
          />
        </div>
      </Section>

      {/* ── Footer count ─────────────────────────────────────────── */}
      <div className="mt-4 pt-4 border-t border-gray-100 text-xs text-gray-400">
        {totalShown} of {totalJobs} jobs shown
      </div>
    </aside>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Section({ label, children }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2.5">
        {label}
      </p>
      {children}
    </div>
  )
}

function Toggle({ label, sublabel, checked, onChange }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-sm text-gray-700 font-medium leading-tight">{label}</p>
        {sublabel && <p className="text-xs text-gray-400 mt-0.5 leading-tight">{sublabel}</p>}
      </div>

      {/* Switch button */}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent
          transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}`}
      >
        <span
          aria-hidden="true"
          className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow
            transition-transform duration-200 ease-in-out
            ${checked ? 'translate-x-4' : 'translate-x-0'}`}
        />
      </button>
    </div>
  )
}
