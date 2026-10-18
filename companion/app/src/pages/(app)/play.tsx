import { Copy, ExternalLink, Gamepad2, QrCode, Smartphone, Wrench } from 'lucide-react'
import { useState } from 'react'

const ADDRESS = 'play.gatorcamp.us:7777'

const steps = [
  {
    icon: Wrench,
    title: 'Install sm64coopdx',
    body: <>Download <strong><a href="https://github.com/coop-deluxe/sm64coopdx/releases" target="_blank" rel="noreferrer">sm64coopdx v1.5.1 <ExternalLink size={12} className="play-step-link-icon" /></a></strong> and launch it once with your own US Super Mario 64 ROM (not included).</>,
  },
  {
    icon: Gamepad2,
    title: 'Direct connect',
    body: <>Choose <strong>Join → Direct Connect</strong>, then enter <code>play.gatorcamp.us</code> on port <code>7777</code>.</>,
  },
  {
    icon: QrCode,
    title: 'Link Gator Pass',
    body: <>Type <code>/login</code> in game and scan the QR code — or enter the device code — with your phone.</>,
  },
  {
    icon: Smartphone,
    title: 'Pick your gator',
    body: <>Approve on your phone and your built gator is selected for you. Your name tag gets a star.</>,
  },
]

export default function PlayPage() {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(ADDRESS)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }
  return <main className="play-page">
    <header className="play-hero">
      <p className="play-kicker">PLAY SUPER GATORLATOR 64</p>
      <h1>Meet your gator<br /><em>on campus.</em></h1>
      <p className="play-sub">The game is native, so install sm64coopdx, connect to the hosted server, and use Gator Pass to select your character — right from inside the game.</p>
    </header>
    <div className="play-layout">
      <ol className="play-steps">
        {steps.map((step, i) => <li key={step.title} className="play-step">
          <span className="play-step-n">{String(i + 1).padStart(2, '0')}</span>
          <step.icon size={18} className="play-step-icon" aria-hidden />
          <div><h3>{step.title}</h3><p>{step.body}</p></div>
        </li>)}
      </ol>
      <aside className="play-server">
        <span className="play-server-label">HOSTED SERVER</span>
        <code className="play-server-address">{ADDRESS}</code>
        <button className="play-copy" onClick={() => void copy()}><Copy size={15} />{copied ? 'Copied to clipboard' : 'Copy server address'}</button>
        <a className="play-guide" href="https://gatorcamp.us" target="_blank" rel="noreferrer">Full game guide <ExternalLink size={13} /></a>
      </aside>
    </div>
  </main>
}
