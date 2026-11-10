// Tests for the app's "requires Dutch" rule (passesDutchRequirement in src/constants/filters.js).
// It must give the same answers as passes_dutch_requirement in filters.py on plain text.
// Run with: npm test   (fake postings only)

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { passesDutchRequirement } from '../src/constants/filters.js'

const DROPPED = [
  'Fluent in Dutch',
  'fluent Dutch',
  'Native Dutch speaker',
  'You are fluent in both Dutch and English',
  'Excellent command of Dutch, written and verbal',
  'Must speak Dutch',
  'You speak and write Dutch fluently',
  'Strong communication skills in English and Dutch',
  'Very good Dutch and English skills',
  'Dutch: fluent',
  'Languages: Dutch and English (fluent)',
  'Native-level Dutch',
  'Dutch (C1)',
  'Dutch is mandatory',
  'Requirements:\n- Fluent in Dutch',
  'What we ask: fluent Dutch',
  'Fluent in Dutch and English, knowledge of German is a plus',
  'Fluent Dutch required, plus 2 years of Python',
]

const KEPT = [
  'Nice to have: fluent Dutch',
  'Nice to haves\n- Fluent in Dutch',
  'Preferred qualifications:\n- Proficiency in Dutch',
  'Bonus points: you speak Dutch',
  "You don't need to speak Dutch",
  'You don’t need to speak Dutch',
  'Knowledge of Dutch is not a prerequisite',
  'Fluent English required, Dutch is a plus',
  'knowledge of the Dutch market',
  'proficiency in Dutch payroll regulations',
  'excellent Dutch pension scheme',
  'We speak Dutch and English in the office',
  'Our team speaks Dutch and English',
  'Support our Dutch-speaking customers',
]

test('drops postings that require Dutch', () => {
  for (const d of DROPPED) assert.equal(passesDutchRequirement('Data Engineer', d), false, d)
})

test('keeps postings where Dutch is optional or only an adjective', () => {
  for (const d of KEPT) assert.equal(passesDutchRequirement('Data Engineer', d), true, d)
})
