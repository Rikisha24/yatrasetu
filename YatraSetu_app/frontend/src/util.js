export const inr = (n) => '₹' + Math.round(n).toLocaleString('en-IN')
export const hm = (m) => {
  const d = Math.floor(m / 1440)
  m = ((m % 1440) + 1440) % 1440
  return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0') + (d > 0 ? ' +1d' : '')
}
export const dur = (m) => Math.floor(m / 60) + 'h ' + (m % 60) + 'm'
export const FAST = /[?&]fast=1/.test(location.search)
export const sleep = (ms) => new Promise((r) => setTimeout(r, FAST ? 0 : ms))
export const STX = { ok: 'On track', warn: 'At risk', bad: 'Broken' }

async function call(path, method = 'GET', body) {
  const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error(path + ' ' + r.status)
  return r.json()
}
export const api = {
  bootstrap: () => call('/api/bootstrap'),
  recover: (b) => call('/api/recover', 'POST', b),
  book: (b) => call('/api/book', 'POST', b),
  keep: (b) => call('/api/keep', 'POST', b),
  chat: (b) => call('/api/chat', 'POST', b),
  draft: (b) => call('/api/draft', 'POST', b),
  support: (b) => call('/api/support', 'POST', b),
  metrics: (s) => call('/api/metrics?session=' + s),
  saveProfile: (p) => call('/api/profile', 'PUT', p),
  deleteProfile: () => call('/api/profile', 'DELETE'),
}
