// Tests for the tracker's unsent-changes queue (src/context/trackerQueue.js).
// Run with: npm test   (uses Node's built-in test runner, no extra packages)
// Fake data only; nothing here talks to the API or the Google Sheet.

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { localDate, mergeUnsent, replayQueue } from '../src/context/trackerQueue.js'

const row = (url, status = 'Applied') => ({
  title: 'Data Engineer', company: 'Acme', url, date_applied: '2026-11-09', status,
})
const add = (id, url) => ({ id, type: 'add', entry: row(url) })
const setStatus = (id, url, status) => ({ id, type: 'status', url, status })

// ── localDate ─────────────────────────────────────────────────────────────────

test('localDate uses the local calendar day, not the UTC one', () => {
  // 00:30 local time on 10 Nov: in any time zone east of UTC, toISOString()
  // would still say 9 Nov.
  const justAfterMidnight = new Date(2026, 10, 10, 0, 30)
  assert.equal(localDate(justAfterMidnight), '2026-11-10')
})

test('localDate pads month and day', () => {
  assert.equal(localDate(new Date(2026, 0, 5, 12)), '2026-01-05')
})

// ── mergeUnsent ───────────────────────────────────────────────────────────────

test('a queued add shows after the Sheet rows', () => {
  const out = mergeUnsent([row('a')], [add('1', 'b')])
  assert.deepEqual(out.map(r => r.url), ['a', 'b'])
})

test('a queued add for a url the Sheet already has is not shown twice', () => {
  const out = mergeUnsent([row('a')], [add('1', 'a')])
  assert.equal(out.length, 1)
})

test('a queued status change wins over the Sheet status', () => {
  const out = mergeUnsent([row('a', 'Applied')], [setStatus('1', 'a', 'Interview')])
  assert.equal(out[0].status, 'Interview')
})

test('a status change queued after an add applies to the new row', () => {
  const out = mergeUnsent([], [add('1', 'a'), setStatus('2', 'a', 'Rejected')])
  assert.deepEqual(out.map(r => [r.url, r.status]), [['a', 'Rejected']])
})

test('merging the same queue twice changes nothing', () => {
  const queue = [add('1', 'b'), setStatus('2', 'a', 'Offer')]
  const once = mergeUnsent([row('a')], queue)
  assert.deepEqual(mergeUnsent(once, queue), once)
})

test('mergeUnsent does not change the rows it is given', () => {
  const rows = [row('a')]
  mergeUnsent(rows, [setStatus('1', 'a', 'Offer')])
  assert.equal(rows[0].status, 'Applied')
})

// ── replayQueue ───────────────────────────────────────────────────────────────

test('sends every change in order and reports each one sent', async () => {
  const sent = [], done = []
  const queue = [add('1', 'b'), setStatus('2', 'b', 'Interview')]
  const ok = await replayQueue(queue, [], async c => { sent.push(c.id) }, id => done.push(id))
  assert.equal(ok, true)
  assert.deepEqual(sent, ['1', '2'])
  assert.deepEqual(done, ['1', '2'])
})

test('skips an add the Sheet already has, but still clears it from the queue', async () => {
  const sent = [], done = []
  const ok = await replayQueue([add('1', 'a')], [row('a')], async c => { sent.push(c.id) }, id => done.push(id))
  assert.equal(ok, true)
  assert.deepEqual(sent, [])
  assert.deepEqual(done, ['1'])
})

test('never sends two adds for the same url in one replay', async () => {
  const sent = []
  await replayQueue([add('1', 'a'), add('2', 'a')], [], async c => { sent.push(c.id) }, () => {})
  assert.deepEqual(sent, ['1'])
})

test('still sends a status change for a url the Sheet already has', async () => {
  const sent = []
  await replayQueue([setStatus('1', 'a', 'Offer')], [row('a')], async c => { sent.push(c.id) }, () => {})
  assert.deepEqual(sent, ['1'])
})

test('stops at the first refusal and keeps it and later changes queued', async () => {
  const done = []
  const queue = [add('1', 'a'), add('2', 'b'), setStatus('3', 'b', 'Offer')]
  const send = async c => { if (c.id === '2') throw new Error('503') }
  const ok = await replayQueue(queue, [], send, id => done.push(id))
  assert.equal(ok, false)
  assert.deepEqual(done, ['1'])
})

test('an empty queue sends nothing', async () => {
  let calls = 0
  const ok = await replayQueue([], [row('a')], async () => { calls++ }, () => {})
  assert.equal(ok, true)
  assert.equal(calls, 0)
})
