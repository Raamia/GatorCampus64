/**
 * ingestVerifiedRun: the server-only action the game API calls for each ranked run
 * (docs/web_platform_spec.md §10.4). It is NOT in the user-callable `actions` map: it has its own
 * route (src/server/ingest-routes.ts) authenticated by an HMAC over the raw body, never by a user
 * session. Mirror of server/api/sgl_api/deepspace.py:
 *
 *   X-SGL-Timestamp: <unix seconds>             accepted within ±MAX_SKEW_SECS of this worker's clock
 *   X-SGL-Nonce:     <32 lowercase hex chars>   rejected if already seen (ingest_nonces)
 *   X-SGL-Signature: v1=<hex HMAC-SHA256(DEEPSPACE_INGEST_SECRET, "v1:" + ts + ":" + nonce + ":" + body)>
 *
 * The signature is checked with crypto.subtle.verify (constant time). Runs are idempotent by the API's
 * runId: a repeated push answers { duplicate: true } and writes nothing.
 */

import type { ActionTools } from 'deepspace/worker'
import { parsePlayers, playerKey, type VerifiedPlayer, type VerifiedRun } from '../lib/leaderboard.js'

export const MAX_SKEW_SECS = 300
export const MAX_BODY_BYTES = 16 * 1024
const NONCE_TTL_MS = 2 * MAX_SKEW_SECS * 1000 // a nonce older than the window cannot be replayed anyway
const NONCE_PATTERN = /^[0-9a-f]{32}$/
const RUN_ID_PATTERN = /^[A-Za-z0-9-]{8,80}$/
const MISSION_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{1,79}$/
const TAG_PATTERN = /^[A-Za-z0-9_-]{1,32}$/
const MAX_FRAMES = 30 * 60 * 60
const MAX_PLAYERS = 16

export type IngestResult = { status: 200 | 400 | 401 | 409 | 413 | 503; body: Record<string, unknown> }

function hexToBytes(hex: string): Uint8Array<ArrayBuffer> | null {
  if (!/^(?:[0-9a-f]{2})+$/i.test(hex)) return null
  const out = new Uint8Array(hex.length / 2)
  for (let i = 0; i < out.length; i += 1) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  return out
}

async function hmacKey(secret: string, usage: 'sign' | 'verify'): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, [usage])
}

function signedMessage(timestamp: string, nonce: string, body: string): Uint8Array<ArrayBuffer> {
  return new TextEncoder().encode(`v1:${timestamp}:${nonce}:${body}`)
}

/** Used by tests and by any future caller that needs to produce the same signature as the API. */
export async function signIngest(secret: string, body: string, timestamp: string, nonce: string): Promise<string> {
  const mac = await crypto.subtle.sign('HMAC', await hmacKey(secret, 'sign'), signedMessage(timestamp, nonce, body))
  return 'v1=' + Array.from(new Uint8Array(mac), (b) => b.toString(16).padStart(2, '0')).join('')
}

export async function verifyIngestSignature(input: {
  secret: string
  body: string
  timestamp: string | null
  nonce: string | null
  signature: string | null
  nowMs?: number
}): Promise<'ok' | 'missing' | 'stale' | 'bad_signature'> {
  const { secret, body, timestamp, nonce, signature } = input
  if (!timestamp || !nonce || !signature) return 'missing'
  if (!/^\d{1,12}$/.test(timestamp) || !NONCE_PATTERN.test(nonce)) return 'bad_signature'
  const now = (input.nowMs ?? Date.now()) / 1000
  if (Math.abs(now - Number(timestamp)) > MAX_SKEW_SECS) return 'stale'
  const given = signature.startsWith('v1=') ? hexToBytes(signature.slice(3)) : null
  if (!given || given.length !== 32) return 'bad_signature'
  const ok = await crypto.subtle.verify('HMAC', await hmacKey(secret, 'verify'), given, signedMessage(timestamp, nonce, body))
  return ok ? 'ok' : 'bad_signature'
}

