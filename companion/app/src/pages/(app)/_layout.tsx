import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import Navigation from '../../components/Navigation'
import { APP_NAME } from '../../constants'

/** Public game pages use the game API; account controls share Gator Pass. */
export default function AppLayout() {
  return <>
    <title>{APP_NAME}</title>
    <div className="app-shell flex h-screen flex-col bg-background overflow-hidden">
      <Navigation />
      <main className="app-content flex-1 overflow-y-auto min-h-0">
        <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>}><Outlet /></Suspense>
      </main>
    </div>
  </>
}
