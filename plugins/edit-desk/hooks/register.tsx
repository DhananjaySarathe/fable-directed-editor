// edit-desk: the Fable-Directed Editor repo's rules and checks, enforced and surfaced while Claude edits.
//   1. Guardrails: HYPERFRAMES_NO_UPDATE_CHECK=1 on every hyperframes command; .env is never read, printed or committed;
//      a video whose last QA run failed is never sent to the user (the QA gate, which the pane can switch off).
//   2. Render alerts: the long step running (render, grade, prep, mix, cut, QA) shows live with its elapsed time; a toast
//      and a sound when it ends, in the foreground (over 30 s) or in the background.
//   3. Cost per video: the tracked video's API cost so far, split by stage, the context window and the 5-hour limit;
//      totals carry across sessions ($.store).
//   4. The desk: a band above the prompt, always there, with buttons (track a video, costs, QA, details, hide) and a
//      details pane, simple (the summary) or detailed (one film's stages, preview, QA findings, cost split, controls).
//      /film start <name> | end | cost and /desk do the same from the prompt.
import { atom, read, update } from 'claude-code'
import type { ElementConstructor, EngineInterface, ImageProps, InputProps, Register, RenderChildren, SelectProps, SvgProps } from 'claude-code'

import type { Desk, DeskAlert, DeskDetail, DeskFinding, DeskQa, DeskStage, DeskVideo, DeskView, PaneMode } from '../types'
import {
  EARLIER, GROUPS, STAGES, addToSplit, at, bar, eta, groupOf, megabytes, readCutcheck, readQaReport, remember,
  runningStage, stagesFrom, timecode,
} from './film'
import type { Kind } from './film'
import {
  ago, backgroundId, basename, classify, clockText, duration, envTarget, filmFromCommand, filmName, isEnvPath, isVideo,
  parseNotification, parseQa, usd, withNoUpdate,
} from './lib'
import type { Notification, QaRecord } from './lib'

type Job = { label: string; startedAt: number; film?: string }
type Film = { name: string; baseUsd: number; carriedUsd: number }

const LONG_MS = 30_000          // a foreground step this long gets a toast and a sound when it ends
const PANE = 'edit-desk'
const THUMBS = 'output/temp/edit-desk'

const EMPTY: Desk = { film: null, ctx: null, five: null, jobs: [], alerts: [], films: [], qa: [] }
const desk = atom({ plugin: 'edit-desk', key: 'desk' } as const, EMPTY)
const view = atom({ plugin: 'edit-desk', key: 'view' } as const, 'compact' as DeskView)
const clock = atom({ plugin: 'edit-desk', key: 'now' } as const, 0)
const pane = atom({ plugin: 'edit-desk', key: 'pane' } as const, 'simple' as PaneMode)
const pick = atom({ plugin: 'edit-desk', key: 'pick' } as const, null as string | null)
const detail = atom({ plugin: 'edit-desk', key: 'detail' } as const, null as DeskDetail | null)

const running = new Map<string, Job>()       // tool_use_id (foreground) or background task id -> the step (the module's own: a reload starts it over)
const handled = new Set<string>()            // background task ids already announced
const thumbs = new Map<string, DeskVideo>()  // video path -> its probe and thumbnail, for the mtime it was made at
let film: Film | undefined
let turnStep: string | undefined             // the last pipeline step run in this turn: where its cost goes
let rootDir: string | undefined

// ---------------------------------------------------------------------------------------------- cost, QA, the desk
async function sessionUsd($: EngineInterface) {
  try {
    return (await $.session.usage()).cost?.usd ?? 0
  } catch {
    return 0                                   // no cost ledger here (a test, a host without one)
  }
}

async function filmUsd($: EngineInterface) {
  return film ? film.carriedUsd + (await sessionUsd($)) - film.baseUsd : 0
}

async function films($: EngineInterface) {
  return ((await $.store.get('films')) ?? {}) as Record<string, number>
}

async function qaBook($: EngineInterface) {
  return ((await $.store.get('qa')) ?? {}) as Record<string, QaRecord>
}

async function stored<T>($: EngineInterface, key: string, fallback: T): Promise<T> {
  return ((await $.store.get(key)) ?? fallback) as T
}

async function saveFilm($: EngineInterface) {
  if (!film) return
  const all = await films($)
  all[film.name] = await filmUsd($)
  await $.store.set('films', all)
  await $.store.set('film', film.name)
}

async function startFilm($: EngineInterface, name: string) {
  await saveFilm($)
  film = { name, baseUsd: await sessionUsd($), carriedUsd: (await films($))[name] ?? 0 }
  await $.store.set('film', name)
  const splits = await stored<Record<string, Record<string, number>>>($, 'split', {})
  if (!splits[name]) {
    splits[name] = film.carriedUsd > 0 ? { [EARLIER]: film.carriedUsd } : {}
    await $.store.set('split', splits)
  }
}

async function endFilm($: EngineInterface) {
  if (!film) return undefined
  const total = await filmUsd($)
  await saveFilm($)
  const done = { name: film.name, usd: total }
  film = undefined
  await $.store.delete('film')
  return done
}

/** Everything the desk and the status line show, read fresh: the band and the pane redraw from this one value. */
async function refresh($: EngineInterface) {
  let u
  try {
    u = await $.session.usage()
  } catch {
    u = undefined                              // no usage here (a test, a host without a ledger): the rest still shows
  }
  const filmNow = film ? { name: film.name, usd: film.carriedUsd + (u?.cost?.usd ?? 0) - film.baseUsd } : null
  const ctx = u?.context.percent != null ? Math.round(u.context.percent) : null
  const fiveLimit = u?.rateLimits.find(r => r.kind === 'five_hour')
  const five = fiveLimit ? Math.round(fiveLimit.percentUsed) : null
  const all = await films($)
  if (filmNow) all[filmNow.name] = filmNow.usd
  const book = await qaBook($)
  const qa: DeskQa[] = Object.entries(book).map(([name, r]) => ({ name, verdict: r.verdict, at: r.at })).sort((a, b) => b.at - a.at).slice(0, 12)
  const jobs = [...running.values()].map(j => ({ label: j.label, film: j.film, startedAt: j.startedAt }))
  await update($, desk, prev => ({
    film: filmNow, ctx, five, jobs, qa,
    alerts: prev?.alerts ?? [],
    films: Object.entries(all).map(([name, v]) => ({ name, usd: v })).sort((a, b) => b.usd - a.usd),
  }))
  const parts: string[] = []
  if (filmNow) parts.push(`🎬 ${filmNow.name} ${usd(filmNow.usd)}`)
  if (ctx != null) parts.push(`ctx ${ctx}%`)
  if (five != null) parts.push(`5h ${five}%`)
  if (jobs.length) parts.push(`⏳ ${[...new Set(jobs.map(j => j.label))].join(', ')}`)
  $.ui.status(parts.length ? parts.join(' · ') : undefined)
  if ((await read($, pane)) === 'detailed') await scan($)
}

