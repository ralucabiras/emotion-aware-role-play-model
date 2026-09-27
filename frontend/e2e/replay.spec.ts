import { expect, test } from '@playwright/test'
import { expectAccessible, installApiMock } from './support'
import { rehearsalReplay } from '../src/services/replay'
import type { ConversationTurn, RolePlayState } from '../src/types/api'

const time=(second:number)=>`2026-09-22T10:00:${String(second).padStart(2,'0')}Z`
const turn=(id:string,role:'user'|'assistant',second:number,content:string):ConversationTurn=>({id,role,created_at:time(second),content})
const turns=[turn('opening','assistant',0,'What needs to change?'),turn('request','user',1,'Could we move the internal report to Monday?'),turn('objection','assistant',2,'The client report must be ready Friday.'),turn('agreement','user',3,'I can finish the client report Friday and move the internal report to Monday.'),turn('closing','assistant',4,'We have agreed on those priorities.'),turn('reflection','user',6,'Later private reflection'),turn('reflection-reply','assistant',7,'Later reflection response')]
const snapshot=(stage:string)=>({dialogue:{stage,stage_labels:{explain:'Explain the situation',constraints:'Discuss constraints',resolved:'Agreement reached'},objection:'client deadline'},status:stage==='resolved'?'completed':'active',turn:1,success_progress:.5,difficulty:.4,cooperation:.5})
const decision=(user:string,assistant:string,before:string,after:string)=>({user_turn_id:user,assistant_turn_id:assistant,before:snapshot(before),after:snapshot(after),action:'raise_constraint',reason_codes:['concrete_request'],evidence_turn_ids:['request'],scenario_version:'workload-v2',policy_version:'dialogue-test-v1',scoring_version:'scoring-test-v1',generation:{source:'template',model:null,latency_ms:0}})
const evidence={turn:1,conversation_turn_id:'request',concrete_request:true,excessive_apology:false,maintained_boundary:false,blame_language:false,specific_detail:true,i_statement:false,language_features:['request']}
const state:RolePlayState={scenario_id:'workload',status:'completed',difficulty_level:'intermediate',turn:2,success_progress:1,started_at:time(0),completed_at:time(3),measurement_ended_at:time(5),evidence:[evidence],decisions:[decision('request','objection','explain','constraints'),decision('agreement','closing','constraints','resolved')]}

test('saved replay links evidence after reload without writes or regeneration',async({page})=>{
  const mock=await installApiMock(page,{existingSession:true});mock.turns=turns.map(item=>({...item}));mock.roleplay={...state}
  const writes:string[]=[];page.on('request',request=>{if(request.method()!=='GET'&&request.url().includes('/api/'))writes.push(request.url())})
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Replay your rehearsal.'})).toBeVisible()
  await expect(page.getByText('Later private reflection')).toHaveCount(0)
  await page.getByRole('button',{name:'Turn 2'}).click()
  await expect(page.getByText('Discuss constraints → Agreement reached')).toBeVisible()
  await page.getByRole('button',{name:'View evidence 1',exact:true}).click()
  await expect(page.locator('#replay-request')).toBeFocused()
  await page.reload();await page.getByRole('button',{name:'Replay',exact:true}).click()
  await page.getByRole('button',{name:'View feedback evidence 1'}).focus();await page.keyboard.press('Enter')
  await expect(page.locator('#replay-request')).toBeFocused()
  await page.getByText('Technical details',{exact:true}).click()
  await expect(page.getByText(/Dialogue policy: dialogue-test-v1/)).toBeVisible()
  await expectAccessible(page)
  // Existing study navigation closes ratings on leaving Feedback; replay has no writes.
  expect(writes.filter(url=>!url.endsWith('/questionnaires/post/close'))).toEqual([])
})

test('legacy replay has honest missing decisions and missing source links',async({page})=>{
  const mock=await installApiMock(page,{existingSession:true});mock.turns=turns.map(item=>({...item}));mock.roleplay={...state,decisions:[],measurement_ended_at:null,evidence:[{...evidence,conversation_turn_id:null}]}
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText('We have agreed on those priorities.')).toBeVisible()
  await expect(page.getByText('Later private reflection')).toHaveCount(0)
  await expect(page.getByText(/Decision details unavailable\./)).toBeVisible()
  await expect(page.getByText('Evidence 1: source unavailable')).toBeVisible()
  await expect(page.getByText(/No saved voice prediction/)).toBeVisible()
})

