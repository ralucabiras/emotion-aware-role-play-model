export const PRACTICE_GOALS = [
  {id:'assertiveness', label:'Become more assertive', description:'State your position clearly while remaining respectful.', scenario:'boundary'},
  {id:'clear_requests', label:'Make clearer requests', description:'Turn a difficult situation into a specific, workable ask.', scenario:'workload'},
  {id:'reduce_apologising', label:'Reduce excessive apologising', description:'Hold a boundary without weakening it through repeated apologies.', scenario:'boundary'},
  {id:'needs_without_blame', label:'Express needs without blame', description:'Use I-statements and concrete requests in close relationships.', scenario:'relationship'},
  {id:'calm_during_pushback', label:'Stay composed during pushback', description:'Practise maintaining your message when the other person resists.', scenario:'colleague_feedback'},
  {id:'prepare_conversation', label:'Prepare a specific conversation', description:'Reflect, choose your wording, and rehearse before speaking.', scenario:'deadline'},
] as const

export type PracticeGoalId = typeof PRACTICE_GOALS[number]['id']

export function goalLabel(id: string) {
  return PRACTICE_GOALS.find(goal => goal.id === id)?.label ?? id.replaceAll('_', ' ')
}

export function recommendedScenario(goals: string[]): string {
  return PRACTICE_GOALS.find(goal => goals.includes(goal.id))?.scenario ?? 'workload'
}
