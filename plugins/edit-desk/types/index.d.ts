export type DeskJob = { label: string; film?: string; startedAt: number }
export type DeskAlert = { text: string; ok: boolean; at: number }
export type DeskQa = { name: string; verdict: 'PASS' | 'WARN' | 'FAIL'; at: number }
export type DeskFilm = { name: string; usd: number }
export type Desk = {
  film: DeskFilm | null
  ctx: number | null
  five: number | null
  jobs: DeskJob[]
  alerts: DeskAlert[]
  films: DeskFilm[]
  qa: DeskQa[]
}
export type DeskView = 'compact' | 'start' | 'costs' | 'qa' | 'hidden'

/** The details pane: the short summary it always had, or the detailed film view. */
export type PaneMode = 'simple' | 'detailed'

export type StageState = 'done' | 'stale' | 'todo' | 'running'
export type DeskStage = { key: string; label: string; state: StageState; at?: number; note?: string }
export type DeskFinding = { t?: number; severity: 'fail' | 'warn'; text: string }
export type DeskVideo = {
  path: string
  name: string
  mtime: number
  bytes: number
  width?: number
  height?: number
  seconds?: number
  /** The thumbnail as base64 JPEG, for the desktop's Svg. */
  thumbJpg?: string
  /** The thumbnail as a PNG file, for the terminal's Image. */
  thumbPng?: string
}
/** What the detailed view shows for the film picked: read off the pipeline's files by a scan. */
export type DeskDetail = {
  film: string
  kind: 'film' | 'take' | 'none'
  options: string[]
  stages: DeskStage[]
  video: DeskVideo | null
  qa: { verdict: 'PASS' | 'WARN' | 'FAIL'; at: number; findings: DeskFinding[] } | null
  contact: string | null
  uploadCopy: string | null
  /** output/final/<film>/thumbnail/: the GPT prompt, the notes, the photos to attach (kit/thumbs/THUMBNAILS.md). */
  thumbKit: { prompt: string; notes: string | null; photos: string; count: number; at: number; stale: boolean } | null
  split: { group: string; usd: number }[]
  usd: number
  durations: Record<string, number[]>
  sound: boolean
  gate: boolean
  scannedAt: number
}

declare module 'claude-code' {
  interface PluginState {
    'edit-desk': {
      desk: Desk
      view: DeskView
      now: number
      pane: PaneMode
      pick: string | null
      detail: DeskDetail | null
    }
  }
}
