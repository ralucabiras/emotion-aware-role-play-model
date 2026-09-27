import { expect, test } from '@playwright/test'
import { expectAccessible, installApiMock, mockMicrophone } from './support'

test.beforeEach(async ({page}) => { await mockMicrophone(page) })

test('restores a reflection and supports transcription review', async ({ page }) => {
  await installApiMock(page,{existingSession:true,transcription:'success'})
  await page.goto('/app')
  await page.getByRole('button',{name:/Manager conversation/}).click()
  await expect(page.getByText('I need help preparing for a conversation.')).toBeVisible()
  await page.getByRole('button',{name:'Record voice sample'}).click()
  await expect(page.getByRole('button',{name:'Stop voice recording'})).toBeVisible()
  await page.getByRole('button',{name:'Stop voice recording'}).click()
  await expect(page.getByRole('textbox')).toHaveValue('I am nervous about tomorrow.')
  await page.getByLabel('Send message').click()
  await expect(page.getByText('What outcome would feel useful to you?')).toBeVisible()
  await expectAccessible(page)
})

test('keeps manual text available when transcription is unavailable', async ({ page }) => {
  await installApiMock(page,{transcription:'unavailable'})
  await page.goto('/practice?new=1')
  await page.getByRole('button',{name:'Record voice sample'}).click()
  await page.getByRole('button',{name:'Stop voice recording'}).click()
  await expect(page.getByText(/Type what you said before sending/i)).toBeVisible()
  await page.getByRole('textbox').fill('My manually entered transcript.')
  await page.getByLabel('Send message').click()
  await expect(page.getByText('My manually entered transcript.').first()).toBeVisible()
})

test('creates a custom scenario and exercises role-play controls and feedback', async ({ page }) => {
  await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'+ Create your own scenario'}).click()
  await page.getByLabel('Scenario title').fill('Flexible hours')
  await page.getByLabel('Who are you speaking with?').fill('team lead')
  await page.getByLabel('Situation').fill('I need to request a temporary flexible schedule.')
  await page.getByLabel('Your objective').fill('Agree two remote mornings each week.')
  await page.getByLabel('Their opening line').fill('What would you like to discuss?')
  await page.getByLabel('specific detail',{exact:true}).check()
  await page.getByRole('button',{name:'Save and select scenario'}).click()
  await page.getByLabel('How confident do you feel about this conversation?').selectOption('4')
  await page.getByLabel('How anxious do you feel about this conversation?').selectOption('4')
  await page.getByRole('button',{name:/Begin with the team lead/}).click()
  await expect(page.getByText('What would you like to discuss?')).toBeVisible()
  await page.getByPlaceholder(/Respond to your/).fill('Could we agree that one lower priority task moves to next week?')
  await page.getByLabel('Send message').click()
  await page.getByRole('button',{name:'Pause'}).click()
  await expect(page.getByRole('button',{name:'Resume'})).toBeVisible()
  await page.getByRole('button',{name:'Resume'}).click()
  await page.getByRole('button',{name:'Retry last turn'}).first().click()
  await page.getByRole('button',{name:'Finish & review'}).click()
  await expect(page.getByRole('heading',{name:'Flexible hours'})).toBeVisible()
  await expect(page.getByText('Your request was specific.')).toBeVisible()
  await page.getByLabel('Personal takeaway').fill('Lead with a concrete request.')
  await page.getByRole('button',{name:'Save takeaway'}).click()
  await expect(page.getByRole('button',{name:'Saved'})).toBeVisible()
  await page.getByRole('button',{name:'Practise again'}).click()
  await expect(page.getByRole('button',{name:/Begin with the/})).toBeVisible()
})


