import { expect, test } from '@playwright/test'
import { installApiMock } from './support'

test('confirmation resend shows errors, prevents duplicate requests, and retries', async ({page}) => {
  await installApiMock(page, {authenticated:false})
  let release: () => void = () => {}
  const gate = new Promise<void>(resolve => {release=resolve})
  let attempts=0
  await page.route('**/api/auth/resend-verification', async route => {
    attempts++
    if(attempts===1){await gate;await route.fulfill({status:503,json:{detail:'Email service unavailable.'}})}
    else await route.fulfill({json:{message:'Confirmation sent.'}})
  })
  await page.goto('/check-email?email=participant@example.com')
  await page.getByRole('button',{name:'Resend confirmation'}).click()
  await expect(page.getByRole('button',{name:/Sending/})).toBeDisabled()
  release()
  await expect(page.getByRole('alert')).toHaveText('Email service unavailable.')
  await page.getByRole('button',{name:'Resend confirmation'}).click()
  await expect(page.getByText('Confirmation sent.')).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(attempts).toBe(2)
})

test('failed session loading is distinct from an empty list and can retry', async ({page}) => {
  await installApiMock(page, {existingSession:true})
  let failing=true
  await page.route('**/api/sessions', route => failing?route.fulfill({status:503,json:{detail:'Unavailable'}}):route.fallback())
  await page.goto('/settings')
  await expect(page.getByRole('alert')).toContainText('Sessions could not be loaded')
  await expect(page.getByText('No active sessions are stored.')).not.toBeVisible()
  failing=false
  await page.getByRole('button',{name:'Retry loading sessions'}).click()
  await expect(page.locator('.settings-session-list article')).toHaveCount(1)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('session deletion failure keeps the session visible for retry', async ({page}) => {
  await installApiMock(page, {existingSession:true})
  let attempts=0
  await page.route('**/api/sessions/session-1', route => {
    if(route.request().method()!=='DELETE')return route.fallback()
    return ++attempts===1?route.fulfill({status:503,json:{detail:'Deletion unavailable.'}}):route.fallback()
  })
  page.on('dialog', dialog=>dialog.accept())
  await page.goto('/settings')
  await page.getByRole('button',{name:'Delete',exact:true}).click()
  await expect(page.getByRole('alert')).toHaveText('Deletion unavailable.')
  await expect(page.locator('.settings-session-list article')).toHaveCount(1)
  await page.getByRole('button',{name:'Delete',exact:true}).click()
  await expect(page.getByText('No active sessions are stored.')).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('account deletion failure keeps the user signed in and supports retry', async ({page}) => {
  const state=await installApiMock(page)
  let attempts=0
  await page.route('**/api/auth/me', route => {
    if(route.request().method()!=='DELETE')return route.fallback()
    return ++attempts===1?route.fulfill({status:503,json:{detail:'Account deletion unavailable.'}}):route.fallback()
  })
  page.on('dialog',dialog=>dialog.accept())
  await page.goto('/settings')
  await page.getByRole('button',{name:'Delete my account'}).click()
  await expect(page.getByRole('alert')).toHaveText('Account deletion unavailable.')
  expect(state.deletedAccount).toBe(false)
  await expect(page).toHaveURL(/settings$/)
  await page.getByRole('button',{name:'Delete my account'}).click()
  await expect(page).toHaveURL(/login$/)
  expect(state.deletedAccount).toBe(true)
})

test('personal JSON download failure is visible and retry downloads the file', async ({page}) => {
  await installApiMock(page)
  let attempts=0
  await page.route('**/api/auth/research-export',route=>++attempts===1?route.fulfill({status:503,json:{detail:'Export unavailable.'}}):route.fulfill({json:{participant_id:'demo',records:[]}}))
  await page.goto('/settings')
  await page.getByRole('button',{name:'Download research JSON'}).click()
  await expect(page.getByRole('alert')).toHaveText('Export unavailable.')
  const download=page.waitForEvent('download')
  await page.getByRole('button',{name:'Download research JSON'}).click()
  expect((await download).suggestedFilename()).toBe('affectlab-research-demo.json')
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('custom scenario deletion reports failure outside the builder and can retry', async ({page}) => {
  await installApiMock(page)
  const scenario={id:'workload',title:'Workload conversation',character:'manager',user_objective:'Agree a priority.',expected_skills:['clarity']}
  await page.route('**/api/roleplay/scenarios',route=>route.fulfill({json:[scenario,{...scenario,id:'custom_demo',title:'Custom demo'}]}))
  let attempts=0
  await page.route('**/api/roleplay/scenarios/custom_demo',route=>++attempts===1?route.fulfill({status:503,json:{detail:'Scenario deletion unavailable.'}}):route.fulfill({status:204}))
  page.on('dialog',dialog=>dialog.accept())
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button',{name:'Delete Custom demo'}).click()
  await expect(page.getByRole('alert')).toHaveText('Scenario deletion unavailable.')
  await expect(page.getByRole('button',{name:'Delete Custom demo'})).toBeVisible()
  await page.getByRole('button',{name:'Delete Custom demo'}).click()
  await expect(page.getByRole('button',{name:'Delete Custom demo'})).toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

for(const failure of ['delete','create','history'] as const){
  test(`Delete & start fresh recovers from ${failure} failure`,async({page})=>{
    await installApiMock(page,{existingSession:true})
    await page.goto('/practice?session=session-1')
    await expect(page.getByText('I need help preparing for a conversation.')).toBeVisible()
    let deletes=0,creates=0,history=0
    await page.route('**/api/sessions/session-1',route=>{
      if(route.request().method()!=='DELETE')return route.fallback()
      deletes++
      return failure==='delete'&&deletes===1?route.fulfill({status:503,json:{detail:'Deletion unavailable.'}}):route.fulfill({status:204})
    })
    await page.route('**/api/sessions',route=>{
      if(route.request().method()==='POST'){
        creates++
        return failure==='create'&&creates===1?route.fulfill({status:503,json:{detail:'Creation unavailable.'}}):route.fulfill({status:201,json:{session_id:'session-new',emotion_state:{dominant_emotion:'neutral',valence:0,arousal:0,confidence:0,trend:'stable'}}})
      }
      history++
      return failure==='history'&&history===1?route.fulfill({status:503,json:{detail:'History unavailable.'}}):route.fulfill({json:[]})
    })
    await page.getByRole('button',{name:'Delete & start fresh'}).click()
    await expect(page.getByRole('alert')).toBeVisible()
    if(failure==='delete')await expect(page.getByText('I need help preparing for a conversation.')).toBeVisible()
    if(failure==='create'){
      await expect(page.getByRole('alert')).toContainText('previous session was deleted')
      await page.getByRole('textbox').fill('A draft for later.')
      await expect(page.getByLabel('Send message')).toBeDisabled()
    }
    if(failure!=='history')await page.getByRole('button',{name:'Delete & start fresh'}).click()
    else await expect(page.getByRole('alert')).toContainText('new workspace is ready')
    await expect(page).toHaveURL(/session=session-new$/)
    await expect(page.getByText('I need help preparing for a conversation.')).not.toBeVisible()
    await page.getByRole('textbox').fill('The new workspace is usable.')
    await expect(page.getByLabel('Send message')).toBeEnabled()
    expect(deletes).toBe(failure==='delete'?2:1)
    if(failure!=='history')await expect(page.getByRole('alert')).toHaveCount(0)
  })
}
