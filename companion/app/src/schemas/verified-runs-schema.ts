import type { CollectionSchema } from 'deepspace/schema'

/**
 * Verified runs from the hosted game server (docs/web_platform_spec.md §10.4). Written ONLY by the
 * server-side ingestVerifiedRun route (HMAC-signed calls from the game API, src/server/ingest-routes.ts),
 * never by a browser: no role may create or update. Anyone, signed in or not, may read the board.
 * Players are Gator Pass accounts on the game API, not DeepSpace users: `players` is a JSON array of
 * {name, tag} (tag = a stable per-account id from the API that reveals nothing about the account).
 */
export const verifiedRunsSchema: CollectionSchema = {
  name: 'verified_runs',
  columns: [
    { name: 'runId', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'missionId', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'missionTitle', storage: 'text', interpretation: 'plain', immutable: true },
    { name: 'frames', storage: 'number', interpretation: 'plain', required: true, immutable: true },
    { name: 'retries', storage: 'number', interpretation: 'plain', required: true, immutable: true },
    { name: 'coop', storage: 'number', interpretation: { kind: 'boolean' }, required: true, immutable: true },
    { name: 'playerCount', storage: 'number', interpretation: 'plain', required: true, immutable: true },
    { name: 'playerNames', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'playerKey', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'players', storage: 'text', interpretation: { kind: 'json' }, required: true, immutable: true },
    { name: 'ranAt', storage: 'text', interpretation: 'plain', required: true, immutable: true },
  ],
  uniqueOn: ['runId'],
  permissions: {
    '*': { read: true, create: false, update: false, delete: false },
    viewer: { read: true, create: false, update: false, delete: false },
    member: { read: true, create: false, update: false, delete: false },
    admin: { read: true, create: false, update: false, delete: true },
  },
}

/**
 * Nonces of accepted ingest calls, so a captured request cannot be replayed inside the timestamp
 * window. Server-only: no role can write; admins may read for debugging. Pruned by the ingest route.
 */
export const ingestNoncesSchema: CollectionSchema = {
  name: 'ingest_nonces',
  columns: [
    { name: 'nonce', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'seenAt', storage: 'number', interpretation: 'plain', required: true, immutable: true },
  ],
  uniqueOn: ['nonce'],
  permissions: {
    '*': { read: false, create: false, update: false, delete: false },
    viewer: { read: false, create: false, update: false, delete: false },
    member: { read: false, create: false, update: false, delete: false },
    admin: { read: true, create: false, update: false, delete: true },
  },
}