test('practise again switches to a fresh session and sends its own pre-ratings', async ({ page }) => {
  const state = await installApiMock(page)
  const preSubmissions: string[] = []
  page.on('request', request => {
    if (request.url().endsWith('/questionnaires/pre')) preSubmissions.push(request.url())
  })
  await page.goto('/practice?mode=roleplay')
  await page.getByLabel('How confident do you feel about this conversation?').selectOption('4')
  await page.getByLabel('How anxious do you feel about this conversation?').selectOption('4')
  await page.getByRole('button', {name: /Begin with the manager/}).click()
  await page.getByRole('button', {name: 'Finish & review'}).click()
  await page.getByLabel('Personal takeaway').fill('Preserve this first attempt.')
  await page.getByRole('button', {name: 'Save takeaway'}).click()
  await expect(page.getByRole('button', {name: 'Saved', exact: true})).toBeVisible()
  const previousRoleplay = {...state.roleplay}
  const previousTurns = [...state.turns]
  const emotion = {dominant_emotion:'neutral',valence:0,arousal:.2,confidence:.7,trend:'stable'}
  const scenario = {id:'workload',title:'Workload conversation',character:'manager',user_objective:'Agree a realistic priority.',expected_skills:['clarity']}
  const opening = {id:'new-opening',role:'assistant',content:'A new rehearsal starts here.',created_at:new Date().toISOString()}
  const roleplay = {scenario_id:'workload',scenario,difficulty_level:'beginner',status:'active',turn:0,success_progress:0}
  await page.route('**/api/sessions/session-1/roleplay', async route => {
    expect(route.request().postDataJSON()).toMatchObject({scenario_id:'workload',pre_ratings:{confidence:4,anxiety:4}})
    await route.fulfill({json:{session_id:'session-2',emotion_state:emotion,scenario,opening_turn:opening,state:roleplay}})
  })
  await page.route('**/api/sessions/session-2', route => route.fulfill({json:{session_id:'session-2',title:scenario.title,turns:[opening],emotion_state:emotion,roleplay,feedback:null,takeaway:''}}))
  await page.getByRole('button', {name:'Practise again'}).click()
  await page.getByLabel('How confident do you feel about this conversation?').selectOption('4')
  await page.getByLabel('How anxious do you feel about this conversation?').selectOption('4')
  await page.getByRole('button', {name:/Begin with the manager/}).click()
  await expect(page).toHaveURL(/session=session-2$/)
  await expect(page.getByText(opening.content)).toBeVisible()
  expect(preSubmissions).toEqual([])
  expect(state.savedTakeaway).toBe('Preserve this first attempt.')
  expect(state.roleplay).toEqual(previousRoleplay)
  expect(state.turns).toEqual(previousTurns)
  await page.reload()
  await expect(page.getByText(opening.content)).toBeVisible()
  await page.route('**/api/chat', async route => {
    expect(route.request().postDataJSON().session_id).toBe('session-2')
    await route.fulfill({json:{turn:{...opening,id:'reply',content:'Reply in the new attempt.'},decision:{emotion_state:emotion},roleplay,feedback:null}})
  })
  await page.getByPlaceholder(/Respond to your manager/).fill('My second attempt.')
  await page.getByLabel('Send message').click()
  await expect(page.getByText('Reply in the new attempt.')).toBeVisible()
})


