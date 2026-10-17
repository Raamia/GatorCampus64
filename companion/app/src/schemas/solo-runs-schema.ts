import type { CollectionSchema } from 'deepspace/schema'

/**
 * Append-only OFFLINE game results, sent by the player's own machine through
 * submitGameRun (the macOS bridge). The client reports its own time, so these
 * rows are labelled unverified "offline" runs and are never mixed into the
 * verified board (verified_runs, docs/web_platform_spec.md §10.4).
 * Authenticated players can read them and create their own rows; only admins
 * can remove a bad entry.
 */
export const soloRunsSchema: CollectionSchema = {
  name: 'solo_runs',
  columns: [
    { name: 'runId', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'userId', storage: 'text', interpretation: 'plain', required: true, userBound: true, immutable: true },
    { name: 'playerTag', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'missionId', storage: 'text', interpretation: 'plain', required: true, immutable: true },
    { name: 'elapsedFrames', storage: 'number', interpretation: 'plain', required: true, immutable: true },
    { name: 'retries', storage: 'number', interpretation: 'plain', required: true, immutable: true },
    { name: 'assisted', storage: 'number', interpretation: { kind: 'boolean' }, required: true, immutable: true },
    { name: 'gameVersion', storage: 'text', interpretation: 'plain', required: true, immutable: true },
  ],
  ownerField: 'userId',
  uniqueOn: ['userId', 'runId'],
  permissions: {
    '*': { read: false, create: false, update: false, delete: false },
    viewer: { read: true, create: false, update: false, delete: false },
    member: { read: true, create: true, update: false, delete: false },
    admin: { read: true, create: true, update: true, delete: true },
  },
}
