/**
 * Leaderboard rules shared by the worker (getGameLeaderboard) and the web board.
 *
 * Two boards, never mixed (docs/web_platform_spec.md §10.4):
 *   - VERIFIED: `verified_runs`, written only by ingestVerifiedRun from the hosted game's API, where
 *     the server measured the time and every player was logged in with Gator Pass. Best run per
 *     player set, ties to the earlier run.
 *   - OFFLINE: `solo_runs`, sent by players through submitGameRun (the macOS bridge). The client
 *     reports its own time, so these are labelled "offline" and listed separately.
 */

export type VerifiedPlayer = { name: string; tag: string }

export type VerifiedRun = {
  runId: string
  missionId: string
  missionTitle: string
  frames: number
  retries: number
  coop: boolean | number
  playerCount: number
  playerNames: string
  playerKey: string
  players: string | VerifiedPlayer[]
  ranAt: string
}

export type VerifiedRow = {
  playerTag: string
  names: string[]
  elapsedFrames: number
  retries: number
  coop: boolean
  verified: true
  source: 'hosted'
  createdAt: string
}

export const PLAYER_TAG_PATTERN = /^[A-Za-z0-9_-]{1,32}$/

/** players is stored as JSON text; the record layer may hand it back parsed or as a string. */
export function parsePlayers(value: unknown): VerifiedPlayer[] {
  let list: unknown = value
  if (typeof value === 'string') {
    try { list = JSON.parse(value) } catch { return [] }
  }
  if (!Array.isArray(list)) return []
  return list.filter((p): p is VerifiedPlayer =>
    typeof p === 'object' && p !== null && typeof (p as VerifiedPlayer).name === 'string' &&
    typeof (p as VerifiedPlayer).tag === 'string')
}

/** The player set's identity: the API's per-account tags, sorted. */
export function playerKey(players: VerifiedPlayer[]): string {
  return players.map((p) => p.tag).sort().join('+')
}

/**
 * A single-token tag for clients that show one short label per row (the macOS bridge's in-game cache
 * accepts ^[A-Za-z0-9_-]{1,32}$): the names joined with "-", other characters as "_".
 */
export function compactTag(players: VerifiedPlayer[]): string {
  const joined = players.map((p) => p.name.trim().replace(/[^A-Za-z0-9_-]+/g, '_')).filter(Boolean).join('-').slice(0, 32)
  if (PLAYER_TAG_PATTERN.test(joined)) return joined
  const first = players[0]?.tag ?? ''
  return PLAYER_TAG_PATTERN.test(first) ? first : 'GATOR'
}

/** Best run per player set, fastest first (ties: fewer retries, then the earlier run). */
export function bestVerifiedRows(
  records: Array<{ data: VerifiedRun; createdAt?: string }>,
  limit: number,
): VerifiedRow[] {
  const best = new Map<string, VerifiedRow>()
  for (const record of records) {
    const run = record.data
    if (!Number.isInteger(run.frames) || run.frames < 1) continue
    const players = parsePlayers(run.players)
    if (players.length === 0) continue
    const key = run.playerKey || playerKey(players)
    const row: VerifiedRow = {
      playerTag: compactTag(players),
      names: players.map((p) => p.name),
      elapsedFrames: run.frames,
      retries: Number(run.retries) || 0,
      coop: run.coop === true || run.coop === 1,
      verified: true,
      source: 'hosted',
      createdAt: run.ranAt || record.createdAt || '',
    }
    const current = best.get(key)
    if (!current || compareRows(row, current) < 0) best.set(key, row)
  }
  return [...best.values()].sort(compareRows).slice(0, limit)
}

function compareRows(a: VerifiedRow, b: VerifiedRow): number {
  return a.elapsedFrames - b.elapsedFrames || a.retries - b.retries || a.createdAt.localeCompare(b.createdAt)
}

/** m:ss.cc from 30 fps frames (the in-game timer's format). */
export function formatFrames(frames: number): string {
  const centis = Math.round((frames * 100) / 30)
  const minutes = Math.floor(centis / 6000)
  const seconds = Math.floor((centis % 6000) / 100)
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(centis % 100).padStart(2, '0')}`
}
