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
      data: { duplicate: false, recordId: 'run-record-1' },
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
      data: { duplicate: true, recordId: 'existing-run' },
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

describe('getGameLeaderboard', () => {
  it('returns unassisted rows sorted by time, retries, then submission time', async () => {
    const tools = fakeTools({ queryRows: [
      { recordId: 'c', createdAt: '2026-10-16T12:00:03.000Z', data: { ...validRun, playerTag: 'GATOR-C', elapsedFrames: 900, retries: 0 } },
      { recordId: 'b', createdAt: '2026-10-16T12:00:02.000Z', data: { ...validRun, playerTag: 'GATOR-B', elapsedFrames: 800, retries: 2 } },
      { recordId: 'a', createdAt: '2026-10-16T12:00:01.000Z', data: { ...validRun, assisted: 0, playerTag: 'GATOR-A', elapsedFrames: 800, retries: 1 } },
      { recordId: 'assisted', data: { ...validRun, assisted: true, playerTag: 'GATOR-ASSISTED', elapsedFrames: 100, retries: 0 } },
    ] })
    const result = await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint', limit: 2 }, tools))
    expect(result).toMatchObject({
      success: true,
      data: { missionId: 'swamp_sprint', rows: [
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

  it('pages past the first 100 rows before applying retry tie-breakers', async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({
      recordId: `first-${index}`,
      data: { ...validRun, playerTag: `GATOR-${index}`, elapsedFrames: 800, retries: 3 },
    }))
    const tools = fakeTools({ pageRows: [firstPage, [
      { recordId: 'best-tie', data: { ...validRun, playerTag: 'GATOR-BEST', elapsedFrames: 800, retries: 0 } },
    ]] })
    const result = await getGameLeaderboard(ctx('player-1', { missionId: 'swamp_sprint', limit: 1 }, tools))
    expect(result).toMatchObject({
      success: true,
      data: { rows: [{ playerTag: 'GATOR-BEST', retries: 0 }] },
    })
    expect(tools.query).toHaveBeenCalledTimes(2)
    expect(tools.query).toHaveBeenLastCalledWith('solo_runs', expect.objectContaining({ offset: 100 }))
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