async function alert($: EngineInterface, text: string, ok: boolean) {
  const item: DeskAlert = { text, ok, at: await $.clock.now() }
  await update($, desk, prev => ({ ...(prev ?? EMPTY), alerts: [item, ...(prev?.alerts ?? [])].slice(0, 10) }))
  $.ui.toast(`${ok ? '✅' : '❌'} ${text}`)
}

async function noteQa($: EngineInterface, text: string | undefined) {
  if (!text) return
  const found = parseQa(text)
  if (found.size === 0) return
  const book = await qaBook($)
  const at = await $.clock.now()
  for (const [name, verdict] of found) {
    book[name] = { verdict, at }
  }
  await $.store.set('qa', book)
  for (const [name, verdict] of found) {
    if (verdict === 'FAIL') await alert($, `QA failed: ${name} (it won't be sent until it passes)`, false)
  }
}

async function chime($: EngineInterface, ok: boolean) {
  if (!(await stored($, 'sound', true))) return
  try {
    await $.audio.play({ asset: ok ? 'assets/done.wav' : 'assets/fail.wav' })
  } catch {
    // no player on this machine: the toast is enough
  }
}

/** A step ended: its duration feeds the ETA, the turn's cost goes to its stage. */
async function stepEnded($: EngineInterface, job: Job, ms: number, ok: boolean) {
  if (!ok) return
  const all = await stored<Record<string, number[]>>($, 'durations', {})
  all[job.label] = remember(all[job.label], ms)
  await $.store.set('durations', all)
}

async function stepStarted($: EngineInterface, job: Job) {
  turnStep = job.label
  if (!job.film) return
  const last = await stored<Record<string, string>>($, 'lastStep', {})
  last[job.film] = job.label
  await $.store.set('lastStep', last)
}

async function finishBackground($: EngineInterface, n: Notification) {
  if (handled.has(n.id)) return
  handled.add(n.id)
  const job = running.get(n.id)
  running.delete(n.id)
  if (!job) return                             // not a pipeline step: no alert
  let output = ''
  if (n.outputFile) {
    try {
      output = await $.fs.read(n.outputFile)
    } catch {
      // the output file is gone or unreadable: judge by the status alone
    }
  }
  await noteQa($, output)
  const qaFailed = [...parseQa(output).values()].includes('FAIL')
  const ok = n.status === 'completed' && (n.exitCode === undefined || n.exitCode === 0) && !qaFailed
  const ms = (await $.clock.now()) - job.startedAt
  await stepEnded($, job, ms, n.status === 'completed' && (n.exitCode === undefined || n.exitCode === 0))
  await alert($, `${job.label}${job.film ? ` (${job.film})` : ''} ${ok ? 'done' : 'failed'} in ${duration(ms)}`, ok)
  await chime($, ok)
  await refresh($)
}

// ---------------------------------------------------------------------------------------------- the detailed view's scan
async function repo($: EngineInterface) {
  rootDir ??= await $.session.root()
  return rootDir
}

async function mtimeOf($: EngineInterface, path: string) {
  try {
    const s = await $.fs.stat(path)
    return s.kind === 'file' ? s.mtimeMs : undefined
  } catch {
    return undefined
  }
}

async function listing($: EngineInterface, dir: string) {
  try {
    return await $.fs.list(dir)
  } catch {
    return []
  }
}

async function newestIn($: EngineInterface, dir: string, ext: string) {
  const files = (await listing($, dir)).filter(f => f.kind === 'file' && f.name.toLowerCase().endsWith(ext))
  const top = files.sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
  return top ? { path: `${dir}/${top.name}`, mtime: top.mtimeMs, bytes: top.size } : undefined
}

async function readText($: EngineInterface, path: string) {
  try {
    return await $.fs.read(path)
  } catch {
    return undefined
  }
}

/** Films (output/temp/films, films/) and takes (output/jobs), the most recently touched first. */
async function options($: EngineInterface, r: string) {
  const seen = new Map<string, number>()
  for (const dir of ['output/temp/films', 'output/jobs', 'films']) {
    for (const e of await listing($, `${r}/${dir}`)) {
      if (e.kind !== 'dir' || e.name.startsWith('.') || e.name.startsWith('_')) continue
      let t = e.mtimeMs
      if (t === 0) t = (await $.fs.stat(`${r}/${dir}/${e.name}`).catch(() => undefined))?.mtimeMs ?? 0
      seen.set(e.name, Math.max(seen.get(e.name) ?? 0, t))
    }
  }
  return [...seen.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name)
}

async function kindOf($: EngineInterface, r: string, name: string): Promise<Kind | 'none'> {
  if (await $.fs.exists(`${r}/output/temp/films/${name}`)) return 'film'
  if (await $.fs.exists(`${r}/output/jobs/${name}`)) return 'take'
  if (await $.fs.exists(`${r}/films/${name}`)) return 'film'
  return 'none'
}

async function run($: EngineInterface, tool: 'ffmpeg' | 'ffprobe', args: string[]) {
  for (const exe of [tool, `/opt/homebrew/bin/${tool}`, `/usr/local/bin/${tool}`]) {
    try {
      return await $.process.run([exe, ...args], { timeoutMs: 20_000 })
    } catch {
      // not on this PATH: try the next place
    }
  }
  return undefined
}

