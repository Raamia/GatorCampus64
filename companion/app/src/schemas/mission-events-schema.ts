import type { CollectionSchema } from 'deepspace/schema'

/**
 * Append-only player-reported mission results. Signed-in members can add
 * results; existing events cannot be changed or deleted.
 */
export const missionEventsSchema: CollectionSchema = {
  name: 'mission_events',
  columns: [
    { name: 'eventType', storage: 'text', interpretation: { kind: 'select', options: ['mission_result'] } },
    { name: 'missionId', storage: 'text', interpretation: 'plain' },
    { name: 'teamSize', storage: 'number', interpretation: 'plain' },
    { name: 'durationSeconds', storage: 'number', interpretation: 'plain' },
    { name: 'retries', storage: 'number', interpretation: 'plain' },
    { name: 'displayName', storage: 'text', interpretation: 'plain' },
    { name: 'occurredAt', storage: 'text', interpretation: 'plain' },
  ],
  permissions: {
    '*': { read: true, create: false, update: false, delete: false },
    viewer: { read: true, create: false, update: false, delete: false },
    member: { read: true, create: true, update: false, delete: false },
    admin: { read: true, create: true, update: false, delete: false },
  },
}
