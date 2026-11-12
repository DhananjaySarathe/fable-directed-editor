// Pure helpers for the detailed pane: a film's (or take's) stages read off the files the pipeline writes, which are
// stale, its QA findings, step ETAs and the cost groups. No `$` here, so the tests can call them directly.

import type { DeskFinding, DeskStage, StageState } from '../types'

export type Kind = 'film' | 'take'

/** One stage: the file that proves it ran (`newest` = the newest file with that extension in the folder), the steps
 * (lib.classify labels) that produce it, and inputs whose edits after it make it stale. Paths use {f} for the name. */
export type StageSpec = { key: string; label: string; path: string; newest?: string; steps: string[]; inputs?: string[] }

const W = 'output/temp/films/{f}'

export const STAGES: Record<Kind, StageSpec[]> = {
  film: [
    { key: 'prep', label: 'Prep (voice, face, matte)', path: `${W}/work/take.mp4`, steps: ['prep'] },
    { key: 'grade', label: 'Grade', path: `${W}/work/take_graded.mp4`, steps: ['grade'] },
    { key: 'cut', label: 'Cut (A-roll, VO)', path: `${W}/work/aroll.mp4`, steps: ['cut'], inputs: ['films/{f}/edl.json', 'films/{f}/cuts.json'] },
    { key: 'audit', label: 'Join audit', path: `${W}/work/cutcheck.json`, steps: ['QA'] },
    { key: 'mix', label: 'Mix', path: `${W}/work/mix.wav`, steps: ['mix'] },
    { key: 'render', label: 'Render (graphics)', path: `${W}/renders`, newest: '.mp4', steps: ['render'], inputs: ['films/{f}/build.py', 'films/{f}/src/template.html'] },
    { key: 'final', label: 'Final file', path: 'output/final/{f}', newest: '.mp4', steps: [] },
    { key: 'qa', label: 'QA', path: `${W}/review/qa.json`, steps: ['QA'] },
  ],
  take: [
    { key: 'probe', label: 'Probe (footage copy)', path: 'output/jobs/{f}/probe.json', steps: [] },
    { key: 'analyze', label: 'Analyze (transcript)', path: 'output/jobs/{f}/analysis.json', steps: ['prep'] },
  ],
}

export function at(path: string, film: string): string {
  return path.replaceAll('{f}', film)
}

const SLACK_MS = 2000      // files a step writes together land a second or two apart

/**
 * The stages' states from when each one's file was written (undefined: not there) and its inputs' newest edit. A
 * stage is stale when an earlier stage, or one of its inputs, changed after it; `sentAt` adds the last row.
 */
export function stagesFrom(
  specs: StageSpec[], times: (number | undefined)[], inputTimes: (number | undefined)[], sentAt?: number,
): DeskStage[] {
  let upstream = 0
  const out: DeskStage[] = specs.map((s, i) => {
    const t = times[i]
    const input = inputTimes[i] ?? 0
    let state: StageState = 'todo'
    let note: string | undefined
    if (t !== undefined) {
      if (upstream > t + SLACK_MS) {
        state = 'stale'
        note = 'an earlier stage changed after it'
      } else if (input > t + SLACK_MS) {
        state = 'stale'
        note = 'its inputs were edited after it'
      } else {
        state = 'done'
      }
      upstream = Math.max(upstream, t)
    }
    return { key: s.key, label: s.label, state, at: t, note }
  })
  const final = out.find(s => s.key === 'final')
  out.push({
    key: 'sent', label: 'Sent to you',
    state: sentAt === undefined ? 'todo' : final?.at !== undefined && final.at > sentAt + SLACK_MS ? 'stale' : 'done',
    at: sentAt,
    note: sentAt !== undefined && final?.at !== undefined && final.at > sentAt + SLACK_MS ? 'the final file changed after it was sent' : undefined,
  })
  return out
}

/** Which stage a running step belongs to: the first of its stages not done yet, else the last (a re-run). */
export function runningStage(specs: StageSpec[], stages: DeskStage[], label: string): string | undefined {
  const matching = specs.filter(s => s.steps.includes(label)).map(s => s.key)
  if (matching.length === 0) return undefined
  return matching.find(k => stages.find(s => s.key === k)?.state !== 'done') ?? matching[matching.length - 1]
}

