import type { Env } from '../../worker.js'
import { ingestVerifiedRun, MAX_BODY_BYTES } from '../actions/verified-runs.js'
import { createActionTools } from './action-routes.js'

/** All ingest/delete requests for this app share one serialized coordinator. The record
 * room holds the durable deletion tombstones; a coordinator restart cannot lose them.
 * Serializing the whole operation prevents delete/create races across Worker isolates.
 */
export class RunIngestRoom {
  constructor(private state: DurableObjectState, private env: Env) {}

  async fetch(request: Request): Promise<Response> {
    const rawBody = await request.text()
    if (new TextEncoder().encode(rawBody).length > MAX_BODY_BYTES) {
      return Response.json({ success: false, error: 'Body too large.' }, { status: 413 })
    }
    return this.state.blockConcurrencyWhile(async () => {
      const result = await ingestVerifiedRun({
        secret: this.env.DEEPSPACE_INGEST_SECRET,
        rawBody,
        headers: request.headers,
        tools: createActionTools(this.env, this.env.OWNER_USER_ID, ''),
      })
      return Response.json(result.body, { status: result.status })
    })
  }
}
