import { confirmStudyEnrollment } from '../enrollment'
import { execFileSync } from 'node:child_process'

import { expect, test, type Page } from '@playwright/test'

const apiUrl = 'http://localhost:8000/api'

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
  await expect(page.getByText('1 / 1', { exact: true })).toBeVisible()
  const dashboard = await api<{participants:number; completed_rehearsals:number; questionnaire_averages:Record<string,number>}>(page, '/research/dashboard')
  expect(dashboard.participants).toBe(1)
  expect(dashboard.completed_rehearsals).toBe(1)
  expect(dashboard.questionnaire_averages).toMatchObject({ pre_confidence: 4, post_confidence: 4 })

  const officialExport = await api<string>(page, '/research/export.csv')
  expect(officialExport).toContain(roleplaySession!.session_id)
  expect(officialExport).not.toContain(syntheticSession!.session_id)

  const project = process.env.FULL_STACK_COMPOSE_PROJECT ?? 'affectlab-full-stack-smoke'
  execFileSync('docker', [
    'compose', '-p', project,
    '-f', '../docker-compose.yml', '-f', '../docker-compose.smoke.yml',
    'restart', 'backend',
  ], { cwd: process.cwd(), stdio: 'inherit', shell: process.platform === 'win32' })

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
