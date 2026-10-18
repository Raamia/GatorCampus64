/**
 * Game run actions (docs/web_platform_spec.md §10.4).
 *
 * submitGameRun: the player's own machine reports a run (the macOS bridge). The time is
 * client-measured, so the run is stored in `solo_runs` as an unverified OFFLINE run.
 * getGameLeaderboard: `rows` is the VERIFIED board only (verified_runs, pushed by the hosted
 * game's API through ingestVerifiedRun); offline runs come back separately in `offlineRows`.
 */
import { soloEraseKey } from './account-erasure.js'
import type { ActionHandler, ActionResult } from 'deepspace/worker'
import type { Env } from '../../worker.js'
import { bestVerifiedRows, type VerifiedRun } from '../lib/leaderboard.js'

const MAX_RUN_FRAMES = 30 * 60 * 60
const MAX_RETRIES = 100
const RUN_ID_PATTERN = /^[A-Za-z0-9_-]{8,80}$/
const MISSION_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{1,79}$/
const VERSION_PATTERN = /^[A-Za-z0-9._+-]{1,32}$/

export type SoloRun = {
  runId: string
  userId: string
  playerTag: string
  missionId: string
  elapsedFrames: number
  retries: number
  assisted: boolean
  gameVersion: string
}

type OfflineRow = Omit<SoloRun, 'userId' | 'runId'> & {
  createdAt: string
  verified: false
  source: 'offline'
}

type Page<T> = {
  records: Array<{ recordId: string; data: T; createdAt: string }>
  count: number
  nextOffset?: number
}

/** Every record matching `where`, ordered, following offset pages. The runtime query tool supports
 * offset/nextOffset pagination even though this SDK version omits those fields from ActionTools'
 * TypeScript types. */
async function queryAll<T>(
  tools: Parameters<ActionHandler<Env>>[0]['tools'],
  collection: string,
  where: Record<string, unknown>,
  orderBy: string,
): Promise<ActionResult<Page<T>['records']>> {
  const queryPage = tools.query as (collection: string, options: {
    where: Record<string, unknown>
    orderBy: string
    orderDir: 'asc' | 'desc'
    limit: number
    offset?: number
  }) => Promise<ActionResult<Page<T>>>
  const records: Page<T>['records'] = []
  let offset: number | undefined
  do {
    const result = await queryPage(collection, {
      where,
      orderBy,
      orderDir: 'asc',
      limit: 100,
      ...(offset === undefined ? {} : { offset }),
    })
    if (!result.success) return result
    records.push(...result.data.records)
    offset = result.data.nextOffset
  } while (offset !== undefined)
  return { success: true, data: records }
}

function parseRun(params: Record<string, unknown>): Omit<SoloRun, 'userId' | 'playerTag'> | null {
  const { runId, missionId, elapsedFrames, retries, assisted, gameVersion } = params
  if (
    typeof runId !== 'string' || !RUN_ID_PATTERN.test(runId) ||
    typeof missionId !== 'string' || !MISSION_ID_PATTERN.test(missionId) ||
    !Number.isInteger(elapsedFrames) || Number(elapsedFrames) < 1 || Number(elapsedFrames) > MAX_RUN_FRAMES ||
    !Number.isInteger(retries) || Number(retries) < 0 || Number(retries) > MAX_RETRIES ||
    typeof assisted !== 'boolean' ||
    typeof gameVersion !== 'string' || !VERSION_PATTERN.test(gameVersion)
  ) return null

  return {
    runId,
    missionId,
    elapsedFrames: Number(elapsedFrames),
    retries: Number(retries),
    assisted,
    gameVersion,
  }
}

async function playerTag(userId: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(userId))
  const suffix = Array.from(new Uint8Array(digest).slice(0, 4), (byte) => byte.toString(16).padStart(2, '0')).join('').toUpperCase()
  return `GATOR-${suffix}`
}

export const submitGameRun: ActionHandler<Env> = async ({ userId, params, tools }) => {
  if (userId.startsWith('anon-')) return { success: false, error: 'Sign in to sync a run.' }
  const run = parseRun(params)
  if (!run) return { success: false, error: 'Run fields are invalid.' }

  const key = await soloEraseKey(userId, run.runId)
  const erased = await tools.query('erased_solo_runs', { where: { key }, limit: 1 })
  if (!erased.success) return erased
  if (erased.data.records.length) return { success: false, error: 'This run was deleted.' }

  const existing = await tools.query<SoloRun>('solo_runs', {
    where: { userId, runId: run.runId },
    limit: 1,
  })
  if (!existing.success) return existing
  if (existing.data.records.length > 0) {
    return { success: true, data: { duplicate: true, recordId: existing.data.records[0].recordId, verified: false, board: 'offline' } }
  }

  const result = await tools.create('solo_runs', {
    ...run,
    userId,
    playerTag: await playerTag(userId),
  })
  if (!result.success) return result
  const after = await tools.query('erased_solo_runs', { where: { key }, limit: 1 })
  if (!after.success) return after
  if (after.data.records.length) {
    const removed = await tools.remove('solo_runs', result.data.recordId)
    if (!removed.success) return removed
    return { success: false, error: 'This run was deleted.' }
  }
  return { success: true, data: { duplicate: false, recordId: result.data.recordId, verified: false, board: 'offline' } }
}

/** The macOS bridge's in-game cache accepts retries 0...100 per row. */
const DISPLAY_MAX_RETRIES = 100

export const getGameLeaderboard: ActionHandler<Env> = async ({ userId, params, tools }) => {
  if (userId.startsWith('anon-')) return { success: false, error: 'Sign in to view the online leaderboard.' }
  const missionId = params.missionId
  if (typeof missionId !== 'string' || !MISSION_ID_PATTERN.test(missionId)) {
    return { success: false, error: 'Mission id is invalid.' }
  }

  const limit = Number.isInteger(params.limit) ? Math.max(1, Math.min(Number(params.limit), 20)) : 10

  // VERIFIED: hosted-server runs, best per player set.
  const verified = await queryAll<VerifiedRun>(tools, 'verified_runs', { missionId }, 'frames')
  if (!verified.success) return verified
  const rows = bestVerifiedRows(verified.data, limit)
    .map((row) => ({ ...row, missionId, retries: Math.min(row.retries, DISPLAY_MAX_RETRIES), assisted: false }))

  // OFFLINE: player-reported runs, kept apart and labelled.
  // `assisted` is a boolean interpretation over numeric 0/1 storage. Query the mission first, then
  // normalize/filter that column below so a stored zero is not lost if the action query compares
  // the JSON boolean literally.
  const offline = await queryAll<SoloRun>(tools, 'solo_runs', { missionId }, 'elapsedFrames')
  if (!offline.success) return offline
  const offlineRows = offline.data
    .filter((record) => {
      const assisted = record.data.assisted as unknown
      return assisted === false || assisted === 0
    })
    .map((record) => ({
      playerTag: record.data.playerTag,
      missionId: record.data.missionId,
      elapsedFrames: record.data.elapsedFrames,
      retries: record.data.retries,
      assisted: false,
      gameVersion: record.data.gameVersion,
      createdAt: record.createdAt,
      verified: false as const,
      source: 'offline' as const,
    }))
    .sort((a, b) => a.elapsedFrames - b.elapsedFrames || a.retries - b.retries || a.createdAt.localeCompare(b.createdAt))
    .slice(0, limit) satisfies OfflineRow[]

  return { success: true, data: { missionId, rows, offlineRows } }
}
