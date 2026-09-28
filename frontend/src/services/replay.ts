import type { ConversationTurn, RolePlayState } from '../types/api'

// Backend timestamps retain microseconds. Date.parse alone would round both
// completion and a later reflection down to the same millisecond.
const timestamp=(value:string)=>new Date(value).toISOString().slice(0,19)+'.'+(value.match(/\.(\d+)/)?.[1]??'').padEnd(9,'0')

// Project saved records only. Never infer missing decisions, predictions or spans.
export function rehearsalReplay(turns:ConversationTurn[], state:RolePlayState, copiedTurnIds:string[] = []) {
  let end = state.measurement_ended_at ?? state.completed_at
  if (!state.measurement_ended_at && state.completed_at) {
    // Older sessions recorded completion before appending the closing reply.
    for (let i=1;i<turns.length;i++) {
      if (turns[i].role==='assistant' && turns[i-1].role==='user' &&
          timestamp(turns[i-1].created_at)<=timestamp(state.completed_at) &&
          timestamp(turns[i].created_at)>timestamp(end!)) end=turns[i].created_at
    }
  }
  const boundaryKnown=Boolean(end)
  const context=new Set(copiedTurnIds)
  const visible=turns.filter(turn => context.has(turn.id) || ((!state.started_at || timestamp(turn.created_at)>=timestamp(state.started_at)) &&
    (end ? timestamp(turn.created_at)<=timestamp(end) : false)))
  const ids=new Set(visible.map(turn=>turn.id))
  const decisions=(state.decisions??[]).filter(item=>ids.has(item.user_turn_id)&&ids.has(item.assistant_turn_id))
  return { turns:visible, decisions, boundaryKnown }
}
