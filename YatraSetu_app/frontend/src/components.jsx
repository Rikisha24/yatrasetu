import { useEffect, useRef, useState } from 'react'
import { STX, dur, hm, inr } from './util.js'

/* ---------------------------------------------------------------- header + sidebar */

export function Header({ profile, onProfile }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 border-b border-line bg-[#0c1327] sticky top-0 z-20">
      <div className="flex items-center gap-2.5 font-bold text-lg tracking-wide">
        <div className="w-8 h-8 rounded-lg bg-gold text-[#1b1500] grid place-items-center font-extrabold">Y</div>
        <div>YatraSetu<small className="block font-normal text-muted text-xs tracking-normal">Travel disruption recovery agent · PS 4.1</small></div>
      </div>
      <div className="flex items-center gap-2.5 flex-wrap sm:justify-end">
        <span className="chip text-muted whitespace-normal">Prototype · mock travel data · sandbox booking</span>
        <button className="btn" onClick={onProfile}>👤 {profile.name.split(' ')[0]} · Profile &amp; defaults</button>
      </div>
    </header>
  )
}

export function TripCard({ trip, S }) {
  const items = S.impact || []
  const done = S.done && S.done.kind === 'booked'
  return (
    <section className="card" aria-label="Trip">
      <h2>Priya's trip · Delhi → Mumbai</h2>
      {trip.bookings.map((b, idx) => {
        const it = items.find((i) => i.id === b.id)
        let st = it ? it.st : 'ok', label = it ? STX[st] : 'On track', title = b.label, sub = b.sub
        if (done && S.done.o) {
          const o = S.done.o
          st = 'ok'; label = 'On track'
          if (b.id === 'F1' && o.kind !== 'hotel') { title = o.name; sub = `Day 1 · ${hm(o.dep)} → ${hm(o.arr)}`; label = 'Rebooked' }
          if (b.id === 'H1' && o.kind === 'hotel') { title = o.name; sub = `Day 1 · ${o.dist} km from venue`; label = 'Rebooked' }
          else if (b.id === 'H1' && o.arr + 45 > b.checkin) { st = 'warn'; label = 'Late check-in' }
        }
        if (S.done && S.done.kind === 'keep') {
          if (b.id === 'H1') { st = 'warn'; label = 'Notice sent' } else { st = 'ok'; label = 'On track' }
          if (b.id === 'F1') { st = 'warn'; label = 'Delayed, kept' }
        }
        return (
          <div key={b.id} className={`grid grid-cols-[34px_1fr_auto] gap-2.5 items-center py-2 ${idx ? 'border-t border-line' : ''}`}>
            <div className="w-[34px] h-[34px] rounded-lg bg-panel2 grid place-items-center text-[17px]" aria-hidden="true">{b.icon}</div>
            <div><b className="block text-sm">{title}</b><span className="text-muted text-[12.5px]">{sub}</span></div>
            <span className={`chip chip-${st}`}>{label}</span>
          </div>
        )
      })}
    </section>
  )
}

