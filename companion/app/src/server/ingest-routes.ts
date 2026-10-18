/**
 * Server-to-server route for the hosted game's API (docs/web_platform_spec.md §10.4).
 *
 * POST /api/actions/ingestVerifiedRun is registered BEFORE the generic user action route, so this
 * path never reaches the session-authenticated handler, and `ingestVerifiedRun` is deliberately not
 * in src/actions/index.ts. Authentication is the HMAC in src/actions/verified-runs.ts with the
 * secret DEEPSPACE_INGEST_SECRET (`npx deepspace secrets set DEEPSPACE_INGEST_SECRET=...`); without
 * it the route answers 503 and writes nothing.
 *
 * Writes run as the app owner through the same RBAC-off record tools the actions use: the caller is
 * the game API, not a DeepSpace user.
 */

import type { Hono } from 'hono'
import type { AppContext } from '../../worker.js'
import { ingestVerifiedRun, MAX_BODY_BYTES } from '../actions/verified-runs.js'
import { createActionTools } from './action-routes.js'

export const INGEST_PATH = '/api/actions/ingestVerifiedRun'

export function registerIngestRoutes(app: Hono<AppContext>): void {
  app.post(INGEST_PATH, async (c) => {
    const length = Number(c.req.header('content-length') ?? '0')
    if (length > MAX_BODY_BYTES) return c.json({ success: false, error: 'Body too large.' }, 413)
    const rawBody = await c.req.text()
    const result = await ingestVerifiedRun({
      secret: c.env.DEEPSPACE_INGEST_SECRET,
      rawBody,
      headers: c.req.raw.headers,
      tools: createActionTools(c.env, c.env.OWNER_USER_ID, ''),
    })
    console.info(`[ingest] status=${result.status}`)
    return c.json(result.body, result.status)
  })
}
