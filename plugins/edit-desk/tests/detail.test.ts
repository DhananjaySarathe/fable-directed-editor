import { describe, expect, mock, test } from 'claude-code/testing'

import {
  EARLIER, STAGES, addToSplit, bar, eta, groupOf, readCutcheck, readQaReport, runningStage, stagesFrom, timecode,
} from '../hooks/film'

describe('film: stages and reports', () => {
  test('a stage is stale when an earlier one or its inputs changed after it', () => {
    const specs = STAGES.film
    const times = [100_000, 200_000, 300_000, 400_000, 500_000, 600_000, 700_000, 800_000]
    const inputs = specs.map(() => undefined as number | undefined)
    const fresh = stagesFrom(specs, times, inputs, 900_000)
    expect(fresh.every(s => s.state === 'done')).toBe(true)
    expect(fresh.at(-1)?.key).toBe('sent')

    inputs[5] = 650_000                              // build.py edited after the render
    const edited = stagesFrom(specs, times, inputs)
    expect(edited.find(s => s.key === 'render')?.state).toBe('stale')
    expect(edited.find(s => s.key === 'sent')?.state).toBe('todo')

    const regraded = stagesFrom(specs, [100_000, 950_000, 300_000, undefined, 500_000, undefined, undefined, undefined], specs.map(() => undefined))
    expect(regraded.find(s => s.key === 'cut')?.state).toBe('stale')
    expect(regraded.find(s => s.key === 'audit')?.state).toBe('todo')

    const resent = stagesFrom(specs, times, specs.map(() => undefined), 600_000)
    expect(resent.find(s => s.key === 'sent')?.state).toBe('stale')
  })

  test('a running step lands on the first of its stages not done', () => {
    const specs = STAGES.film
    const stages = stagesFrom(specs, [1, 2, 3, undefined, undefined, undefined, undefined, undefined], specs.map(() => undefined))
    expect(runningStage(specs, stages, 'QA')).toBe('audit')
    expect(runningStage(specs, stages, 'render')).toBe('render')
    expect(runningStage(specs, stages, 'nothing')).toBeUndefined()
  })

  test('reads qa.py and the join audit', () => {
    const qa = readQaReport(JSON.stringify({
      verdict: 'WARN',
      issues: [{ severity: 'MEDIUM', id: 'cut@30.1', t: 30.1, detail: 'click at the cut', fix: 'add a fade' }],
    }))
    expect(qa?.verdict).toBe('WARN')
    expect(qa?.findings[0]).toEqual({ t: 30.1, severity: 'warn', text: 'click at the cut → add a fade' })
    expect(readQaReport('not json')).toBeUndefined()

    const joins = readCutcheck(JSON.stringify({ joins: [{ t: 3.5, verdict: 'WARN', why: 'mid-word' }, { t: 4, verdict: 'PASS' }], trims: [] }))
    expect(joins).toEqual([{ t: 3.5, severity: 'warn', text: 'join: mid-word' }])
    expect(timecode(30.1)).toBe('0:30.1')
    expect(timecode(75.25)).toBe('1:15.3')
  })

  test('the cost split always adds up to the total', () => {
    expect(groupOf('render')).toBe('Graphics and render')
    expect(groupOf(undefined)).toBe('Planning')
    let split = addToSplit(undefined, 2, 'Planning')
    expect(split).toEqual({ [EARLIER]: 2 })
    split = addToSplit(split, 3.5, 'Graphics and render')
    split = addToSplit(split, 4, 'QA and fixes')
    expect(split).toEqual({ [EARLIER]: 2, 'Graphics and render': 1.5, 'QA and fixes': 0.5 })
    expect(addToSplit({}, 0.25, 'Planning')).toEqual({ Planning: 0.25 })
    expect(eta([30_000, 10_000, 20_000])).toBe(20_000)
    expect(eta([])).toBeUndefined()
    expect(bar(0.5, 10)).toBe('█████░░░░░')
  })
})

