/** One app-scoped Durable Object serializes admission across Worker isolates.
 * Counters persist across restarts and expire together at the next UTC hour.
 * Failed upstream attempts consume admission too: retries must remain bounded.
 */
export const USER_HOURLY_LIMIT = 30
export const GLOBAL_HOURLY_LIMIT = 500

type Budget = { hour: number; total: number; users: Record<string, number> }

export class StudyBudgetRoom {
  constructor(private state: DurableObjectState) {}

  async fetch(request: Request): Promise<Response> {
    const { userId } = await request.json<{ userId?: string }>()
    if (!userId || userId.startsWith('anon-') || userId.length > 256) {
      return new Response('Unauthorized', { status: 401 })
    }
    const now = Date.now()
    const hour = Math.floor(now / 3_600_000)
    // Prefix avoids special object keys such as __proto__ for arbitrary subjects.
    const key = `user:${userId}`
    const accepted = await this.state.storage.transaction(async (tx) => {
      let budget = await tx.get<Budget>('budget')
      if (!budget || budget.hour !== hour) budget = { hour, total: 0, users: {} }
      const used = budget.users[key] ?? 0
      if (used >= USER_HOURLY_LIMIT || budget.total >= GLOBAL_HOURLY_LIMIT) return false
      budget.users[key] = used + 1
      budget.total++
      await tx.put('budget', budget)
      return true
    })
    return new Response(null, {
      status: accepted ? 204 : 429,
      headers: accepted ? {} : { 'Retry-After': String(Math.ceil(((hour + 1) * 3_600_000 - now) / 1000)) },
    })
  }
}
