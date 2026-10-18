import { afterEach, expect, it, vi } from 'vitest'
import { fetchGameBoards } from './game-board'
afterEach(() => vi.unstubAllGlobals())
it('reads anonymous rankings directly from the game API without reordering server ranks', async () => {
  const missions = [{ mission: 'reitz_rooftop', title: 'Reitz', rows: [{ rank: 1, names: ['Ali', 'Bo'], frames: 900, retries: 2, players: 2, at: '2026-10-18' }] }]
  const fetcher = vi.fn().mockResolvedValue(Response.json({ missions })); vi.stubGlobal('fetch', fetcher)
  const signal = new AbortController().signal
  expect(await fetchGameBoards(signal)).toEqual(missions)
  expect(fetcher).toHaveBeenCalledWith('https://api.gatorcamp.us/leaderboards', { credentials: 'omit', signal })
})
it('surfaces outages and malformed ranking data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('', { status: 503 })).mockResolvedValueOnce(Response.json({ missions: [{ mission: 'x', title: 'X', rows: [{ names: 'bad' }] }] })))
  await expect(fetchGameBoards(new AbortController().signal)).rejects.toThrow('unavailable')
  await expect(fetchGameBoards(new AbortController().signal)).rejects.toThrow('invalid')
})
