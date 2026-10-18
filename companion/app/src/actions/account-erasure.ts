import type { ActionTools } from 'deepspace/worker'

export async function soloEraseKey(userId: string, runId: string): Promise<string> {
  const data = new TextEncoder().encode(JSON.stringify(['sgl-solo-erasure', userId, runId]))
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('')
}

/** One bounded page per delivery. Tombstones precede removal; retries resume from surviving rows. */
export async function eraseOfflineRuns(tools: ActionTools, userId: string, beforeMs: number): Promise<boolean> {
  const rows = await tools.query<{ runId: string }>('solo_runs', {
    where: { userId }, orderBy: 'createdAt', orderDir: 'asc', limit: 100,
  })
  if (!rows.success) return false
  for (const row of rows.data.records) {
    const created = Date.parse(row.createdAt)
    if (!Number.isFinite(created)) return false
    if (created > beforeMs) return true
    const key = await soloEraseKey(userId, row.data.runId)
    const seen = await tools.query('erased_solo_runs', { where: { key }, limit: 1 })
    if (!seen.success) return false
    if (!seen.data.records.length && !(await tools.create('erased_solo_runs', { key })).success) return false
    if (!(await tools.remove('solo_runs', row.recordId)).success) return false
  }
  return rows.data.records.length < 100
}
