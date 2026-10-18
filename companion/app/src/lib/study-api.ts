import { finishLogin, token } from './gator-api'

export async function studyFetch(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers)
  try { if (await finishLogin()) headers.set('Authorization', `Bearer ${await token()}`) }
  catch { /* Public catalog hints remain available when sign-in is unavailable. */ }
  return fetch(path, { ...init, headers })
}
