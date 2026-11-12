import { describe, expect, mock, test } from 'claude-code/testing'

import {
  backgroundId, classify, envTarget, filmFromCommand, parseNotification, parseQa, withNoUpdate,
} from '../hooks/lib'

describe('lib: reading commands', () => {
  test('labels the long pipeline steps, most important first', () => {
    expect(classify('npx hyperframes render output/temp/films/x/hf -o raw.mp4')).toBe('render')
    expect(classify('uv run python prep.py --only=grade && uv run python kit/qa/qa.py a.mp4')).toBe('grade')
    expect(classify('uv run python kit/qa/qa.py out.mp4 --cuts=c.json')).toBe('QA')
    expect(classify('ls -la')).toBeUndefined()
  })

  test('finds .env but never its examples', () => {
    expect(envTarget('cat .env')).toBe('.env')
    expect(envTarget('grep KEY "/repo/.env.local"')).toBe('/repo/.env.local')
    expect(envTarget('git add .env')).toBe('.env')
    expect(envTarget('cp .env.example .env.sample')).toBeUndefined()
    expect(envTarget('echo $ENV_NAME; cat src/env.ts')).toBeUndefined()
  })

  test('adds the HyperFrames no-update flag once', () => {
    expect(withNoUpdate('npx hyperframes lint hf')).toBe('export HYPERFRAMES_NO_UPDATE_CHECK=1; npx hyperframes lint hf')
    expect(withNoUpdate('HYPERFRAMES_NO_UPDATE_CHECK=1 npx hyperframes render hf')).toBe('HYPERFRAMES_NO_UPDATE_CHECK=1 npx hyperframes render hf')
    expect(withNoUpdate('ls')).toBe('ls')
  })

  test('names the film or take a pipeline command works on', () => {
    expect(filmFromCommand('uv run python films/haiku-vs-opus/build.py --audio')).toBe('haiku-vs-opus')
    expect(filmFromCommand('cd "/repo/films/what-it-cost" && uv run python edl.py')).toBe('what-it-cost')
    expect(filmFromCommand('uv run shorts probe "/x/clip.mp4" --job haiky')).toBe('haiky')
    expect(filmFromCommand('uv run shorts analyze haiky')).toBe('haiky')
    expect(filmFromCommand('cat films/what-it-cost/README.md')).toBeUndefined()
  })
})

describe('lib: reading outputs', () => {
  test('reads qa.py verdicts', () => {
    const qa = parseQa('PASS: reel.mp4  1080x1920 30 fps 54.33 s  LUFS -14.0  TP -2.0\nFAIL: other.mp4  1080x1920 30 fps 9.00 s')
    expect(qa.get('reel.mp4')).toBe('PASS')
    expect(qa.get('other.mp4')).toBe('FAIL')
  })

  test('reads a background task notification and its id at launch', () => {
    const n = parseNotification('<task-notification>\n<task-id>bz5o61jaf</task-id>\n<output-file>/tmp/t/bz5o61jaf.output</output-file>\n<status>completed</status>\n<summary>Background command "render" completed (exit code 0)</summary>\n</task-notification>')
    expect(n).toEqual({ id: 'bz5o61jaf', status: 'completed', summary: 'Background command "render" completed (exit code 0)', outputFile: '/tmp/t/bz5o61jaf.output', exitCode: 0 })
    expect(backgroundId('Command running in background with ID: b074qvex7. Output is being written to: /tmp/x')).toBe('b074qvex7')
  })
})

describe('hooks', () => {
  test('a shell command that touches .env is refused', async ($, on) => {
    mock.store(on)
    mock.clock(on)
    let reached = false
    on('tool.call', { tool: 'Bash' }, () => {
      reached = true
      return { result: { stdout: '', stderr: '', interrupted: false }, text: '' }
    })
    const r = await $.tool.call({ tool: 'Bash', command: 'cat .env' })
    expect(String(r.deny ?? r.text)).toContain('off limits')
    expect(reached).toBe(false)
  })

  test('hyperframes commands run with the no-update flag', async ($, on) => {
    mock.store(on)
    mock.clock(on)
    let seen = ''
    on('tool.call', { tool: 'Bash' }, ($, e) => {
      seen = e.command
      return { result: { stdout: '', stderr: '', interrupted: false }, text: '' }
    })
    await $.tool.call({ tool: 'Bash', command: 'npx hyperframes lint output/temp/films/x/hf' })
    expect(seen).toBe('export HYPERFRAMES_NO_UPDATE_CHECK=1; npx hyperframes lint output/temp/films/x/hf')
  })

  test('a video whose last QA failed is not sent; one that passed is', async ($, on) => {
    mock.store(on)
    mock.clock(on, { now: 1_000_000 })
    let verdict = 'FAIL'
    on('tool.call', { tool: 'Bash' }, () => {
      const text = `${verdict}: reel.mp4  1080x1920 30 fps 54.33 s  LUFS -14.0  TP -2.0`
      return { result: { stdout: text, stderr: '', interrupted: false }, text }
    })
    let sent = 0
    on('tool.call', { tool: 'SendUserFile' }, () => {
      sent += 1
      return { result: { files: [] }, text: 'sent' }
    })
    await $.tool.call({ tool: 'Bash', command: 'uv run python kit/qa/qa.py output/final/x/reel.mp4' })
    const refused = await $.tool.call({ tool: 'SendUserFile', files: ['output/final/x/reel.mp4'], status: 'normal' })
    expect(String(refused.deny ?? refused.text)).toContain('failed its last QA run')
    expect(sent).toBe(0)

    verdict = 'PASS'
    await $.tool.call({ tool: 'Bash', command: 'uv run python kit/qa/qa.py output/final/x/reel.mp4' })
    await $.tool.call({ tool: 'SendUserFile', files: ['output/final/x/reel.mp4'], status: 'normal' })
    expect(sent).toBe(1)
  })
})