export function SimPanel({ scenarios, scnKey, setScnKey, fDrift, setFDrift, fFail, setFFail, onRun, onReset }) {
  return (
    <section className="card" aria-label="Simulate">
      <h2>Simulate a disruption</h2>
      <label className="lbl" htmlFor="scn">Scenario</label>
      <select id="scn" className="field" value={scnKey} onChange={(e) => setScnKey(e.target.value)}>
        {Object.entries(scenarios).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <label className="flex gap-2 items-center text-[13px] mt-2"><input type="checkbox" id="fDrift" checked={fDrift} onChange={(e) => setFDrift(e.target.checked)} /> Price rises at re-check (+₹300)</label>
      <label className="flex gap-2 items-center text-[13px] mt-1.5"><input type="checkbox" id="fFail" checked={fFail} onChange={(e) => setFFail(e.target.checked)} /> Hotel update fails (shows rollback)</label>
      <div className="flex gap-2.5 mt-2.5">
        <button className="btn btn-primary flex-1" id="btnRun" onClick={onRun}>⚡ Trigger disruption</button>
        <button className="btn flex-1" id="btnReset" onClick={onReset}>Reset</button>
      </div>
      <p className="note mt-2">In production this trigger is a push from airline / railway status feeds.</p>
    </section>
  )
}

export function LogPanel({ log }) {
  const ref = useRef(null)
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight }, [log])
  const col = { w: 'text-amber', b: 'text-bad', g: 'text-ok' }
  return (
    <section className="card" aria-label="Agent activity">
      <h2>Agent activity</h2>
      <div ref={ref} id="log" className="max-h-[250px] overflow-auto font-mono text-xs flex flex-col gap-1.5" aria-live="polite">
        {log.length === 0 && <div className="pl-3.5 relative text-[#c6d0ee] before:content-['›'] before:absolute before:left-0 before:text-gold">Idle. Monitoring 4 bookings…</div>}
        {log.map((l, i) => (
          <div key={i} className={`pl-3.5 relative before:content-['›'] before:absolute before:left-0 before:text-gold ${col[l.k] || 'text-[#c6d0ee]'}`}>{l.msg}</div>
        ))}
      </div>
    </section>
  )
}

export function MetricsPanel({ m }) {
  const k = m || {}
  const cells = [
    [k.lastSecs != null ? k.lastSecs.toFixed(1) + 's' : '–', 'last time to approved plan'],
    [k.avgSecs != null ? k.avgSecs.toFixed(1) + 's' : '–', `average over ${k.recoveries || 0} run${k.recoveries === 1 ? '' : 's'}`],
    [k.lastDelta == null ? '–' : (k.lastDelta >= 0 ? '+' : '−') + inr(Math.abs(k.lastDelta)), 'net cost vs original'],
    [k.evaluated ? k.removed + '/' + k.evaluated : '–', 'options removed by rules'],
    [k.recoveries ? Math.round(100 * k.topAccepted / k.recoveries) + '%' : '–', 'top pick accepted'],
    [k.fallbacks || 0, 'human handovers'],
  ]
  return (
    <section className="card" aria-label="Metrics">
      <h2>Session metrics</h2>
      <div className="grid grid-cols-2 gap-2">
        {cells.map(([v, l]) => (
          <div key={l} className="bg-panel2 rounded-[10px] px-2.5 py-2"><b className="block font-mono text-lg text-gold">{v}</b><span className="text-[11.5px] text-muted">{l}</span></div>
        ))}
      </div>
      <p className="note mt-2">Recovery time is measured in this session. Manual baseline (~45 min) is our assumption, to be validated.</p>
    </section>
  )
}

/* ---------------------------------------------------------------- main stage */

const Alert = ({ icon, title, children, kind = '' }) => (
  <div className={`alert ${kind}`}><div className="text-[26px]">{icon}</div><div><h2 className="m-0 text-[17px]">{title}</h2>{children}</div></div>
)

function Impact({ items, trip }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(230px,1fr))] gap-2.5">
      {items.map((i) => {
        const b = trip.bookings.find((x) => x.id === i.id)
        return (
          <div key={i.id} className="bg-panel2 rounded-[10px] px-3 py-2.5 text-[13.5px]">
            <b className="flex justify-between gap-2 mb-0.5"><span>{b.icon} {b.label}</span><span className={`chip chip-${i.st}`}>{STX[i.st]}</span></b>
            <span className="text-muted">{i.text}</span>
          </div>
        )
      })}
    </div>
  )
}