type QaJson = { verdict?: string; issues?: { severity?: string; id?: string; t?: number; detail?: string; fix?: string }[] }
type CutJson = { joins?: CutRow[]; trims?: CutRow[] }
type CutRow = { t?: number; verdict?: string; why?: string; left?: string; right?: string }

/** kit/qa/qa.py's --json report: its verdict and each finding. */
export function readQaReport(text: string): { verdict: 'PASS' | 'WARN' | 'FAIL'; findings: DeskFinding[] } | undefined {
  let j: QaJson
  try {
    j = JSON.parse(text) as QaJson
  } catch {
    return undefined
  }
  const verdict = j.verdict === 'FAIL' || j.verdict === 'WARN' || j.verdict === 'PASS' ? j.verdict : undefined
  if (!verdict) return undefined
  const findings = (j.issues ?? []).map(i => ({
    t: typeof i.t === 'number' ? i.t : undefined,
    severity: i.severity === 'CRITICAL' || i.severity === 'HIGH' ? 'fail' as const : 'warn' as const,
    text: `${i.detail ?? i.id ?? 'issue'}${i.fix ? ` → ${i.fix}` : ''}`,
  }))
  return { verdict, findings }
}

/** kit.cut.cutcheck's report: the joins and trims it did not pass. */
export function readCutcheck(text: string): DeskFinding[] {
  let j: CutJson
  try {
    j = JSON.parse(text) as CutJson
  } catch {
    return []
  }
  return [...(j.joins ?? []), ...(j.trims ?? [])]
    .filter(r => r.verdict && r.verdict !== 'PASS')
    .map(r => ({
      t: typeof r.t === 'number' ? r.t : undefined,
      severity: r.verdict === 'FAIL' ? 'fail' as const : 'warn' as const,
      text: `join: ${r.why ?? `${r.left ?? ''} | ${r.right ?? ''}`}`,
    }))
}

/** The median of a step's past durations, or undefined with none. */
export function eta(past: readonly number[] | undefined): number | undefined {
  if (!past?.length) return undefined
  const s = [...past].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1]! + s[m]!) / 2
}

/** Keeps the last five durations of a step. */
export function remember(past: readonly number[] | undefined, ms: number): number[] {
  return [...(past ?? []), ms].slice(-5)
}

export const GROUPS = ['Planning', 'Prep and grade', 'Cut and mix', 'Graphics and render', 'QA and fixes'] as const
export const EARLIER = 'Before the split'

/** The cost group a turn's money goes to: the step that ran in it, else the film's last step (work around it). */
export function groupOf(step: string | undefined): string {
  switch (step) {
    case 'prep':
    case 'grade':
      return 'Prep and grade'
    case 'cut':
    case 'mix':
      return 'Cut and mix'
    case 'render':
      return 'Graphics and render'
    case 'QA':
      return 'QA and fixes'
    default:
      return 'Planning'
  }
}

/** Adds what the film cost since the split last summed to the group: the split always adds up to the film's total. A
 * film tracked before splitting existed starts with its whole earlier cost under EARLIER. */
export function addToSplit(split: Record<string, number> | undefined, total: number, group: string): Record<string, number> {
  const next = { ...(split ?? (total > 0 ? { [EARLIER]: total } : {})) }
  if (!split) return next
  const sum = Object.values(next).reduce((a, b) => a + b, 0)
  const delta = total - sum
  if (delta > 0.0005) next[group] = (next[group] ?? 0) + delta
  return next
}

/** A text bar, `width` cells: ███░░░ */
export function bar(frac: number, width: number): string {
  const n = Math.max(0, Math.min(width, Math.round(Math.max(0, Math.min(1, frac)) * width)))
  return '█'.repeat(n) + '░'.repeat(width - n)
}

/** Seconds as m:ss.s for a finding's timecode. */
export function timecode(t: number): string {
  const m = Math.floor(t / 60)
  return `${m}:${(t - m * 60).toFixed(1).padStart(4, '0')}`
}

export function megabytes(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`
}
