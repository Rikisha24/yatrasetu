import { useCallback, useEffect, useRef, useState } from 'react'
import { api, sleep } from './util.js'
import { Chat, DraftModal, Header, LogPanel, MetricsPanel, ProfileModal, SimPanel, Stage, TripCard } from './components.jsx'

const fresh = () => ({
  phase: 'idle', scn: null, impact: null, ranked: [], removed: [], expl: {}, payload: null, constraints: null,
  log: [], steps: null, prompt: null, chosen: null, done: null, busy: false,
})
const sessionId = Math.random().toString(36).slice(2, 10)
const PACE = [500, 500, 550, 450, 500, 350] // narration pauses so viewers can follow the agent

export default function App() {
  const [boot, setBoot] = useState(null)
  const [profile, setProfile] = useState(null)
  const [S, setS] = useState(fresh())
  const [scnKey, setScnKey] = useState('cancel')
  const [fDrift, setFDrift] = useState(false)
  const [fFail, setFFail] = useState(false)
  const [metrics, setMetrics] = useState(null)
  const [showProfile, setShowProfile] = useState(false)
  const [draft, setDraft] = useState(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [msgs, setMsgs] = useState([{ who: 'a', t: "Hi Priya, I'm YatraSetu. Ask me about your trip, refunds or why an option was chosen." }])
  const ov = useRef({})
  const t0 = useRef(0)
  const decide = useRef(null)
  const busyRef = useRef(false)
  const patch = useCallback((p) => setS((s) => ({ ...s, ...(typeof p === 'function' ? p(s) : p) })), [])
  const addLog = useCallback((l) => setS((s) => ({ ...s, log: [...s.log, l] })), [])
  const refreshMetrics = useCallback(() => api.metrics(sessionId).then(setMetrics).catch(() => {}), [])

  useEffect(() => {
    api.bootstrap().then((b) => { setBoot(b); setProfile(b.profile) })
    refreshMetrics()
  }, [refreshMetrics])

  const apply = (rec) => patch({
    ranked: rec.ranked, removed: rec.removed, expl: rec.expl, payload: rec.payload, constraints: rec.constraints,
    impact: rec.impact, phase: rec.phase,
  })

  async function runScenario(key) {
    if (busyRef.current) return
    busyRef.current = true
    ov.current = {}
    const rec = await api.recover({ scenario: key, overrides: {}, session: sessionId })
    setS({ ...fresh(), phase: 'detect', scn: rec.scenario, busy: true })
    for (let i = 0; i < rec.log.length; i++) {
      const e = rec.log[i]
      addLog(e)
      if (e.mark === 't0') t0.current = performance.now()
      if (e.reveal === 'impact') patch({ impact: rec.impact })
      await sleep(PACE[i] ?? 0)
    }
    apply(rec)
    patch({ busy: false, constraints: rec.constraints })
    busyRef.current = false
    refreshMetrics()
  }

  async function play(timeline, names) {
    for (let i = 0; i < timeline.length; i++) {
      const ev = timeline[i]
      patch({ steps: names.map((n, k) => ({ n, st: ev.steps[k] })) })
      if (ev.msg) addLog({ msg: ev.msg, k: ev.k })
      if (i < timeline.length - 1) await sleep(600)
    }
  }

  async function book(id) {
    if (busyRef.current || !S.scn) return
    const o = S.ranked.find((x) => x.id === id)
    if (!o) return
    busyRef.current = true
    const secs = (performance.now() - t0.current) / 1000
    patch({ busy: true, chosen: o, phase: 'booking', steps: null })
    const base = { scenario: S.scn.key, overrides: ov.current, option_id: id, simulate_drift: fDrift, simulate_fail: fFail, secs, session: sessionId }
    let res = await api.book(base)
    await play(res.timeline, res.steps)
    if (res.status === 'needs_price_approval') {
      patch({ prompt: { from: res.from, to: res.to } })
      const ok = await new Promise((r) => { decide.current = r })
      patch({ prompt: null })
      res = await api.book({ ...base, drift_accepted: ok })
      await play(res.timeline, res.steps)
    }
    if (res.status === 'declined') patch({ phase: 'options', steps: null, busy: false })
    else if (res.status === 'rolled_back') patch({ phase: 'rollback', busy: false })
    else patch({ phase: 'done', busy: false, done: { kind: 'booked', ref: res.ref, o: res.option, secs, delta: res.delta } })
    busyRef.current = false
    refreshMetrics()
  }

  async function acceptKeep() {
    const secs = (performance.now() - t0.current) / 1000
    await api.keep({ scenario: S.scn.key, overrides: ov.current, secs, session: sessionId })
    addLog({ msg: 'Kept original booking. Notices ready. Tracking continues.', k: 'g' })
    patch({ phase: 'done', done: { kind: 'keep', secs } })
    refreshMetrics()
  }

  function reset() {
    ov.current = {}
    busyRef.current = false
    setS(fresh())
  }

  async function ask(q) {
    setMsgs((m) => [...m, { who: 'u', t: q }])
    const res = await api.chat({ message: q, scenario: S.scn ? S.scn.key : null, overrides: ov.current, session: sessionId })
    ov.current = res.overrides
    if (res.recovery) {
      busyRef.current = true
      patch({ busy: true })
      res.recovery.log.forEach(addLog)
      await sleep(500)
      apply(res.recovery)
      patch({ busy: false })
      busyRef.current = false
      refreshMetrics()
    }
    setMsgs((m) => [...m, { who: 'a', t: res.reply }])
  }

  async function openDraft(kind, title) {
    const optId = (S.done && S.done.o && S.done.o.id) || (S.chosen && S.chosen.id) || null
    const r = await api.draft({ kind, scenario: S.scn.key, overrides: ov.current, option_id: optId, session: sessionId })
    setDraft({ title, text: r.text })
  }
  async function openSupport() {
    const r = await api.support({ scenario: S.scn.key, overrides: ov.current, session: sessionId })
    setDraft({ title: 'Support handoff summary', text: r.text })
  }

  async function saveProfile(p) {
    const saved = await api.saveProfile(p)
    setProfile(saved)
    addLog({ msg: 'Profile defaults updated.' })
  }
  async function deleteProfile() {
    const d = await api.deleteProfile()
    setProfile(d)
    addLog({ msg: 'Saved profile deleted. Defaults restored.', k: 'w' })
    return d
  }

  if (!boot || !profile) return <div className="p-8 text-muted">Loading YatraSetu…</div>
  const ctx = { boot, profile, S, ovBudget: ov.current.budget, book, acceptKeep, reset, openDraft, openSupport, runScenario, scnKey, decide }

  return (
    <>
      <Header profile={profile} onProfile={() => setShowProfile(true)} />
      <main className="grid lg:grid-cols-[360px_1fr] gap-[18px] px-5 py-[18px] max-w-[1280px] mx-auto">
        <aside className="flex flex-col gap-3.5">
          <TripCard trip={boot.trip} S={S} />
          <SimPanel scenarios={boot.scenarios} scnKey={scnKey} setScnKey={setScnKey} fDrift={fDrift} setFDrift={setFDrift}
            fFail={fFail} setFFail={setFFail} onRun={() => runScenario(scnKey)} onReset={reset} />
          <LogPanel log={S.log} />
          <MetricsPanel m={metrics} />
        </aside>
        <section className="flex flex-col gap-3.5 min-w-0" aria-live="polite">
          <Stage {...ctx} onHero={() => { setScnKey('cancel'); runScenario('cancel') }} />
        </section>
      </main>
      <button className="fixed right-5 bottom-5 z-30 bg-gold text-[#1b1500] rounded-full px-[18px] py-3 font-bold shadow-2xl"
        aria-expanded={chatOpen} onClick={() => setChatOpen((o) => !o)}>💬 Ask YatraSetu</button>
      {chatOpen && <Chat msgs={msgs} suggestions={boot.suggestions} onAsk={ask} onClose={() => setChatOpen(false)} />}
      {showProfile && <ProfileModal profile={profile} onSave={saveProfile} onDelete={deleteProfile} onClose={() => setShowProfile(false)} />}
      {draft && <DraftModal d={draft} onClose={() => setDraft(null)} />}
    </>
  )
}
