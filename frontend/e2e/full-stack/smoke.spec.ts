import { confirmStudyEnrollment } from '../enrollment'
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { expect, test, type Page } from '@playwright/test'

const apiUrl = process.env.FULL_STACK_API_URL ?? 'http://localhost:8000/api'

async function restartBackend() {
  const control = process.env.FULL_STACK_CONTROL_DIR
  if (control) {
    const id = crypto.randomUUID()
    writeFileSync(join(control, 'restart.request'), id)
    await expect.poll(() => {
      try { return readFileSync(join(control, 'restart.response'), 'utf8') } catch { return '' }
    }, {timeout: 90_000}).toBe(id)
    return
  }
  execFileSync('docker', ['compose', '-p', process.env.FULL_STACK_COMPOSE_PROJECT ?? 'affectlab-full-stack-smoke', '-f', '../docker-compose.yml', '-f', '../docker-compose.smoke.yml', 'restart', 'backend'], {cwd: process.cwd(), stdio: 'inherit', shell: process.platform === 'win32'})
}

async function api<T>(page: Page, path: string): Promise<T> {
  return page.evaluate(async ({ url, token }) => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error(`${response.status} ${await response.text()}`)
    const contentType = response.headers.get('content-type') ?? ''
    return contentType.includes('application/json') ? response.json() : response.text()
  }, { url: `${apiUrl}${path}`, token: await page.evaluate(() => sessionStorage.getItem('access_token')) })
}

test('compiled app, FastAPI, and MongoDB complete and persist the core study journey', async ({ page, request }) => {
  test.setTimeout(120_000)
  await page.goto('/login')
  await page.getByLabel('Email').fill('smoke-researcher@example.com')
  await page.getByLabel('Password').fill('full-stack-smoke-password')
  await page.locator('form').getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { name: /Welcome back, Demo/ })).toBeVisible()

  await page.getByRole('button', { name: 'Start a reflection' }).click()
  const syntheticMessage = 'Synthetic pre-enrollment reflection that must stay outside the study export.'
  await page.getByRole('textbox').fill(syntheticMessage)
  const reflectionSaved = page.waitForResponse(response => response.url() === `${apiUrl}/chat` && response.request().method() === 'POST')
  await page.getByLabel('Send message').click()
  expect((await reflectionSaved).ok()).toBeTruthy()
  await expect(page.getByRole('textbox')).toHaveValue('')
  await expect(page.getByText(syntheticMessage, { exact: true })).toBeVisible()
  const sessionsAfterReflection = await api<Array<{session_id:string; title:string}>>(page, '/sessions')
  const syntheticSession = sessionsAfterReflection.find(item => item.title.startsWith('Synthetic pre-enrollment'))
  expect(syntheticSession).toBeTruthy()

  await page.goto(`/practice?session=${syntheticSession!.session_id}`)
  await expect(page.getByText(syntheticMessage)).toBeVisible()

  await page.goto('/settings')
  await page.getByLabel('Study access code').fill('smoke-pilot-code')
  await confirmStudyEnrollment(page)
  await page.getByRole('button', { name: 'Consent and join pilot study' }).click()
  await expect(page.getByRole('heading', { name: 'You are enrolled' })).toBeVisible()
  const enrolled = await api<{eligibility_version:string; eligibility_confirmed_at:string}>(page, '/auth/me')
  expect(enrolled.eligibility_version).toMatch(/^eligibility-v1-/)
  expect(Date.parse(enrolled.eligibility_confirmed_at)).not.toBeNaN()

  await page.goto('/app')
  // The goal-based recommendation can be a different scenario. Exercise the
  // required checklist task, which also fixes intermediate difficulty.
  await page.getByRole('button', { name: 'Next task: Workload conversation', exact: true }).click()
  await page.getByLabel('How confident do you feel about this conversation?').selectOption('4')
  await page.getByLabel('How anxious do you feel about this conversation?').selectOption('4')
  await page.getByRole('button', { name: /Begin with the manager/ }).click()
  await expect(page.getByText('Thanks for meeting with me. What did you want to discuss?')).toBeVisible()
  await page.getByPlaceholder(/Respond to your manager/).fill(
    'I need you to move the report deadline to Friday because I have 12 hours of priority work this week.',
  )
  await page.getByLabel('Send message').click()
  await expect(page.getByText('Rehearsal complete')).toBeVisible()
  await page.getByLabel('Confidence now').selectOption('4')
  await page.getByLabel('Scenario realism').selectOption('4')
  await page.getByLabel('Feedback usefulness').selectOption('4')
  await page.getByRole('button', { name: 'Save research ratings' }).click()
  await expect(page.getByText('Your original ratings are saved and cannot be changed.')).toBeVisible()

  const studySessions = await api<Array<{session_id:string; roleplay?:{status:string}}>>(page, '/sessions')
  const roleplaySession = studySessions.find(item => item.roleplay?.status === 'completed')
  expect(roleplaySession).toBeTruthy()

  const progress = await api<{completed_tasks:number}>(page, '/research/progress')
  expect(progress.completed_tasks).toBe(1)

  await page.goto('/research')
  await expect(page.getByRole('heading', { name: 'AffectLab pilot study' })).toBeVisible()
  await expect(page.locator('article').getByText('1 / 1', { exact: true })).toBeVisible()
  const dashboard = await api<{participants:number; completed_rehearsals:number; questionnaire_averages:Record<string,number>}>(page, '/research/dashboard')
  expect(dashboard.participants).toBe(1)
  expect(dashboard.completed_rehearsals).toBe(1)
  expect(dashboard.questionnaire_averages).toMatchObject({ pre_confidence: 4, post_confidence: 4 })

  const officialExport = await api<string>(page, '/research/export.csv')
  expect(officialExport).toContain(roleplaySession!.session_id)
  expect(officialExport).not.toContain(syntheticSession!.session_id)

  await restartBackend()

  await expect.poll(async () => {
    try { return (await request.get(`${apiUrl}/health/ready`)).status() } catch { return 0 }
  }, {
    timeout: 60_000,
    intervals: [500, 1_000, 2_000],
  }).toBe(200)
  await page.goto(`/practice?session=${roleplaySession!.session_id}`)
  await expect(page.getByRole('heading', { name: 'Workload conversation' })).toBeVisible()
  await expect(page.getByText('Rehearsal complete')).toBeVisible()
})


