import { useEffect, useSyncExternalStore } from 'react'
import { finishLogin, profile } from './gator-api'

type Session = { loaded: boolean; signedIn: boolean; name?: string; email?: string; error?: string }
const initial: Session = { loaded: false, signedIn: false }
let session = initial
let pending: Promise<void> | undefined
const listeners = new Set<() => void>()
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
const snapshot = () => session
const serverSnapshot = () => initial

export function refreshGatorSession() {
  pending ??= (async () => {
    try {
      const signedIn = await finishLogin()
      const user = signedIn ? await profile() : undefined
      session = { loaded: true, signedIn, name: user?.name ?? user?.nickname, email: user?.email }
    } catch (error) { session = { loaded: true, signedIn: false, error: (error as Error).message } }
    for (const listener of listeners) listener()
  })().finally(() => { pending = undefined })
  return pending
}

export function useGatorSession() {
  const current = useSyncExternalStore(subscribe, snapshot, serverSnapshot)
  useEffect(() => { if (!session.loaded) void refreshGatorSession() }, [])
  return current
}
