import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e/full-stack',
  outputDir: '../.local/full-stack-results',
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.FULL_STACK_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [{ name: 'full-stack-chromium', use: { ...devices['Desktop Chrome'] } }],
})