/** The video's size and length (ffprobe) and a thumbnail a third of the way in, made once per version of the file. */
async function probe($: EngineInterface, r: string, name: string, v: { path: string; mtime: number; bytes: number }): Promise<DeskVideo> {
  const cached = thumbs.get(v.path)
  if (cached && cached.mtime === v.mtime) return cached
  const out: DeskVideo = { path: v.path, name: basename(v.path), mtime: v.mtime, bytes: v.bytes }
  const p = await run($, 'ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', v.path])
  try {
    const j = JSON.parse(p?.stdout ?? '{}') as { streams?: { width?: number; height?: number }[]; format?: { duration?: string } }
    out.width = j.streams?.[0]?.width
    out.height = j.streams?.[0]?.height
    out.seconds = j.format?.duration ? Number(j.format.duration) : undefined
  } catch {
    // no ffprobe: the name and size still show
  }
  const dir = `${r}/${THUMBS}`
  await $.process.run(['mkdir', '-p', dir]).catch(() => undefined)
  const ss = String(Math.max(0, (out.seconds ?? 3) / 3).toFixed(2))
  const jpg = `${dir}/${name}.jpg`
  const png = `${dir}/${name}.png`
  const madeJpg = await run($, 'ffmpeg', ['-v', 'error', '-y', '-ss', ss, '-i', v.path, '-frames:v', '1', '-vf', 'scale=180:-2', '-q:v', '5', jpg])
  if (madeJpg?.exitCode === 0) {
    try {
      out.thumbJpg = (await $.fs.read(jpg, { as: 'bytes' })).base64
    } catch {
      // unreadable: no thumbnail on the desktop
    }
  }
  const madePng = await run($, 'ffmpeg', ['-v', 'error', '-y', '-ss', ss, '-i', v.path, '-frames:v', '1', '-vf', 'scale=240:-2', png])
  if (madePng?.exitCode === 0) out.thumbPng = png
  thumbs.set(v.path, out)
  return out
}

/** The film's thumbnail kit (kit/thumbs/THUMBNAILS.md), if made: stale when the final file changed after it. */
async function kitOf($: EngineInterface, r: string, name: string, finalAt: number | undefined): Promise<DeskDetail['thumbKit']> {
  const dir = `${r}/output/final/${name}/thumbnail`
  const at = await mtimeOf($, `${dir}/gpt_prompt.md`)
  if (at === undefined) return null
  const photos = (await listing($, `${dir}/photos`)).filter(f => f.kind === 'file' && /^(face|ref)_\d+\.(jpe?g|png|webp|heic)$/i.test(f.name))
  const notes = `${dir}/notes.md`
  return {
    prompt: `${dir}/gpt_prompt.md`, notes: (await $.fs.exists(notes)) ? notes : null, photos: `${dir}/photos`,
    count: photos.length, at, stale: finalAt !== undefined && finalAt > at + 2000,
  }
}

let scanning: Promise<void> | undefined

/** Reads the picked film's files into the detailed view. One scan at a time; a second ask waits for the first. */
async function scan($: EngineInterface) {
  if (scanning) return scanning
  scanning = scanOnce($).finally(() => {
    scanning = undefined
  })
  return scanning
}

async function scanOnce($: EngineInterface) {
  const r = await repo($)
  const opts = await options($, r)
  const d = await read($, desk)
  const picked = (await read($, pick)) ?? d.film?.name ?? opts[0]
  const durations = await stored<Record<string, number[]>>($, 'durations', {})
  const sound = await stored($, 'sound', true)
  const gate = await stored($, 'gate', true)
  const now = await $.clock.now()
  const base: DeskDetail = {
    film: picked ?? '', kind: 'none', options: opts, stages: [], video: null, qa: null, contact: null, uploadCopy: null, thumbKit: null,
    split: [], usd: 0, durations, sound, gate, scannedAt: now,
  }
  if (!picked) {
    await update($, detail, () => base)
    return
  }
  const kind = await kindOf($, r, picked)
  const filmCost = d.films.find(f => f.name === picked)?.usd ?? 0
  const splits = await stored<Record<string, Record<string, number>>>($, 'split', {})
  const split = Object.entries(splits[picked] ?? {}).filter(([, v]) => v > 0.004)
    .sort((a, b) => [EARLIER, ...GROUPS].indexOf(a[0] as never) - [EARLIER, ...GROUPS].indexOf(b[0] as never))
    .map(([group, v]) => ({ group, usd: v }))
  if (kind === 'none') {
    await update($, detail, () => ({ ...base, usd: filmCost, split }))
    return
  }
  const specs = STAGES[kind]
  const times: (number | undefined)[] = []
  const inputTimes: (number | undefined)[] = []
  const files: ({ path: string; mtime: number; bytes: number } | undefined)[] = []
  for (const s of specs) {
    const p = `${r}/${at(s.path, picked)}`
    const f = s.newest ? await newestIn($, p, s.newest) : await mtimeOf($, p).then(t => (t === undefined ? undefined : { path: p, mtime: t, bytes: 0 }))
    files.push(f)
    times.push(f?.mtime)
    let input: number | undefined
    for (const i of s.inputs ?? []) {
      const t = await mtimeOf($, `${r}/${at(i, picked)}`)
      if (t !== undefined) input = Math.max(input ?? 0, t)
    }
    inputTimes.push(input)
  }
  const finalIdx = specs.findIndex(s => s.key === 'final')
  const renderIdx = specs.findIndex(s => s.key === 'render')
  const videoFile = files[finalIdx] ?? (renderIdx >= 0 ? files[renderIdx] : undefined)
  const sent = await stored<Record<string, number>>($, 'sent', {})
  const sentAt = files[finalIdx] ? sent[files[finalIdx]!.path] : undefined
  const stages = stagesFrom(specs, times, inputTimes, sentAt)
  const video = videoFile ? await probe($, r, picked, videoFile) : null

  let qa: DeskDetail['qa'] = null
  let contact: string | null = null
  const qaIdx = specs.findIndex(s => s.key === 'qa')
  const qaText = files[qaIdx] ? await readText($, files[qaIdx]!.path) : undefined
  if (qaText && kind === 'film') {
    const rep = readQaReport(qaText)
    if (rep) qa = { ...rep, at: times[qaIdx]! }
    const overview = `${r}/${at('output/temp/films/{f}/review/overview.jpg', picked)}`
    if (await $.fs.exists(overview)) contact = overview
  }
  if (kind === 'film') {
    const auditIdx = specs.findIndex(s => s.key === 'audit')
    const cut = files[auditIdx] ? await readText($, files[auditIdx]!.path) : undefined
    const joins: DeskFinding[] = cut ? readCutcheck(cut) : []
    if (joins.length) qa = qa ? { ...qa, findings: [...qa.findings, ...joins] } : { verdict: 'WARN', at: times[auditIdx]!, findings: joins }
  }
  const copy = `${r}/output/final/${picked}/upload_copy.txt`
  const uploadCopy = (await $.fs.exists(copy)) ? copy : null
  const thumbKit = await kitOf($, r, picked, files[finalIdx]?.mtime)

  await update($, detail, () => ({ ...base, kind, stages, video, qa, contact, uploadCopy, thumbKit, usd: filmCost, split }))
}

