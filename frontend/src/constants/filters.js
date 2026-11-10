/** Shared filter constants — imported by both JobBrowser and FilterBar. */

export const ROLE_MAP = {
  'AI Engineer':       ['ai engineer', 'artificial intelligence engineer'],
  'Software Engineer': ['software engineer'],
  'Data Scientist':    ['data scientist'],
  'Data Engineer':     ['data engineer'],
  'ML Engineer':       ['ml engineer', 'machine learning engineer'],
}

/** Whole words, checked against the title only — same rule as filters.py. */
export const SENIORITY_EXCLUDE = [
  'senior', 'sr', 'lead', 'principal', 'staff', 'head of',
  'manager', 'director',
]

export const EXPERIENCE_EXCLUDE = ['3+ years', '4+ years', '5+ years', '7+ years', '10+ years']

/**
 * 3 or more years of experience asked, same rule as _YEARS_REQUIRED in filters.py:
 * "3+ years", "3-5 years of experience", "at least three years", "min. 4 yrs".
 * A range counts by its lower end, so "2-3 years" is kept.
 */
const NUM = '(?:[3-9]|[1-9]\\d|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)'
const YRS = "(?:years?|yrs?)\\b'?"
const NOT_RANGE_END = '(?<![\\d\\-\\u2013])(?<!to\\s)(?<!or\\s)\\b'
const RANGE = '(?:\\s*(?:[\\-\\u2013]|to)\\s*(?:\\d+|[a-z]+))?'
export const YEARS_REQUIRED = new RegExp(
  `${NOT_RANGE_END}${NUM}\\s*(?:\\+|plus)\\s*${YRS}` +
  `|${NOT_RANGE_END}${NUM}${RANGE}\\s*${YRS}\\s+(?:of\\s+)?(?:\\S+\\s+){0,2}?experience` +
  `|\\b(?:at\\s+least|minimum(?:\\s+of)?|min\\.?)\\s+${NUM}${RANGE}\\s*(?:\\+\\s*)?${YRS}`
)

export const DUTCH_EXCLUDE = [
  'dutch', 'nederlands', 'fluent in dutch', 'native dutch',
]

export const EDU_INCLUDE = ['master', 'msc', 'm.sc']

export const DEFAULT_FILTERS = {
  roles:      [],
  seniority:  true,
  language:   true,
  indSponsor: true,   // W4: sponsors only is on by default
  education:  false,
}
