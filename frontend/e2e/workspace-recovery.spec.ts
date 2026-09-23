import { expect, test } from '@playwright/test'
import { installApiMock, mockMicrophone } from './support'

for(const failure of ['server','network'] as const){
  test(`retains an editable draft after a ${failure} send failure without a delivered bubble`,async({page})=>{
    const state=await installApiMock(page)
    let attempts=0
    await page.route('**/api/chat',route=>{
      attempts++
      if(attempts===1)return failure==='network'?route.abort('failed'):route.fulfill({status:503,json:{detail:'The service is temporarily unavailable'}})
      return route.fallback()
    })
    await page.goto('/practice?new=1')
    const draft='  I need help preparing my request.  '
    await page.getByRole('textbox').fill(draft)
    await page.getByLabel('Send message').click()
    await expect(page.getByRole('alert')).toContainText('Your draft is kept below')
    await expect(page.getByRole('textbox')).toHaveValue(draft)
    await expect(page.locator('.messages .message.user')).toHaveCount(0)
    expect(state.turns).toHaveLength(0)
    await page.getByRole('textbox').fill('My edited request.')
    await page.getByLabel('Send message').click()
    await expect(page.locator('.messages .message.user')).toHaveCount(1)
    await expect(page.locator('.messages .message.user')).toHaveText('My edited request.')
    await expect(page.getByRole('textbox')).toHaveValue('')
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(attempts).toBe(2)
  })
}

test('retains the voice attachment and transcript when chat fails',async({page})=>{
  await mockMicrophone(page)
  await installApiMock(page)
  await page.route('**/api/chat',route=>route.fulfill({status:503,json:{detail:'Please try again'}}))
  await page.goto('/practice?new=1')
  await page.getByRole('button',{name:'Record voice sample'}).click()
  await page.getByRole('button',{name:'Stop voice recording'}).click()
  await expect(page.getByRole('textbox')).toHaveValue('I am nervous about tomorrow.')
  await page.getByLabel('Send message').click()
  await expect(page.getByRole('alert')).toContainText('Your draft is kept below')
  await expect(page.getByRole('textbox')).toHaveValue('I am nervous about tomorrow.')
  await expect(page.getByRole('button',{name:'Remove attached voice sample'})).toBeVisible()
  await expect(page.locator('.messages .message.user')).toHaveCount(0)
})

test('shows start errors in setup and retries with the selected ratings',async({page})=>{
  await installApiMock(page)
  let attempts=0
  await page.route('**/api/sessions/session-1/roleplay',route=>{
    attempts++
    expect(route.request().postDataJSON()).toMatchObject({scenario_id:'workload',difficulty:'intermediate',pre_ratings:{confidence:3,anxiety:6}})
    if(attempts===1)return route.fulfill({status:503,json:{detail:'Rehearsal could not be started. Please retry.'}})
    return route.fallback()
  })
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('radio',{name:/intermediate/}).check()
  await page.getByLabel('How confident do you feel about this conversation?').selectOption('3')
  await page.getByLabel('How anxious do you feel about this conversation?').selectOption('6')
  await page.getByRole('button',{name:/Begin with the manager/}).click()
  await expect(page.getByRole('alert')).toContainText('Rehearsal could not be started')
  await expect(page.getByLabel('How confident do you feel about this conversation?')).toHaveValue('3')
  await expect(page.getByLabel('How anxious do you feel about this conversation?')).toHaveValue('6')
  await page.getByRole('button',{name:/Begin with the manager/}).click()
  await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(attempts).toBe(2)
})

test('pauses for reflection, allows sending, and resumes without advancing the paused rehearsal',async({page})=>{
  const state=await installApiMock(page)
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await page.getByRole('textbox').fill('A draft for reflection.')
  page.once('dialog',dialog=>dialog.accept())
  await page.getByRole('button',{name:'Reflect',exact:true}).click()
  await expect(page.getByText('Your rehearsal is paused. You can reflect here, then return to Active role-play to resume.')).toBeVisible()
  await expect(page.getByLabel('Send message')).toBeEnabled()
  await page.getByLabel('Send message').click()
  await expect(page.getByText('What outcome would feel useful to you?')).toBeVisible()
  expect(state.roleplay?.status).toBe('paused')
  expect(state.roleplay?.turn).toBe(0)
  await page.getByRole('button',{name:'Active role-play',exact:true}).click()
  await page.getByRole('textbox').fill('My rehearsal reply.')
  await expect(page.getByLabel('Send message')).toBeDisabled()
  await page.getByRole('button',{name:'Resume',exact:true}).click()
  await expect(page.getByLabel('Send message')).toBeEnabled()
  await page.getByLabel('Send message').click()
  await expect(page.getByText('Could we agree which task should move to next week?')).toBeVisible()
  expect(state.roleplay?.turn).toBe(1)
})

test('does not call a successful rehearsal start a failure when history refresh fails',async({page})=>{
  await installApiMock(page)
  let started=false
  await page.route('**/api/sessions/session-1/roleplay',route=>{started=true;return route.fallback()})
  await page.route('**/api/sessions',route=>{
    if(started&&route.request().method()==='GET')return route.fulfill({status:503,json:{detail:'History unavailable'}})
    return route.fallback()
  })
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'Skip pre-ratings and begin'}).click()
  await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('The rehearsal started, but the saved-session list could not be refreshed.')
})
