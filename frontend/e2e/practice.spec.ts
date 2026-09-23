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
