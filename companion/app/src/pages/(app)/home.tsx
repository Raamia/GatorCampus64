import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Building2, Gamepad2, MapPin, Sparkles, Users } from 'lucide-react'
import catalog from '../../data/mission-catalog.json'
import { studyFetch } from '../../lib/study-api'

type Mission = (typeof catalog.missions)[number]
const catalogMissions = catalog.missions as Mission[]
const campusStages = [...new Set(catalogMissions.map((mission) => mission.stage))]

export default function HomePage() {
  const [selected, setSelected] = useState<Mission | null>(null)
  const [hint, setHint] = useState('')
  const choose = async (mission: Mission) => {
    setSelected(mission)
    setHint('')
    try {
      const response = await studyFetch('/api/study/dispatcher', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ missionId: mission.id }),
      })
      const data = await response.json() as { text?: string }
      setHint(data.text ?? mission.hint)
    } catch {
      setHint(mission.hint)
    }
  }

  return <main className="hub-wrap">
    <section className="hub-hero run-board-hero">
      <div className="hub-copy">
        <div className="hub-kicker"><Gamepad2 size={16}/> NATIVE CO-OP GAME <span>·</span> UF CAMPUS</div>
        <h1>Pick a mission.<br/><em>Make your mark.</em></h1>
        <p>Choose a campus challenge and finish it in game. On the hosted server, sign in with Gator Pass using /login to have your completed run recorded on the leaderboard.</p>
        <div className="hub-actions"><Link className="primary-action" to="/play"><Gamepad2 size={17}/> How to launch the game <ArrowUpRight size={16}/></Link></div>
        <p className="hub-footnote"><MapPin size={13}/> Reitz Union and Marston Library interiors, plus the outdoor campus.</p>
      </div>
      <aside className="level-select run-board-summary" aria-label="Campus mission summary">
        <div className="level-select-top"><span><Gamepad2 size={14}/> CAMPUS MISSION BOARD</span><span>7 CAMPUS MISSIONS</span></div>
        <div className="run-summary-content">
          <div><strong>02</strong><span>ENTERABLE<br/>INTERIORS</span></div>
          <i aria-hidden="true"/>
          <div><strong>07</strong><span>CAMPUS<br/>MISSIONS</span></div>
        </div>
        <div className="level-select-bottom"><span><span className="status-lamp"/> IN-GAME RECORDS</span><span>GATOR PASS</span></div>
      </aside>
    </section>

    <section className="campus-stages" aria-labelledby="campus-stages-title">
      <div className="campus-stages-heading"><div><span className="section-index">THREE LOCATIONS · SEVEN MISSIONS</span><h2 id="campus-stages-title">Choose a mission</h2></div><span className="run-log-count">7 CAMPUS CHALLENGES</span></div>
      <div className="stage-grid">{campusStages.map((stage, index) => {
        const missions = catalogMissions.filter((mission) => mission.stage === stage)
        return <article className="stage-card" key={stage}>
          <div className="stage-card-top"><span className={`stage-icon ${index === 1 ? 'blue' : ''}`}><Building2 size={17}/></span><span>{String(index + 1).padStart(2, '0')} · {stage.toUpperCase()}</span><span>{missions.length} {missions.length === 1 ? 'MISSION' : 'MISSIONS'}</span></div>
          <ul>{missions.map((mission) => <li className={mission.minimumPlayers > 1 ? 'stage-coop' : undefined} key={mission.id}>
            <button className="run-mission-select" onClick={() => void choose(mission)} aria-pressed={selected?.id === mission.id}>
              <span className="run-act">{String(mission.act).padStart(2, '0')}</span><strong>{mission.title}</strong>
              <small>{mission.id === 'swamp_chorus' ? 'SOLO / CO-OP' : mission.minimumPlayers > 1 ? <><Users size={11}/> CO-OP</> : 'SOLO'}</small>
            </button>
          </li>)}</ul>
        </article>
      })}</div>
      <p className="stage-boundary"><MapPin size={13}/> The buildings are enterable; the surrounding campus is an outdoor game world.</p>
    </section>

    <section className="individual-runs" aria-labelledby="run-log-title">
      <div className="run-log-heading"><div><span className="section-index">RECORDED IN GAME</span><h2 id="run-log-title">Chase your next record</h2></div><p>Finish a mission on the hosted server while signed in with <code>/login</code>. Your time and retries are recorded when the round ends.</p></div>
      {selected && <section className="selected-run"><div><span className="section-index">SELECTED MISSION</span><h3>{selected.title}</h3><p>{hint || selected.objective}</p><span className="reported-label"><Sparkles size={13}/> {selected.id === 'swamp_chorus' ? 'RHYTHM MISSION · SOLO OR CO-OP' : selected.minimumPlayers > 1 ? 'CO-OP MISSION · PLAY WITH A TEAMMATE' : 'SOLO MISSION'}</span></div><Link className="primary-action" to="/play"><Gamepad2 size={16}/>Play in game</Link></section>}
      <Link className="primary-action" to="/leaderboard">View recorded runs <ArrowUpRight size={16}/></Link>
    </section>
  </main>
}
