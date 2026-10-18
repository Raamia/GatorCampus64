import { getAuthToken } from 'deepspace'

export async function studyFetch(path: string, init: RequestInit): Promise<Response> {
  const token = await getAuthToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return fetch(path, { ...init, headers })
}
