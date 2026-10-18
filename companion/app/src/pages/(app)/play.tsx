import { Copy, ExternalLink } from 'lucide-react'
import { useState } from 'react'

export default function PlayPage() {
  const [copied, setCopied] = useState(false)
  const copy = async () => { await navigator.clipboard.writeText('play.gatorcamp.us:7777'); setCopied(true); window.setTimeout(() => setCopied(false), 1500) }
  return <main className="mx-auto max-w-3xl px-6 py-12 text-foreground"><p className="text-xs font-semibold tracking-[.2em] text-primary">PLAY SUPER GATORLATOR 64</p><h1 className="mt-3 text-4xl font-bold">Meet your gator on campus.</h1><p className="mt-3 max-w-xl text-muted-foreground">The game is native, so install sm64coopdx, connect to the hosted server, and use Gator Pass to select your character.</p><section className="mt-8 space-y-5 rounded-xl border border-border bg-card p-6"><ol className="list-decimal space-y-4 pl-5"><li>Install sm64coopdx 1.5.1 and launch it once with your own US Super Mario 64 ROM.</li><li>Choose <strong>Join → Direct Connect</strong>.</li><li>Enter <code>play.gatorcamp.us</code> and port <code>7777</code>.</li><li>In the game, type <code>/login</code>, approve the QR/code, and choose your gator.</li></ol><button className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2" onClick={() => void copy()}><Copy size={15}/>{copied ? 'Copied' : 'Copy server address'}<code>play.gatorcamp.us:7777</code></button><a className="ml-3 inline-flex items-center gap-2 text-sm underline" href="https://gatorcamp.us" target="_blank" rel="noreferrer">Game guide <ExternalLink size={14}/></a></section></main>
}
