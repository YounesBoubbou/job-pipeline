// Tests for the "3 or more years" rule (YEARS_REQUIRED in src/constants/filters.js),
// which mirrors _YEARS_REQUIRED in filters.py. JobBrowser tests it on lowercased text.
// Run with: npm test

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { YEARS_REQUIRED } from '../src/constants/filters.js'

const asks3Plus = text => YEARS_REQUIRED.test(text.toLowerCase())

test('excludes 3 or more years of experience', () => {
  for (const text of [
    '3+ years of experience',
    '3-5 years of experience',
    '3 to 5 years of experience',
    'At least three (3) years',
    "3 years’ experience",
    '3-5 years of experience on a contract basis',
    'Between 3 and 5 years of experience',
    'Between three and five years of experience',
    'More than 3 years of experience',
    'Minimum of 3 years of experience',
    '3-5 years of contract experience',
    '3-5 years experience, contract type: permanent',
    '3-5 years experience contract',
  ]) assert.ok(asks3Plus(text), text)
})

test('keeps contract lengths, ranges starting below 3, and ceilings', () => {
  for (const text of [
    '2-3 years of experience',
    '1.5 years of experience',
    'A 3-year contract',
    'A 3-5 year contract',
    'A 3 to 5 year fixed-term contract',
    "3-5 years' contract, 2 years of experience",
    'Between 1 and 3 years of experience',
    'Between 2 and 3 years of experience',
    'Between one and three years of experience',
    'Max 3 years of experience',
    'Max. 3 years of experience',
    'No more than 3 years of experience',
    'Not more than 3 years of experience',
    'Maximum of 3 years of experience',
    'Maximum 3 years experience',
    '3-5 year (fixed-term) contract',
    'MBO 4 and 2 years of experience',
    'Python 3 and 1 year of experience',
    'Team of 5 and 2 years of experience',
  ]) assert.ok(!asks3Plus(text), text)
})
