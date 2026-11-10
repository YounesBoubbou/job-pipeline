/**
 * FilterBar — sticky left sidebar with all 5 filter controls.
 * Below 768px (phones) it becomes a full-width panel above the job list,
 * folded away behind a "Filters" button so the jobs stay on screen.
 */

import { useState } from 'react'
import { DEFAULT_FILTERS, ROLE_MAP } from '../constants/filters.js'

const ROLES = Object.keys(ROLE_MAP)

export default function FilterBar({ filters, onChange, totalShown, totalJobs }) {
  const [open, setOpen] = useState(false)   // phone fold-out only; always open from 768px

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
    <aside className="w-full md:w-60 md:shrink-0 bg-white border-b md:border-b-0 md:border-r border-gray-200
                      md:sticky md:top-[49px] md:overflow-y-auto md:h-[calc(100vh-49px)]">

      {/* Phone-only fold-out button */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="md:hidden w-full flex items-center justify-between gap-3 px-4 py-3 text-sm"
      >
        <span className="font-semibold text-gray-800">
          Filters{activeFilterCount > 0 && ` (${activeFilterCount} on)`}
        </span>
        <span className="text-gray-500">
          {totalShown} of {totalJobs} shown {open ? '▴' : '▾'}
        </span>
      </button>

      <div className={`${open ? 'block' : 'hidden'} md:block px-4 pb-4 md:p-5`}>
        {/* Header */}
        {/* On phones the fold-out button already says "Filters" */}
        <div className="flex items-center justify-end md:justify-between mb-4">
          <h2 className="hidden md:block font-semibold text-gray-800 text-sm">Filters</h2>
          {activeFilterCount > 0 && (
            <button
              onClick={clearAll}
              className="text-xs text-blue-600 hover:underline px-2 py-2.5 -my-2.5 md:p-0 md:m-0"
            >
              Clear ({activeFilterCount})
            </button>
          )}
        </div>

        {/* ── Role type ──────────────────────────────────────────── */}
        <Section label="Role Type">
          <div className="space-y-2">
            {ROLES.map(role => (
              <label key={role} className="flex items-center gap-2 cursor-pointer group py-1.5 md:py-0">
                <input
                  type="checkbox"
                  checked={filters.roles.includes(role)}
                  onChange={() => toggleRole(role)}
                  className="h-5 w-5 md:h-3.5 md:w-3.5 shrink-0 rounded border-gray-300 text-blue-600 cursor-pointer"
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

// The whole row is the switch, so on a phone the tap target is the full row, not the 20px knob
function Toggle({ label, sublabel, checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="w-full flex items-start justify-between gap-3 text-left cursor-pointer rounded-md
        py-1 md:py-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <span className="min-w-0">
        <span className="block text-sm text-gray-700 font-medium leading-tight">{label}</span>
        {sublabel && <span className="block text-xs text-gray-400 mt-0.5 leading-tight">{sublabel}</span>}
      </span>

      {/* Switch */}
      <span
        aria-hidden="true"
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent
          transition-colors duration-200
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow
            transition-transform duration-200 ease-in-out
            ${checked ? 'translate-x-4' : 'translate-x-0'}`}
        />
      </span>
    </button>
  )
}
