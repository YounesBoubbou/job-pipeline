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
 * A range counts by its lower end, so "2-3 years" and "2 - 3 years" are kept.
 */
const NUM = '(?:[3-9]|[1-9]\\d|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)'
// Any number, for the top end of a range: "3-5", "three to five"
const ANY_NUM = '(?:\\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)'
// "three (3) years": the number repeated in brackets
const PAREN = '(?:\\s*\\(\\d+\\))?'
// "years", "yrs", "years'", "years’" (straight or curly apostrophe)
const YRS = "(?:years?|yrs?)\\b['\\u2019]?"
// Not the top end of a range ("2-3", "2 - 3", "2 to 3", "2 or 3"), not the decimal
// part of "1.5", and not a ceiling ("less than 3", "under 3", "up to 3")
const NOT_RANGE_END = '(?<![\\d\\-\\u2013.])(?<![\\-\\u2013]\\s)(?<![\\-\\u2013]\\s\\s)(?<!to\\s)(?<!or\\s)' +
  '(?<!less than\\s)(?<!under\\s)\\b'
const RANGE = `\\s*(?:[\\-\\u2013]|to)\\s*${ANY_NUM}`
export const YEARS_REQUIRED = new RegExp(
  // "3+ years", "5 plus years", "3 or more years": always a minimum
  `${NOT_RANGE_END}${NUM}${PAREN}\\s*(?:\\+|plus|or\\s+more)\\s*${YRS}` +
  // "3-5 years", "5–7 yrs", "three to five years": a range of years is a requirement
  `|${NOT_RANGE_END}${NUM}${RANGE}[\\s\\-]*${YRS}` +
  // "3 years of experience", "three (3) years experience", "4 yrs' hands-on experience"
  `|${NOT_RANGE_END}${NUM}${PAREN}[\\s\\-]*${YRS}\\s+(?:of\\s+)?(?:\\S+\\s+){0,2}?experience` +
  // "at least 3 years", "minimum of three (3) years", "min. 4 yrs"
  `|\\b(?:at\\s+least|minimum(?:\\s+of)?|min\\.?)\\s+${NUM}${PAREN}(?:${RANGE})?\\s*(?:\\+\\s*)?${YRS}`
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
