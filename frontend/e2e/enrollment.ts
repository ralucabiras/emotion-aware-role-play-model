import { expect, type Page } from '@playwright/test'

export async function confirmStudyEnrollment(page: Page) {
  const submit = page.getByRole('button', { name: 'Consent and join pilot study' })
  await expect(submit).toBeDisabled()
  for (const name of [
    /I am aged 18 or over/,
    /I am currently located in Romania/,
    /I am comfortable reading and responding in English/,
    /I meet all the additional inclusion and exclusion criteria/,
    /I have read and understood participant information version/,
    /I voluntarily agree to participate/,
    /I agree to the processing described above/,
  ]) {
    await expect(submit).toBeDisabled()
    await page.getByRole('checkbox', { name }).check()
  }
  await expect(submit).toBeEnabled()
}
