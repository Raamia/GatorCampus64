import { describe, expect, it } from 'vitest'
import { bestVerifiedRows, compactTag, formatFrames, parsePlayers, playerKey, type VerifiedRun } from './leaderboard'

/**
 * `bestVerifiedRows`/`formatFrames`'s core ranking behavior (best run per
 * player set, basic time formatting) is already covered in
 * src/server/ingest-routes.test.ts's "verified board" block, alongside the
 * route that feeds this data. This file covers what that one doesn't: the
 * tie-break order, record filtering, and the player-tag helpers the
 * leaderboard page (src/pages/(app)/leaderboard.tsx) renders directly.
 */

function run(overrides: Partial<VerifiedRun> & { frames: number }): { data: VerifiedRun; createdAt?: string } {
  return {
    data: {
      runId: `r-${Math.random()}`,
      missionId: 'm1',
      missionTitle: 'Mission',
      frames: overrides.frames,
      retries: overrides.retries ?? 0,
      coop: overrides.coop ?? false,
      playerCount: 1,
      playerNames: 'Alice',
      playerKey: overrides.playerKey ?? '',
      players: overrides.players ?? [{ name: 'Alice', tag: 'A' }],
      ranAt: overrides.ranAt ?? '2026-10-17T12:00:00Z',
    },
  }
}

describe('bestVerifiedRows tie-breaks', () => {
  it('breaks a frames tie by fewer retries', () => {
    const rows = bestVerifiedRows([
      run({ frames: 100, retries: 3, players: [{ name: 'Slow Retrier', tag: 'A' }] }),
      run({ frames: 100, retries: 0, players: [{ name: 'Clean Run', tag: 'B' }] }),
    ], 10)
    expect(rows.map((r) => r.names[0])).toEqual(['Clean Run', 'Slow Retrier'])
  })

  it('breaks a frames+retries tie by the earlier run', () => {
    const rows = bestVerifiedRows([
      run({ frames: 100, retries: 0, ranAt: '2026-10-17T12:00:05Z', players: [{ name: 'Later', tag: 'A' }] }),
      run({ frames: 100, retries: 0, ranAt: '2026-10-17T12:00:01Z', players: [{ name: 'Earlier', tag: 'B' }] }),
    ], 10)
    expect(rows.map((r) => r.names[0])).toEqual(['Earlier', 'Later'])
  })

  it('truncates to the requested limit, keeping the fastest rows', () => {
    const records = [300, 100, 200].map((frames, i) =>
      run({ frames, players: [{ name: `P${i}`, tag: `T${i}` }] }))
    const rows = bestVerifiedRows(records, 2)
    expect(rows.map((r) => r.elapsedFrames)).toEqual([100, 200])
  })
})

describe('bestVerifiedRows filtering', () => {
  it('drops non-positive or non-integer frame counts', () => {
    const rows = bestVerifiedRows([
      run({ frames: 0 }),
      run({ frames: -5 }),
      run({ frames: 12.5 }),
      run({ frames: 150 }),
    ], 10)
    expect(rows.map((r) => r.elapsedFrames)).toEqual([150])
  })

  it('drops records with no parseable players', () => {
    const rows = bestVerifiedRows([
      run({ frames: 100, players: [] }),
      run({ frames: 110, players: 'not json' as unknown as VerifiedRun['players'] }),
      run({ frames: 120, players: [{ name: 'Only valid', tag: 'A' }] }),
    ], 10)
    expect(rows.map((r) => r.elapsedFrames)).toEqual([120])
  })

  it('uses the stored playerKey over a recomputed one when present', () => {
    // Two runs with the same single player but a deliberately different
    // stored playerKey group separately instead of merging.
    const rows = bestVerifiedRows([
      run({ frames: 100, playerKey: 'group-1', players: [{ name: 'Alice', tag: 'A' }] }),
      run({ frames: 90, playerKey: 'group-2', players: [{ name: 'Alice', tag: 'A' }] }),
    ], 10)
    expect(rows).toHaveLength(2)
  })
})

describe('formatFrames', () => {
  it('formats sub-minute, whole-minute and multi-minute times at 30fps', () => {
    expect(formatFrames(0)).toBe('0:00.00')
    expect(formatFrames(30)).toBe('0:01.00')
    expect(formatFrames(30 * 75)).toBe('1:15.00')
    expect(formatFrames(1250)).toBe('0:41.67')
  })
})

describe('parsePlayers', () => {
  it('parses a JSON-string players field', () => {
    expect(parsePlayers(JSON.stringify([{ name: 'Alice', tag: 'A' }]))).toEqual([{ name: 'Alice', tag: 'A' }])
  })

  it('returns an empty list for invalid JSON, non-arrays, or malformed entries', () => {
    expect(parsePlayers('not json')).toEqual([])
    expect(parsePlayers({ name: 'Alice' })).toEqual([])
    expect(parsePlayers([{ name: 'Alice' }, { tag: 'B' }, 'nope', null])).toEqual([])
  })

  it('keeps only well-formed entries out of a mixed array', () => {
    expect(parsePlayers([{ name: 'Alice', tag: 'A' }, { name: 'bad' }])).toEqual([{ name: 'Alice', tag: 'A' }])
  })
})

describe('playerKey', () => {
  it('sorts tags so player order does not change the group identity', () => {
    expect(playerKey([{ name: 'B', tag: 'bb' }, { name: 'A', tag: 'aa' }])).toBe('aa+bb')
    expect(playerKey([{ name: 'A', tag: 'aa' }, { name: 'B', tag: 'bb' }])).toBe('aa+bb')
  })
})

describe('compactTag', () => {
  it('joins and sanitizes names for a solo and a co-op run', () => {
    expect(compactTag([{ name: 'Alice', tag: 'A' }])).toBe('Alice')
    expect(compactTag([{ name: 'Ann', tag: 'A' }, { name: 'Bob', tag: 'B' }])).toBe('Ann-Bob')
  })

  it('collapses disallowed characters to underscores', () => {
    expect(compactTag([{ name: 'A B', tag: 'A' }])).toBe('A_B')
  })

  it('truncates to 32 characters', () => {
    const long = compactTag([{ name: 'x'.repeat(40), tag: 'A' }])
    expect(long).toHaveLength(32)
  })

  it('falls back to the first player tag when the name sanitizes to nothing', () => {
    expect(compactTag([{ name: '', tag: 'validtag' }])).toBe('validtag')
  })

  it('falls back to GATOR when neither the name nor the tag are usable', () => {
    expect(compactTag([{ name: '', tag: 'has spaces' }])).toBe('GATOR')
    expect(compactTag([])).toBe('GATOR')
  })
})
