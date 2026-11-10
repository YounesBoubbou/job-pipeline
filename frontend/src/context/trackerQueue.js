/**
 * trackerQueue — plain functions behind the tracker's "unsent changes" queue.
 *
 * Kept free of React and localStorage so they can be tested with Node alone
 * (see frontend/tests/trackerQueue.test.js).
 *
 * A "change" is one thing the user did that the Google Sheet must learn about:
 *   { id, type: 'add',    entry: { title, company, url, date_applied, status } }
 *   { id, type: 'status', url, status }
 * Changes are kept in the order they were made, oldest first.
 */

// Today's date as YYYY-MM-DD in the browser's own time zone.
// (toISOString() would give the UTC date, which is yesterday's date in the
// Netherlands between midnight and 01:00, or 02:00 in summer.)
export function localDate(d = new Date()) {
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// Apply changes to a list of tracker rows and return the new list.
// - An add is skipped when a row with the same url is already there.
// - A status change overwrites the status of the row with that url, so a
//   change the Sheet has not received yet wins over the Sheet's older status.
// Applying the same change twice gives the same result, so it is safe to
// merge the queue into a list that already contains some of it.
export function mergeUnsent(rows, changes) {
  let out = rows.map(r => ({ ...r }))
  for (const change of changes) {
    if (change.type === 'add') {
      if (!out.some(r => r.url === change.entry.url)) out.push({ ...change.entry })
    } else if (change.type === 'status') {
      out = out.map(r => (r.url === change.url ? { ...r, status: change.status } : r))
    }
  }
  return out
}

// Send queued changes to the Sheet, one by one, in order.
//   sheetRows — the rows the Sheet returned just now (used to skip repeats)
//   send      — async function that sends one change; throws if refused
//   onSent    — called with a change's id once the Sheet has it, so the
//               caller can drop it from the stored queue straight away
// Stops at the first change the Sheet refuses, so later changes never
// overtake earlier ones (a status change must not reach the Sheet before the
// row it belongs to). Returns true if every change went through.
export async function replayQueue(queue, sheetRows, send, onSent) {
  const knownUrls = new Set(sheetRows.map(r => r.url))
  for (const change of queue) {
    // Never add the same job twice: the Sheet may already have this row
    // (for example, an earlier send got through but its answer was lost).
    const isRepeat = change.type === 'add' && knownUrls.has(change.entry.url)
    if (!isRepeat) {
      try {
        await send(change)
      } catch {
        return false
      }
      if (change.type === 'add') knownUrls.add(change.entry.url)
    }
    onSent(change.id)
  }
  return true
}
