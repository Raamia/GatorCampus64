import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { RecordScope, useAuthProfileReady, useMutations, useQuery } from 'deepspace'
import { ArrowDownRight, ArrowUpRight, Copy, Flag, MapPin, Radio, Sparkles, Users } from 'lucide-react'
import catalog from '../../data/mission-catalog.json'
import { missionEventsSchema } from '../../schemas/mission-events-schema'

type Mission = (typeof catalog.missions)[number]
type MissionEvent = {
  eventType: 'squad_opened' | 'mission_selected' | 'mission_result'
  missionId: string
  teamSize: number
  durationSeconds: number
  retries: number
  displayName: string
  occurredAt: string
}
const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
const catalogMissions = catalog.missions as Mission[]

function makeCode() {
  const bytes = new Uint8Array(12)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join('')
}

export default function HomePage() {
  const [room, setRoom] = useState(() => {
    if (typeof window === 'undefined') return ''
    return window.localStorage.getItem('gator-squad-code') ?? ''
  })
  const [joinCode, setJoinCode] = useState('')
  const [selected, setSelected] = useState<Mission | null>(null)
  const [hint, setHint] = useState('')
  const [resultOpen, setResultOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const { isSignedIn } = useAuthProfileReady({ requireUser: true })

  const startSquad = async () => {
    const code = makeCode()
    window.localStorage.setItem('gator-squad-code', code)
    setRoom(code)
  }
  const enterSquad = () => {
    const code = joinCode.toUpperCase().replace(/[^A-Z2-9]/g, '').slice(0, 12)
    if (code.length !== 12) return
    window.localStorage.setItem('gator-squad-code', code)
    setRoom(code)
  }

  if (!room) return <div className="board-wrap"><section className="welcome-card">
    <div className="eyebrow"><MapPin size={15}/> SUPER GATORLATOR 64 · UNIVERSITY OF FLORIDA</div>
    <h1>Choose your next<br/><em>campus mission.</em></h1>
    <p>Plan a campus run with your squad for the native SM64CoopDX game. Log player-reported results here; the hosted game server supplies verified leaderboard times.</p>
    <div className="welcome-actions">
      <button className="primary-action" onClick={startSquad}><Users size={17}/> Start a squad <ArrowUpRight size={16}/></button>
      <div className="join-row"><input aria-label="Squad code" placeholder="Enter squad code" maxLength={12} value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase())}/><button onClick={enterSquad} disabled={joinCode.length !== 12}>Join squad <ArrowDownRight size={16}/></button></div>
    </div>
    <div className="privacy-note"><span/> No account needed to browse. Sign in to post a run. Squad code is your private invite.</div>
    <p className="welcome-links">New here? <Link to="/play">Get the game</Link> · <Link to="/gatorize">Make your gator</Link></p>
  </section><aside className="welcome-aside"><div className="map-graphic"><div className="map-grid"/><div className="route route-one"/><div className="route route-two"/><span className="pin pin-a"/><span className="pin pin-b"/><span className="pin pin-c"/><span className="map-label label-a">REITZ UNION</span><span className="map-label label-b">MARSTON</span><span className="map-label label-c">THE QUAD</span><div className="map-caption"><span>FIELD NOTES · 01</span><strong>Two corners<br/>of campus. One<br/>good afternoon.</strong></div></div><div className="aside-foot"><span>GAINESVILLE, FL</span><span>29° 38′ N · 82° 21′ W</span></div></aside></div>
  return <RecordScope roomId={`squad:${room}`} schemas={[missionEventsSchema]} isolated><SquadBoard code={room} signedIn={isSignedIn} selected={selected} setSelected={setSelected} hint={hint} setHint={setHint} resultOpen={resultOpen} setResultOpen={setResultOpen} copied={copied} setCopied={setCopied}/></RecordScope>
}