test('ratings require explicit choices and saved answers survive reopening', async ({page})=>{
  const state=await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await expect(page.getByRole('button',{name:/Begin with the manager/})).toBeDisabled()
  await expect(page.getByLabel('How confident do you feel about this conversation?')).toHaveValue('')
  const startRequest=page.waitForRequest(request=>request.url().endsWith('/session-1/roleplay'))
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  expect((await startRequest).postDataJSON()).toMatchObject({pre_skipped:true,pre_ratings:null})
  await page.getByRole('button',{name:'Finish & review'}).click()
  await expect(page.getByRole('button',{name:'Save research ratings'})).toBeDisabled()
  await page.getByLabel('Confidence now').selectOption('6')
  await page.getByLabel('Scenario realism').selectOption('5')
  await page.getByLabel('Feedback usefulness').selectOption('7')
  let failSave=true
  await page.route('**/api/sessions/session-1/questionnaires/post',route=>{
    if(failSave){failSave=false;return route.fulfill({status:503,json:{detail:'Ratings could not be saved. Please try again.'}})}
    return route.fallback()
  })
  await page.getByRole('button',{name:'Save research ratings'}).click()
  await expect(page.getByRole('alert')).toContainText('Ratings could not be saved')
  await expect(page.getByLabel('Confidence now')).toHaveValue('6')
  expect(state.questionnaires.post).toBeUndefined()
  await page.getByRole('button',{name:'Save research ratings'}).click()
  await expect(page.getByText('Your original ratings are saved and cannot be changed.')).toBeVisible()
  expect(state.questionnaires.post).toMatchObject({confidence:6,realism:5,usefulness:7})
  await page.reload()
  await expect(page.getByText('Your original ratings are saved and cannot be changed.')).toBeVisible()
  await expect(page.locator('.post-study')).toContainText('6 / 7')
  await expect(page.getByRole('button',{name:'Save research ratings'})).toHaveCount(0)
})

test('post-ratings can be explicitly skipped without inventing answers', async ({page})=>{
  const state=await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await page.getByRole('button',{name:'Finish & review'}).click()
  await page.getByRole('button',{name:'Skip post-ratings'}).click()
  await expect(page.getByText('You skipped these ratings. No answers were recorded.')).toBeVisible()
  expect(state.questionnaires.post).toBeUndefined()
  expect(state.questionnaire_skips.post).toBeTruthy()
  await page.reload()
  await expect(page.getByText('You skipped these ratings. No answers were recorded.')).toBeVisible()
})

test('leaving feedback closes unanswered post-ratings',async({page})=>{
  const state=await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await page.getByRole('button',{name:'Finish & review'}).click()
  await expect(page.getByRole('button',{name:'Save research ratings'})).toBeVisible()
  await page.getByRole('button',{name:'Return to conversation'}).click()
  await expect.poll(()=>state.postToken).toBeNull()
  await page.getByRole('button',{name:'Feedback',exact:true}).click()
  await expect(page.getByText('Ratings are closed after leaving the task screen. No retrospective answers can be added.')).toBeVisible()
  expect(state.questionnaires.post).toBeUndefined()
})


test('transcribes without a trained multimodal model and sends only text for analysis', async ({ page }) => {
  await installApiMock(page, {multimodal:false, transcription:'success'})
  const affectRequests: string[] = []
  page.on('request', request => {
    if (request.url().includes('/affect/multimodal')) affectRequests.push(request.url())
  })
  await page.goto('/practice?new=1')
  await page.getByRole('button', {name:'Record voice sample'}).click()
  await page.getByRole('button', {name:'Stop voice recording'}).click()
  await expect(page.getByRole('textbox')).toHaveValue('I am nervous about tomorrow.')
  await page.getByRole('textbox').fill('My reviewed transcript.')
  await page.getByLabel('Send message').click()
  await expect(page.locator('.message.user')).toHaveText('My reviewed transcript.')
  await expect(page.getByText('What outcome would feel useful to you?')).toBeVisible()
  expect(affectRequests).toEqual([])
  await expect(page.getByText(/Voice analysis was unavailable/)).not.toBeVisible()
})

for (const microphoneDisabled of [false, true]) {
  test(`keeps voice input disabled when ${microphoneDisabled ? 'the microphone preference is off' : 'both capabilities are unavailable'}`, async ({ page }) => {
    await installApiMock(page, {multimodal:false, transcription:microphoneDisabled?'success':'unavailable'})
    if (microphoneDisabled) await page.addInitScript(() => localStorage.setItem('affectlab_microphone_enabled', 'false'))
    await page.goto('/practice?new=1')
    await expect(page.getByText('Voice input unavailable')).toBeVisible()
    await expect(page.getByRole('button', {name:'Record voice sample'})).not.toBeVisible()
    await page.getByRole('textbox').fill('Text still works.')
    await page.getByLabel('Send message').click()
    await expect(page.locator('.message.user')).toHaveText('Text still works.')
  })
}


