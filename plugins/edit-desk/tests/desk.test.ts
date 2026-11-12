import { describe, expect, mock, test } from 'claude-code/testing'

const BAND = {
  plugin: 'edit-desk',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 14, bodyColumns: 110, scroll: { offset: 0, bodyRows: 14 }, view: {} },
} as const

describe('the desk above the prompt', () => {
  test('draws its status and buttons, tracks a video from its own field, hides and shows', async ($, on) => {
    mock.store(on)
    mock.clock(on, { now: 1_000_000 })
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ ...BAND, surface })
      expect(await ui.find({ text: /no video tracked|🎬/ })).toBeDefined()
      for (const key of ['track', 'costs', 'qa', 'details', 'hide']) expect(await ui.find({ key })).toBeDefined()

      await ui.press({ key: 'track' })
      expect(await ui.find({ key: 'film-name' })).toBeDefined()
      await ui.input({ key: 'film-name', text: `My Reel ${surface}` })
      expect(await ui.find({ text: new RegExp(`my-reel-${surface}`) })).toBeDefined()
      expect(await ui.find({ key: 'end' })).toBeDefined()

      await ui.press({ key: 'costs' })
      expect(await ui.find({ text: /API cost per video/ })).toBeDefined()
      await ui.press({ key: 'close' })

      await ui.press({ key: 'end' })
      expect(await ui.find({ key: 'end' })).toBeUndefined()

      await ui.press({ key: 'hide' })
      expect(await ui.find({ key: 'show' })).toBeDefined()
      await ui.press({ key: 'show' })
      expect(await ui.find({ key: 'track' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('the QA view lists the verdicts the shell printed', async ($, on) => {
    mock.store(on)
    mock.clock(on, { now: 2_000_000 })
    on('tool.call', { tool: 'Bash' }, () => {
      const text = 'FAIL: reel.mp4  1080x1920 30 fps 54.33 s  LUFS -14.0  TP -2.0'
      return { result: { stdout: text, stderr: '', interrupted: false }, text }
    })
    await $.tool.call({ tool: 'Bash', command: 'uv run python kit/qa/qa.py output/final/x/reel.mp4' })
    const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
    await ui.press({ key: 'qa' })
    expect(await ui.find({ text: /FAIL\s+reel\.mp4/ })).toBeDefined()
    await ui.unmount()
  })
})
