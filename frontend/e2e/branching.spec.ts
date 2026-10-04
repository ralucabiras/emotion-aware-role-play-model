import { expect, test, type Page } from '@playwright/test'
import { expectAccessible, installApiMock } from './support'
import type { BranchLineage, ConversationTurn, DialogueDecision, RolePlayState, SessionResponse } from '../src/types/api'

const t=(n:number)=>`2026-09-28T10:00:${String(n).padStart(2,'0')}Z`
const turn=(id:string,role:'user'|'assistant',content:string,n:number):ConversationTurn=>({id,role,content,created_at:t(n),generation:role==='assistant'?{source:'deterministic_roleplay'}:null})
const snapshot=(stage:string,count:number)=>({dialogue:{stage,stage_labels:{explain:'Explain the situation',constraints:'Discuss constraints',resolved:'Agreement reached'},outcome:stage==='resolved'?'agreement':null},status:stage==='resolved'?'completed':'active',turn:count,success_progress:stage==='resolved'?1:.33,difficulty:.5,cooperation:.5})
const decision=(id:string,reply:string,before:string,after:string,count:number):DialogueDecision=>({user_turn_id:id,assistant_turn_id:reply,before:snapshot(before,count),after:snapshot(after,count+1),action:'hold_delivery_constraint',reason_codes:['workable_option_missing'],evidence_turn_ids:['request'],scenario_version:'workload-v2',policy_version:'workload-v2',scoring_version:'workload-v2',generation:{source:'deterministic_roleplay'}})
const first=decision('request','objection','explain','constraints',0)
const second=decision('apology','reply','constraints','constraints',1)
const parentTurns=[turn('opening','assistant','What is at risk?',0),turn('request','user','Could we prioritise my 12 hours of work?',1),turn('objection','assistant','The report must be ready Friday.',2),turn('apology','user','Sorry, sorry, perhaps I can do everything.',3),turn('reply','assistant','What other work could move?',4)]
const parentState:RolePlayState={scenario_id:'workload',status:'completed',turn:2,difficulty_level:'intermediate',success_progress:.33,started_at:t(0),completed_at:t(5),measurement_ended_at:t(5),policy_version:'workload-v2',decisions:[first,second],dialogue:{stage:'constraints',final_agreement:null},evidence:[]}

async function fixture(page:Page) {
  const mock=await installApiMock(page,{existingSession:true});mock.turns=parentTurns.map(item=>({...item}));mock.roleplay={...parentState}
  let child:SessionResponse|null=null
  let missing=false, conflict=false, comparisonFailure=false
  const requests:Array<Record<string,unknown>>=[]
  await page.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname.replace('/api','')
    const json=(body:unknown,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
    if(path==='/sessions/session-1/branches') {
      requests.push(req.postDataJSON())
      if(conflict)return json({detail:'The original changed. Reload it before creating an alternative.'},409)
      const branch:BranchLineage={parent_session_id:'session-1',parent_version:0,branch_point_turn_id:'apology',branch_group_id:'session-1',request_id:String(req.postDataJSON().request_id),before:second.before,copied_turn_ids:['opening','request','objection'],copied_evidence_turns:[1],generation_mode:'deterministic',created_at:t(10)}
      child={session_id:'child-1',version:1,title:'Alternative: Workload',turns:parentTurns.slice(0,3),roleplay:{...parentState,status:'active',completed_at:null,measurement_ended_at:null,started_at:t(10),turn:1,decisions:[first]},branch,emotion_state:{dominant_emotion:'neutral',valence:0,arousal:.2,confidence:.7,trend:'stable'},feedback:null,takeaway:'',questionnaires:{},questionnaire_skips:{}}
      return json(child,201)
    }
    if(path==='/sessions/child-1'&&req.method()==='GET')return json(child)
    if(path==='/sessions/child-1/questionnaires/post/close')return route.fulfill({status:204})
    if(path==='/chat'&&req.postDataJSON().session_id==='child-1'&&child) {
      const userTurn=turn('alternative-user','user',req.postDataJSON().message,11),reply=turn('alternative-reply','assistant','Agreed: protect Friday and move the other work.',12)
      child.turns=[...child.turns,userTurn,reply];child.version=2
      child.roleplay={...child.roleplay!,status:'completed',completed_at:t(12),measurement_ended_at:t(13),turn:2,success_progress:1,dialogue:{stage:'resolved',outcome:'agreement',final_agreement:userTurn.content},decisions:[first,decision(userTurn.id,reply.id,'constraints','resolved',1)]}
      child.feedback={session_id:'child-1',scenario_id:'workload',observed:['You proposed a trade-off.'],strengths:[],suggestions:[],metrics:[],comparisons:[],generation_source:'deterministic',evidence_scope:'continuation'}
      return json({version:2,user_turn:userTurn,turn:reply,roleplay:child.roleplay,feedback:child.feedback,decision:{emotion_state:child.emotion_state,strategy:'clarify',cognitive_assessment:{possible_distortion:null,possible_cause:null,intent:'practice'},decision_reasons:[],analyzer_version:'synthetic'}})
    }
    if(path==='/sessions/child-1/comparison'&&child) {
      if(comparisonFailure)return json({detail:'Comparison temporarily unavailable'},503)
      return json({shared_context:parentTurns.slice(0,3),branch:child.branch,unavailable_reason:missing?'The original was deleted or expired. Your alternative is still available.':null,original:missing?null:{session_id:'session-1',title:'Original',status:'completed',outcome:null,agreement:null,completion_reason:'user_finished',turns:parentTurns.slice(3),decisions:[second],evidence:[]},alternative:{session_id:'child-1',title:child.title,status:child.roleplay!.status,outcome:child.roleplay!.dialogue?.outcome??null,agreement:child.roleplay!.dialogue?.final_agreement??null,completion_reason:child.roleplay!.completion_reason??null,turns:child.turns.slice(3),decisions:child.roleplay!.decisions!.slice(1),evidence:[]}})
    }
    return route.fallback()
  })
  return {mock,requests,setMissing:()=>{missing=true},setConflict:(value:boolean)=>{conflict=value},setComparisonFailure:(value:boolean)=>{comparisonFailure=value},child:()=>child}
}

