import type { ActionHandler } from 'deepspace/worker'
import type { Env } from '../../worker'
import { getGameLeaderboard, submitGameRun } from './game-runs.js'

export const actions: Record<string, ActionHandler<Env>> = {
  getGameLeaderboard,
  submitGameRun,
}