test('restores enhanced workload progress on desktop and mobile', async ({ page }) => {
  const state = await installApiMock(page, {existingSession:true})
  state.roleplay = {scenario_id:'workload',status:'active',difficulty_level:'intermediate',turn:1,success_progress:1/3,
    dialogue:{stage:'constraints',final_agreement:null},policy_version:'workload-v2'}
  await page.goto('/practice?session=session-1')
  const progress = page.getByRole('list', {name:'Conversation progress'})
  await expect(progress).toBeVisible()
  await expect(progress.locator('[aria-current="step"]')).toHaveText('2. Discuss constraints')
  await page.getByRole('button', {name:'Pause',exact:true}).click()
  await page.reload()
  await expect(page.getByRole('button', {name:'Resume',exact:true})).toBeVisible()
  await expect(progress.locator('[aria-current="step"]')).toHaveText('2. Discuss constraints')
  await expectAccessible(page)
})


test('selects a character profile before starting practice', async ({page}) => {
  await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('radio', {name:/sceptical/i}).check()
  await expect(page.getByRole('note').filter({hasText:'Questions the proposal'})).toBeVisible()
  const request = page.waitForRequest(request => request.url().endsWith('/roleplay') && request.method()==='POST')
  await page.getByRole('button', {name:'Skip pre-ratings and begin'}).click()
  expect((await request).postDataJSON().character_profile).toBe('sceptical')
})

test('restores boundary pressure and its fixed profile', async ({page}) => {
  const state = await installApiMock(page, {existingSession:true})
  state.roleplay = {scenario_id:'boundary',status:'active',difficulty_level:'difficult',turn:2,success_progress:1/3,
    character_profile:'sceptical',profile_description:'Questions the proposal and repeats pressure.',
    dialogue:{stage:'pressure',stage_labels:{refuse:'State your boundary',pressure:'Respond to pressure',close:'Close respectfully'},final_agreement:null},policy_version:'scenario-dialogue-v3'}
  await page.goto('/practice?session=session-1')
  await expect(page.getByRole('list', {name:'Conversation progress'}).locator('[aria-current="step"]')).toHaveText('2. Respond to pressure')
  await expect(page.locator('.profile-summary')).toContainText('sceptical')
  await page.getByRole('button', {name:'Pause',exact:true}).click()
  await page.reload()
  await expect(page.getByRole('button', {name:'Resume',exact:true})).toBeVisible()
  await expect(page.locator('.profile-summary')).toContainText('sceptical')
  await expectAccessible(page)
})

for (const ending of ['boundary_held','unresolved']) {
  test(`shows honest ${ending} feedback`, async ({page}) => {
    const state = await installApiMock(page, {existingSession:true})
    state.roleplay = {scenario_id:ending==='boundary_held'?'boundary':'relationship',status:'completed',difficulty_level:'intermediate',turn:3,success_progress:ending==='boundary_held'?1:1/3,
      character_profile:'sceptical',completion_reason:ending==='boundary_held'?'success':'unresolved',
      dialogue:{stage:ending==='boundary_held'?'resolved':'unresolved',outcome:ending,final_agreement:null},policy_version:'scenario-dialogue-v3'}
    await page.goto('/practice?session=session-1')
    await page.getByRole('button', {name:'Feedback',exact:true}).click()
    await expect(page.getByText(ending==='boundary_held'?'You held your boundary and closed respectfully. Agreement or a concession was not required.':'You ended with a recorded disagreement. There is no agreed next step; this is not a personal failure.')).toBeVisible()
  })
}


