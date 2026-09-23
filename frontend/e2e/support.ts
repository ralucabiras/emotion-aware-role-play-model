import type { StudyInformation } from '../src/types/api'
import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, type Route } from '@playwright/test'

const now = '2026-09-22T10:00:00Z'
export const baseUser = {
  id: '11111111-1111-4111-8111-111111111111', email: 'participant@example.com', first_name: 'Alex', last_name: 'Morgan', preferred_name: 'Alex',
  country: 'Romania', timezone: 'Europe/Bucharest', email_verified: true, practice_goals: ['clear_requests'], onboarding_completed: true,
  onboarding_version: '1.0', researcher: false, pilot_enrolled: false, study_consent_version: null, study_consented_at: null, eligibility_version: null as string|null, eligibility_confirmed_at: null as string|null,
  study_withdrawn: false, study_withdrawn_at: null as string|null, participant_id: '22222222-2222-4222-8222-222222222222',
}

const emotion = { dominant_emotion: 'neutral', valence: 0, arousal: .2, confidence: .7, trend: 'stable' }
const scenario = { id: 'workload', title: 'Workload conversation', character: 'manager', situation: 'Your workload is too high.', user_objective: 'Agree a realistic priority.', opening_line: 'What did you want to discuss?', expected_skills: ['clarity', 'specificity', 'boundary_maintenance'] }
const studyScenarios = [scenario, {...scenario,id:'boundary',title:'Boundary conversation',character:'friend'}, {...scenario,id:'relationship',title:'Relationship conversation',character:'partner'}]
const feedback = { session_id: 'session-1', scenario_id: 'workload', observed: ['You made a concrete request.'], strengths: ['Your request was specific.'], suggestions: ['State the boundary earlier.'], generation_source: 'template', metrics: [{name:'clarity',score:.8,evidence_turns:[1]}], compared_with_session_id:null, comparisons:[] }

export const studyInformation: StudyInformation = {version:'2026.1',protocol_version:'AL-FEAS-1.0',study_label:'AffectLab pilot',title:'Participant information',summary:'A feasibility study.',data_collected:['Ratings'],processors:['OpenAI'],audio_and_transcripts:['Audio is not retained.'],retention:'One year.',risks_and_limitations:['Predictions may be wrong.'],withdrawal:['Withdraw from settings.'],researcher:{name:'Researcher',email:'research@example.com'},supervisor:{name:'Supervisor',email:'supervisor@example.com'},institution:'Test University',eligibility_version:'eligibility-test-v1',minimum_participant_age:18,geographic_scope:'Romania',supported_language:'English',other_eligibility_criteria:['I can provide informed consent and complete the study independently.']}

export type MockOptions = { authenticated?: boolean; onboarding?: boolean; researcher?: boolean; enrolled?: boolean; transcription?: 'success'|'unavailable'; existingSession?: boolean }

