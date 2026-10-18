/** Server-ranked, public game records. Legacy offline Field Board data stays stored. */
import { useEffect, useMemo, useState } from 'react'
import { BadgeCheck, Trophy, Users } from 'lucide-react'
import catalog from '../../data/mission-catalog.json'
import { formatFrames } from '../../lib/leaderboard'
import { fetchGameBoards, type MissionBoard } from '../../lib/game-board'

type MissionTab = { id: string; title: string; stage?: string; act?: number }

export default function LeaderboardPage() {
  const [boards, setBoards] = useState<MissionBoard[]>([])
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout>
    let controller: AbortController
    async function refresh() {
      controller = new AbortController()
      const deadline = setTimeout(() => controller.abort(), 10_000)
      try {
        const result = await fetchGameBoards(controller.signal)
        if (active) { setBoards(result); setError(''); setLoaded(true) }
      } catch (e) { if (active) setError((e as Error).name === 'AbortError' ? 'The leaderboard timed out. Retrying automatically.' : (e as Error).message) }
      finally { clearTimeout(deadline); if (active) timer = setTimeout(() => void refresh(), 30_000) }
    }
    void refresh()
    return () => { active = false; clearTimeout(timer); controller?.abort() }
  }, [])

  // Catalog missions first, then any other mission the server has verified runs for.
  const missions = useMemo<MissionTab[]>(() => {
    const tabs: MissionTab[] = catalog.missions.map((m) => ({ id: m.id, title: m.title, stage: m.stage, act: m.act }))
    const known = new Set(tabs.map((t) => t.id))
    for (const board of boards) {
      if (!known.has(board.mission) && board.rows.length > 0) {
        known.add(board.mission)
        tabs.push({ id: board.mission, title: board.title })
      }
    }
    return tabs
  }, [boards])
  const [selected, setSelected] = useState<string>(catalog.missions[0]?.id ?? '')
  const mission = missions.find((m) => m.id === selected) ?? missions[0]
  const rows = boards.find(b => b.mission === mission?.id)?.rows ?? []
  const counts = new Map(boards.map(b => [b.mission, b.rows.length]))

  return <div className="board-page leaderboard-page">
    <header className="board-topline leaderboard-topline"><div className="leaderboard-title-row"><span className="leaderboard-emblem"><Trophy size={22}/></span><div><div className="eyebrow"><Trophy size={14}/> CAMPUS RECORD BOARD · GATOR PASS</div><h1>Leaderboards</h1><p>Compare server-timed runs across campus missions.</p></div></div><span className="leaderboard-live"><i/> UPDATES EVERY 30s</span></header>
    <div className="lb-layout">
      <nav className="lb-missions" aria-label="Missions">
        {missions.map((m) => <button key={m.id} className={`lb-mission ${m.id === mission?.id ? 'is-selected' : ''}`} onClick={() => setSelected(m.id)} aria-pressed={m.id === mission?.id}>
          <span className="lb-mission-world">{m.stage ?? 'Campus'} <i>·</i> {m.act ? `ACT ${String(m.act).padStart(2, '0')}` : 'NEW MISSION'}</span><strong>{m.title}</strong><small>{counts.get(m.id) ?? 0} RANKED TEAMS</small>
        </button>)}
      </nav>
      <main>
        <section className="lb-card" aria-labelledby="verified-title">
          <div className="section-heading"><div><span className="section-index"><BadgeCheck size={13}/> VERIFIED</span><h2 id="verified-title">{mission?.title}</h2></div><span className="tiny-caption">BEST RUN PER TEAM</span></div>
          <p className="lb-note">{mission?.id === 'swamp_chorus' ? 'Co-op runs are timed by the hosted server. Solo rhythm mode awards a grade rather than a verified time.' : 'Timed by the hosted game server; every player was logged in with Gator Pass.'}</p>
          {error && <p role="status" className="lb-note">{error}{loaded ? ' Showing the last loaded results.' : ''}</p>}
          {!loaded && !error ? <div className="lb-empty">Loading the board…</div>
            : !loaded ? <div className="lb-empty">Results could not be loaded.</div> : rows.length === 0 ? <div className="lb-empty">No verified runs yet. Play this mission on the hosted server, log in with <code>/login</code>, and finish a round.</div>
            : <ol className="lb-rows">{rows.map((row) => <li key={`${row.names.join('|')}-${row.frames}`} className="lb-row">
                <span className="lb-rank">{row.rank}</span>
                <span className="lb-names">{row.names.join(' & ')}{row.players > 1 && <em><Users size={12}/> co-op</em>}</span>
                <span className="lb-time">{formatFrames(row.frames)}</span>
                <span className="lb-retries">{row.retries} {row.retries === 1 ? 'retry' : 'retries'}</span>
              </li>)}</ol>}
        </section>
      </main>
    </div>
  </div>
}