function SquadBoard({ code, signedIn, selected, setSelected, hint, setHint, resultOpen, setResultOpen, copied, setCopied }: {
  code: string; signedIn: boolean; selected: Mission | null; setSelected: (m: Mission | null) => void;
  hint: string; setHint: (h: string) => void; resultOpen: boolean; setResultOpen: (b: boolean) => void;
  copied: boolean; setCopied: (b: boolean) => void
}) {
  const { records, status } = useQuery<MissionEvent>('mission_events', { orderBy: 'occurredAt', orderDir: 'desc', limit: 200 })
  const { createConfirmed, ready } = useMutations<MissionEvent>('mission_events')
  const { isSignedIn: currentSignedIn } = useAuthProfileReady({ requireUser: true })
  const events = records.map((r) => r.data)
  const results = events.filter((e) => e.eventType === 'mission_result')
  const lastRun = results[0]
  const addEvent = async (event: MissionEvent) => {
    if (!currentSignedIn || !ready) return
    await createConfirmed(event)
  }
  const choose = async (mission: Mission) => {
    setSelected(mission); setHint('')
    void addEvent({ eventType: 'mission_selected', missionId: mission.id, teamSize: 0, durationSeconds: 0, retries: 0, displayName: '', occurredAt: new Date().toISOString() })
    try {
      const response = await fetch('/api/study/dispatcher', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ missionId: mission.id }) })
      const data = await response.json() as { text?: string }
      setHint(data.text ?? mission.hint)
    } catch { setHint(mission.hint) }
  }
  const share = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true); window.setTimeout(() => setCopied(false), 1800)
  }
  return <div className="board-page">
    <header className="board-topline"><div><div className="eyebrow"><Radio size={14}/> SUPER GATORLATOR 64 · SQUAD LIVE</div><h1>Mission board</h1></div><button className="invite-button" onClick={share}><Copy size={15}/>{copied ? 'Copied' : 'Invite squad'}<span>{code}</span></button></header>
    <div className="field-layout"><main>
      <div className="section-heading"><div><span className="section-index">01 / PICK A RUN</span><h2>Choose your mission</h2></div><span className="tiny-caption">6 CAMPUS CHALLENGES</span></div>
      <div className="mission-grid">{catalogMissions.map((mission) => <button className={`mission-card ${selected?.id === mission.id ? 'is-selected' : ''}`} key={mission.id} onClick={() => void choose(mission)}>
        <div className="mission-meta"><span>{mission.stage}</span><span>ACT {String(mission.act).padStart(2, '0')}</span></div><h3>{mission.title}</h3><p>{mission.objective}</p><div className="mission-foot"><span><Users size={13}/> {mission.minimumPlayers === 2 ? '2 players' : '1+ players'}</span><span className="card-arrow">↗</span></div>
      </button>)}</div>
      {selected && <section className="selected-run"><div><span className="section-index">YOUR CURRENT RUN</span><h2>{selected.title}</h2><p>{hint || 'Finding a route note…'}</p><span className="reported-label"><Sparkles size={13}/> GAMEPLAY GUIDANCE · CATALOG BASED</span></div><button className="primary-action" disabled={!signedIn} title={!signedIn ? 'Sign in to add a report to this squad' : undefined} onClick={() => setResultOpen(true)}><Flag size={16}/>{signedIn ? 'Log a result' : 'Sign in to log'}</button></section>}
    </main><aside className="activity-column">
      <section className="activity-card"><div className="section-heading compact"><div><span className="section-index">02 / SQUAD PULSE</span><h2>On the board</h2></div><span className="live-dot"/></div>
        <div className="stat-row"><strong>{results.length.toString().padStart(2, '0')}</strong><span>reported<br/>runs</span><i/></div>
        {lastRun ? <div className="last-run"><span>LATEST REPORT</span><strong>{catalogMissions.find((m) => m.id === lastRun.missionId)?.title ?? 'Campus mission'}</strong><p>{lastRun.durationSeconds}s · {lastRun.teamSize} players · {lastRun.retries} retries</p></div> : <div className="empty-activity">{status === 'loading' ? 'Connecting to your squad…' : 'No runs reported yet. Be the first to add one.'}</div>}
      </section>
      <section className="board-note"><span>FIELD NOTE</span><p>Runs are player-reported. The board is a shared log, not an automatic game tracker.</p><div className="note-rule"/><small>ONE CAMPUS · MANY WAYS UP</small></section>
      <button className="leave-squad" onClick={() => { window.localStorage.removeItem('gator-squad-code'); window.location.reload() }}>Leave this squad</button>
    </aside></div>
    {resultOpen && <ResultDialog mission={selected} onClose={() => setResultOpen(false)} onSubmit={async (duration, team, retries) => { if (!selected) return; const occurredAt = new Date().toISOString(); const event = { eventType: 'mission_result' as const, missionId: selected.id, teamSize: team, durationSeconds: duration, retries, displayName: '', occurredAt }; await addEvent(event); void fetch('/api/study/events', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ eventId: crypto.randomUUID(), ...event }) }); setResultOpen(false) }}/ >}
    {!signedIn && <div className="signin-hint">Sign in using the account menu to add a shared run.</div>}
  </div>
}

function ResultDialog({ mission, onClose, onSubmit }: { mission: Mission | null; onClose: () => void; onSubmit: (duration: number, team: number, retries: number) => Promise<void> }) {
  const [duration, setDuration] = useState('')
  const [team, setTeam] = useState(String(mission?.minimumPlayers ?? 1))
  const [retries, setRetries] = useState('0')
  const valid = duration.trim() !== '' && Number(duration) >= 0 && Number.isInteger(Number(duration)) && Number(team) >= (mission?.minimumPlayers ?? 1) && Number(team) <= 4 && Number.isInteger(Number(retries)) && Number(retries) >= 0 && Number(retries) <= 100
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className="result-dialog" role="dialog" aria-modal="true" aria-labelledby="result-title" onClick={(e) => e.stopPropagation()}><button className="modal-close" onClick={onClose} aria-label="Close">×</button><span className="section-index">PLAYER REPORTED</span><h2 id="result-title">Log your run</h2><p>{mission?.title}</p><label>Time in seconds<input type="number" min="0" max="7200" value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="e.g. 184"/></label><div className="form-pair"><label>Players<input type="number" min={mission?.minimumPlayers ?? 1} max="4" value={team} onChange={(e) => setTeam(e.target.value)}/></label><label>Retries<input type="number" min="0" max="100" value={retries} onChange={(e) => setRetries(e.target.value)}/></label></div><p className="privacy-note dialog-note">Use no real names or personal details. This report is visible to anyone with the squad code.</p><button className="primary-action submit-run" disabled={!valid} onClick={() => void onSubmit(Number(duration), Number(team), Number(retries))}>Add to squad log <ArrowUpRight size={16}/></button></section></div>
}
