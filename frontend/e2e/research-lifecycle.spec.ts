import { expect, test } from '@playwright/test'
import { confirmStudyEnrollment } from './enrollment'
import { expectAccessible, installApiMock, studyInformation } from './support'

test('participant enrolls and withdraws with separate research consent', async ({ page }) => {
  const state=await installApiMock(page)
  await page.goto('/settings')
  await expect(page.getByRole('heading',{name:'Participant information and consent'})).toBeVisible()
  await page.getByLabel('Study access code').fill('PILOT-2026')
  await confirmStudyEnrollment(page)
  const enrollmentRequest = page.waitForRequest(request => request.url().endsWith('/research/enroll') && request.method() === 'POST')
  await page.getByRole('button',{name:'Consent and join pilot study'}).click()
  expect((await enrollmentRequest).postDataJSON()).toEqual({access_code:'PILOT-2026',consent_version:studyInformation.version,eligibility_version:studyInformation.eligibility_version,age_confirmed:true,geography_confirmed:true,english_confirmed:true,other_criteria_confirmed:true,information_sheet_read:true,research_participation_accepted:true,data_processing_accepted:true})
  await expect(page.getByRole('heading',{name:'You are enrolled'})).toBeVisible()
  await expect(page.getByText(studyInformation.eligibility_version, {exact:true})).toBeVisible()
  expect(state.user.eligibility_confirmed_at).toBeTruthy()
  await page.getByRole('button',{name:'Withdraw from study'}).click()
  await page.getByLabel(/I understand that withdrawal/).check()
  await page.getByRole('button',{name:'Confirm study withdrawal'}).click()
  await expect(page.getByRole('heading',{name:'You withdrew from the study'})).toBeVisible()
  expect(state.user.study_withdrawn).toBe(true)
  await expectAccessible(page)
})

test('research access is authorized and CSV export downloads', async ({ page }) => {
  await installApiMock(page,{researcher:true})
  await page.goto('/research')
  await expect(page.getByRole('heading',{name:'AffectLab pilot'})).toBeVisible()
  const downloadPromise=page.waitForEvent('download')
  await page.getByRole('button',{name:'Export pseudonymous CSV'}).click()
  const download=await downloadPromise
  expect(download.suggestedFilename()).toContain('.csv')
  await expectAccessible(page)
})

test('non-researcher cannot open the researcher dashboard', async ({ page }) => {
  await installApiMock(page,{researcher:false})
  await page.goto('/research')
  await expect(page.getByRole('heading',{name:'Welcome back.'})).toBeVisible()
  await expect(page.getByText('AffectLab pilot')).not.toBeVisible()
})

test('account deletion requires browser confirmation', async ({ page }) => {
  const state=await installApiMock(page)
  await page.goto('/settings')
  page.once('dialog',dialog=>dialog.accept())
  await page.getByRole('button',{name:'Delete my account'}).click()
  await expect(page).toHaveURL(/\/login$/)
  expect(state.deletedAccount).toBe(true)
})
