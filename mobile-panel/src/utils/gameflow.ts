// Utility functions for gameflow state management

import type { GameflowPhase, ChampSelectSession } from "@/types";

export type ActionType = "ban" | "pick" | null;
export type FlowStep = "waiting" | "ready" | "ban" | "pick" | "setup";

export function getActionType(champSelect: ChampSelectSession | null): ActionType {
  if (!champSelect || typeof champSelect !== "object") return null;
  
  const localCell = champSelect.localPlayerCellId;
  
  for (const turn of champSelect.actions || []) {
    for (const action of turn || []) {
      if (action?.actorCellId !== localCell) continue;
      if (action?.completed) continue;
      if (action?.type === "ban") return "ban";
      if (action?.type === "pick") return "pick";
    }
  }
  
  return null;
}

export function getFlowStep(
  phase: GameflowPhase,
  actionType: ActionType,
  hasChampion: boolean
): FlowStep {
  if (phase === "ReadyCheck") return "ready";
  
  if (phase === "ChampSelect") {
    if (actionType === "ban") return "ban";
    if (actionType === "pick") return "pick";
    if (hasChampion) return "setup";
    return "pick";
  }
  
  return "waiting";
}

export function stageProgress(step: FlowStep): number {
  const map: Record<FlowStep, number> = {
    waiting: 0,
    ready: 1,
    ban: 2,
    pick: 3,
    setup: 4,
  };
  return map[step] ?? 0;
}
