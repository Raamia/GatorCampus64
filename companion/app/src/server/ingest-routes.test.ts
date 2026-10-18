/**
 * The game API → DeepSpace ingest (docs/web_platform_spec.md §10.4), end to end through the Hono
 * route and the real action-tools wiring, with an in-memory stand-in for the RecordRoom's
 * /api/tools/execute endpoint.
 */
import { Hono } from 'hono'
import { beforeEach, describe, expect, it } from 'vitest'
import type { AppContext, Env } from '../../worker.js'
import { parseIngestBody, signIngest, verifyIngestSignature } from '../actions/verified-runs.js'
import { bestVerifiedRows, formatFrames, type VerifiedRun } from '../lib/leaderboard.js'
import { registerActionRoutes } from './action-routes.js'
import { RunIngestRoom } from './run-ingest-room.js'
import { INGEST_PATH, registerIngestRoutes } from './ingest-routes.js'

const SECRET = 'test-ingest-secret-0123456789abcdef'

type Stored = { recordId: string; data: Record<string, unknown>; createdBy: string; createdAt: string }

/** Just enough of the RecordRoom tools API: records.query (where equality, orderBy, limit), create, delete. */
function fakeRecordRoom() {
  const tables = new Map<string, Stored[]>()
  const calls: Array<{ tool: string; userId: string | null; action: string | null }> = []
  let next = 1
  const execute = (tool: string, params: Record<string, unknown>, userId: string) => {
    const collection = String(params.collection)
    const rows = tables.get(collection) ?? []
    tables.set(collection, rows)
    if (tool === 'records.query') {
      const where = (params.where ?? {}) as Record<string, unknown>
      let found = rows.filter((r) => Object.entries(where).every(([k, v]) => r.data[k] === v))
      if (params.orderBy) {
        const key = String(params.orderBy)
        const dir = params.orderDir === 'desc' ? -1 : 1
        found = [...found].sort((a, b) => (Number(a.data[key]) - Number(b.data[key])) * dir)
      }
      const limit = Number(params.limit ?? 50)
      return { success: true, data: { records: found.slice(0, limit), count: Math.min(found.length, limit) } }
    }
    if (tool === 'records.create') {
      const data = params.data as Record<string, unknown>
      if (collection === 'verified_runs' && rows.some((r) => r.data.runId === data.runId)) {
        return { success: false, error: 'unique constraint' }
      }
      const record = { recordId: `r${next++}`, data, createdBy: userId, createdAt: new Date().toISOString() }
      rows.push(record)
      return { success: true, data: { recordId: record.recordId, record } }
    }
    if (tool === 'records.delete') {
      const i = rows.findIndex((r) => r.recordId === params.recordId)
      if (i >= 0) rows.splice(i, 1)
      return { success: true, data: { recordId: params.recordId } }
    }
    return { success: false, error: `unsupported ${tool}` }
  }
  const stub = {
    fetch: async (req: Request) => {
      const { tool, params } = await req.json() as { tool: string; params: Record<string, unknown> }
      calls.push({ tool, userId: req.headers.get('X-User-Id'), action: req.headers.get('X-App-Action') })
      return Response.json(execute(tool, params, req.headers.get('X-User-Id') ?? ''))
    },
  }
  const namespace = { idFromName: (name: string) => name, get: () => stub }
  return { tables, calls, namespace }
}

function makeApp(secret: string | undefined = SECRET) {
  const room = fakeRecordRoom()
  const env = {
    RECORD_ROOMS: room.namespace,
    DEEPSPACE_APP_ID: 'app_test',
    OWNER_USER_ID: 'owner-1',
    DEEPSPACE_INGEST_SECRET: secret,
  } as unknown as Env
  let gate = Promise.resolve()
  const coordinator = new RunIngestRoom({
    blockConcurrencyWhile: <T>(fn: () => Promise<T>) => {
      const task = gate.then(fn)
      gate = task.then(() => undefined, () => undefined)
      return task
    },
  } as DurableObjectState, env)
  env.RUN_INGEST = { idFromName: (name: string) => name, get: () => coordinator } as unknown as DurableObjectNamespace
  const app = new Hono<AppContext>()
  registerIngestRoutes(app)
  // The user action route sits behind it: a request without a session must never reach it.
  registerActionRoutes(app, async () => null)
  return { app, env, room }
}

function body(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({
    v: 1,
    runId: '7d3f1c2e-0b9a-4c55-8f0e-2a1b3c4d5e6f',
    missionId: 'swamp_sprint',
    missionTitle: 'STADIUM STAIR SPRINT',
    frames: 1250,
    retries: 1,
    coop: true,
    players: [{ name: 'AliGator', tag: 'GP-AAAA0001' }, { name: 'Bo the Bold', tag: 'GP-BBBB0002' }],
    level: 9,
    act: 2,
    createdAt: '2026-10-17T12:00:00+00:00',
    ...overrides,
  })
}

