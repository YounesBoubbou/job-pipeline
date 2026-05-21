/** Shared filter constants — imported by both JobBrowser and FilterBar. */

export const ROLE_MAP = {
  'AI Engineer':       ['ai engineer', 'artificial intelligence engineer'],
  'Software Engineer': ['software engineer'],
  'Data Scientist':    ['data scientist'],
  'Data Engineer':     ['data engineer'],
  'ML Engineer':       ['ml engineer', 'machine learning engineer'],
}

export const SENIORITY_EXCLUDE = [
  'senior', 'lead', 'principal', 'staff', 'head of',
  'manager', 'director', '5+ years', '7+ years', '10+ years',
]

export const DUTCH_EXCLUDE = [
  'dutch', 'nederlands', 'fluent in dutch', 'native dutch',
]

export const EDU_INCLUDE = ['master', 'msc', 'm.sc']

export const DEFAULT_FILTERS = {
  roles:      [],
  seniority:  true,
  language:   true,
  indSponsor: false,
  education:  false,
}
