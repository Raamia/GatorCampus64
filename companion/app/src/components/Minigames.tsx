import { Gamepad2, MapPin, Music2, Users } from 'lucide-react'
import catalog from '../data/mission-catalog.json'

export function Minigames() {
  return <section className="campus-minigames" aria-labelledby="minigames-title">
    <div className="minigames-heading"><div><span className="section-index">MORE WAYS TO PLAY</span><h2 id="minigames-title">Campus minigames</h2></div><span className="minigame-preview">RHYTHM · SOLO & CO-OP</span></div>
    {catalog.minigames.map((game) => <article className="chomp-card" key={game.id}>
      <div className="chomp-intro">
        <span className="chomp-kicker"><Music2 size={17} aria-hidden/> WATCH · REMEMBER · CHOMP</span>
        <h3>{game.title}</h3>
        <p>{game.objective}</p>
        <div className="chomp-meta"><span><MapPin size={14} aria-hidden/>{game.stage} · Act {game.act}</span><span><Gamepad2 size={14} aria-hidden/>1 player</span><span><Users size={14} aria-hidden/>2+ co-op mode</span></div>
        <div className="chomp-phrase" aria-label="Example four-note pad sequence: 1, 4, 2, 3">{[1, 4, 2, 3].map((pad) => <span key={pad}>{pad}</span>)}<small>WATCH THE PADS.<br/>REPEAT THE PHRASE.</small></div>
        <p className="chomp-grade">{game.grade}. {game.hint}</p>
      </div>
      <div className="chomp-guide">
        <h4>How to play</h4>
        <ol>{game.steps.map((step) => <li key={step}>{step}</li>)}</ol>
        <p className="chomp-coop">{game.multiplayer}</p>
        <div className="chomp-launch"><span>IN-GAME CHAT · ENTER SOLO</span><code>{game.command}</code></div>

      </div>
    </article>)}
  </section>
}