test('branches selected replay turn, submits alternative and compares after reload',async({page})=>{
  const fixtureState=await fixture(page)
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await page.getByRole('button',{name:'Turn 2'}).click()
  await page.getByRole('button',{name:'Try a different response here'}).focus();await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/session=child-1/)
  await expect(page.getByText('Alternative practice · 3 shared context messages.',{exact:false})).toBeVisible()
  await expect(page.getByText('Shared context ·',{exact:false})).toHaveCount(3)
  await expect(page.getByRole('textbox')).toHaveValue('Sorry, sorry, perhaps I can do everything.')
  expect(fixtureState.requests[0]).toMatchObject({turn_id:'apology',expected_version:0})
  await page.getByRole('textbox').fill('I can keep Friday if we move the other tasks to Monday.')
  await page.getByRole('button',{name:'Send message'}).click()
  await page.getByRole('button',{name:'Compare',exact:true}).click()
  const original=page.getByRole('region',{name:'Original continuation'}),alternative=page.getByRole('region',{name:'Alternative continuation'})
  await expect(original.getByText('Sorry, sorry, perhaps I can do everything.')).toBeVisible()
  await expect(alternative.getByText('Agreed: protect Friday and move the other work.')).toBeVisible()
  await page.getByText('Shared context (3 messages)',{exact:true}).click()
  await expect(page.getByText('The report must be ready Friday.',{exact:true})).toHaveCount(1)
  await expectAccessible(page)
  expect(fixtureState.mock.turns).toEqual(parentTurns)
  await page.reload();await page.getByRole('button',{name:'Compare',exact:true}).click()
  await expect(alternative.getByText('Agreed: protect Friday and move the other work.')).toBeVisible()
  await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText('What is at risk?',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Try a different response here'})).toHaveCount(0)
})

test('comparison handles missing parent and recovers from loading failure',async({page})=>{
  const data=await fixture(page)
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click();await page.getByRole('button',{name:'Turn 2'}).click();await page.getByRole('button',{name:'Try a different response here'}).click()
  data.setMissing();data.setComparisonFailure(true)
  await page.getByRole('button',{name:'Compare',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Comparison temporarily unavailable')
  data.setComparisonFailure(false);await page.getByRole('button',{name:'Retry comparison'}).click()
  await expect(page.getByRole('heading',{name:'Original unavailable'})).toBeVisible()
  await expect(page.getByRole('button',{name:'Open original rehearsal'})).toHaveCount(0)
  await expect(page.getByText('No new response yet.',{exact:false})).toBeVisible()
})

test('stale branch failure preserves source and allows reload',async({page})=>{
  const data=await fixture(page);data.setConflict(true)
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click();await page.getByRole('button',{name:'Turn 2'}).click();await page.getByRole('button',{name:'Try a different response here'}).click()
  await expect(page.getByRole('alert')).toHaveText('The original changed. Reload it before creating an alternative.')
  await expect(page).toHaveURL(/session=session-1/)
  expect(data.child()).toBeNull()
  await page.getByRole('button',{name:'Reload saved session'}).click()
  await expect(page.getByRole('heading',{name:'Review your rehearsal.'})).toBeVisible()
})
