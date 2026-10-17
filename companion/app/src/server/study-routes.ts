import type { Context, Hono } from 'hono'
import catalog from '../data/mission-catalog.json'
import type { AppContext } from '../../worker.js'

type Mission = (typeof catalog.missions)[number]

const missions = new Map<string, Mission>(catalog.missions.map((mission) => [mission.id, mission]))

function serviceHeaders(env: AppContext['Bindings']): HeadersInit {
  return {
    'content-type': 'application/json',
    authorization: `Bearer ${env.VULTR_SERVICE_TOKEN ?? ''}`,
  }
}

function serviceReady(env: AppContext['Bindings']): boolean {
  return Boolean(env.VULTR_SERVICE_URL && env.VULTR_SERVICE_TOKEN)
}

async function safeServiceFetch(
  env: AppContext['Bindings'],
  path: string,
  init: RequestInit,
): Promise<Response | null> {
  if (!serviceReady(env)) return null
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 8_000)
  try {
    return await fetch(new URL(path, env.VULTR_SERVICE_URL), {
      ...init,
      headers: { ...serviceHeaders(env), ...init.headers },
      signal: controller.signal,
    })
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}

async function readJson(c: Context<AppContext>): Promise<Record<string, unknown> | null> {
  const body = await c.req.json<unknown>().catch(() => null)
  if (typeof body !== 'object' || body === null || Array.isArray(body)) return null
  return body as Record<string, unknown>
}

export function registerStudyRoutes(app: Hono<AppContext>): void {
  app.post('/api/study/dispatcher', async (c) => {
    const body = await readJson(c)
    const mission = typeof body?.missionId === 'string' ? missions.get(body.missionId) : undefined
    if (!mission) return c.json({ error: 'Choose a mission from the mission board.' }, 400)

    const response = await safeServiceFetch(c.env, '/dispatcher', {
      method: 'POST',
      body: JSON.stringify({ missionId: mission.id }),
    })
    if (!response?.ok) {
      return c.json({ missionId: mission.id, responseType: 'hint', text: mission.hint, fallback: true })
    }

    const result = await response.json<unknown>().catch(() => null)
    if (
      typeof result === 'object' && result !== null &&
      'missionId' in result && result.missionId === mission.id &&
      'responseType' in result && result.responseType === 'hint' &&
      'text' in result && typeof result.text === 'string' && result.text.length <= 240
    ) {
      return c.json({ missionId: mission.id, responseType: 'hint', text: result.text, fallback: 'fallback' in result && result.fallback === true })
    }
    return c.json({ missionId: mission.id, responseType: 'hint', text: mission.hint, fallback: true })
  })

  app.post('/api/study/events', async (c) => {
    const body = await readJson(c)
    if (
      typeof body?.eventId !== 'string' || body.eventId.length > 80 ||
      typeof body.missionId !== 'string' || !missions.has(body.missionId) ||
      !Number.isInteger(body.teamSize) || Number(body.teamSize) < 1 || Number(body.teamSize) > 4 ||
      !Number.isInteger(body.durationSeconds) || Number(body.durationSeconds) < 0 || Number(body.durationSeconds) > 7200 ||
      !Number.isInteger(body.retries) || Number(body.retries) < 0 || Number(body.retries) > 100
    ) {
      return c.json({ error: 'The result fields are invalid.' }, 400)
    }

    const response = await safeServiceFetch(c.env, '/events', {
      method: 'POST',
      body: JSON.stringify({
        eventId: body.eventId,
        missionId: body.missionId,
        teamSize: body.teamSize,
        durationSeconds: body.durationSeconds,
        retries: body.retries,
        occurredAt: typeof body.occurredAt === 'string' ? body.occurredAt : new Date().toISOString(),
        eventType: 'mission_result',
      }),
    })
    if (!response?.ok) return c.json({ mirrored: false }, 503)
    return c.json({ mirrored: true })
  })

  app.get('/api/study/analytics/:missionId', async (c) => {
    const mission = missions.get(c.req.param('missionId'))
    if (!mission) return c.json({ error: 'Unknown mission.' }, 404)
    const response = await safeServiceFetch(
      c.env,
      `/analytics/${encodeURIComponent(mission.id)}`,
      { method: 'GET', headers: { authorization: `Bearer ${c.env.VULTR_SERVICE_TOKEN ?? ''}` } },
    )
    if (!response?.ok) return c.json({ error: 'Analytics are unavailable right now.' }, 503)
    const result = await response.json<unknown>().catch(() => null)
    if (typeof result !== 'object' || result === null || !('count' in result)) {
      return c.json({ error: 'Analytics response was invalid.' }, 502)
    }
    return c.json(result)
  })
}