test('submits reviewed voice text once with pacing and version binding', async ({page}) => {
  const state = await installApiMock(page, {existingSession:true,transcription:'success'})
  state.roleplay={scenario_id:'boundary',status:'active',difficulty_level:'intermediate',turn:0,success_progress:0,attempt_purpose:'additional',dialogue:{stage:'refuse',final_agreement:null}}
  const detachedRequests:string[]=[]
  page.on('request',request=>{if(request.url().includes('/affect/multimodal'))detachedRequests.push(request.url())})
  await page.goto('/practice?session=session-1')
  await page.getByRole('combobox',{name:'Pace',exact:true}).selectOption('gentler')
  await page.getByLabel('Allow voice-informed acknowledgement and pacing suggestions').check()
  await page.getByRole('button',{name:'Record voice sample'}).click()
  await page.getByRole('button',{name:'Stop voice recording'}).click()
  await expect(page.getByRole('textbox')).toHaveValue('I am nervous about tomorrow.')
  await page.getByRole('textbox').fill('I cannot take this on. Thank you.')
  const pending=page.waitForRequest(request=>request.url().endsWith('/chat')&&request.method()==='POST')
  await page.getByLabel('Send message').click()
  const payload=(await pending).postDataJSON()
  expect(payload.message).toBe('I cannot take this on. Thank you.')
  expect(payload.audio_wav_base64).toBeTruthy()
  expect(payload.request_id).toMatch(/^[a-f0-9-]{36}$/)
  expect(payload.expected_version).toBe(0)
  expect(payload.pacing).toBe('gentler')
  expect(payload.adaptation_enabled).toBe(true)
  expect(detachedRequests).toEqual([])
  await expectAccessible(page)
})

test('reloads a conflicted conversation while keeping the draft', async ({page}) => {
  await installApiMock(page,{existingSession:true})
  await page.route('**/api/chat',route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Session changed. Reload before sending your draft.'})}))
  await page.goto('/practice?session=session-1')
  await page.getByRole('textbox').fill('My unsent draft.')
  await page.getByLabel('Send message').click()
  await page.getByRole('button',{name:'Reload saved conversation and keep draft'}).click()
  await expect(page.getByRole('textbox')).toHaveValue('My unsent draft.')
  await expect(page.getByRole('button',{name:'Reload saved conversation and keep draft'})).not.toBeVisible()
})


test('restores stored prediction provenance and pacing explanation', async ({page}) => {
  const state=await installApiMock(page,{existingSession:true})
  state.turns.push({id:'assistant-linked',role:'assistant',content:'Would you prefer to keep going or take a gentler pace?',created_at:'2026-09-27T00:00:00Z',
    affect_decision:{policy_version:'affect-pacing-v1',request_id:'synthetic-request',session_version:2,user_turn_id:'turn-old',assistant_turn_id:'assistant-linked',
      adaptation_enabled:true,preference:'auto',audio_submitted:true,audio_available:true,model_available:true,source:'trained_multimodal',analysis_ms:14,
      action:'offer_pacing',reason:'modality_disagreement',fallback_reason:null,
      prediction:{label:'anger',confidence:.6,distribution:{anger:.6,sadness:.4},text_label:'anger',text_confidence:.6,text_distribution:{anger:.6,sadness:.4},
        audio_label:'sadness',audio_confidence:.6,audio_distribution:{anger:.4,sadness:.6},modalities_agree:false,confidence_level:'moderate',low_confidence_threshold:.55,
        model_version:'synthetic-test-model',latency_ms:12,queue_ms:2,audio_persisted:false,disclaimer:'Synthetic research estimate.'}}})
  await page.goto('/practice?session=session-1')
  await page.getByText('Why this response?',{exact:true}).click()
  await expect(page.getByText('Linked reply: assistant-linked',{exact:true})).toBeVisible()
  await expect(page.getByText(/Reason: modality disagreement/)).toBeVisible()
  await expect(page.getByText(/Model: synthetic-test-model/)).toBeVisible()
  await expect(page.getByText(/Text and voice point to different leading labels/)).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading',{name:'Last submitted exchange'})).toBeVisible()
  await expectAccessible(page)
})