export async function installApiMock(page: Page, options: MockOptions = {}) {
  const state = {
    user: { ...baseUser, onboarding_completed: options.onboarding ?? true, researcher: options.researcher ?? false, pilot_enrolled: options.enrolled ?? false,
      study_consent_version: options.enrolled ? '2026.1' : null, study_consented_at: options.enrolled ? now : null, eligibility_version: options.enrolled ? studyInformation.eligibility_version : null, eligibility_confirmed_at: options.enrolled ? now : null },
    authenticated: options.authenticated ?? true,
    turns: options.existingSession ? [{id:'turn-old',role:'user',content:'I need help preparing for a conversation.',created_at:now}] : [] as Array<Record<string, unknown>>,
    roleplay: null as null | Record<string, unknown>,
    savedTakeaway: '',
    questionnaires: {} as Record<string,unknown>,
    questionnaire_skips: {} as Record<string,string>,
    postToken: null as string|null,
    studyTaskStatuses: {workload:'not_started',boundary:'not_started',relationship:'not_started'} as Record<string,string>,
    deletedAccount: false,
    exported: false,
    customScenario: null as null | typeof scenario,
  }
  const session = () => ({ session_id:'session-1', title:'Manager conversation', turns:state.turns, emotion_state:emotion, roleplay:state.roleplay, feedback:state.roleplay?.status === 'completed' ? feedback : null, takeaway:state.savedTakeaway,questionnaires:state.questionnaires,questionnaire_skips:state.questionnaire_skips })
  const summary = () => ({ session_id:'session-1', title:'Manager conversation', created_at:now, updated_at:now, turn_count:state.turns.length, roleplay:state.roleplay, feedback:state.roleplay?.status === 'completed' ? feedback : null, takeaway:state.savedTakeaway,questionnaires:state.questionnaires,questionnaire_skips:state.questionnaire_skips })
  const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType:'application/json', body:JSON.stringify(body) })

  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname.replace(/^\/api/, ''), method = request.method()
    if (path === '/auth/me' && method === 'GET') return state.authenticated ? json(route,state.user) : json(route,{detail:'Not authenticated'},401)
    if (path === '/auth/refresh') return json(route,{detail:'Not authenticated'},401)
    if (path === '/auth/register') return json(route,{message:'Check your email.',email:'new@example.com'},202)
    if (path === '/auth/verify-email') return json(route,{message:'Your email address has been confirmed.'})
    if (path === '/auth/login') { state.authenticated=true; return json(route,{access_token:'test-token',user:state.user}) }
    if (path === '/auth/onboarding') { state.user={...state.user,onboarding_completed:true,practice_goals:['clear_requests']}; return json(route,state.user) }
    if (path === '/auth/logout') { state.authenticated=false; return json(route,null,204) }
    if (path === '/auth/me' && method === 'DELETE') { state.deletedAccount=true; state.authenticated=false; return json(route,null,204) }
    if (path === '/models/info') return json(route,{trained_model:true,multimodal_model:'test',multimodal_status:'ready',transcription_available:options.transcription!=='unavailable',transcription_model:'gpt-4o-mini-transcribe',disclaimer:'Research estimate.'})
    if (path === '/roleplay/scenarios' && method === 'GET') return json(route,options.enrolled?studyScenarios:[scenario])
    if (path === '/roleplay/scenarios' && method === 'POST') { state.customScenario={...scenario,id:'custom_assertiveness',title:'Flexible hours',character:'team lead',opening_line:'What would you like to discuss?'}; return json(route,state.customScenario) }
    if (path === '/sessions' && method === 'GET') return json(route,(options.existingSession || state.turns.length || state.roleplay) ? [summary()] : [])
    if (path === '/sessions' && method === 'POST') return json(route,{session_id:'session-1',emotion_state:emotion},201)
    if (path === '/sessions/session-1' && method === 'GET') return json(route,session())
    if (path === '/sessions/session-1' && method === 'DELETE') return json(route,null,204)
    if (path === '/sessions/session-1/title') return json(route,summary())
    if (path === '/sessions/session-1/takeaway') { state.savedTakeaway=(JSON.parse(request.postData()||'{}').takeaway); return json(route,session()) }
    if (path === '/chat') { const message=JSON.parse(request.postData()||'{}').message; state.turns.push({id:`user-${state.turns.length}`,role:'user',content:message,created_at:now}); const turn={id:`assistant-${state.turns.length}`,role:'assistant',content:state.roleplay?.status==='active'?'Could we agree which task should move to next week?':'What outcome would feel useful to you?',created_at:now};state.turns.push(turn);if(state.roleplay?.status==='active')state.roleplay={...state.roleplay,turn:Number(state.roleplay.turn)+1,success_progress:.67};return json(route,{turn,decision:{emotion_state:emotion,strategy:'clarify',cognitive_assessment:{possible_distortion:null,possible_cause:null,intent:'practice'},decision_reasons:[],analyzer_version:'test'},roleplay:state.roleplay,feedback:null}) }
    if (path === '/audio/transcriptions') return options.transcription === 'unavailable' ? json(route,{detail:'Transcription unavailable'},503) : json(route,{text:'I am nervous about tomorrow.',model:'test',latency_ms:12,audio_persisted:false})
    if (path === '/affect/multimodal') return json(route,{label:'anxiety',confidence:.72,distribution:{anxiety:.72,neutral:.28},text_label:'anxiety',text_confidence:.8,text_distribution:{anxiety:.8},audio_label:'neutral',audio_confidence:.55,audio_distribution:{neutral:.55},modalities_agree:false,confidence_level:'moderate',low_confidence_threshold:.5,model_version:'test',latency_ms:10,queue_ms:0,audio_persisted:false,disclaimer:'Research estimate.'})
    if (path === '/sessions/session-1/questionnaires/post/close') {state.postToken=null;if(state.roleplay&&state.studyTaskStatuses[String(state.roleplay.scenario_id)]==='awaiting_ratings')state.studyTaskStatuses[String(state.roleplay.scenario_id)]='incomplete';return json(route,null,204)}
    if (path === '/sessions/session-1/questionnaires/pre' || path === '/sessions/session-1/questionnaires/post') {
      const phase=path.endsWith('/pre')?'pre':'post',payload=request.postDataJSON()
      if(state.questionnaires[phase]||state.questionnaire_skips[phase])return json(route,{detail:'Decision already recorded'},409)
      if(payload.skipped){if(phase==='post'&&state.roleplay)state.studyTaskStatuses[String(state.roleplay.scenario_id)]='incomplete';state.questionnaire_skips[phase]=now;return json(route,{questionnaire:null})}
      if(phase==='post'&&state.roleplay)state.studyTaskStatuses[String(state.roleplay.scenario_id)]='complete'
      state.questionnaires[phase]={phase,...payload,submitted_at:now};return json(route,{questionnaire:state.questionnaires[phase]})
    }
    if (path === '/sessions/session-1/roleplay' && method === 'POST') { const requested=JSON.parse(request.postData()||'{}').scenario_id;const selected=requested?.startsWith('custom_')&&state.customScenario?state.customScenario:(studyScenarios.find(item=>item.id===requested)??scenario);state.questionnaires={};state.questionnaire_skips={};state.postToken=null;state.studyTaskStatuses[selected.id]='in_progress';state.roleplay={scenario_id:selected.id,scenario:selected,difficulty_level:'intermediate',status:'active',turn:0,success_progress:0,completion_reason:null}; const opening={id:'opening',role:'assistant',content:selected.opening_line,created_at:now};state.turns=[opening];return json(route,{session_id:'session-1',emotion_state:emotion,scenario:selected,opening_turn:opening,state:state.roleplay}) }
    if (path === '/sessions/session-1/roleplay/action') { const action=JSON.parse(request.postData()||'{}').action; if(action==='finish'){state.postToken='post-token';state.studyTaskStatuses[String(state.roleplay?.scenario_id)]='awaiting_ratings'}state.roleplay={...state.roleplay,status:action==='finish'?'completed':action==='pause'?'paused':'active',completion_reason:action==='finish'?'manual':null};return json(route,{...session(),post_questionnaire_token:state.postToken}) }
    if (path === '/sessions/session-1/roleplay/rewind') { state.turns=state.turns.slice(0,-2);state.roleplay={...state.roleplay,turn:Math.max(0,Number(state.roleplay?.turn||0)-1)};return json(route,{removed_message:'test',session:session()}) }
    if (path === '/research/progress') {
      const tasks=studyScenarios.map((item,index)=>({order:index+1,scenario_id:item.id,title:item.title,difficulty:'intermediate',status:state.studyTaskStatuses[item.id],session_id:['in_progress','awaiting_ratings'].includes(state.studyTaskStatuses[item.id])?'session-1':null}))
      return json(route,{protocol_version:'test-v1',tasks,completed_tasks:tasks.filter(task=>task.status==='complete').length,next_task_id:tasks.find(task=>['not_started','in_progress','awaiting_ratings'].includes(task.status))?.scenario_id??null,available:true})
    }
    if (path === '/research/study-information') return json(route,studyInformation)
    if (path === '/research/enroll') { state.user={...state.user,pilot_enrolled:true,study_consent_version:'2026.1',study_consented_at:now,eligibility_version:studyInformation.eligibility_version,eligibility_confirmed_at:now};return json(route,state.user) }
    if (path === '/research/withdraw') { state.user={...state.user,pilot_enrolled:false,study_withdrawn:true,study_withdrawn_at:now};return json(route,{user:state.user,questionnaires_deleted:1,research_events_deleted:2,message:'Withdrawal recorded.',anonymized_analysis_notice:'Aggregate analysis may remain.'}) }
    if (path === '/research/dashboard') return json(route,{study_label:'AffectLab pilot',protocol_version:'AL-FEAS-1.0',generated_at:now,participants:1,participant_target:20,sessions:1,completed_rehearsals:1,completion_rate:1,protocol_completers:1,completer_target:20,protocol_completion_rate:.05,scenario_completions:{workload:1},difficulty_completions:{intermediate:1},average_skill_scores:{clarity:.8},questionnaire_averages:{confidence:.7},generation_sources:{template:1},lifecycle:{protocol_version:'AL-FEAS-1.0',start_date:'2026-09-01',end_date:'2026-12-01',dataset_frozen_at:null,frozen_export_id:null},frozen_export:null,participant_activity:[{participant_id:state.user.participant_id,enrolled_at:now,last_active_at:now,sessions:1,completed_rehearsals:1,protocol_complete:true,completion_status:'complete',excluded:false,withdrawn:false,exclusion_reason:'',data_quality_notes:'',pre_questionnaires:1,post_questionnaires:1}],privacy:{contains_names:false,contains_emails:false,contains_conversation_text:false,contains_takeaways:false}})
    if (path === '/research/export.csv') { state.exported=true; return route.fulfill({status:200,contentType:'text/csv',headers:{'Content-Disposition':'attachment; filename="affectlab.csv"'},body:'participant_id,completed\nabc,true\n'}) }
    return json(route,{detail:`Unhandled mock route: ${method} ${path}`},500)
  })
  return state
}

export async function mockMicrophone(page: Page) {
  await page.addInitScript(() => {
    const processor = { onaudioprocess:null as null|((event:{inputBuffer:{getChannelData:()=>Float32Array}})=>void), connect(){ setTimeout(()=>this.onaudioprocess?.({inputBuffer:{getChannelData:()=>new Float32Array(4096).fill(.1)}}),20) }, disconnect(){} }
    class FakeAudioContext { sampleRate=16000;destination={};createMediaStreamSource(){return{connect(){},disconnect(){}}}createScriptProcessor(){return processor}close(){return Promise.resolve()} }
    Object.defineProperty(window,'AudioContext',{value:FakeAudioContext})
    Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})}})
  })
}

export async function expectAccessible(page: Page) {
  // Avoid sampling the intentionally translucent entry transition mid-frame.
  await page.waitForTimeout(350)
  const result = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()
  expect(result.violations, result.violations.map(v=>`${v.id}: ${v.help}`).join('\n')).toEqual([])
}