test('uncertain saved predictions display disagreement, pacing and provenance',async({page})=>{
  const mock=await installApiMock(page,{existingSession:true});mock.turns=turns.map(item=>({...item}));mock.roleplay={...state,decisions:[{...state.decisions![0],affect_decision:{policy_version:'affect-pacing-v1',request_id:'request-1',session_version:2,user_turn_id:'request',assistant_turn_id:'objection',adaptation_enabled:true,preference:'auto',audio_submitted:true,audio_available:true,model_available:true,source:'trained_multimodal',analysis_ms:18,action:'offer_pacing',reason:'uncertain_or_conflicting',fallback_reason:null,prediction:{label:'neutral',confidence:.4,distribution:{neutral:.4,anger:.3,sadness:.2,happiness:.1},text_label:'neutral',text_confidence:.6,text_distribution:{neutral:.6,anger:.4},audio_label:'anger',audio_confidence:.7,audio_distribution:{anger:.7,neutral:.3},modalities_agree:false,confidence_level:'low',low_confidence_threshold:.5,model_version:'synthetic-model-v1',latency_ms:15,queue_ms:3,audio_persisted:false,disclaimer:'Synthetic test estimate, not a diagnosis.'}}}]}
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText('Text and voice estimates disagree.')).toBeVisible()
  await expect(page.getByText(/Uncertain estimate;/)).toBeVisible()
  await expect(page.getByText(/Recorded pacing: offer pacing/)).toBeVisible()
  await page.getByText('Technical details',{exact:true}).click();await expect(page.getByText(/Model: synthetic-model-v1/)).toBeVisible()
  await expectAccessible(page)
})

test('projection excludes reflection and discarded decisions without modifying records',()=>{
  const input={...state,decisions:[...state.decisions!,decision('discarded','removed','explain','resolved')]}
  const before=JSON.stringify({turns,input});const replay=rehearsalReplay(turns,input)
  expect(replay.turns.map(item=>item.id)).toEqual(['opening','request','objection','agreement','closing'])
  expect(replay.decisions).toHaveLength(2);expect(JSON.stringify({turns,input})).toBe(before)
  expect(rehearsalReplay(turns,{...state,measurement_ended_at:null}).turns).toHaveLength(5)
  expect(rehearsalReplay(turns,{...state,measurement_ended_at:null,completed_at:null})).toMatchObject({boundaryKnown:false,turns:[],decisions:[]})
  const precise=[{...turns[1],created_at:'2026-09-22T10:00:01.123456Z'},{...turns[5],created_at:'2026-09-22T10:00:01.123458Z'}]
  expect(rehearsalReplay(precise,{...state,measurement_ended_at:'2026-09-22T10:00:01.123457Z'}).turns.map(item=>item.id)).toEqual(['request'])
})

test('failed inference remains a gap with its saved fallback reason',async({page})=>{
  const mock=await installApiMock(page,{existingSession:true});mock.turns=turns.map(item=>({...item}));mock.roleplay={...state,status:'interrupted',decisions:[{...state.decisions![0],affect_decision:{policy_version:'affect-pacing-v1',user_turn_id:'request',assistant_turn_id:'objection',adaptation_enabled:true,preference:'auto',audio_submitted:true,audio_available:false,model_available:false,source:'unavailable',prediction:null,analysis_ms:10,action:'baseline',reason:'prediction_unavailable',fallback_reason:'inference_failed'}}]}
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText(/No saved voice prediction/)).toBeVisible()
  await expect(page.getByText('prediction unavailable · inference failed')).toBeVisible()
  await expect(page.getByText('No saved feedback is available for this rehearsal.')).toBeVisible()
})

test('empty and unavailable boundaries are clearly explained',async({page})=>{
  const mock=await installApiMock(page,{existingSession:true});mock.roleplay={...state};mock.turns=[]
  await page.goto('/practice?session=session-1');await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText('No saved rehearsal turns are available.')).toBeVisible()
  mock.roleplay={...state,measurement_ended_at:null,completed_at:null};await page.reload();await page.getByRole('button',{name:'Replay',exact:true}).click()
  await expect(page.getByText(/The rehearsal boundary is unavailable/)).toBeVisible()
})