let nonceCounter = 0
async function signedRequest(raw: string, options: { secret?: string; timestamp?: string; nonce?: string } = {}) {
  const timestamp = options.timestamp ?? String(Math.floor(Date.now() / 1000))
  const nonce = options.nonce ?? (++nonceCounter).toString(16).padStart(32, '0')
  const signature = await signIngest(options.secret ?? SECRET, raw, timestamp, nonce)
  return new Request(`https://board.test${INGEST_PATH}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-sgl-timestamp': timestamp, 'x-sgl-nonce': nonce, 'x-sgl-signature': signature },
    body: raw,
  })
}

describe('ingestVerifiedRun route', () => {
  let ctx: ReturnType<typeof makeApp>
  beforeEach(() => { ctx = makeApp() })

  it('stores a correctly signed run as the app owner', async () => {
    const res = await ctx.app.fetch(await signedRequest(body()), ctx.env)
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ success: true, data: { duplicate: false, recordId: expect.any(String) } })
    const runs = ctx.room.tables.get('verified_runs') ?? []
    expect(runs).toHaveLength(1)
    expect(runs[0].createdBy).toBe('owner-1')
    expect(runs[0].data).toMatchObject({
      runId: '7d3f1c2e-0b9a-4c55-8f0e-2a1b3c4d5e6f', missionId: 'swamp_sprint', frames: 1250, retries: 1, coop: true,
      playerCount: 2, playerNames: 'AliGator & Bo the Bold', playerKey: 'GP-AAAA0001+GP-BBBB0002',
      ranAt: '2026-10-17T12:00:00+00:00',
    })
    expect(JSON.parse(String(runs[0].data.players))).toEqual([{ name: 'AliGator', tag: 'GP-AAAA0001' }, { name: 'Bo the Bold', tag: 'GP-BBBB0002' }])
    expect(ctx.room.calls.every((c) => c.userId === 'owner-1' && c.action === 'true')).toBe(true)
  })

  it('rejects a bad signature, a wrong secret, a tampered body and missing headers', async () => {
    const good = await signedRequest(body())
    const tampered = new Request(good.url, { method: 'POST', headers: good.headers, body: body({ frames: 100 }) })
    expect((await ctx.app.fetch(tampered, ctx.env)).status).toBe(401)
    expect((await ctx.app.fetch(await signedRequest(body(), { secret: 'not-the-secret' }), ctx.env)).status).toBe(401)
    const bare = new Request(good.url, { method: 'POST', body: body() })
    const res = await ctx.app.fetch(bare, ctx.env)
    expect(res.status).toBe(401)
    expect(await res.json()).toEqual({ success: false, error: 'Unauthorized (missing).' })
    expect(ctx.room.tables.get('verified_runs') ?? []).toHaveLength(0)
  })

  it('rejects stale timestamps and replayed nonces', async () => {
    const old = String(Math.floor(Date.now() / 1000) - 301)
    const stale = await ctx.app.fetch(await signedRequest(body(), { timestamp: old }), ctx.env)
    expect(stale.status).toBe(401)
    expect(await stale.json()).toEqual({ success: false, error: 'Unauthorized (stale).' })

    const nonce = 'ab'.repeat(16)
    const first = await signedRequest(body(), { nonce })
    const replay = new Request(first.url, { method: 'POST', headers: first.headers, body: body() })
    expect((await ctx.app.fetch(first, ctx.env)).status).toBe(200)
    const again = await ctx.app.fetch(replay, ctx.env)
    expect(again.status).toBe(409)
    expect(ctx.room.tables.get('verified_runs')).toHaveLength(1)
  })

  it('is idempotent by runId: a retried push (fresh nonce) writes nothing new', async () => {
    expect((await ctx.app.fetch(await signedRequest(body()), ctx.env)).status).toBe(200)
    const retry = await ctx.app.fetch(await signedRequest(body()), ctx.env)
    expect(retry.status).toBe(200)
    expect(await retry.json()).toEqual({ success: true, data: { duplicate: true, recordId: expect.any(String) } })
    expect(ctx.room.tables.get('verified_runs')).toHaveLength(1)
  })

  it('validates the run and refuses when no secret is configured', async () => {
    expect((await ctx.app.fetch(await signedRequest(body({ frames: -5 })), ctx.env)).status).toBe(400)
    expect((await ctx.app.fetch(await signedRequest(body({ players: [] })), ctx.env)).status).toBe(400)
    expect((await ctx.app.fetch(await signedRequest('not json'), ctx.env)).status).toBe(400)
    const off = makeApp('')
    expect((await off.app.fetch(await signedRequest(body()), off.env)).status).toBe(503)
    expect(off.room.calls).toHaveLength(0)
  })

  it('prunes nonces older than the replay window', async () => {
    ctx.room.tables.set('ingest_nonces', [
      { recordId: 'old', data: { nonce: 'f'.repeat(32), seenAt: Date.now() - 3_600_000 }, createdBy: 'owner-1', createdAt: '' },
    ])
    expect((await ctx.app.fetch(await signedRequest(body()), ctx.env)).status).toBe(200)
    expect(ctx.room.tables.get('ingest_nonces')?.map((r) => r.recordId)).not.toContain('old')
  })
})

describe('signature scheme', () => {
  it('matches the API (server/api/tests/test_runs.py::test_sign_vector)', async () => {
    expect(await signIngest('s3cret', '{"runId":"r1"}', '1760000000', '0'.repeat(32)))
      .toBe('v1=3d19ad467ef59d58cb86868105871536d42b5edbbe0e2c62ef9a8ccacaa1b9d0')
    expect(await verifyIngestSignature({
      secret: 's3cret', body: '{"runId":"r1"}', timestamp: '1760000000', nonce: '0'.repeat(32),
      signature: 'v1=3d19ad467ef59d58cb86868105871536d42b5edbbe0e2c62ef9a8ccacaa1b9d0', nowMs: 1760000000_000,
    })).toBe('ok')
    expect(await verifyIngestSignature({
      secret: 's3cret', body: '{"runId":"r1"}', timestamp: '1760000000', nonce: '0'.repeat(32),
      signature: 'v1=' + '0'.repeat(64), nowMs: 1760000000_000,
    })).toBe('bad_signature')
  })

  it('parses only well-formed bodies', () => {
    expect(parseIngestBody(JSON.parse(body()))).toMatchObject({ frames: 1250, coop: true })
    expect(parseIngestBody(JSON.parse(body({ v: 2 })))).toBeNull()
    expect(parseIngestBody(JSON.parse(body({ players: [{ name: 'A', tag: 'x y' }] })))).toBeNull()
    expect(parseIngestBody(JSON.parse(body({ players: [{ name: 'A', tag: 'T1' }, { name: 'B', tag: 'T1' }] })))).toBeNull()
  })
})

describe('verified board', () => {
  it('keeps the best run per player set and formats times like the game', () => {
    const run = (frames: number, tags: string[], ranAt: string): { data: VerifiedRun } => ({ data: {
      runId: `r${frames}`, missionId: 'm1', missionTitle: 'M', frames, retries: 0, coop: tags.length > 1 ? 1 : 0,
      playerCount: tags.length, playerNames: tags.join(' & '), playerKey: [...tags].sort().join('+'),
      players: tags.map((t) => ({ name: `N-${t}`, tag: t })), ranAt,
    } })
    const rows = bestVerifiedRows([
      run(1300, ['A'], '2026-10-17T12:00:01Z'), run(1200, ['A'], '2026-10-17T12:00:02Z'),
      run(1200, ['B'], '2026-10-17T12:00:00Z'), run(1100, ['B', 'A'], '2026-10-17T12:00:03Z'),
    ], 10)
    expect(rows.map((r) => [r.names.join(','), r.elapsedFrames])).toEqual([['N-B,N-A', 1100], ['N-B', 1200], ['N-A', 1200]])
    expect(formatFrames(1250)).toBe('0:41.67')
    expect(formatFrames(30 * 75)).toBe('1:15.00')
  })
})

describe('account deletion propagation', () => {
  it('removes a verified run and ignores late re-ingestion', async () => {
    const ctx = makeApp()
    const runId = JSON.parse(body()).runId
    expect((await ctx.app.fetch(await signedRequest(body()), ctx.env)).status).toBe(200)
    const deletion = JSON.stringify({ v: 1, deleteRunId: runId })
    expect((await ctx.app.fetch(await signedRequest(deletion), ctx.env)).status).toBe(200)
    expect(ctx.room.tables.get('verified_runs')).toHaveLength(0)
    expect(ctx.room.tables.get('erased_runs')).toHaveLength(1)
    expect((await ctx.app.fetch(await signedRequest(body()), ctx.env)).status).toBe(200)
    expect(ctx.room.tables.get('verified_runs')).toHaveLength(0)
    expect((await ctx.app.fetch(await signedRequest(deletion), ctx.env)).status).toBe(200)
  })

  it('serializes concurrent deletion and ingestion across the coordinator', async () => {
    const ctx = makeApp()
    const runId = JSON.parse(body()).runId
    const requests = await Promise.all([
      signedRequest(JSON.stringify({ v: 1, deleteRunId: runId })), signedRequest(body()), signedRequest(body()),
    ])
    const results = await Promise.all(requests.map((r) => ctx.app.fetch(r, ctx.env)))
    expect(results.every((r) => r.status === 200)).toBe(true)
    expect(ctx.room.tables.get('verified_runs') ?? []).toHaveLength(0)
  })

  it('requires a signed deletion and fails closed without its coordinator', async () => {
    const ctx = makeApp()
    const request = await signedRequest(JSON.stringify({ v: 1, deleteRunId: JSON.parse(body()).runId }), { secret: 'wrong' })
    expect((await ctx.app.fetch(request, ctx.env)).status).toBe(401)
    expect(ctx.room.tables.get('erased_runs') ?? []).toHaveLength(0)
    delete (ctx.env as Partial<Env>).RUN_INGEST
    expect((await ctx.app.fetch(await signedRequest(body()), ctx.env)).status).toBe(503)
  })
})