function OptCard({ o, i, S, onBook }) {
  const e = S.expl[o.id]
  if (!e) return null
  const t3 = S.ranked.slice(0, 3)
  const isHotel = o.kind === 'hotel'
  let tag = 'Best overall'
  if (i > 0) {
    if (isHotel) tag = o.dist === Math.min(...t3.map((x) => x.dist)) ? 'Closest to meeting' : 'Cheaper alternative'
    else if (o.price === Math.min(...t3.map((x) => x.price))) tag = 'Cheapest of the top 3'
    else if (o.arr === Math.min(...t3.map((x) => x.arr))) tag = 'Arrives earliest'
    else tag = 'Alternative'
  }
  const g = S.constraints.group
  const pressure = isHotel ? null : o.seats <= g + 1 ? <span className="chip chip-bad">only {o.seats} left, book first</span>
    : o.seats <= g + 3 ? <span className="chip chip-warn">filling fast</span> : <span className="chip chip-ok">{o.seats} seats</span>
  const d = o.net
  return (
    <article className={`grid grid-cols-[44px_1fr_auto] max-md:grid-cols-[36px_1fr] gap-3.5 bg-panel2 border rounded-2xl px-4 py-3.5 ${i === 0 ? 'border-gold shadow-[0_0_0_1px_rgba(242,184,75,.25)]' : 'border-line'}`}>
      <div className="w-11 h-11 rounded-[10px] bg-[#0c1429] grid place-items-center font-mono text-xl text-gold" aria-label={'Rank ' + (i + 1)}>{i + 1}</div>
      <div>
        <div className="flex gap-1.5 flex-wrap">
          <span className={`chip ${i === 0 ? 'chip-ok' : 'chip-info'}`}>{tag}</span>{pressure}
          {isHotel ? (o.freeCancel ? <span className="chip chip-ok">free cancellation</span> : <span className="chip chip-warn">non-refundable</span>)
            : <span className="chip chip-info">{o.mode === 'multi' ? 'multi-leg' : o.mode}</span>}
        </div>
        <h4 className="mt-2 mb-0.5 text-base font-semibold">{o.name}</h4>
        <div className="font-mono text-xl tracking-wider">
          {isHotel ? <>{o.dist} km <small className="text-muted text-xs tracking-normal">from venue · ★ {o.rating}</small></>
            : <>{hm(o.dep)} → {hm(o.arr)} <small className="text-muted text-xs tracking-normal">{dur(o.arr - o.dep)}</small></>}
        </div>
        <p className="mt-1.5 text-sm text-[#cfd7f1]">{e.text}</p>
        <p className={`text-[12.5px] ${e.verified ? 'text-ok' : 'text-muted'}`}>
          {e.verified ? '✓ numbers verified against data' : '⚠ numbers could not be verified'}{e.src === 'llm' ? ' · written by the AI model' : ''}
        </p>
        <div className="h-1.5 bg-[#0c1429] rounded-md overflow-hidden mt-2" title={`score ${o.score}/100`}><i className="block h-full bg-gold" style={{ width: o.score + '%' }} /></div>
        <div className="text-[12.5px] text-muted mt-1">Score {o.score}/100 · cost {Math.round(o.sub.cost * 100)} · time {Math.round(o.sub.time * 100)} · comfort {Math.round(o.sub.comfort * 100)} · availability {Math.round(o.sub.risk * 100)}</div>
      </div>
      <div className="flex flex-col gap-1.5 items-end max-md:col-span-2 max-md:items-stretch min-w-[150px]">
        <div className="font-mono text-xl">{inr(o.price)}{isHotel && <small className="text-muted"> /night</small>}</div>
        <span className="text-[12.5px] text-muted">{d >= 0 ? '+' : '−'}{inr(Math.abs(d))} net</span>
        <button className={`btn ${i === 0 ? 'btn-primary' : ''}`} data-book={o.id} disabled={S.busy} onClick={() => onBook(o.id)}>Approve &amp; book</button>
      </div>
    </article>
  )
}

