import { describe, expect, it, vi } from 'vitest'
import type { ActionContext, ActionTools } from 'deepspace/worker'
import type { Env } from '../../worker.js'
import { getGameLeaderboard, submitGameRun } from './game-runs.js'

function ctx(userId: string, params: Record<string, unknown>, tools: ActionTools): ActionContext<Env> {
  return { userId, params, tools, env: {} as Env, callerJwt: 'test-jwt' }
}

function fakeTools(options?: {
  existing?: Array<{ recordId: string; data: Record<string, unknown>; createdAt?: string }>
  queryRows?: Array<{ recordId: string; data: Record<string, unknown>; createdAt?: string }>
  pageRows?: Array<Array<{ recordId: string; data: Record<string, unknown>; createdAt?: string }>>
  queryFails?: boolean
}) {
  const query = vi.fn(async (_collection: string, queryOptions?: { offset?: number; limit?: number }) => options?.queryFails
    ? { success: false as const, error: 'storage unavailable' }
    : {
        success: true as const,
        data: {
          records: (options?.pageRows?.[queryOptions?.offset ? 1 : 0] ?? options?.existing ?? options?.queryRows ?? []).map((row) => ({
            ...row,
            createdBy: 'player-1',
            createdAt: row.createdAt ?? '2026-10-16T12:00:00.000Z',
            updatedAt: row.createdAt ?? '2026-10-16T12:00:00.000Z',
          })),
          count: (options?.pageRows?.[queryOptions?.offset ? 1 : 0] ?? options?.existing ?? options?.queryRows ?? []).length,
          ...(options?.pageRows && !queryOptions?.offset && options.pageRows.length > 1 ? { nextOffset: 100 } : {}),
        },
      })
  const create = vi.fn(async () => ({ success: true as const, data: { recordId: 'run-record-1' } }))
  return { query, create } as unknown as ActionTools & {
    query: ReturnType<typeof query>
    create: ReturnType<typeof create>
  }
}

const validRun = {
  runId: 'run_20261016_000001',
  missionId: 'swamp_sprint',
  elapsedFrames: 1800,
  retries: 1,
  assisted: false,
  gameVersion: '0.1.0',
}

describe('submitGameRun', () => {
  it('requires an authenticated player and validates the result fields', async () => {
    const tools = fakeTools()
    expect(await submitGameRun(ctx('anon-local', validRun, tools))).toEqual({
      success: false,
      error: 'Sign in to sync a run.',
    })
    expect(await submitGameRun(ctx('player-1', { ...validRun, elapsedFrames: -1 }, tools))).toEqual({
      success: false,
      error: 'Run fields are invalid.',
    })
    expect(tools.query).not.toHaveBeenCalled()
    expect(tools.create).not.toHaveBeenCalled()
  })

  it('creates an immutable run row with server-derived identity', async () => {
    const tools = fakeTools()
    expect(await submitGameRun(ctx('player-1', validRun, tools))).toEqual({
      success: true,
      data: { duplicate: false, recordId: 'run-record-1', verified: false, board: 'offline' },
    })
    expect(tools.create).toHaveBeenCalledWith('solo_runs', {
      ...validRun,
      userId: 'player-1',
      playerTag: expect.stringMatching(/^GATOR-[0-9A-F]{8}$/),
    })
  })

  it('treats retries of the same run id as idempotent', async () => {
    const tools = fakeTools({ existing: [{ recordId: 'existing-run', data: validRun }] })
    expect(await submitGameRun(ctx('player-1', validRun, tools))).toEqual({
      success: true,
      data: { duplicate: true, recordId: 'existing-run', verified: false, board: 'offline' },
    })
    expect(tools.query).toHaveBeenCalledWith('solo_runs', {
      where: { userId: 'player-1', runId: validRun.runId },
      limit: 1,
    })
    expect(tools.create).not.toHaveBeenCalled()
  })

  it('surfaces a failed duplicate lookup instead of silently accepting an unsaved run', async () => {
    const tools = fakeTools({ queryFails: true })
    expect(await submitGameRun(ctx('player-1', validRun, tools))).toEqual({
      success: false,
      error: 'storage unavailable',
    })
    expect(tools.create).not.toHaveBeenCalled()
  })
})

type Row = { recordId: string; data: Record<string, unknown>; createdAt?: string }

/** A query tool that answers per collection (verified_runs / solo_runs), in pages of 100. */
function boardTools(byCollection: Record<string, Row[]>) {
  const query = vi.fn(async (collection: string, options?: { offset?: number }) => {
    const all = byCollection[collection] ?? []
    const offset = options?.offset ?? 0
    const page = all.slice(offset, offset + 100)
    return {
      success: true as const,
      data: {
        records: page.map((row) => ({ ...row, createdBy: 'owner', createdAt: row.createdAt ?? '2026-10-16T12:00:00.000Z', updatedAt: row.createdAt ?? '2026-10-16T12:00:00.000Z' })),
        count: page.length,
        ...(offset + 100 < all.length ? { nextOffset: offset + 100 } : {}),
      },
    }
  })
  return { query } as unknown as ActionTools & { query: ReturnType<typeof query> }
}

function verifiedRun(runId: string, frames: number, players: Array<[string, string]>, extra: Record<string, unknown> = {}): Row {
  const list = players.map(([name, tag]) => ({ name, tag }))
  return {
    recordId: `rec-${runId}`,
    data: {
      runId, missionId: 'swamp_sprint', missionTitle: 'STADIUM STAIR SPRINT', frames, retries: 0, coop: list.length > 1 ? 1 : 0,
      playerCount: list.length, playerNames: list.map((p) => p.name).join(' & '),
      playerKey: list.map((p) => p.tag).sort().join('+'), players: JSON.stringify(list),
      ranAt: `2026-10-17T12:00:${String(frames % 60).padStart(2, '0')}.000Z`, ...extra,
    },
  }
}

