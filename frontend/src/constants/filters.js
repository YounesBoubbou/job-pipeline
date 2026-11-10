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

/**
 * "Dutch" meant as the language, not as an adjective, same as _DUTCH_LANGUAGE in config.py:
 * "fluent in Dutch" and "fluent Dutch, written and spoken" count, "the Dutch market" does not.
 */
const DUTCH_LANGUAGE = String.raw`dutch(?=\s*(?:$|[,().!?;:]|(?:language|and\s+english|&\s*english|is|are|written|spoken|both` +
  String.raw`|fluently|skills|speakers?|at|as|level|required|mandatory|essential)\b))`

/**
 * A part of a sentence saying Dutch is required, same as DUTCH_REQUIRED in config.py:
 * "fluent in Dutch", "Dutch is a must", "Dutch (C1)", "Dutch: fluent", "Nederlands vereist".
 * Matched on lowercase text with "-" turned into " " and the ":" after "Dutch", "English" or
 * "Language(s)" dropped. Bare "Dutch speaking" is left out on purpose, so "our Dutch-speaking
 * customers" is kept.
 */
export const DUTCH_REQUIRED = new RegExp([
  String.raw`(?:fluent|fluency|proficient|proficiency|command|knowledge|mastery)\s+(?:in|of)\s+(?:(?:both|the|english|and|&|,)\s*)*` + DUTCH_LANGUAGE,
  String.raw`(?:fluent|native|excellent|proficient|business level|native level)\s+` + DUTCH_LANGUAGE,
  String.raw`(?<!\bwe )(?<!team )\b(?:speak|write|master)\s+(?:(?:and|&|write|fluent|the)\s+)*` + DUTCH_LANGUAGE,
  String.raw`skills\s+in\s+(?:(?:both|english|and|&|,)\s*)*` + DUTCH_LANGUAGE,
  String.raw`dutch\s+(?:and|&)\s+english\s+(?:language\s+)?skills`,
  String.raw`dutch\s*(?:at\s+)?\(?\s*[abc][12]\b`,
  String.raw`dutch\s*(?:(?:and|&)\s*english\s*)?[:(]?\s*(?:fluent|native)\b`,
  String.raw`dutch\s+(?:native\s+)?speaker\b|dutch\s+(?:language\s+)?(?:skills|proficiency|fluency)`,
  String.raw`(?:english\s+(?:and|&)\s+)?dutch(?:\s+(?:and|&)\s+english)?\s+(?:(?:speaking|language|skills)\s+)*(?:is|are)\s+(?:a\s+)?(?:must|required|mandatory|essential|requirement)`,
  String.raw`dutch\s+(?:required|mandatory|essential)`,
  String.raw`nederlands\w*\s+(?:is\s+)?(?:vereist|verplicht)|vloeiend\s+nederlands|nederlandstalig`,
].join('|'))

/**
 * Whole words that make Dutch only a wish, so the job is kept, same as DUTCH_OPTIONAL in
 * config.py. They count in the comma-separated part that names Dutch, or in the heading above.
 */
export const DUTCH_OPTIONAL = [
  'plus', 'pluses', 'nice to have', 'nice to haves', 'advantage', 'advantageous', 'bonus',
  'preferred', 'preferable', 'preferably', 'ideally', 'desirable', 'beneficial', 'helpful',
  'optional', 'welcome', 'asset', 'or not', 'not required', 'not a requirement',
  'not necessary', 'not needed', 'not mandatory', 'not a must', 'not essential',
  'not a prerequisite', "don't need", 'do not need', 'no need', "don't have to",
  'do not have to', "don't require", 'does not require', 'no dutch', 'pluspunt',
]

const OPTIONAL_WORDS = DUTCH_OPTIONAL.map(p => new RegExp(String.raw`\b${p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\b`))
const saysOptional = text => OPTIONAL_WORDS.some(re => re.test(text))

/** Only the comma-separated parts naming Dutch count: in "Fluent in Dutch, German is a plus" the "plus" is about German. */
function dutchIsOptional(segment) {
  const clauses = segment.split(',')
  const dutchClauses = clauses.filter(c => c.includes('dutch') || c.includes('nederlands'))
  return (dutchClauses.length ? dutchClauses : clauses).some(saysOptional)
}

/**
 * Same rule as passes_dutch_requirement in filters.py, on plain text (the app only has a
 * plain-text snippet). False if a part of the posting asks for Dutch and neither that part
 * nor the heading above it calls Dutch optional. A heading is a label ending in ":"
 * ("Nice to have:", "What we ask:") or a short line that isn't a list item ("Requirements").
 * A heading on its own line covers the lines below it, up to the next heading; a label with
 * text after it covers the rest of its line.
 */
export function passesDutchRequirement(title, description = '') {
  const text = `${title}\n${description}`.toLowerCase().replace(/\u2019/g, "'").replace(/_/g, ' ')
    .replace(/[•·]/g, '\n- ')
  let sectionOptional = false   // under a heading like "Nice to have", until the next heading
  for (let line of text.split('\n')) {
    const isItem = /^\s*(?:[-*–+]|\d+[.)])(?:\s|$)/.test(line)
    line = line.replace(/-/g, ' ').replace(/\b(dutch|english|languages?)\s*:/g, '$1 ')
    const segments = (line.match(/[^.!?;:]+[.!?;:]?/g) || []).map(s => s.trim()).filter(Boolean)
    let optional = sectionOptional
    for (const [i, segment] of segments.entries()) {
      const required = DUTCH_REQUIRED.test(segment)
      const shortLine = !isItem && segments.length === 1 && segment.split(/\s+/).length <= 5 &&
        !'.!?;'.includes(segment[segment.length - 1]) && !required
      if (segment.endsWith(':') || shortLine) {
        optional = saysOptional(segment)
        if (i === segments.length - 1) sectionOptional = optional
      }
      if (required && !optional && !dutchIsOptional(segment)) return false
    }
  }
  return true
}

export const EDU_INCLUDE = ['master', 'msc', 'm.sc']

export const DEFAULT_FILTERS = {
  roles:      [],
  seniority:  true,
  language:   true,
  indSponsor: true,   // W4: sponsors only is on by default
  education:  false,
}