function Options({ S, onBook }) {
  const c = S.constraints
  const top = S.ranked.slice(0, 3)
  return (
    <>
      <div className="card"><h3>Applied constraints</h3>
        <div className="flex gap-1.5 flex-wrap">
          <span className="chip chip-info">Budget {inr(c.budget)}{c.isHotel ? ' / night' : ' / person'}</span>
          {!c.isHotel && <span className="chip chip-info">Arrive by {c.arriveBy}</span>}
          {!c.isHotel && c.noNight && <span className="chip chip-info">No night travel</span>}
          {!c.isHotel && <span className="chip chip-info">{c.group} traveller{c.group > 1 ? 's' : ''}</span>}
          {c.isHotel && <span className="chip chip-info">Within 8 km of meeting</span>}
          {c.override && <span className="chip chip-warn">trip override active</span>}
        </div>
      </div>
      {top.map((o, i) => <OptCard key={o.id} o={o} i={i} S={S} onBook={onBook} />)}
      {S.ranked.length > 3 && (
        <details className="details"><summary>{S.ranked.length - 3} more valid option{S.ranked.length > 4 ? 's' : ''}</summary>
          {S.ranked.slice(3).map((o, i) => <p key={o.id} className="text-[12.5px]">{i + 4}. {o.name}, {inr(o.price)}{o.arr != null ? ', arrives ' + hm(o.arr) : ''} · score {o.score}</p>)}
        </details>)}
      {S.removed.length > 0 && (
        <details className="details"><summary>Why {S.removed.length} option{S.removed.length > 1 ? 's were' : ' was'} removed</summary>
          {S.removed.map((o) => <p key={o.id} className="text-[12.5px]"><b>{o.name}</b>: {o.why}</p>)}
        </details>)}
      <details className="details"><summary>What the AI sees (masked, no ID, phone or payment data)</summary>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-xs text-[#c6d0ee]">{JSON.stringify(S.payload, null, 2)}</pre>
      </details>
    </>
  )
}

function Progress({ S }) {
  return (
    <div className="card"><h3>Booking {S.chosen.name} (sandbox)</h3>
      <div className="flex flex-col gap-2">
        {(S.steps || []).map((s, i) => {
          const dot = s.st === 'ok' ? 'bg-ok text-[#04281a] border-ok' : s.st === 'fail' ? 'bg-bad text-[#2b0505] border-bad' : s.st === 'run' ? 'border-gold text-gold' : 'border-line'
          return (
            <div key={i} className="flex gap-2.5 items-center bg-panel2 px-3 py-2.5 rounded-[10px]">
              <span className={`w-[22px] h-[22px] rounded-full grid place-items-center text-xs bg-[#0c1429] border ${dot}`}>{s.st === 'ok' ? '✓' : s.st === 'fail' ? '✕' : i + 1}</span>{s.n}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function beforeAfter(S, trip) {
  const d = S.done, f = trip.bookings[0]
  if (d.kind === 'keep') {
    const nf = f.arr + S.scn.delay
    return { before: ['✈️ 6E-2041 08:00 → 10:10', '🏨 Check-in 14:00', '📅 Meeting 17:00'],
      after: [`✈️ 6E-2041 ${hm(480 + S.scn.delay)} → ${hm(nf)} (kept)`, `🏨 Late check-in ~${hm(nf + 45)} (notice sent)`, `📅 Meeting 17:00 · ${dur(1020 - (nf + 60))} spare`] }
  }
  const o = d.o
  if (o.kind === 'hotel') return { before: ['🏨 Harbour View Inn (cancelled)', '✈️ Flight unchanged', '📅 Meeting 17:00'],
    after: [`🏨 ${o.name} · ${o.dist} km from venue · ${inr(o.price)}/night`, '✈️ Flight unchanged', '📅 Meeting 17:00 · short ride'] }
  return { before: ['✈️ IndiGo 6E-2041 08:00 → 10:10 (cancelled)', '🏨 Check-in 14:00', '📅 Meeting 17:00'],
    after: [`✈️ ${o.name} ${hm(o.dep)} → ${hm(o.arr)}`, o.arr + 45 > 840 ? `🏨 Late check-in ~${hm(o.arr + 45)} (notice drafted)` : '🏨 Check-in 14:00 still fine', `📅 Meeting 17:00 · ${dur(1020 - (o.arr + 60))} spare`] }
}

function Done({ S, boot, openDraft, reset, ovBudget }) {
  const d = S.done, scn = S.scn, o = d.o
  const x = beforeAfter(S, boot.trip)
  const delta = d.kind === 'keep' ? 0 : d.delta
  const refundable = scn.type === 'flight' && (scn.status === 'cancelled' || scn.delay / 60 >= 3)
  const actions = []
  if (d.kind === 'booked' && scn.type === 'flight' && refundable) actions.push(['refund', 'Claim refund for cancelled flight'])
  if (scn.type === 'flight' && (d.kind === 'keep' || o.arr + 45 > 840)) actions.push(['hotel', 'Tell the hotel about late check-in'])
  if (scn.type === 'hotel') actions.push(['hotel', 'Cancel the old room and ask for a refund'])
  actions.push(['client', 'Tell the client about the new timing'])
  if (d.kind === 'keep' && refundable) actions.unshift(['refund', 'Optional: request refund (delay ≥ 3 h)'])
  const ics = `/api/ics?scenario=${scn.key}&option_id=${o ? o.id : ''}&ref=${d.ref || ''}${ovBudget ? '&budget=' + ovBudget : ''}`
  return (
    <>
      <Alert icon="✅" title={d.kind === 'keep' ? 'Plan kept. Notices are ready.' : 'Recovery complete. You are rebooked.'} kind="alert-g">
        <p className="mt-0.5 text-[#d5dcf2]">{d.kind === 'keep' ? 'No new booking was needed.' : <>Booking ref <b className="font-mono">{d.ref}</b> (sandbox). Net cost vs original: <b>{delta >= 0 ? '+' : '−'}{inr(Math.abs(delta))}</b>.</>} Approved in {d.secs.toFixed(1)} s of session time.</p>
      </Alert>
      <div className="card"><h3>New itinerary</h3>
        <div className="grid md:grid-cols-2 gap-2.5">
          {[['Before', x.before], ['After', x.after]].map(([h, l]) => (
            <div key={h} className="bg-panel2 rounded-[10px] px-3 py-2.5"><h5 className="m-0 mb-1.5 text-xs text-muted uppercase tracking-wider">{h}</h5>
              <ul className="m-0 pl-4.5">{l.map((t, i) => <li key={i} className="my-1">{t}</li>)}</ul></div>
          ))}
        </div>
      </div>
      <div className="card"><h3>What you need to do</h3>
        <ul className="m-0 p-0 list-none flex flex-col gap-2">
          {actions.map((a) => (
            <li key={a[1]} className="flex gap-2.5 items-center justify-between bg-panel2 rounded-[10px] px-3 py-2">
              <span className="flex gap-2 items-center"><input type="checkbox" aria-label={a[1]} /> {a[1]}</span>
              <button className="btn btn-sm" data-draft={a[0]} onClick={() => openDraft(a[0], a[1])}>View draft</button>
            </li>
          ))}
          {d.kind === 'booked' && scn.type === 'flight' && (
            <li className="flex gap-2.5 items-center justify-between bg-panel2 rounded-[10px] px-3 py-2">
              <span className="flex gap-2 items-center"><input type="checkbox" aria-label="Add to calendar" /> Add the new flight to your calendar</span>
              <a className="btn btn-sm" id="btnIcs" href={ics}>Download .ics</a>
            </li>)}
        </ul>
        <p className="note mt-2.5">🔎 Tracking: if the new journey is delayed or cancelled, the agent restarts this flow and alerts you.</p>
      </div>
      <div className="flex justify-end"><button className="btn" id="btnAgain" onClick={reset}>Run another scenario</button></div>
    </>
  )
}

export function Stage({ boot, profile, S, book, acceptKeep, reset, openDraft, openSupport, onHero, decide, ovBudget }) {
  if (S.phase === 'idle') {
    return (
      <div className="card px-6 py-7">
        <h1 className="m-0 mb-1.5 text-[26px] font-semibold">Your trip is on track, {profile.name.split(' ')[0]}.</h1>
        <p className="m-0 mb-3.5 text-muted max-w-[60ch]">YatraSetu watches every booking. When something breaks it finds what else is affected, searches alternatives inside your rules, and prepares a new itinerary for you to approve. Nothing is booked without your approval.</p>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-2.5 my-4">
          {[['1 · Detect', 'Cancellation or delay from a status feed'], ['2 · Impact', 'Hotel, meeting and return legs checked'], ['3 · Decide', 'Rules filter, code ranks, the AI explains'], ['4 · Approve', 'Re-check, hold, confirm or roll back']].map(([a, b]) => (
            <div key={a} className="bg-panel2 rounded-[10px] px-3 py-2.5 text-[13.5px]"><b className="text-gold block mb-0.5">{a}</b>{b}</div>
          ))}
        </div>
        <button className="btn btn-primary" id="btnHero" onClick={onHero}>⚡ Simulate: flight cancelled</button>
        <span className="note">&nbsp;Nothing to type. Your saved profile is applied automatically.</span>
      </div>
    )
  }
  if (S.phase === 'done') return <Done S={S} boot={boot} openDraft={openDraft} reset={reset} ovBudget={ovBudget} />
  const t = S.scn, c = S.constraints
  return (
    <>
      <Alert icon={t.type === 'hotel' ? '🏨' : '✈️'} title={t.title} kind={t.key === 'delay4' ? 'alert-w' : ''}>
        <p className="mt-0.5 text-[#d5dcf2]">Detected just now. The agent is working through your bookings.</p>
      </Alert>
      {S.impact && <Impact items={S.impact} trip={boot.trip} />}
      {S.phase === 'options' && <Options S={S} onBook={book} />}
      {S.phase === 'keep' && (
        <>
          <Alert icon="🧠" title="Recommendation: keep your booking" kind="alert-g">
            <p className="mt-0.5 text-[#d5dcf2]">The delayed flight still lands at {hm(boot.trip.bookings[0].arr + t.delay)}, before your {c.arriveBy} deadline. Switching would only cost more. We prepared a late check-in note for the hotel and a message for your client.</p>
            <div className="mt-2.5"><button className="btn btn-good" id="btnKeep" onClick={acceptKeep}>Keep booking &amp; send notices</button></div>
          </Alert>
          <details className="details"><summary>See alternatives anyway (not needed)</summary><div className="flex flex-col gap-3.5 mt-3"><Options S={S} onBook={book} /></div></details>
        </>
      )}
      {S.phase === 'fallback' && (
        <>
          <Alert icon="🙋" title="I could not find a good option">
            <p className="mt-0.5 text-[#d5dcf2]">Every alternative breaks at least one of your hard rules. I will not force a weak option on you. Here is what I tried, and a ready summary for our support team so you do not have to repeat yourself.</p>
            <div className="mt-2.5"><button className="btn btn-primary" id="btnSupport" onClick={openSupport}>Talk to support</button></div>
          </Alert>
          <div className="card"><h3>Closest compromises (not recommended)</h3>
            {S.removed.filter((o) => !/closed/i.test(o.why)).slice(0, 3).map((o) => <p key={o.id} className="text-[12.5px]"><b>{o.name}</b> · {inr(o.price)} · breaks: {o.why}</p>)}
            {S.removed.every((o) => /closed/i.test(o.why)) && <p className="text-[12.5px] text-muted">All services are unavailable right now.</p>}
          </div>
          <details className="details"><summary>All removed options</summary>{S.removed.map((o) => <p key={o.id} className="text-[12.5px]"><b>{o.name}</b>: {o.why}</p>)}</details>
        </>
      )}
      {S.phase === 'booking' && (
        <>
          {S.chosen && S.steps && <Progress S={S} />}
          {S.prompt && (
            <Alert icon="💸" title="Price changed at re-check" kind="alert-w">
              <p className="mt-0.5 text-[#d5dcf2]">{inr(S.prompt.from)} → {inr(S.prompt.to)}. Approve the new price?</p>
              <div className="mt-2.5 flex gap-2.5">
                <button className="btn btn-good" onClick={() => decide.current && decide.current(true)}>Approve {inr(S.prompt.to)}</button>
                <button className="btn" onClick={() => decide.current && decide.current(false)}>Decline</button>
              </div>
            </Alert>)}
        </>
      )}
      {S.phase === 'rollback' && (
        <>
          <Progress S={S} />
          <Alert icon="↩️" title="Rolled back safely" kind="alert-w">
            <p className="mt-0.5 text-[#d5dcf2]">A step failed, so the hold was released and your original plan is untouched. You are never left half-booked.</p>
            <div className="mt-2.5 flex gap-2.5">
              {S.ranked.find((x) => x.id !== S.chosen.id) && <button className="btn btn-primary" onClick={() => book(S.ranked.find((x) => x.id !== S.chosen.id).id)}>Try next best: {S.ranked.find((x) => x.id !== S.chosen.id).name}</button>}
              <button className="btn" id="btnSupport" onClick={openSupport}>Talk to support</button>
            </div>
          </Alert>
        </>
      )}
    </>
  )
}

/* ---------------------------------------------------------------- chat + dialogs */

export function Chat({ msgs, suggestions, onAsk, onClose }) {
  const [v, setV] = useState('')
  const end = useRef(null)
  useEffect(() => { if (end.current) end.current.scrollTop = end.current.scrollHeight }, [msgs])
  return (
    <div className="fixed right-5 bottom-[76px] w-[360px] max-w-[calc(100vw-24px)] h-[480px] max-h-[70vh] bg-panel border border-line rounded-2xl flex flex-col z-30 shadow-2xl" role="dialog" aria-label="Help chatbot">
      <div className="flex items-center justify-between px-3.5 py-2.5 font-semibold border-b border-line"><span>YatraSetu help</span><button className="btn btn-sm" onClick={onClose} aria-label="Close chat">✕</button></div>
      <div ref={end} id="msgs" className="flex-1 overflow-auto p-3 flex flex-col gap-2">
        {msgs.map((m, i) => <div key={i} className={`max-w-[88%] px-[11px] py-2 rounded-xl text-sm whitespace-pre-wrap ${m.who === 'u' ? 'self-end bg-gold text-[#1b1500]' : 'self-start bg-panel2'}`}>{m.t}</div>)}
      </div>
      <div className="flex gap-1.5 flex-wrap px-3 pb-2">
        {suggestions.map((s) => <button key={s} type="button" className="bg-transparent border border-line text-muted rounded-full px-2.5 py-1 text-xs hover:text-ink hover:border-gold" onClick={() => onAsk(s)}>{s}</button>)}
      </div>
      <form className="flex gap-2 p-2.5 border-t border-line" onSubmit={(e) => { e.preventDefault(); const q = v.trim(); if (!q) return; setV(''); onAsk(q) }}>
        <input className="field" id="chatIn" value={v} onChange={(e) => setV(e.target.value)} placeholder="Ask anything about this trip…" autoComplete="off" aria-label="Message" />
        <button className="btn btn-primary" type="submit">Send</button>
      </form>
    </div>
  )
}

const Modal = ({ children, onClose }) => (
  <div className="fixed inset-0 z-40 bg-[#030610]/70 grid place-items-center p-4" onClick={onClose}>
    <div className="bg-panel border border-line rounded-2xl p-5 w-[min(560px,94vw)] max-h-[92vh] overflow-auto" role="dialog" onClick={(e) => e.stopPropagation()}>{children}</div>
  </div>
)

export function DraftModal({ d, onClose }) {
  const [copied, setCopied] = useState(false)
  return (
    <Modal onClose={onClose}>
      <h3 className="m-0 mb-1.5 text-lg">{d.title}</h3>
      <textarea className="field" id="dBody" rows={10} readOnly value={d.text} />
      <div className="flex gap-2.5 justify-end mt-3">
        <button className="btn" onClick={async () => { try { await navigator.clipboard.writeText(d.text); setCopied(true); setTimeout(() => setCopied(false), 1200) } catch { /* ignore */ } }}>{copied ? 'Copied ✓' : 'Copy'}</button>
        <button className="btn btn-primary" onClick={onClose}>Close</button>
      </div>
    </Modal>
  )
}

export function ProfileModal({ profile, onSave, onDelete, onClose }) {
  const [p, setP] = useState(profile)
  const set = (k, v) => setP((x) => ({ ...x, [k]: v }))
  const num = (k) => (e) => set(k, e.target.value === '' ? '' : +e.target.value)
  const weights = [['wCost', 'Cost'], ['wTime', 'Arrival time'], ['wComfort', 'Comfort'], ['wRisk', 'Seat availability']]
  return (
    <Modal onClose={onClose}>
      <h3 className="m-0 mb-1.5 text-lg">Profile &amp; defaults</h3>
      <p className="note mb-2">Entered once, reused for every trip. Change anytime; trip-level overrides never alter these.</p>
      <div className="grid grid-cols-2 gap-2.5">
        <div><label className="lbl" htmlFor="pName">Name</label><input id="pName" className="field" value={p.name} onChange={(e) => set('name', e.target.value)} /></div>
        <div><label className="lbl" htmlFor="pGroup">Travellers (default)</label><input id="pGroup" className="field" type="number" min="1" max="9" value={p.group} onChange={num('group')} /></div>
        <div><label className="lbl" htmlFor="pBudget">Max budget per traveller (₹)</label><input id="pBudget" className="field" type="number" min="500" step="100" value={p.budget} onChange={num('budget')} /></div>
        <div><label className="lbl" htmlFor="pHotel">Hotel budget / night (₹)</label><input id="pHotel" className="field" type="number" min="500" step="100" value={p.hotelBudget} onChange={num('hotelBudget')} /></div>
        <div><label className="lbl" htmlFor="pArr">Must arrive by</label><input id="pArr" className="field" type="time" value={p.arriveBy} onChange={(e) => set('arriveBy', e.target.value)} /></div>
        <div><label className="lbl" htmlFor="pMode">Preferred mode</label>
          <select id="pMode" className="field" value={p.mode} onChange={(e) => set('mode', e.target.value)}><option value="any">Any</option><option value="flight">Flight</option><option value="train">Train</option></select></div>
      </div>
      <label className="flex gap-2 items-center text-[13px] mt-2"><input type="checkbox" id="pNight" checked={p.noNight} onChange={(e) => set('noNight', e.target.checked)} /> No night travel (hard rule)</label>
      <label className="flex gap-2 items-center text-[13px] mt-1.5"><input type="checkbox" id="pConsent" checked={p.consent} onChange={(e) => set('consent', e.target.checked)} /> I consent to my trip data being used to plan recoveries (ID/payment never sent to the AI)</label>
      <div className="lbl">Ranking weights (soft preferences)</div>
      <div className="grid grid-cols-2 gap-2.5">
        {weights.map(([k, l]) => (
          <div key={k}><span className="note">{l} <b>{p[k]}</b></span><input id={k} type="range" min="0" max="100" value={p[k]} onChange={num(k)} className="w-full" /></div>
        ))}
      </div>
      <div className="flex justify-between mt-3.5">
        <button className="btn" id="btnDelete" onClick={async () => setP(await onDelete())}>Delete my data</button>
        <span className="flex gap-2"><button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" id="btnSave" onClick={async () => { await onSave({ ...p, name: p.name || 'Traveller' }); onClose() }}>Save</button></span>
      </div>
    </Modal>
  )
}
