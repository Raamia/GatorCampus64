# NPC chat: packet-size crash fix

coopdx custom-packet strings are limited to 256 **bytes**, not characters. `sgl_npc.lua` was
sending the question, the asker's full stats blob, and the bridge's reply as single packet
fields with no bound — a long question (especially with multi-byte UTF-8), a reply from Gemini,
or just having several stages' worth of stats in `my_stats()` could exceed that limit and crash
the client/server on send.

Fixed in `mods/sgl64/sgl_npc.lua` by splitting any string that can exceed the limit across
several `textN` packet fields (`pack_text`/`unpack_text`) and truncating at a UTF-8-safe boundary
(`bounded`) before sending:

- `npc_say` (host -> clients, the reply or the "..." placeholder): bounded to 600 bytes, 3 pieces.
- `ask` (client -> host, `npc_ask`): the question bounded to 240 bytes; stats split into 4 pieces
  (960 bytes). NPC location descriptions are no longer part of the client-sent stats — they're
  long enough on their own to blow the budget and crowd out everything else (stars, lives,
  where the asker is) — the host appends them itself in `host_enqueue` after receiving the
  request, since it already knows where its own mascots are.
- `/albert`/`/alberta`'s `npc_q` chat-announce broadcast: bounded to 480 bytes, 2 pieces.

`mods/sgl64/sgl_bridge.lua` got two related one-line fixes: the generic bridge event relay no
longer matches `t == "npc_ask"` (that path skipped `host_enqueue`'s own validation entirely, so a
forged event could still send an oversized/unvalidated request straight to the bridge), and
`route_command` drops empty-string fields before building a packet (coopdx rejects them).

`tools/luatest/sim.lua`'s `network_send`/`network_send_to` stubs now assert every packet string
is 1..256 bytes, so a regression here fails the test suite instead of only showing up live.

## Deferred: sender-identity hardening

A fuller version of this fix also had the host derive the asker's identity (name, one-pending-
per-connection, a cooldown) from the network transport itself instead of trusting the `player`
field the client sends — closing a spoofing/flood vector. That requires a connected-peer
argument on `HOOK_ON_PACKET_RECEIVE` that stock sm64coopdx doesn't provide (see the
unshipped `tools/coopdx/npc-packet-sender.patch` on `fix/npc-interaction-errors`), and the client
side refuses to send `npc_ask` at all when the engine doesn't expose that capability — which
would silently break NPC chat for every non-host player until all clients and the host run the
patched engine. Deferred until that engine patch actually ships; this fix keeps the existing
trust-the-client-supplied-name model.