type IngestBody = {
  runId: string
  missionId: string
  missionTitle: string
  frames: number
  retries: number
  coop: boolean
  players: VerifiedPlayer[]
  createdAt: string
}

export function parseIngestBody(raw: unknown): IngestBody | null {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return null
  const b = raw as Record<string, unknown>
  const players = Array.isArray(b.players) ? parsePlayers(b.players) : []
  if (
    b.v !== 1 ||
    typeof b.runId !== 'string' || !RUN_ID_PATTERN.test(b.runId) ||
    typeof b.missionId !== 'string' || !MISSION_ID_PATTERN.test(b.missionId) ||
    !Number.isInteger(b.frames) || Number(b.frames) < 1 || Number(b.frames) > MAX_FRAMES ||
    !Number.isInteger(b.retries) || Number(b.retries) < 0 || Number(b.retries) > 1_000_000 ||
    !Array.isArray(b.players) || players.length !== b.players.length ||
    players.length < 1 || players.length > MAX_PLAYERS ||
    players.some((p) => p.name.trim().length < 1 || p.name.length > 64 || !TAG_PATTERN.test(p.tag)) ||
    new Set(players.map((p) => p.tag)).size !== players.length ||
    (b.missionTitle !== undefined && (typeof b.missionTitle !== 'string' || b.missionTitle.length > 80)) ||
    (b.coop !== undefined && typeof b.coop !== 'boolean') ||
    (b.createdAt !== undefined && (typeof b.createdAt !== 'string' || b.createdAt.length > 40))
  ) return null
  return {
    runId: b.runId,
    missionId: b.missionId,
    missionTitle: typeof b.missionTitle === 'string' ? b.missionTitle : b.missionId,
    frames: Number(b.frames),
    retries: Number(b.retries),
    coop: typeof b.coop === 'boolean' ? b.coop : players.length > 1,
    players: players.map((p) => ({ name: p.name.trim(), tag: p.tag })),
    createdAt: typeof b.createdAt === 'string' ? b.createdAt : new Date().toISOString(),
  }
}

/** Drop a few nonces that are older than the replay window (bounded work per call). */
async function pruneNonces(tools: ActionTools, nowMs: number): Promise<void> {
  const old = await tools.query<{ nonce: string; seenAt: number }>('ingest_nonces', {
    orderBy: 'seenAt', orderDir: 'asc', limit: 20,
  })
  if (!old.success) return
  for (const record of old.data.records) {
    if (Number(record.data.seenAt) >= nowMs - NONCE_TTL_MS) break
    await tools.remove('ingest_nonces', record.recordId)
  }
}

