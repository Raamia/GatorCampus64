import { Hono } from 'hono'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AppContext, Env } from '../../worker.js'
import { StudyBudgetRoom, GLOBAL_HOURLY_LIMIT, USER_HOURLY_LIMIT } from './study-budget.js'
import { registerStudyRoutes } from './study-routes.js'

vi.mock('./http-routes.js', () => ({
  resolveAuth: async (request: Request) => request.headers.get('Authorization') === 'Bearer verified-test-token'
    ? { userId: 'alice' } : null,
}))

// Serialize like Durable Object storage transactions; retain data when the
// class instance is recreated, so restart and concurrent-admission tests matter.
function storageState() {
  const data = new Map<string, unknown>()
  let tail: Promise<unknown> = Promise.resolve()
  const tx = {
    get: async (key: string) => structuredClone(data.get(key)),
    put: async (key: string, value: unknown) => { data.set(key, structuredClone(value)) },
  }
  return { storage: {
    transaction: (fn: (transaction: typeof tx) => Promise<unknown>) => {
      const result = tail.then(() => fn(tx))
      tail = result.catch(() => {})
      return result
    },
  } } as unknown as DurableObjectState
}

function admission(room: StudyBudgetRoom, userId: string) {
  return room.fetch(new Request('https://internal/admit', { method: 'POST', body: JSON.stringify({ userId }) }))
}

function setup() {
  const app = new Hono<AppContext>()
  registerStudyRoutes(app)
  const room = new StudyBudgetRoom(storageState())
  const env = {
    VULTR_SERVICE_URL: 'https://upstream.invalid', VULTR_SERVICE_TOKEN: 'server-only',
    DEEPSPACE_APP_ID: 'test-app',
    STUDY_BUDGETS: { idFromName: (s: string) => s, get: () => room },
  } as unknown as Env
  const upstream = vi.fn(async () => Response.json({ count: 1 }))
  vi.stubGlobal('fetch', upstream)
  const request = (path: string, signedIn = false, body?: unknown) => app.request(path, {
    method: body ? 'POST' : 'GET',
    headers: { ...(signedIn ? { Authorization: 'Bearer verified-test-token' } : {}), 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  }, env)
  return { env, upstream, request }
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('study service boundary', () => {
  const event = { eventId: 'event-1234', missionId: 'reitz_rooftop', teamSize: 1, durationSeconds: 10, retries: 0 }

  it('does not lend service credentials to anonymous writes or reads', async () => {
    const { request, upstream } = setup()
    expect((await request('/api/study/events', false, event)).status).toBe(401)
    expect((await request('/api/study/analytics/reitz_rooftop')).status).toBe(401)
    const hint = await request('/api/study/dispatcher', false, { missionId: 'reitz_rooftop' })
    expect((await hint.json() as { fallback: boolean }).fallback).toBe(true)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('labels authenticated reports unverified and limits upstream calls', async () => {
    const { request, upstream } = setup()
    for (let i = 0; i < USER_HOURLY_LIMIT; i++) {
      expect((await request('/api/study/events', true, event)).status).toBe(200)
    }
    const denied = await request('/api/study/events', true, event)
    expect(denied.status).toBe(429)
    expect(Number(denied.headers.get('Retry-After'))).toBeGreaterThan(0)
    expect(upstream).toHaveBeenCalledTimes(USER_HOURLY_LIMIT)
    const options = (upstream.mock.calls[0] as unknown as [URL, RequestInit])[1]
    expect(JSON.parse(String(options.body))).toMatchObject({ source: 'self_reported', verified: false })
    expect(options.headers).toMatchObject({ authorization: 'Bearer server-only' })
  })

  it('fails closed when the budget binding is missing', async () => {
    const { request, upstream, env } = setup()
    delete (env as Partial<Env>).STUDY_BUDGETS
    expect((await request('/api/study/events', true, event)).status).toBe(503)
    expect(upstream).not.toHaveBeenCalled()
  })
})

describe('durable admission', () => {
  it('bounds concurrent users globally and retains limits after reconstruction', async () => {
    const state = storageState()
    const room = new StudyBudgetRoom(state)
    const results = await Promise.all(Array.from({ length: GLOBAL_HOURLY_LIMIT + 10 }, (_, i) => admission(room, `user-${i}`)))
    expect(results.filter(r => r.status === 204)).toHaveLength(GLOBAL_HOURLY_LIMIT)
    expect((await admission(new StudyBudgetRoom(state), 'new-user')).status).toBe(429)
  })

  it('resets admission in the next hour', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(3_600_000)
    const room = new StudyBudgetRoom(storageState())
    for (let i = 0; i < USER_HOURLY_LIMIT; i++) await admission(room, 'alice')
    expect((await admission(room, 'alice')).status).toBe(429)
    vi.spyOn(Date, 'now').mockReturnValue(7_200_000)
    expect((await admission(room, 'alice')).status).toBe(204)
  })
})
