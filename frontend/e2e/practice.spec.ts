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