const ROOT = '/repo'
const FILES: Record<string, number> = {
  [`${ROOT}/output/temp/films/reel/work/take.mp4`]: 1_000,
  [`${ROOT}/output/temp/films/reel/work/take_graded.mp4`]: 2_000,
  [`${ROOT}/output/temp/films/reel/work/aroll.mp4`]: 3_000,
  [`${ROOT}/output/temp/films/reel/work/mix.wav`]: 4_000,
  [`${ROOT}/films/reel/build.py`]: 9_000,          // edited after the render
  [`${ROOT}/output/temp/films/reel/review/qa.json`]: 7_000,
  [`${ROOT}/output/final/reel/thumbnail/gpt_prompt.md`]: 8_000,
}
const DIRS: Record<string, { name: string; kind: 'file' | 'dir'; mtimeMs: number; size: number; isLink: false }[]> = {
  [`${ROOT}/output/temp/films`]: [{ name: 'reel', kind: 'dir', mtimeMs: 9_000, size: 0, isLink: false }],
  [`${ROOT}/output/temp/films/reel/renders`]: [{ name: 'raw.mp4', kind: 'file', mtimeMs: 5_000, size: 9e7, isLink: false }],
  [`${ROOT}/output/final/reel/thumbnail/photos`]: ['face_01.jpg', 'face_04.jpg', 'ref_01.jpg', 'sheet.jpg']
    .map(name => ({ name, kind: 'file' as const, mtimeMs: 8_000, size: 1, isLink: false as const })),
  [`${ROOT}/output/final/reel`]: [{ name: 'reel.mp4', kind: 'file', mtimeMs: 6_000, size: 4.2e7, isLink: false }],
}
const QA = JSON.stringify({ verdict: 'WARN', issues: [{ severity: 'MEDIUM', id: 'cut@30.1', t: 30.1, detail: 'click at the cut', fix: 'add a fade' }] })

const PANE = {
  plugin: 'edit-desk',
  component: 'Pane',
  requestId: 'edit-desk',
  props: { title: 'Edit Desk', isFocused: true, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 60 }, view: {} },
} as const

describe('the detailed pane', () => {
  test('switches from the summary to one film: stages, staleness, QA findings, toggles', async ($, on) => {
    mock.store(on)
    mock.clock(on, { now: 10_000 })
    on('session.root', () => ({ value: ROOT }))
    on('fs.list', (_$, e) => ({ value: DIRS[e.path] ?? [] }))
    on('fs.exists', (_$, e) => ({ value: e.path in FILES || e.path in DIRS || e.path === `${ROOT}/output/temp/films/reel` }))
    on('fs.stat', (_$, e) => {
      const t = FILES[e.path]
      return t === undefined ? { deny: 'ENOENT' } : { value: { kind: 'file' as const, size: 1, mtimeMs: t, isLink: false } }
    })
    on('fs.read', (_$, e) => {
      if (e.path.endsWith('gpt_prompt.md')) return { value: 'I am attaching 3 photos of me...' }
      return e.path.endsWith('qa.json') ? { value: QA } : { deny: 'ENOENT' }
    })
    let clipboard = ''
    on('process.run', (_$, e) => {
      if (e.argv[0] === 'pbcopy') clipboard = e.init?.stdin ?? ''
      return { value: { exitCode: e.argv[0] === 'pbcopy' ? 0 : 1, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    })
    let asked = ''
    on('prompt.submit', (_$, e) => {
      asked = e.text
      return { text: e.text }
    })

    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ ...PANE, surface })
      expect(await ui.find({ text: /Cost per video/ })).toBeDefined()        // the summary by default
      await ui.press({ key: 'mode-detailed' })
      expect(await ui.find({ text: /Render \(graphics\)\s+stale/ })).toBeDefined()
      expect(await ui.find({ text: /its inputs were edited after it/ })).toBeDefined()
      expect(await ui.find({ text: /reel\.mp4/ })).toBeDefined()
      expect(await ui.find({ text: /0:30\.1 click at the cut → add a fade/ })).toBeDefined()
      expect(await ui.find({ text: /Stale stage/ })).toBeDefined()

      expect(await ui.find({ text: /GPT prompt ready · 3 photos to attach/ })).toBeDefined()
      await ui.press({ key: 'copy-gpt' })
      if (surface === 'desktop') expect(clipboard).toMatch(/attaching 3 photos/)
      await ui.press({ key: 'thumb-kit' })
      expect(asked).toMatch(/Make the thumbnail kit again for reel: follow kit\/thumbs\/THUMBNAILS\.md/)

      await ui.press({ key: 'qa-fix' })
      expect(asked).toMatch(/Fix these QA findings on reel/)

      await ui.press({ key: 'gate' })
      expect(await ui.find({ key: 'gate', label: 'QA gate: off' } as never)).toBeDefined()
      await ui.press({ key: 'gate' })

      await ui.press({ key: 'mode-simple' })
      expect(await ui.find({ text: /Cost per video/ })).toBeDefined()
      await ui.unmount()
    }
  })
})
