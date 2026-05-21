/**
 * StatusDropdown — coloured <select> for application status.
 * Used in the Tracker view.
 */

const STATUS_OPTIONS = [
  'Applied',
  'Waiting for answer',
  'Got interview',
  'Rejected',
  'Ghosted',
  'Withdrawn',
]

// Tailwind classes per status (bg + text + border)
const STATUS_STYLE = {
  'Applied':            'bg-blue-50   text-blue-700   border-blue-200',
  'Waiting for answer': 'bg-yellow-50 text-yellow-700 border-yellow-200',
  'Got interview':      'bg-green-50  text-green-700  border-green-200',
  'Rejected':           'bg-red-50    text-red-700    border-red-200',
  'Ghosted':            'bg-gray-100  text-gray-600   border-gray-200',
  'Withdrawn':          'bg-gray-50   text-gray-400   border-gray-200',
}

export default function StatusDropdown({ value, onChange }) {
  const colorClass = STATUS_STYLE[value] ?? 'bg-gray-50 text-gray-600 border-gray-200'

  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={`text-xs font-medium border rounded-md px-2 py-1 cursor-pointer
        focus:outline-none focus:ring-2 focus:ring-blue-400 transition-colors
        ${colorClass}`}
    >
      {STATUS_OPTIONS.map(opt => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  )
}
