import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const frontendDirectory = fileURLToPath(new URL('..', import.meta.url))
const project = process.env.FULL_STACK_COMPOSE_PROJECT ?? 'affectlab-full-stack-smoke'
const compose = [
  'compose',
  '-p', project,
  '-f', '../docker-compose.yml',
  '-f', '../docker-compose.smoke.yml',
]

function run(command, args, allowFailure = false) {
  const result = spawnSync(command, args, {
    cwd: frontendDirectory,
    env: { ...process.env, FULL_STACK_COMPOSE_PROJECT: project },
    shell: process.platform === 'win32',
    stdio: 'inherit',
  })
  if (!allowFailure && result.status !== 0) {
    const error = new Error(`${command} exited with status ${result.status ?? 1}`)
    error.exitCode = result.status ?? 1
    throw error
  }
  return result.status ?? 1
}

try {
  run('docker', [...compose, 'up', '--build', '--wait'])
  const status = run(
    'npx',
    ['playwright', 'test', '--config=playwright.fullstack.config.ts'],
    true,
  )
  if (status !== 0) process.exitCode = status
} catch (error) {
  process.exitCode = error.exitCode ?? 1
  console.error(error)
} finally {
  if (process.exitCode) run('docker', [...compose, 'logs', '--no-color', '--tail', '200'], true)
  run('docker', [...compose, 'down', '--volumes', '--remove-orphans'], true)
}
