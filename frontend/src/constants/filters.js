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
// Not the top end of a range ("2-3", "2 - 3", "2 to 3", "2 or 3", "between 1 and 3"),
// not the decimal part of "1.5", and not a ceiling ("less than 3", "under 3", "up to 3",
// "max 3", "maximum of 3", "no more than 3", "at most 3")
const NOT_RANGE_END = '(?<![\\d\\-\\u2013.])(?<![\\-\\u2013]\\s)(?<![\\-\\u2013]\\s\\s)(?<!to\\s)(?<!or\\s)' +
  '(?<!between\\s\\d\\sand\\s)(?<!between\\s\\d\\.\\d\\sand\\s)' +
  '(?<!between\\sone\\sand\\s)(?<!between\\stwo\\sand\\s)' +
  '(?<!less than\\s)(?<!under\\s)(?<!max\\s)(?<!max\\.\\s)(?<!maximum\\s)' +
  '(?<!maximum of\\s)(?<!no more than\\s)(?<!not more than\\s)(?<!at most\\s)\\b'
// "3-5", "3 to 5" ("and" only counts after "between", so "MBO 4 and 2 years" is no range)
const RANGE = `\\s*(?:[\\-\\u2013]|to)\\s*${ANY_NUM}`
// Not the length of a contract: "a 3-5 year contract", "3-5 year (fixed-term) contract",
// at most one word in between and not "of"/"experience", so "3-5 years of contract
// experience" and "3-5 years experience, contract: permanent" still count
const NOT_CONTRACT = "(?!['\\u2019]?[\\s\\-]+(?:(?!of\\b|experience\\b)\\(?[a-z\\-]+\\)?\\s+)?" +
  'contract\\b(?!\\s+experience))'
export const YEARS_REQUIRED = new RegExp(
  // "3+ years", "5 plus years", "3 or more years": always a minimum
  `${NOT_RANGE_END}${NUM}${PAREN}\\s*(?:\\+|plus|or\\s+more)\\s*${YRS}` +
  // "3-5 years", "5–7 yrs", "three to five years": a range of years is a requirement,
  // unless it is the length of a contract
  `|${NOT_RANGE_END}${NUM}${RANGE}[\\s\\-]*${YRS}${NOT_CONTRACT}` +
  // "between 3 and 5 years", "between three and five years"
  `|\\bbetween\\s+${NUM}${PAREN}\\s+and\\s+${ANY_NUM}[\\s\\-]*${YRS}${NOT_CONTRACT}` +
  // "3 years of experience", "three (3) years experience", "4 yrs' hands-on experience"
  `|${NOT_RANGE_END}${NUM}${PAREN}[\\s\\-]*${YRS}\\s+(?:of\\s+)?(?:\\S+\\s+){0,2}?experience` +
  // "at least 3 years", "minimum of three (3) years", "min. 4 yrs"
  `|\\b(?:at\\s+least|minimum(?:\\s+of)?|min\\.?)\\s+${NUM}${PAREN}(?:${RANGE})?\\s*(?:\\+\\s*)?${YRS}`
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