describe('getGameLeaderboard', () => {
  it('returns the verified board in rows and offline runs separately, never mixed', async () => {
    const tools = boardTools({
      verified_runs: [
        verifiedRun('run-0001', 1300, [['AliGator', 'GP-AAAA0001']]),
        verifiedRun('run-0002', 1250, [['AliGator', 'GP-AAAA0001']]),       // Ali's best
        verifiedRun('run-0003', 1400, [['Bo the Bold', 'GP-BBBB0002']]),
        verifiedRun('run-0004', 1200, [['Bo the Bold', 'GP-BBBB0002'], ['AliGator', 'GP-AAAA0001']]),
      ],
      solo_runs: [
        { recordId: 'offline-fast', data: { ...validRun, playerTag: 'GATOR-FAST', elapsedFrames: 100, retries: 0 } },
      ],
    })
    const result = await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint' }, tools))
    expect(result.success).toBe(true)
    const data = (result as { data: { rows: Array<Record<string, unknown>>; offlineRows: Array<Record<string, unknown>> } }).data
    expect(data.rows.map((r) => [r.names, r.elapsedFrames])).toEqual([
      [['Bo the Bold', 'AliGator'], 1200],
      [['AliGator'], 1250],
      [['Bo the Bold'], 1400],
    ])
    expect(data.rows[0]).toMatchObject({ playerTag: 'Bo_the_Bold-AliGator', verified: true, source: 'hosted', coop: true, retries: 0 })
    expect(data.rows.every((r) => /^[A-Za-z0-9_-]{1,32}$/.test(String(r.playerTag)))).toBe(true)
    expect(data.rows.some((r) => r.playerTag === 'GATOR-FAST')).toBe(false)
    expect(data.offlineRows).toMatchObject([{ playerTag: 'GATOR-FAST', elapsedFrames: 100, verified: false, source: 'offline' }])
    expect(tools.query).toHaveBeenCalledWith('verified_runs', expect.objectContaining({ where: { missionId: 'swamp_sprint' }, orderBy: 'frames' }))
  })

  it('returns unassisted offline rows sorted by time, retries, then submission time', async () => {
    const tools = boardTools({ solo_runs: [
      { recordId: 'c', createdAt: '2026-10-16T12:00:03.000Z', data: { ...validRun, playerTag: 'GATOR-C', elapsedFrames: 900, retries: 0 } },
      { recordId: 'b', createdAt: '2026-10-16T12:00:02.000Z', data: { ...validRun, playerTag: 'GATOR-B', elapsedFrames: 800, retries: 2 } },
      { recordId: 'a', createdAt: '2026-10-16T12:00:01.000Z', data: { ...validRun, assisted: 0, playerTag: 'GATOR-A', elapsedFrames: 800, retries: 1 } },
      { recordId: 'assisted', data: { ...validRun, assisted: true, playerTag: 'GATOR-ASSISTED', elapsedFrames: 100, retries: 0 } },
    ] })
    const result = await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint', limit: 2 }, tools))
    expect(result).toMatchObject({
      success: true,
      data: { missionId: 'swamp_sprint', rows: [], offlineRows: [
        { playerTag: 'GATOR-A', elapsedFrames: 800, retries: 1 },
        { playerTag: 'GATOR-B', elapsedFrames: 800, retries: 2 },
      ] },
    })
    expect(tools.query).toHaveBeenCalledWith('solo_runs', {
      where: { missionId: 'swamp_sprint' },
      orderBy: 'elapsedFrames',
      orderDir: 'asc',
      limit: 100,
    })
  })

  it('pages past the first 100 rows of each board before applying tie-breakers', async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({
      recordId: `first-${index}`,
      data: { ...validRun, playerTag: `GATOR-${index}`, elapsedFrames: 800, retries: 3 },
    }))
    const verifiedPage = Array.from({ length: 100 }, (_, index) =>
      verifiedRun(`run-v${String(index).padStart(4, '0')}`, 2000 + index, [[`P${index}`, `GP-P${index}`]]))
    const tools = boardTools({
      solo_runs: [...firstPage, { recordId: 'best-tie', data: { ...validRun, playerTag: 'GATOR-BEST', elapsedFrames: 800, retries: 0 } }],
      verified_runs: [...verifiedPage, verifiedRun('run-best', 900, [['Best', 'GP-BEST']])],
    })
    const result = await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint', limit: 1 }, tools))
    expect(result).toMatchObject({
      success: true,
      data: { rows: [{ names: ['Best'], elapsedFrames: 900 }], offlineRows: [{ playerTag: 'GATOR-BEST', retries: 0 }] },
    })
    expect(tools.query).toHaveBeenCalledTimes(4)
    expect(tools.query).toHaveBeenLastCalledWith('solo_runs', expect.objectContaining({ offset: 100 }))
  })

  it('surfaces a failed board query', async () => {
    const tools = fakeTools({ queryFails: true })
    expect(await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint' }, tools))).toEqual({
      success: false,
      error: 'storage unavailable',
    })
  })

  it('refuses anonymous requests and malformed mission ids', async () => {
    const tools = fakeTools()
    expect(await getGameLeaderboard(ctx('anon-local', { missionId: 'swamp_sprint' }, tools))).toEqual({
      success: false,
      error: 'Sign in to view the online leaderboard.',
    })
    expect(await getGameLeaderboard(ctx('player-1', { missionId: '../users' }, tools))).toEqual({
      success: false,
      error: 'Mission id is invalid.',
    })
    expect(tools.query).not.toHaveBeenCalled()
  })
})
