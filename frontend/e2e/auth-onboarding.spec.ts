import { expect, test } from '@playwright/test'
import { expectAccessible, installApiMock } from './support'

test('registration, email confirmation, login, and guided onboarding', async ({ page }) => {
  await installApiMock(page,{authenticated:false,onboarding:false})
  await page.goto('/signup')
  await expectAccessible(page)
  await page.getByLabel('First name').fill('Alex')
  await page.getByLabel('Last name').fill('Morgan')
  await page.getByLabel('Preferred name').fill('Alex')
  await page.getByLabel('Email').fill('new@example.com')
  await page.getByLabel('Password').fill('long-password-123')
  await page.getByLabel(/I accept the account privacy/).check()
  await page.locator('.auth-form').getByRole('button',{name:'Create account'}).click()
  await expect(page.getByRole('heading',{name:'Check your email.'})).toBeVisible()

  await page.goto('/verify-email?token=valid-test-token')
  await expect(page.getByRole('heading',{name:'Email confirmed.'})).toBeVisible()
  await page.getByRole('button',{name:'Continue to sign in'}).click()
  await page.getByLabel('Email').fill('new@example.com')
  await page.getByLabel('Password').fill('long-password-123')
  await page.locator('.auth-form').getByRole('button',{name:'Sign in',exact:true}).click()

  await expect(page.getByRole('heading',{name:'Practise at your own pace.'})).toBeVisible()
  await page.getByRole('button',{name:'Continue'}).click()
  await expect(page.getByRole('heading',{name:'You are the authority on how you feel.'})).toBeVisible()
  await page.getByRole('button',{name:'Continue'}).click()
  await expect(page.getByRole('heading',{name:'Voice is always optional.'})).toBeVisible()
  await page.getByRole('button',{name:'Continue'}).click()
  await expect(page.getByRole('button',{name:/Make clearer requests/i})).toHaveAttribute('aria-pressed','true')
  await page.getByRole('button',{name:'Start practising'}).click()
  await expect(page.getByRole('heading',{name:/Welcome back, Alex/})).toBeVisible()
  await expectAccessible(page)
})