export async function ingestVerifiedRun(input: {
  secret: string | undefined
  rawBody: string
  headers: Headers
  tools: ActionTools
  nowMs?: number
}): Promise<IngestResult> {
  const { secret, rawBody, headers, tools } = input
  const nowMs = input.nowMs ?? Date.now()
  if (!secret) return { status: 503, body: { success: false, error: 'Verified run ingest is not configured.' } }
  if (new TextEncoder().encode(rawBody).length > MAX_BODY_BYTES) {
    return { status: 413, body: { success: false, error: 'Body too large.' } }
  }
  const nonce = headers.get('x-sgl-nonce')
  const check = await verifyIngestSignature({
    secret,
    body: rawBody,
    timestamp: headers.get('x-sgl-timestamp'),
    nonce,
    signature: headers.get('x-sgl-signature'),
    nowMs,
  })
  if (check !== 'ok') return { status: 401, body: { success: false, error: `Unauthorized (${check}).` } }

  let parsed: unknown
  try { parsed = JSON.parse(rawBody) } catch { parsed = null }
  const run = parseIngestBody(parsed)
  const deleteRunId = typeof parsed === 'object' && parsed !== null &&
    'v' in parsed && parsed.v === 1 && 'deleteRunId' in parsed &&
    typeof parsed.deleteRunId === 'string' && RUN_ID_PATTERN.test(parsed.deleteRunId)
    ? parsed.deleteRunId : null
  if (!run && !deleteRunId) return { status: 400, body: { success: false, error: 'Run fields are invalid.' } }

  // Replay protection: a nonce is accepted once.
  const seen = await tools.query('ingest_nonces', { where: { nonce }, limit: 1 })
  if (!seen.success) return { status: 503, body: { success: false, error: seen.error } }
  if (seen.data.records.length > 0) return { status: 409, body: { success: false, error: 'Replayed request.' } }
  const marked = await tools.create('ingest_nonces', { nonce: nonce as string, seenAt: nowMs })
  if (!marked.success) return { status: 409, body: { success: false, error: 'Replayed request.' } }

  if (deleteRunId) {
    const prior = await tools.query('erased_runs', { where: { runId: deleteRunId }, limit: 1 })
    if (!prior.success) return { status: 503, body: { success: false, error: prior.error } }
    if (!prior.data.records.length) {
      const tombstone = await tools.create('erased_runs', { runId: deleteRunId })
      if (!tombstone.success) return { status: 503, body: { success: false, error: tombstone.error } }
    }
    const matches = await tools.query('verified_runs', { where: { runId: deleteRunId }, limit: 100 })
    if (!matches.success) return { status: 503, body: { success: false, error: matches.error } }
    for (const record of matches.data.records) {
      const removed = await tools.remove('verified_runs', record.recordId)
      if (!removed.success) return { status: 503, body: { success: false, error: removed.error } }
    }
    await pruneNonces(tools, nowMs).catch(() => undefined)
    return { status: 200, body: { success: true, data: { deleted: true } } }
  }
  if (!run) return { status: 400, body: { success: false, error: 'Invalid run.' } }
  const erased = await tools.query('erased_runs', { where: { runId: run.runId }, limit: 1 })
  if (!erased.success) return { status: 503, body: { success: false, error: erased.error } }
  if (erased.data.records.length) {
    const leftovers = await tools.query('verified_runs', { where: { runId: run.runId }, limit: 100 })
    if (!leftovers.success) return { status: 503, body: { success: false, error: leftovers.error } }
    for (const record of leftovers.data.records) {
      const removed = await tools.remove('verified_runs', record.recordId)
      if (!removed.success) return { status: 503, body: { success: false, error: removed.error } }
    }
    return { status: 200, body: { success: true, data: { deleted: true } } }
  }

  const existing = await tools.query<VerifiedRun>('verified_runs', { where: { runId: run.runId }, limit: 1 })
  if (!existing.success) return { status: 503, body: { success: false, error: existing.error } }
  let result: IngestResult
  if (existing.data.records.length > 0) {
    result = { status: 200, body: { success: true, data: { duplicate: true, recordId: existing.data.records[0].recordId } } }
  } else {
    const created = await tools.create<VerifiedRun>('verified_runs', {
      runId: run.runId,
      missionId: run.missionId,
      missionTitle: run.missionTitle,
      frames: run.frames,
      retries: run.retries,
      coop: run.coop,
      playerCount: run.players.length,
      playerNames: run.players.map((p) => p.name).join(' & '),
      playerKey: playerKey(run.players),
      players: JSON.stringify(run.players),
      ranAt: run.createdAt,
    })
    if (!created.success) return { status: 503, body: { success: false, error: created.error } }
    // Delete can race the earlier check. Checking again after create closes that window:
    // either deletion sees this row, or this check sees its durable tombstone.
    const after = await tools.query('erased_runs', { where: { runId: run.runId }, limit: 1 })
    if (!after.success) return { status: 503, body: { success: false, error: after.error } }
    if (after.data.records.length) {
      const removed = await tools.remove('verified_runs', created.data.recordId)
      if (!removed.success) return { status: 503, body: { success: false, error: removed.error } }
      return { status: 200, body: { success: true, data: { deleted: true } } }
    }
    result = { status: 200, body: { success: true, data: { duplicate: false, recordId: created.data.recordId } } }
  }
  await pruneNonces(tools, nowMs).catch(() => undefined)
  return result
}
