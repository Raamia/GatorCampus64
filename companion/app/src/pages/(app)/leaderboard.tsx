/**
 * Leaderboards (docs/web_platform_spec.md §10.4).
 *
 * VERIFIED board: `verified_runs`, written only by the hosted game server's API (server-timed runs,
 * every player logged in with Gator Pass). Public: anyone can read it.
 * OFFLINE runs: `solo_runs`, reported by a player's own machine (submitGameRun). Shown below the
 * verified board, labelled, for signed-in players only, and never ranked together with it.
 */
import { useMemo, useState } from 'react'
import { useAuthProfileReady, useQuery } from 'deepspace'
import { BadgeCheck, CloudOff, Trophy, Users } from 'lucide-react'
import catalog from '../../data/mission-catalog.json'
import { bestVerifiedRows, formatFrames, type VerifiedRun } from '../../lib/leaderboard'

type OfflineRun = { playerTag: string; missionId: string; elapsedFrames: number; retries: number; assisted: boolean | number }
type MissionTab = { id: string; title: string; stage?: string }

const TOP = 10

export default function LeaderboardPage() {
  const { isSignedIn } = useAuthProfileReady({ requireUser: true })
  const { records, status } = useQuery<VerifiedRun>('verified_runs', { orderBy: 'frames', orderDir: 'asc', limit: 1000 })

  // Catalog missions first, then any other mission the server has verified runs for.
  const missions = useMemo<MissionTab[]>(() => {
    const tabs: MissionTab[] = catalog.missions.map((m) => ({ id: m.id, title: m.title, stage: m.stage }))
    const known = new Set(tabs.map((t) => t.id))
    for (const r of records) {
      if (!known.has(r.data.missionId)) {
        known.add(r.data.missionId)
        tabs.push({ id: r.data.missionId, title: r.data.missionTitle || r.data.missionId })
      }
    }
    return tabs
  }, [records])
  const [selected, setSelected] = useState<string>(catalog.missions[0]?.id ?? '')
  const mission = missions.find((m) => m.id === selected) ?? missions[0]
  const rows = useMemo(
    () => bestVerifiedRows(records.filter((r) => r.data.missionId === mission?.id), TOP),
    [records, mission?.id],
  )
  const counts = useMemo(() => {
    const out = new Map<string, number>()
    for (const r of records) out.set(r.data.missionId, (out.get(r.data.missionId) ?? 0) + 1)
    return out
  }, [records])

  return <div className="board-page">
    <header className="board-topline"><div><div className="eyebrow"><Trophy size={14}/> HOSTED SERVER · GATOR PASS</div><h1>Leaderboards</h1></div></header>
    <div className="lb-layout">
      <nav className="lb-missions" aria-label="Missions">
        {missions.map((m) => <button key={m.id} className={`lb-mission ${m.id === mission?.id ? 'is-selected' : ''}`} onClick={() => setSelected(m.id)}>
          <span>{m.stage ?? 'Campus'}</span><strong>{m.title}</strong><small>{counts.get(m.id) ?? 0} verified</small>
        </button>)}
      </nav>
      <main>
        <section className="lb-card" aria-labelledby="verified-title">
          <div className="section-heading"><div><span className="section-index"><BadgeCheck size={13}/> VERIFIED</span><h2 id="verified-title">{mission?.title}</h2></div><span className="tiny-caption">BEST RUN PER TEAM</span></div>
          <p className="lb-note">Timed by the hosted game server; every player was logged in with Gator Pass.</p>
          {status === 'loading' ? <div className="lb-empty">Loading the board…</div>
            : rows.length === 0 ? <div className="lb-empty">No verified runs yet. Play this mission on the hosted server, log in with <code>/login</code>, and finish a round.</div>
            : <ol className="lb-rows">{rows.map((row, i) => <li key={`${row.names.join('|')}-${row.elapsedFrames}`} className="lb-row">
                <span className="lb-rank">{i + 1}</span>
                <span className="lb-names">{row.names.join(' & ')}{row.coop && <em><Users size={12}/> co-op</em>}</span>
                <span className="lb-time">{formatFrames(row.elapsedFrames)}</span>
                <span className="lb-retries">{row.retries} {row.retries === 1 ? 'retry' : 'retries'}</span>
              </li>)}</ol>}
        </section>
        {mission && (isSignedIn ? <OfflineRuns missionId={mission.id}/> : <section className="lb-card lb-offline"><div className="section-heading compact"><div><span className="section-index"><CloudOff size={13}/> OFFLINE · UNVERIFIED</span><h2>Player-reported runs</h2></div></div><p className="lb-note">Sign in to see runs synced from players’ own games. They are self-reported and never ranked with the verified board.</p></section>)}
      </main>
    </div>
  </div>
}

function OfflineRuns({ missionId }: { missionId: string }) {
  const { records, status } = useQuery<OfflineRun>('solo_runs', { where: { missionId }, orderBy: 'elapsedFrames', orderDir: 'asc', limit: 50 })
  const rows = records.filter((r) => r.data.assisted === false || r.data.assisted === 0).slice(0, TOP)
  return <section className="lb-card lb-offline" aria-labelledby="offline-title">
    <div className="section-heading compact"><div><span className="section-index"><CloudOff size={13}/> OFFLINE · UNVERIFIED</span><h2 id="offline-title">Player-reported runs</h2></div></div>
    <p className="lb-note">Synced from players’ own games. The time is measured on their machine, so these are listed separately and never ranked with the verified board.</p>
    {status === 'loading' ? <div className="lb-empty">Loading…</div>
      : rows.length === 0 ? <div className="lb-empty">No offline runs for this mission.</div>
      : <ol className="lb-rows">{rows.map((r) => <li key={r.recordId} className="lb-row">
          <span className="lb-rank">·</span>
          <span className="lb-names">{r.data.playerTag}<em>offline</em></span>
          <span className="lb-time">{formatFrames(r.data.elapsedFrames)}</span>
          <span className="lb-retries">{r.data.retries} {r.data.retries === 1 ? 'retry' : 'retries'}</span>
        </li>)}</ol>}
  </section>
}
