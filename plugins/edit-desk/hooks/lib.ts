// Pure helpers for edit-desk: parsing commands and outputs. No `$` here, so the tests can call them directly.

export type Verdict = 'PASS' | 'WARN' | 'FAIL'
export type QaRecord = { verdict: Verdict; at: number }
export type Notification = { id: string; status: string; summary: string; outputFile?: string; exitCode?: number }

/** The long steps of the pipeline, most important first: the label shown while one runs and when it ends. */
const STEPS: [RegExp, string][] = [
  [/\bhyperframes\s+render\b/, 'render'],
  [/\bgrade\.py\b|\bprep\.py\b[^;&|]*--only=grade\b/, 'grade'],
  [/\bprep\.py\b|\bdeepFilter\b|\bpersonseg\b|\bfaces\.py\b|\bscribble\.py\b/, 'prep'],
  [/\bbuild\.py\s+--audio\b/, 'mix'],
  [/\bedl\.py\b/, 'cut'],
  [/\bqa\.py\b|\bkit\.cut\.cutcheck\b/, 'QA'],
]

export function classify(command: string): string | undefined {
  return STEPS.find(([re]) => re.test(command))?.[1]
}

/** A `.env` file the command touches (reading, printing, committing): never `.env.example` and its kin. */
export function envTarget(command: string): string | undefined {
  for (const raw of command.split(/[\s'"`=;&|()<>,]+/)) {
    const base = raw.split('/').pop() ?? ''
    if (/^\.env(\.[\w.-]+)?$/.test(base) && !/\.(example|sample|template|dist)$/.test(base)) return raw
  }
  return undefined
}

export function isEnvPath(path: string): boolean {
  return envTarget(path) !== undefined
}

/** HyperFrames updates itself mid-render unless this is set (the repo's standing rule). */
export function withNoUpdate(command: string): string {
  if (!/\bhyperframes\b/.test(command) || /HYPERFRAMES_NO_UPDATE_CHECK=1/.test(command)) return command
  return `export HYPERFRAMES_NO_UPDATE_CHECK=1; ${command}`
}

/** The film or take a pipeline command works on: films/<name>/(prep|edl|build).py, `shorts analyze <job>`, `--job <job>`. */
export function filmFromCommand(command: string): string | undefined {
  const film = command.match(/films\/([a-z0-9][\w-]*)\/(?:prep|edl|build)\.py\b/i)
    ?? command.match(/films\/([a-z0-9][\w-]*)["']?\s*&&\s*(?:\S+=\S+\s+)*uv run python (?:prep|edl|build)\.py\b/i)
  if (film?.[1]) return film[1]
  const job = command.match(/--job[=\s]+([a-z0-9][\w-]*)/i)
    ?? command.match(/\bshorts\s+analyze\s+([a-z0-9][\w-]*)/i)
  return job?.[1]
}

/** Verdicts printed by kit/qa/qa.py ("PASS: name.mp4  ..."). */
export function parseQa(text: string): Map<string, Verdict> {
  const out = new Map<string, Verdict>()
  for (const m of text.matchAll(/^(PASS|WARN|FAIL): (\S+\.(?:mp4|mov|m4v|webm))\b/gm)) out.set(m[2]!, m[1] as Verdict)
  return out
}

/** A background task's notification (the XML the engine hands the model when a task ends). */
export function parseNotification(text: string): Notification | undefined {
  if (!text.includes('<task-notification>')) return undefined
  const tag = (name: string) => text.match(new RegExp(`<${name}>([\\s\\S]*?)</${name}>`))?.[1]?.trim()
  const id = tag('task-id')
  if (!id) return undefined
  const summary = tag('summary') ?? ''
  const code = summary.match(/exit code (\d+)/)
  return { id, status: tag('status') ?? 'completed', summary, outputFile: tag('output-file'), exitCode: code ? Number(code[1]) : undefined }
}

/** The id a backgrounded shell command was given ("Command running in background with ID: b074qvex7"). */
export function backgroundId(text: string | undefined): string | undefined {
  return text?.match(/background with ID:\s*([\w-]+)/)?.[1]
}

export function basename(path: string): string {
  return path.split('/').pop() ?? path
}

export function isVideo(path: string): boolean {
  return /\.(mp4|mov|m4v|webm)$/i.test(path)
}

export function duration(ms: number): string {
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${String(s % 60).padStart(2, '0')}s`
}

export function usd(n: number): string {
  return `$${n.toFixed(2)}`
}

/** A running step's elapsed time as a clock: 0:42, 3:05, 1:02:10. */
export function clockText(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`
}

/** How long ago: "now", "40s ago", "5m ago", "2h ago", "3d ago". */
export function ago(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  if (s < 10) return 'now'
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

/** A video name as /film start takes it: lowercase, spaces to dashes; undefined when nothing usable is left. */
export function filmName(raw: string): string | undefined {
  const name = raw.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '')
  return /^[a-z0-9][\w-]*$/.test(name) ? name : undefined
}
