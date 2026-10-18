import config from './gator-config.json'

export type BoardRow = { rank: number; names: string[]; frames: number; retries: number; players: number; at: string }
export type MissionBoard = { mission: string; title: string; rows: BoardRow[] }

export async function fetchGameBoards(signal: AbortSignal): Promise<MissionBoard[]> {
  const response = await fetch(`${config.apiBase}/leaderboards`, { credentials: 'omit', signal })
  if (!response.ok) throw new Error('The leaderboard is unavailable. Retrying automatically.')
  const body = await response.json() as { missions?: MissionBoard[] }
  if (!Array.isArray(body.missions) || !body.missions.every(m => typeof m.mission === 'string' && typeof m.title === 'string' && Array.isArray(m.rows) && m.rows.every(row => Number.isInteger(row.rank) && row.rank > 0 && Number.isInteger(row.frames) && row.frames > 0 && Array.isArray(row.names) && row.names.every(name => typeof name === 'string') && Number.isInteger(row.retries) && Number.isInteger(row.players)))) throw new Error('The leaderboard response was invalid. Retrying automatically.')
  return body.missions
}