test('offline enhanced rehearsal survives network failure, branching and backend restart', async ({page}) => {
  test.setTimeout(180_000)
  await page.goto('/login')
  await page.getByLabel('Email').fill('smoke-researcher@example.com')
  await page.getByLabel('Password').fill('full-stack-smoke-password')
  await page.locator('form').getByRole('button', {name:'Sign in', exact:true}).click()
  await expect(page.getByRole('heading', {name:/Welcome back, Demo/})).toBeVisible()
  await page.goto('/practice?mode=roleplay')
  await page.getByRole('button', {name:/Workload conversation Practise with/}).click()
  await page.getByRole('radio', {name:/intermediate/}).check()
  await page.getByRole('button', {name:'Skip pre-ratings and begin'}).click()
  const opening = 'I have too many tasks and 12 hours of work. Could you help me prioritise?'
  await page.getByRole('textbox').fill(opening)
  await page.route('**/api/chat', route => route.abort('failed'))
  await page.getByLabel('Send message').click()
  await expect(page.getByRole('textbox')).toHaveValue(opening)
  await expect(page.getByRole('alert').first()).toBeVisible()
  await page.unroute('**/api/chat')
  await page.getByLabel('Send message').click()
  await expect(page.getByRole('textbox')).toHaveValue('')
  for (const text of ['I understand the report must be ready by Friday. Could we move the other tasks to Monday?', 'Agreed, I will carry out that plan.']) {
    await page.getByRole('textbox').fill(text)
    await page.getByLabel('Send message').click()
    await expect(page.getByRole('textbox')).toHaveValue('')
  }
  await expect(page.getByText('Rehearsal complete')).toBeVisible()
  const parentUrl = page.url()
  await page.getByRole('button', {name:'Replay', exact:true}).click()
  await page.getByRole('button', {name:/^Turn 2/}).click()
  if (process.env.AFFECTLAB_EVIDENCE_DIR) await page.screenshot({path:join(process.env.AFFECTLAB_EVIDENCE_DIR,'replay.png'),fullPage:true})
  await page.getByRole('button', {name:'Try a different response here'}).click()
  await expect(page).not.toHaveURL(parentUrl)
  const childUrl = page.url()
  await page.getByRole('textbox').fill('Sorry, perhaps I can do everything.')
  await page.getByLabel('Send message').click()
  await expect(page.getByRole('textbox')).toHaveValue('')
  await page.getByRole('button', {name:'Finish & review'}).click()
  await page.getByRole('button', {name:'Compare', exact:true}).click()
  await expect(page.getByRole('region', {name:'Original continuation'})).toBeVisible()
  await expect(page.getByRole('region', {name:'Alternative continuation'})).toContainText('Sorry, perhaps I can do everything.')
  if (process.env.AFFECTLAB_EVIDENCE_DIR) await page.screenshot({path:join(process.env.AFFECTLAB_EVIDENCE_DIR,'comparison.png'),fullPage:true})
  await page.getByRole('button', {name:'Action card', exact:true}).click()
  await page.getByLabel('Main request', {exact:true}).fill('Could we move the other tasks to Monday?')
  await page.getByRole('button', {name:'Save action card', exact:true}).click()
  await expect(page.getByRole('region', {name:'Action card', exact:true}).getByRole('status')).toHaveText('Action card saved.')
  await restartBackend()
  await page.goto(childUrl)
  await page.getByRole('button', {name:'Action card', exact:true}).click()
  await expect(page.getByLabel('Main request', {exact:true})).toHaveValue('Could we move the other tasks to Monday?')
  await page.getByRole('button', {name:'Compare', exact:true}).click()
  await expect(page.getByRole('region', {name:'Original continuation'})).toBeVisible()
  await page.goto(parentUrl)
  await expect(page.getByText('Rehearsal complete')).toBeVisible()
  const progress = await api<{completed_tasks:number}>(page, '/research/progress')
  expect(progress.completed_tasks).toBe(1)
})
