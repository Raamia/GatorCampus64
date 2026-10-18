# Final showcase and shutdown handoff

Updated from the project owner's decisions. Earlier operational
observations remain in [operations](operations.md); this is the current docket.

## Accepted

- [x] End-to-end character generation/deployment, leaderboard delivery and account
  deletion are good, as confirmed by the owner.
- [x] The approved 23-shape batch and current Qwen behavior are accepted; no further
  tuning to individual reference photos is requested.
- [x] README integration documentation and track assessment are prepared.

## Remaining

- [ ] Merge/deploy the no-login `/showcase` character gallery. The feature branch
  includes synthetic samples and needs no auth, database or inference for viewing.
- [ ] Owner decision on the proposed AI evaluation card; see
  [the explanation](sponsor_track_review.md#ai-evaluation-card--proposal-not-implemented).
- [ ] Optional DEV article; undecided.
- [ ] Publish the team's LinkedIn post, then shut servers down Tuesday night,
  October 20. Shutdown execution belongs to the operator; no shutdown has been
  scheduled or performed by the showcase branch.

## Dropped from this sprint

No new database/backup work, extra cost/monitoring controls, queue-position/ETA
feature, or Tiger Data integration. The deployment is short-lived and expected
concurrency is roughly a dozen players. This decision does not remove the
existing databases required by the currently running app.