// ---------------------------------------------------------------------------------------------- what the buttons do
async function show($: EngineInterface, next: DeskView) {
  await update($, view, () => next)
}

async function trackFromDesk($: EngineInterface, raw: string) {
  const name = filmName(raw)
  if (!name) {
    $.ui.toast('Use letters, digits, - and _ for the video name')
    return
  }
  await startFilm($, name)
  await update($, view, () => 'compact' as DeskView)
  await refresh($)
  $.ui.toast(`Tracking API cost for "${name}"`)
}

async function endFromDesk($: EngineInterface) {
  const done = await endFilm($)
  await refresh($)
  if (done) $.ui.toast(`Stopped tracking "${done.name}": ${usd(done.usd)}`)
}

async function openDetails($: EngineInterface) {
  await refresh($)
  await $.ui.open({ id: PANE, title: 'Edit Desk' })
}

async function setPane($: EngineInterface, mode: PaneMode) {
  await update($, pane, () => mode)
  await $.store.set('pane', mode)
  if (mode === 'detailed') await scan($)
}

async function pickFilm($: EngineInterface, name: string) {
  await update($, pick, () => name)
  await scan($)
}

async function toggle($: EngineInterface, key: 'sound' | 'gate') {
  const next = !(await stored($, key, true))
  await $.store.set(key, next)
  await update($, detail, prev => (prev ? { ...prev, [key]: next } : prev))
  $.ui.toast(key === 'sound' ? `Sounds ${next ? 'on' : 'off'}` : `QA gate ${next ? 'on: a failed video is never sent' : 'off: a failed video is sent with a warning'}`)
}

async function openFile($: EngineInterface, path: string, reveal = false) {
  const res = await $.process.run(reveal ? ['open', '-R', path] : ['open', path]).catch(() => undefined)
  if (!res || res.exitCode !== 0) $.ui.toast(`Couldn't open ${basename(path)}`)
}

async function ask($: EngineInterface, text: string) {
  await $.prompt.submit({ text })
  $.ui.toast('Sent to Claude')
}

/** Copies the kit's GPT prompt: the surface's clipboard, else macOS's (the desktop has no copy path yet). */
async function copyPrompt($: EngineInterface, path: string, surface: string | undefined) {
  let text: string
  try {
    text = await $.fs.read(path)
  } catch {
    $.ui.toast('The GPT prompt is gone: make the kit again')
    return
  }
  let ok = false
  try {
    ok = (await $.ui.copy({ text, surface: surface as never })).isCopied
  } catch {
    ok = false
  }
  if (!ok) ok = (await $.process.run(['pbcopy'], { stdin: text }).catch(() => undefined))?.exitCode === 0
  $.ui.toast(ok ? 'GPT prompt copied: paste it in ChatGPT and attach the photos (Show photos)' : "Couldn't copy: open the prompt with Notes")
}

function kitPrompt(film: string, again: boolean) {
  return `${again ? 'Make the thumbnail kit again' : 'Make the thumbnail kit'} for ${film}: follow kit/thumbs/THUMBNAILS.md `
    + '(the video, face frames with kit/thumbs/frames.py checked on the sheet, real research on competing thumbnails, three '
    + 'concepts), writing gpt_prompt.md and notes.md in its thumbnail folder. Then tell me the three concepts in a few lines.'
}

async function tick($: EngineInterface, n: number) {
  // once a second while a step runs (its elapsed time), else every 30 s (the "ago" labels)
  if (running.size === 0 && n % 30 !== 0) return
  const t = await $.clock.now()
  await update($, clock, () => t)
}

const ICON: Record<DeskStage['state'], string> = { done: '✓', stale: '⚠', todo: '○', running: '⏳' }
const TINT: Record<DeskStage['state'], 'success' | 'warning' | 'subtle' | undefined> = { done: 'success', stale: 'warning', todo: 'subtle', running: 'warning' }

