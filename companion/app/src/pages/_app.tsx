/** Root shell for static and dynamic pages. Gator Pass session checks run only
 * in client effects; prerendering remains independent of browser credentials. */

import { Suspense } from 'react'
import { Outlet, useRouteError } from 'react-router-dom'
import { ErrorScreen } from '../components/ErrorScreen'
import { ToastProvider, TooltipProvider } from '@/components/ui'

export default function App() {
  return (
    <ToastProvider>
      {/* The single TooltipProvider: owns the hover delay for every Tooltip
          and groups them so adjacent triggers switch instantly. Tune delay
          here — per-Tooltip providers would shadow it (see ui/Tooltip.tsx). */}
      <TooltipProvider>
        {/* data-testid="app-root" is the canonical "app shell mounted" hook,
            present on every page (static and dynamic). Don't rename without
            updating templates/tests. */}
        <div data-testid="app-root" className="min-h-screen bg-background text-foreground">
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-muted-foreground">Loading...</div>}>
            <Outlet />
          </Suspense>
        </div>
      </TooltipProvider>
    </ToastProvider>
  )
}

/**
 * Root error boundary. Generouted wires a `_app` `Catch` export to the root
 * route's errorElement, so any render-time crash in a page — a thrown error,
 * or a hooks-rule violation like React #310 — lands here instead of React
 * Router's raw minified screen. ErrorScreen decodes the error for the developer.
 */
export function Catch() {
  const error = useRouteError()
  return <ErrorScreen error={error} />
}

/** Root fallback shown while Generouted loads the first lazy route module. */
export function HydrateFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
      Loading...
    </div>
  )
}