export const register: Register = on => {
  // ------------------------------------------------------------------ session: commands, the film, the timer
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'film',
      description: 'Track a video\'s API cost: start <name>, end, or cost',
      argumentHint: 'start <name> | end | cost',
    })
    await $.command.register({ name: 'desk', description: 'Show the edit desk (and its details pane)' })
    const name = (await $.store.get('film')) as string | undefined
    if (name) film = { name, baseUsd: await sessionUsd($), carriedUsd: (await films($))[name] ?? 0 }
    const mode = await stored<PaneMode>($, 'pane', 'simple')      // the pane opens the way it was last left; simple at first
    await update($, pane, () => mode)
    const t0 = await $.clock.now()
    await update($, clock, () => t0)
    await refresh($)
    let n = 0
    $.clock.every(1000, () => {
      n += 1
      void tick($, n)
    })
    return next(e)
  })

  on('command.run', { command: 'desk' }, async $ => {
    await show($, 'compact')
    await openDetails($)
    return { text: 'Edit desk shown above the prompt; details pane opened (Detailed at its top for the film view).' }
  })

  on('command.run', { command: 'film' }, async ($, e) => {
    const [verb = '', ...rest] = e.args.trim().split(/\s+/)
    if (verb === 'start') {
      const name = filmName(rest.join('-'))
      if (!name) return { text: 'Usage: /film start <name> (letters, digits, - and _).' }
      await startFilm($, name)
      await refresh($)
      return { text: `Tracking API cost for "${name}"${film && film.carriedUsd > 0 ? ` (carried over: ${usd(film.carriedUsd)})` : ''}.` }
    }
    if (verb === 'end') {
      const done = await endFilm($)
      await refresh($)
      return { text: done ? `Stopped tracking "${done.name}": ${usd(done.usd)} in API cost.` : 'No video is being tracked.' }
    }
    const all = await films($)
    if (film) all[film.name] = await filmUsd($)
    const rows = Object.entries(all).sort((a, b) => b[1] - a[1]).map(([n, v]) => `${n === film?.name ? '▸' : ' '} ${n}: ${usd(v)}`)
    return {
      text: [
        film ? `Now tracking "${film.name}": ${usd(all[film.name] ?? 0)} so far.` : 'No video is being tracked (/film start <name>).',
        rows.length ? `\nAPI cost per video (list prices, as /cost totals it):\n${rows.join('\n')}` : '',
      ].join(''),
    }
  })

  on('turn.complete', async ($, e, next) => {
    const ran = await next(e)
    await saveFilm($)
    if (film) {
      const splits = await stored<Record<string, Record<string, number>>>($, 'split', {})
      const last = (await stored<Record<string, string>>($, 'lastStep', {}))[film.name]
      splits[film.name] = addToSplit(splits[film.name], await filmUsd($), groupOf(turnStep ?? last))
      await $.store.set('split', splits)
    }
    turnStep = undefined
    await refresh($)
    return ran
  })

  // ------------------------------------------------------------------ the desk: a band above the prompt
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const d = await read($, desk)
    const v = await read($, view)
    const now = await read($, clock)
    const canType = e.surface !== 'mobile'

    if (v === 'hidden') {
      return (
        <Box flexDirection="row" gap={1}>
          <Text dimColor>edit-desk</Text>
          <Button key="show" label="Show" plain onPress={() => show($, 'compact')} />
        </Box>
      )
    }

    const head = (
      <Box flexDirection="row" flexWrap="wrap" columnGap={2}>
        <Text bold>{d.film ? `🎬 ${d.film.name}` : '🎬 no video tracked'}</Text>
        {d.film && <Text color="claude" bold>{usd(d.film.usd)}</Text>}
        {d.ctx != null && <Text color={d.ctx >= 85 ? 'warning' : 'subtle'}>ctx {d.ctx}%</Text>}
        {d.five != null && <Text color={d.five >= 85 ? 'warning' : 'subtle'}>5h {d.five}%</Text>}
        {d.jobs.map(j => (
          <Text color="warning">⏳ {j.label}{j.film ? ` (${j.film})` : ''} {clockText(now - j.startedAt)}</Text>
        ))}
        {d.jobs.length === 0 && d.alerts[0] && (
          <Text color={d.alerts[0].ok ? 'success' : 'error'} dimColor>
            {d.alerts[0].ok ? '✅' : '❌'} {d.alerts[0].text} · {ago(now - d.alerts[0].at)}
          </Text>
        )}
      </Box>
    )

    if (v === 'start' && canType) {
      const { Input } = $.ui.resolve(e) as unknown as { Input: ElementConstructor<InputProps> }
      return (
        <Box flexDirection="column">
          {head}
          <Box flexDirection="row" gap={1}>
            <Input key="film-name" label="Video" placeholder="e.g. my-next-reel" submitLabel="Track" autoFocus
              onSubmit={(value: string) => trackFromDesk($, value)} />
            <Button key="cancel" label="Cancel" role="dismiss" onPress={() => show($, 'compact')} />
          </Box>
        </Box>
      )
    }

    if (v === 'costs') {
      const total = d.films.reduce((s, f) => s + f.usd, 0)
      return (
        <Box flexDirection="column">
          {head}
          <Text dimColor>API cost per video (list prices)</Text>
          {d.films.length === 0 && <Text dimColor>No video tracked yet.</Text>}
          {d.films.slice(0, 8).map(f => (
            <Text color={f.name === d.film?.name ? 'claude' : undefined}>{f.name === d.film?.name ? '▸' : ' '} {f.name.padEnd(24)} {usd(f.usd)}</Text>
          ))}
          {d.films.length > 1 && <Text bold>  {'all videos'.padEnd(24)} {usd(total)}</Text>}
          <Button key="close" label="Close" role="dismiss" onPress={() => show($, 'compact')} />
        </Box>
      )
    }

    if (v === 'qa') {
      return (
        <Box flexDirection="column">
          {head}
          <Text dimColor>Last QA verdicts (a FAIL blocks sending that file)</Text>
          {d.qa.length === 0 && <Text dimColor>No QA run seen yet.</Text>}
          {d.qa.slice(0, 6).map(q => (
            <Text color={q.verdict === 'FAIL' ? 'error' : q.verdict === 'WARN' ? 'warning' : 'success'}>
              {q.verdict === 'FAIL' ? '❌' : q.verdict === 'WARN' ? '⚠️' : '✅'} {q.verdict.padEnd(4)} {q.name} · {ago(now - q.at)}
            </Text>
          ))}
          <Button key="close" label="Close" role="dismiss" onPress={() => show($, 'compact')} />
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {head}
        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          {canType && (
            <Button key="track" hotkey="1" label={d.film ? 'Switch video' : 'Track a video'} variant="primary" onPress={() => show($, 'start')} />
          )}
          <Button key="costs" hotkey="2" label="Costs" onPress={() => show($, 'costs')} />
          <Button key="qa" hotkey="3" label="QA" onPress={() => show($, 'qa')} />
          <Button key="details" hotkey="4" label="Details" onPress={() => openDetails($)} />
          {d.film && <Button key="end" hotkey="5" label="Stop tracking" onPress={() => endFromDesk($)} />}
          <Button key="hide" hotkey="6" label="Hide" plain dimColor onPress={() => show($, 'hidden')} />
        </Box>
      </Box>
    )
  })

  // ------------------------------------------------------------------ the details pane: simple or detailed
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const els = $.ui.resolve(e)
    const { Box, Text, Button } = els
    const d = await read($, desk)
    const now = await read($, clock)
    const mode = await read($, pane)

    const switcher = (
      <Box flexDirection="row" gap={1}>
        <Button key="mode-simple" label="Simple" variant={mode === 'simple' ? 'primary' : 'secondary'} onPress={() => setPane($, 'simple')} />
        <Button key="mode-detailed" label="Detailed" variant={mode === 'detailed' ? 'primary' : 'secondary'} onPress={() => setPane($, 'detailed')} />
      </Box>
    )

    if (mode === 'simple') {
      const total = d.films.reduce((s, f) => s + f.usd, 0)
      return (
        <Box flexDirection="column" gap={1}>
          {switcher}
          <Box flexDirection="column">
            <Text bold>Now</Text>
            <Text>{d.film ? `🎬 ${d.film.name}: ${usd(d.film.usd)} in API cost so far` : '🎬 No video tracked (/film start <name>)'}</Text>
            <Text dimColor>
              {d.ctx != null ? `Context window ${d.ctx}% full` : 'Context: n/a'} · {d.five != null ? `5-hour limit ${d.five}% used` : '5-hour limit: n/a'}
            </Text>
            {d.jobs.length === 0 && <Text dimColor>Nothing running.</Text>}
            {d.jobs.map(j => (
              <Text color="warning">⏳ {j.label}{j.film ? ` (${j.film})` : ''} running for {clockText(now - j.startedAt)}</Text>
            ))}
          </Box>
          <Box flexDirection="column">
            <Text bold>Cost per video</Text>
            {d.films.length === 0 && <Text dimColor>No video tracked yet.</Text>}
            {d.films.map(f => (
              <Text color={f.name === d.film?.name ? 'claude' : undefined}>{f.name === d.film?.name ? '▸' : ' '} {f.name.padEnd(26)} {usd(f.usd)}</Text>
            ))}
            {d.films.length > 1 && <Text bold>  {'all videos'.padEnd(26)} {usd(total)}</Text>}
          </Box>
          <Box flexDirection="column">
            <Text bold>QA</Text>
            {d.qa.length === 0 && <Text dimColor>No QA run seen yet.</Text>}
            {d.qa.map(q => (
              <Text color={q.verdict === 'FAIL' ? 'error' : q.verdict === 'WARN' ? 'warning' : 'success'}>
                {q.verdict === 'FAIL' ? '❌' : q.verdict === 'WARN' ? '⚠️' : '✅'} {q.verdict.padEnd(4)} {q.name} · {ago(now - q.at)}
              </Text>
            ))}
          </Box>
          <Box flexDirection="column">
            <Text bold>Recent alerts</Text>
            {d.alerts.length === 0 && <Text dimColor>None yet.</Text>}
            {d.alerts.map(a => (
              <Text color={a.ok ? 'success' : 'error'}>{a.ok ? '✅' : '❌'} {a.text} · {ago(now - a.at)}</Text>
            ))}
          </Box>
          <Box flexDirection="row" gap={1}>
            <Button key="refresh" label="Refresh" onPress={() => refresh($)} />
            {d.film && <Button key="end" label="Stop tracking" onPress={() => endFromDesk($)} />}
          </Box>
        </Box>
      )
    }

    // ---- detailed: one film
    const x = await read($, detail)
    if (!x) {
      return (
        <Box flexDirection="column" gap={1}>
          {switcher}
          <Text dimColor>Reading the film's files…</Text>
        </Box>
      )
    }
    const cols = e.props.bodyColumns
    const barW = Math.max(6, Math.min(18, cols - 34))
    const labelW = Math.max(14, Math.min(26, cols - 22))
    const jobs = d.jobs.filter(j => j.film === x.film || (!j.film && x.film === d.film?.name))
    const stages: DeskStage[] = x.stages.map(s => ({ ...s }))
    const specs = x.kind === 'none' ? [] : STAGES[x.kind]
    for (const j of jobs) {
      const key = runningStage(specs, x.stages, j.label)
      const s = stages.find(t => t.key === key)
      if (s) s.state = 'running'
    }
    const job = jobs[0]
    const jobEta = job ? eta(x.durations[job.label]) : undefined
    const stale = stages.some(s => s.state === 'stale')
    const status = job
      ? { text: `⏳ ${job.label}`, color: 'warning' as const }
      : x.qa?.verdict === 'FAIL'
        ? { text: '❌ QA failed', color: 'error' as const }
        : stale
          ? { text: '⚠ Stale stage', color: 'warning' as const }
          : stages.find(s => s.key === 'sent')?.state === 'done'
            ? { text: '✅ Sent', color: 'success' as const }
            : x.qa
              ? { text: '✅ Ready to send', color: 'success' as const }
              : x.kind === 'none'
                ? { text: 'No files yet', color: 'subtle' as const }
                : { text: 'In progress', color: 'subtle' as const }

    const picker = 'Select' in els && x.options.length > 0
      ? (() => {
          const { Select } = els as unknown as { Select: ElementConstructor<SelectProps> }
          return <Select key="film-pick" label="Film" value={x.film} options={x.options.map(o => ({ value: o, label: o === d.film?.name ? `${o} (tracked)` : o }))}
            onSelect={(value: string) => pickFilm($, value)} />
        })()
      : <Text bold>🎬 {x.film || 'no film yet'}</Text>

    const v = x.video
    const portrait = v?.width && v?.height ? v.height > v.width : true
    let thumb: RenderChildren = null
    if (v && e.surface === 'terminal' && v.thumbPng && 'Image' in els) {
      const { Image } = els as unknown as { Image: ElementConstructor<ImageProps> }
      thumb = <Image key="thumb" source={{ file: v.thumbPng, format: 'png', generation: Math.round(v.mtime) }} columns={portrait ? 10 : 22} rows={portrait ? 9 : 6} alt={`frame of ${v.name}`} />
    } else if (v?.thumbJpg && 'Svg' in els) {
      const { Svg } = els as unknown as { Svg: ElementConstructor<SvgProps> }
      const w = portrait ? 72 : 160, ht = portrait ? 128 : 90
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${ht}" viewBox="0 0 ${w} ${ht}"><image href="data:image/jpeg;base64,${v.thumbJpg}" width="${w}" height="${ht}" preserveAspectRatio="xMidYMid slice"/></svg>`
      thumb = <Svg source={svg} alt={`frame of ${v.name}`} width={w} height={ht} />
    }

    const findings = x.qa?.findings ?? []
    const splitTotal = x.split.reduce((s, g) => s + g.usd, 0)
    const avg = d.films.filter(f => f.usd > 0.05)
    const avgUsd = avg.length ? avg.reduce((s, f) => s + f.usd, 0) / avg.length : undefined
    const perMin = v?.seconds && x.usd > 0 ? x.usd / (v.seconds / 60) : undefined
    const tracked = d.film?.name === x.film

    return (
      <Box flexDirection="column" gap={1}>
        {switcher}
        <Box flexDirection="column">
          {picker}
          <Text color={status.color} bold>{status.text}</Text>
        </Box>

        <Box flexDirection="column">
          <Text bold>Latest video</Text>
          {!v && <Text dimColor>No render yet.</Text>}
          {v && (
            <Box flexDirection="row" gap={2}>
              {thumb}
              <Box flexDirection="column">
                <Text>{v.name}</Text>
                <Text dimColor>
                  {v.width && v.height ? `${v.width}×${v.height}` : ''}{v.seconds ? ` · ${clockText(v.seconds * 1000)}` : ''}
                </Text>
                <Text dimColor>{v.bytes ? `${megabytes(v.bytes)} · ` : ''}made {ago(now - v.mtime)}</Text>
                <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
                  <Button key="play" label="Play" onPress={() => openFile($, v.path)} />
                  <Button key="reveal" label="Reveal" onPress={() => openFile($, v.path, true)} />
                  {x.contact && <Button key="frames" label="Frames" onPress={() => openFile($, x.contact!)} />}
                  {x.uploadCopy && <Button key="upload-copy" label="Upload copy" onPress={() => openFile($, x.uploadCopy!)} />}
                </Box>
              </Box>
            </Box>
          )}
        </Box>

        <Box flexDirection="column">
          <Text bold>Pipeline{x.kind === 'take' ? ' (shorts take)' : ''}</Text>
          {x.kind === 'none' && <Text dimColor>Nothing under output/ for this name yet.</Text>}
          {stages.map(s => {
            const right = s.state === 'running' && job
              ? `${clockText(now - job.startedAt)}${jobEta ? ` / ~${clockText(jobEta)}` : ''}`
              : s.state === 'stale' ? 'stale' : s.at !== undefined ? ago(now - s.at) : ''
            return (
              <Box flexDirection="column">
                <Text color={TINT[s.state]} bold={s.state === 'running'}>{ICON[s.state]} {s.label.padEnd(labelW)} {right}</Text>
                {s.state === 'running' && job && jobEta && <Text color="warning">  {bar((now - job.startedAt) / jobEta, barW + 8)}</Text>}
                {s.note && <Text dimColor>  {s.note}</Text>}
              </Box>
            )
          })}
        </Box>

        <Box flexDirection="column">
          <Text bold>QA{x.qa ? ` · ${x.qa.verdict} · ${findings.length} finding${findings.length === 1 ? '' : 's'} · ${ago(now - x.qa.at)}` : ''}</Text>
          {!x.qa && <Text dimColor>No QA report yet.</Text>}
          {findings.slice(0, 6).map(f => (
            <Text color={f.severity === 'fail' ? 'error' : 'warning'}>{f.t !== undefined ? `${timecode(f.t)} ` : ''}{f.text}</Text>
          ))}
          {findings.length > 6 && <Text dimColor>…and {findings.length - 6} more</Text>}
          {x.kind !== 'none' && (
            <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
              <Button key="qa-run" label="Run QA ↗" onPress={() => ask($, `Run QA on ${x.film} (kit/qa/qa.py with the flags its build uses, plus the join audit if the cut changed) and tell me the verdict.`)} />
              {findings.length > 0 && (
                <Button key="qa-fix" label="Fix findings ↗" onPress={() => ask($, `Fix these QA findings on ${x.film}, then re-render and run QA again:\n${findings.map(f => `- ${f.t !== undefined ? `${timecode(f.t)} ` : ''}${f.text}`).join('\n')}`)} />
              )}
            </Box>
          )}
        </Box>

        {x.kind !== 'none' && (
          <Box flexDirection="column">
            <Text bold>Thumbnails</Text>
            {!x.thumbKit && !x.video && <Text dimColor>After the final render: a prompt for ChatGPT plus photos of you.</Text>}
            {!x.thumbKit && x.video && <Text dimColor>No kit yet: Claude researches the topic's thumbnails and writes a ChatGPT prompt with photos of you.</Text>}
            {x.thumbKit && (
              <Text color={x.thumbKit.stale ? 'warning' : undefined}>
                {x.thumbKit.stale ? '⚠ made before the latest final file · ' : '✓ '}GPT prompt ready · {x.thumbKit.count} photo{x.thumbKit.count === 1 ? '' : 's'} to attach · {ago(now - x.thumbKit.at)}
              </Text>
            )}
            <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
              {x.thumbKit && <Button key="copy-gpt" label="Copy GPT prompt" variant="primary" onPress={press => copyPrompt($, x.thumbKit!.prompt, press.surface)} />}
              {x.thumbKit && <Button key="kit-photos" label="Show photos" onPress={() => openFile($, x.thumbKit!.photos)} />}
              {x.thumbKit?.notes && <Button key="kit-notes" label="Notes" onPress={() => openFile($, x.thumbKit!.notes!)} />}
              {x.video && (
                <Button key="thumb-kit" label={x.thumbKit ? 'Redo kit ↗' : 'Thumbnail kit ↗'} onPress={() => ask($, kitPrompt(x.film, !!x.thumbKit))} />
              )}
            </Box>
          </Box>
        )}

        <Box flexDirection="column">
          <Text bold>Cost{tracked ? '' : ' (not tracked now)'} · {usd(x.usd)}</Text>
          {x.split.length === 0 && <Text dimColor>{tracked ? 'The split by stage fills in as turns end.' : 'No split for this film yet.'}</Text>}
          {x.split.map(g => (
            <Text>{g.group.padEnd(20)} {bar(splitTotal > 0 ? g.usd / splitTotal : 0, barW)} {usd(g.usd)}</Text>
          ))}
          {(perMin !== undefined || avgUsd !== undefined) && (
            <Text dimColor>{perMin !== undefined ? `${usd(perMin)} per finished minute` : ''}{perMin !== undefined && avgUsd !== undefined ? ' · ' : ''}{avgUsd !== undefined ? `average film ${usd(avgUsd)}` : ''}</Text>
          )}
          <Text dimColor>The split is approximate: each turn's cost goes to the step it ran, else the film's last step.</Text>
        </Box>

        <Box flexDirection="column">
          <Text bold>Limits</Text>
          <Text color={d.ctx != null && d.ctx >= 85 ? 'warning' : undefined}>{'Context'.padEnd(9)} {bar((d.ctx ?? 0) / 100, barW)} {d.ctx != null ? `${d.ctx}%` : 'n/a'}</Text>
          <Text color={d.five != null && d.five >= 85 ? 'warning' : undefined}>{'5-hour'.padEnd(9)} {bar((d.five ?? 0) / 100, barW)} {d.five != null ? `${d.five}%` : 'n/a'}</Text>
        </Box>

        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          <Button key="sound" label={`Sound: ${x.sound ? 'on' : 'off'}`} onPress={() => toggle($, 'sound')} />
          <Button key="gate" label={`QA gate: ${x.gate ? 'on' : 'off'}`} onPress={() => toggle($, 'gate')} />
          {!tracked && x.film && <Button key="track-this" label="Track this film" onPress={async () => { await startFilm($, x.film); await refresh($) }} />}
          {d.film && <Button key="end" label="Stop tracking" onPress={() => endFromDesk($)} />}
          <Button key="refresh" label="Refresh" onPress={() => scan($)} />
        </Box>
      </Box>
    )
  })

  // ------------------------------------------------------------------ guardrails and step tracking on the shell
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const env = envTarget(e.command)
    if (env) return { deny: `edit-desk: ${env} is off limits here (it can hold API keys). Ask the user to handle it.` }
    const command = withNoUpdate(e.command)
    const label = classify(command)
    const named = filmFromCommand(command)
    if (named && !film) {
      await startFilm($, named)
      $.ui.toast(`Tracking API cost for "${named}" (Switch video on the desk to change it)`)
    }
    const key = e.tool_use_id ?? `call-${await $.clock.now()}`
    const job: Job | undefined = label ? { label, startedAt: await $.clock.now(), film: named ?? film?.name } : undefined
    if (job) {
      running.set(key, job)
      await stepStarted($, job)
      await update($, clock, () => job.startedAt)
      await refresh($)
    }
    let ran
    try {
      ran = await next(command === e.command ? e : { ...e, command })
    } finally {
      if (job) running.delete(key)
    }
    const bgId = ran.deny === undefined ? backgroundId(ran.text) : undefined
    if (job && bgId) {
      running.set(bgId, job)                       // it runs on: its notification ends it
    } else if (job && ran.deny === undefined) {
      await noteQa($, ran.text)
      const took = (await $.clock.now()) - job.startedAt
      const qaFailed = [...parseQa(ran.text ?? '').values()].includes('FAIL')
      await stepEnded($, job, took, ran.isError !== true)
      if (took >= LONG_MS) {
        const ok = ran.isError !== true && !qaFailed
        await alert($, `${job.label}${job.film ? ` (${job.film})` : ''} ${ok ? 'done' : 'failed'} in ${duration(took)}`, ok)
        await chime($, ok)
      }
    } else if (ran.deny === undefined) {
      await noteQa($, ran.text)
    }
    await refresh($)
    return ran
  }).catch(($, e, next) => (next.called ? next(e) : next({ ...e, command: withNoUpdate(e.command) })))

  // .env through the file tools too
  for (const tool of ['Read', 'Edit', 'Write'] as const) {
    on('tool.call', { tool }, ($, e, next) =>
      isEnvPath(e.file_path)
        ? { deny: `edit-desk: ${e.file_path} is off limits here (it can hold API keys). Ask the user to handle it.` }
        : next(e),
    ).catch(($, e, next) => (next.called ? next(e) : { deny: 'edit-desk: its .env guard failed; not opening the file.' }))
  }

  // ------------------------------------------------------------------ the QA gate: no failed video reaches the user
  on('tool.call', { tool: 'SendUserFile' }, async ($, e, next) => {
    const book = await qaBook($)
    const gate = await stored($, 'gate', true)
    const unchecked: string[] = []
    for (const file of e.files.filter(isVideo)) {
      const name = basename(file)
      const rec = book[name]
      let mtime: number | undefined
      try {
        mtime = (await $.fs.stat(file)).mtimeMs
      } catch {
        mtime = undefined
      }
      const changedSince = rec !== undefined && mtime !== undefined && mtime > rec.at + 2000
      if (rec?.verdict === 'FAIL' && !changedSince) {
        if (gate) return { deny: `edit-desk: ${name} failed its last QA run. Fix it and run kit/qa/qa.py again before sending it.` }
        $.ui.toast(`QA gate is off: sending ${name}, which failed its last QA run`)
      }
      if (!rec || changedSince) unchecked.push(name)
    }
    if (unchecked.length) $.ui.toast(`Sent without a fresh QA pass: ${unchecked.join(', ')}`)
    const ran = await next(e)
    if (ran.deny === undefined && e.files.some(isVideo)) {
      try {
        const r = await repo($)
        const sent = await stored<Record<string, number>>($, 'sent', {})
        const t = await $.clock.now()
        for (const file of e.files.filter(isVideo)) sent[file.startsWith('/') ? file : `${r}/${file}`] = t
        await $.store.set('sent', sent)
      } catch {
        // the send went through; only the pane's "Sent" row misses it
      }
    }
    return ran
  }).catch(($, e, next) => next(e))

  // ------------------------------------------------------------------ background steps ending
  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind === 'task-notification') {
      const n = parseNotification(e.text)
      if (n) await finishBackground($, n)
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('session.append', async ($, e, next) => {
    const appended = await next(e)
    const text = e.message.content.map(b => ('text' in b && typeof b.text === 'string' ? b.text : '')).join('\n')
    const n = parseNotification(text)
    if (n) await finishBackground($, n)
    return appended
  }).catch(($, e, next) => next(e))
}
