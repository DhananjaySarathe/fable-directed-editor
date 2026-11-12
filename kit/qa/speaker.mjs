// The speaker, density and transition measurements precheck makes from its samples (2026-10-22, kit v11: the owner
// asked for "dynamic zoom" on him, takeovers with him removed, and edits that are "holistic, not heavy"). Pure functions
// over plain data, so tests/test_precheck_speaker.py runs them in node without a browser; kit/qa/precheck.mjs does the
// sampling and prints what these return.
//
// A speaker sample is what the probe read at time t, from window.__speaker(t) (the engine contract: every engine
// publishes it, kit/hf/README "window.__speaker"), else estimated from window.__faceRect / window.__box / a full-bleed
// plate of his footage as before (fallbackSpeaker; src says which, est marks the guess):
//   { t, src, on, kind: "full" | "frame" | "card" | "circle" | "corner" | "off" | "?", face: {x, y, w, h} | null,
//     rect: {x, y, w, h} | null, zoom: number | null, lens: string, track: string | null, max_zoom: number | null, est }
// A density sample: { t, n (top-level visual groups on screen), labels }. A transition: { t, kind, why } (window.__trans).

export const SPEAKER = {
  move: 0.02,               // a framing change: the face centre moves >= 2 % of the frame (hypot of dx/W, dy/H) ...
  scale: 0.04,              // ... or the face's scale changes >= 4 % (a push across a thought is +6-12 %)
  merge: 1.0,               // changes closer than this are one move (a 0.7 s whip crosses the 2 % line at every sample)
  med: 8, high: 15,         // the longest unchanged framing while he is on: MEDIUM over 8 s, HIGH over 15 s
  declared: 0.8,            // ... unless the lens declared a hold (lens "hold") for this share of the stretch
  want: [7.5, 15],          // THOUGHT moves a minute while he is on: one every 4-8 s (a jump-cut reframe is not one)
  join: 0.3,                // a framing change within this many seconds of a join the lens reframed (__lens[id].jumps)
  paceMin: 20,              // the thought pace is judged over at least this many seconds of framed time
  away: 12,                 // never away longer than this (s; was 18 s before 2026-10-22)
  takeover: 1.0,            // an off stretch this long is a takeover; shorter ones are a whip or a cut passing through
  hook: 3,                  // the hook opens on his face (the first 3 s)
  offShare: [0.15, 0.30],   // long-form: 15-30 % of the runtime in takeovers
  zoom: 1.2,                // a track's max_zoom when work/tracks.json didn't give one (the tracks.json contract)
  soft: 0.24,               // tracks.json's soft (kit/film/cut.py SOFT) when a track gives none
};
export const TAKEOVER = { len: [4, 12], gap: 3 };       // each takeover 4-12 s, at least 3 s of his face between two
export const DENSITY = { med: 3, high: 5, dur: 2 };   // > 3 groups for > 2 s MEDIUM, > 5 for > 2 s HIGH (SCENES.md §10)
export const TRANS = { whips: 0.4 };                    // whips at most 40 % of the transitions; cuts may repeat

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(1).padStart(4, "0")}`;

// {x, y, w, h} from the shapes pages publish: __faceRect's {left, right, top, bottom}, the contract's {x, y, w, h}
export const toBox = (r) => {
  if (!r) return null;
  const b = "left" in r ? { x: +r.left, y: +r.top, w: +r.right - +r.left, h: +r.bottom - +r.top } : { x: +r.x, y: +r.y, w: +r.w, h: +r.h };
  return [b.x, b.y, b.w, b.h].every(Number.isFinite) && b.w > 0 && b.h > 0 ? b : null;
};

// the framing a sample shows: where his face is and how big. The face box when the page gives it; else his shape's rect
// scaled by the footage zoom (a push inside a fixed card changes the zoom, not the rect); else (the contract allows
// rect and face null) the published zoom alone, centred. fz: an old box page's footage zoom (HF.box.at), used for the
// framing only. basis: which of the three it is (sizes on different bases don't compare: a switch is a change). null
// when nothing gives the framing: that time is unmeasured, never "unchanged"
export const frameOf = (s, FW = 1920, FH = 1080) => {
  const b = s.face || s.rect;
  if (b && b.w > 0 && b.h > 0)
    return { cx: b.x + b.w / 2, cy: b.y + b.h / 2, sc: Math.sqrt(b.w * b.h) * (s.face ? 1 : s.zoom || s.fz || 1), basis: s.face ? "face" : "rect" };
  if (Number.isFinite(s.zoom) && s.zoom > 0) return { cx: FW / 2, cy: FH / 2, sc: s.zoom, basis: "zoom" };
  return null;
};

// his own footage by name (a <video>'s id or file name): the tracks the looks give him (face, aroll, room plate, ...).
// A screen recording, a photo or a meme clip (scr, screen, ph, meme, broll) is not him
export const FACE_TRACK = /^(face|aroll|a-roll|a|room|cam|camera|take|speaker|pip)$/i;

// the speaker sample for a page without window.__speaker (pages from before v11), from what those pages publish:
//   faceRect  the page defines window.__faceRect: it knows the real face (night_reel.js, canvas.js, redline.js)
//   face      {x, y, w, h} | null: __faceRect's face, else (no __faceRect) the box's face zone (42 % down a shown box)
//   box       window.__box.rect(t) ({cx, cy, w, h, op}) | null; boxed: the page has window.__box
//   plate     {x, y, w, h} | null: a shown <video> of his own footage (FACE_TRACK) covering 90 % of the frame
//   fz        an old box page's footage zoom (HF.box.at), for the framing only
// The page's own face decides on / off, as precheck's face check trusts it: claude-makes-claude plays its A-roll full
// frame with the box hidden (op 0), and he is on. The box only names the kind while it is shown. With no face, a
// full-bleed plate of him is him: oss-editor-reels-a opens on his room plate with the speaker card hidden. Everything
// here is estimated (est): speakerFindings says so and keeps the hook / away / face-off findings at MEDIUM
export function fallbackSpeaker({ faceRect = false, face = null, box = null, boxed = false, plate = null, fz = null, FW = 1920, FH = 1080 } = {}) {
  const src = faceRect ? "__faceRect" : boxed && box ? "__box" : "none";
  const shown = (b) => (b && b.w > 4 && b.h > 4 && b.x < FW && b.y < FH && b.x + b.w > 0 && b.y + b.h > 0 ? b : null);
  const fv = shown(face);
  const boxOn = !!(boxed && box && box.op >= 0.5);
  const rect = boxOn ? { x: box.cx - box.w / 2, y: box.cy - box.h / 2, w: box.w, h: box.h } : null;
  const boxKind = boxOn ? (box.w >= 0.9 * FW && box.h >= 0.9 * FH ? "full" : (box.w * box.h) / (FW * FH) < 0.1 ? "corner" : "card") : null;
  const base = { src, zoom: null, fz, lens: "", track: null, max_zoom: null, est: true };
  if (src === "none") return { ...base, on: false, kind: "off", face: null, rect: null };
  const onPlate = (b) => !!(plate && b && b.x + b.w / 2 >= plate.x && b.x + b.w / 2 <= plate.x + plate.w && b.y + b.h / 2 >= plate.y && b.y + b.h / 2 <= plate.y + plate.h);
  if (src === "__faceRect" && fv)
    return { ...base, on: true, kind: boxKind || (onPlate(fv) ? "full" : "?"), face: fv, rect: rect || (onPlate(fv) ? plate : null) };
  // the box's face zone is a guess from its rect: no face, the framing comes from the rect x the footage zoom
  if (src === "__box" && fv && boxOn) return { ...base, on: true, kind: boxKind, face: null, rect };
  if (plate && !boxOn) return { ...base, on: true, kind: "full", face: null, rect: plate };
  return { ...base, on: false, kind: "off", face: null, rect: null };
}

// the kind of footage playing at t: the edl piece (D.pieces: [{ kind, out_a }]) that starts at or before t
export const kindAt = (pieces, t) => {
  if (!Array.isArray(pieces) || !pieces.length || !Number.isFinite(t)) return null;
  let k = null;
  for (const p of pieces) if (p && Number.isFinite(+p.out_a) && +p.out_a <= t + 1e-6 && (!k || +p.out_a >= +k.out_a)) k = p;
  return k ? String(k.kind || "") || null : null;
};

// a sample's zoom budgets over cover -> { sharp, soft (null: no soft tier), how, kind? }. tracks: D.tracks as precheck reads
// it, { name: { max_zoom, sharp_px, soft_zoom, soft, kinds: { kind: { sharp_px, ... } }, w, h } } (work/tracks.json), or
// { name: max_zoom } (the numbers alone, as before). In this order:
//   sample    the sample publishes max_zoom (the cap the engine enforced there): that, with today's rule (over by up to
//             5 % MEDIUM, more HIGH)
//   contract  his track (s.track, else face / aroll / a, else the only one) gives sharp_px: the tracks.json contract,
//             "any shape S px tall: max(1, sharp_px / S)", with the sharp_px of the kind playing at t (D.pieces) winning
//             over the track's (the poorest kind's) and S the sample's shape: its rect height, or its cover height when
//             the shape is wider than the footage (the lens's own Hc, HF.motion.lensBudget), the frame without a rect.
//             The soft tier the same way: max(r, 1 + soft * min(r, 1)) (kit/film/cut.py soft_budget). Over sharp up to
//             soft is MEDIUM, over soft HIGH. Box pages with the lens off, redline.js and HF.camera pages publish no
//             max_zoom: their windows and punches are judged here, not against the track's full-height max_zoom
//   track     only the track's max_zoom (and soft_zoom when given)
//   default   no track: 1.2 (and the smallest of several numbers, the safe side)
export const budgetsOf = (s, tracks = {}, { pieces = null, FH = 1080 } = {}) => {
  if (Number.isFinite(s.max_zoom)) return { sharp: s.max_zoom, soft: null, how: "sample" };
  const has = (k) => tracks[k] != null && (typeof tracks[k] === "object" || Number.isFinite(tracks[k]));
  const names = Object.keys(tracks).filter(has);
  const name = s.track && has(s.track) ? s.track : ["face", "aroll", "a"].find(has) || (names.length === 1 ? names[0] : null);
  if (name == null) {
    const v = names.map((k) => (typeof tracks[k] === "number" ? tracks[k] : +tracks[k].max_zoom)).filter(Number.isFinite);
    return v.length ? { sharp: Math.min(...v), soft: null, how: "track" } : { sharp: SPEAKER.zoom, soft: null, how: "default" };
  }
  const T = tracks[name];
  if (typeof T === "number") return { sharp: T, soft: null, how: "track" };
  const kind = kindAt(pieces, s.t), K = kind && T.kinds && T.kinds[kind] && typeof T.kinds[kind] === "object" ? T.kinds[kind] : null;
  const px = K && +K.sharp_px > 0 ? +K.sharp_px : +T.sharp_px > 0 ? +T.sharp_px : null;
  if (px) {
    const r0 = s.rect, fw = +T.w > 0 && +T.h > 0 ? +T.w / +T.h : null;
    const H = r0 && r0.h > 0 ? Math.max(r0.h, fw ? r0.w / fw : 0) : FH;
    const r = px / H, sf = Number.isFinite(+T.soft) && T.soft != null ? +T.soft : SPEAKER.soft;
    return { sharp: +Math.max(1, r).toFixed(4), soft: +Math.max(r, 1 + sf * Math.min(r, 1)).toFixed(4), how: "contract", kind: K ? kind : null };
  }
  if (Number.isFinite(+T.max_zoom) && T.max_zoom != null)
    return { sharp: +T.max_zoom, soft: Number.isFinite(+T.soft_zoom) && T.soft_zoom != null ? +T.soft_zoom : null, how: "track" };
  return { sharp: SPEAKER.zoom, soft: null, how: "default" };
};
// the sharp budget alone (as before 2026-10-22's per-kind contract)
export const budgetOf = (s, tracks = {}, o = {}) => budgetsOf(s, tracks, o).sharp;

// consecutive samples (no gap over 1.5 steps) where pick(s) holds -> [{a, b, ss}] (b = the last sample's time)
const runs = (S, step, pick) => {
  const out = [];
  let cur = null;
  for (const s of S) {
    if (!pick(s)) { cur = null; continue; }
    if (cur && s.t - cur.b <= 1.5 * step + 1e-6) { cur.b = s.t; cur.ss.push(s); }
    else { cur = { a: s.t, b: s.t, ss: [s] }; out.push(cur); }
  }
  return out;
};

// -> { src, est (on / off estimated: no window.__speaker), on, off, full (null: no kind known; fullMin: some on-time of
//      unknown kind, so full is a lower bound), unmeasured (s on with nothing to frame by), corner (s on in a corner:
//      framing not judged), moves, perMin, thought, joinMoves, thoughtPerMin, joinPerMin, judged (s), stretches
//      [{a, b, dur, declared}], longest, aways [{a, b, dur}], takeovers, longestAway, hookOff (s),
//      zoom: { max, budget, soft, how, over: [{a, b, max, budget, soft, sev}] } | null, softRuns [{a, b}], changes: [t] }
// A corner is on screen but too small for the lens to move on: its time is neither a stretch nor unmeasured, and the
// framing gate skips it, as plan_check does (its ON set has no 'corner'; review 2026-10-22: a 20 s corner picture-in-
// picture over a proof insert read as a framing HIGH and stopped the build). Going into or out of a corner is a change.
// moves / perMin count every framing change (what precheck has always published). A move whose first change lies within
// SPEAKER.join (0.3 s) of a join the lens reframed (joins: the times in window.__lens[id].jumps) is a JOIN reframe: the
// jump cut is meant to reframe, so it does not count against the pace. The rest are THOUGHT moves (thoughtPerMin, the
// pace the 7.5-15 a minute want is about). pieces (D.pieces) and FH feed the zoom budget (budgetsOf)
export function speakerStats(S, { step, FW, FH, tracks = {}, pieces = null, joins = [] }) {
  const C = SPEAKER, n = S.length;
  if (!n) return null;
  const srcs = {};
  S.forEach((s) => (srcs[s.src] = (srcs[s.src] || 0) + 1));
  const src = Object.entries(srcs).sort((a, b) => b[1] - a[1])[0][0];
  if (src === "none") return { src, none: true };
  let onT = 0, fullT = 0, kindT = 0, unT = 0, cornerT = 0, anchor = null, cur = null, prevOn = null, hookOff = 0;
  const stretches = [], changes = [];
  const close = (t) => { if (cur) { cur.b = t; cur.dur = +(t - cur.a).toFixed(2); cur.declared = cur.n > 0 && cur.hold / cur.n >= C.declared; stretches.push(cur); cur = null; } };
  const open = (t) => { cur = { a: t, n: 0, hold: 0 }; };
  for (const s of S) {
    if (s.on && s.kind && s.kind !== "?") kindT += step;               // a fallback without __box or a plate knows on / off only
    if (s.on && s.kind === "full") fullT += step;
    if (s.t < C.hook - 1e-6 && !s.on) hookOff += step;
    if (!s.on) { close(s.t); anchor = null; prevOn = false; continue; }
    onT += step;
    if (s.kind === "corner") {                                         // a corner: on, not judged (see above)
      if (anchor) changes.push(s.t);                                   // into the corner from a framing: a change
      close(s.t); anchor = null; cornerT += step; prevOn = "corner"; continue;
    }
    const f = frameOf(s, FW, FH);
    if (!f) { close(s.t); anchor = null; unT += step; prevOn = true; continue; }   // on, nothing to frame by: unmeasured, not "unchanged"
    if (!anchor) {
      if (prevOn === false || prevOn === "corner") changes.push(s.t);   // he comes back, or out of the corner: a new framing
      close(s.t); anchor = f; open(s.t);
    } else if (f.basis !== anchor.basis || Math.hypot((f.cx - anchor.cx) / FW, (f.cy - anchor.cy) / FH) >= C.move || Math.abs(f.sc / anchor.sc - 1) >= C.scale) {
      changes.push(s.t); close(s.t); anchor = f; open(s.t);
    }
    cur.n++;
    if (s.lens === "hold") cur.hold++;
    prevOn = true;
  }
  close(S[n - 1].t + step);
  // moves: changes closer than 1 s are one move in progress; a move that starts on a reframed join is a join reframe
  const J = (joins || []).filter(Number.isFinite);
  let moves = 0, joinMoves = 0, lastC = -1e9;
  for (const t of changes) {
    if (t - lastC > C.merge + 1e-6) { moves++; if (J.some((j) => Math.abs(t - j) <= C.join + 1e-6)) joinMoves++; }
    lastC = t;
  }
  const runtime = n * step;
  const aways = runs(S, step, (s) => !s.on).map((r) => ({ a: r.a, b: r.b + step, dur: +(r.b - r.a + step).toFixed(2) }));
  const takeovers = aways.filter((r) => r.dur >= C.takeover - 1e-6);
  const longest = stretches.reduce((m, x) => (x.dur > (m ? m.dur : -1) ? x : m), null);
  // zoom: only when the page publishes it (the __speaker contract); over budget = softer than the source allows. Each
  // sample's budgets (budgetsOf): the cap it published, else tracks.json's per kind and shape. HIGH over the soft tier
  // when there is one, else (a published cap, or numbers only) over the budget by more than 5 %
  const bo = { pieces, FH };
  const zs = S.filter((s) => s.on && Number.isFinite(s.zoom));
  let zoom = null;
  if (zs.length) {
    const over = runs(S, step, (s) => s.on && Number.isFinite(s.zoom) && s.zoom > budgetsOf(s, tracks, bo).sharp + 0.005).map((r) => {
      const bs = r.ss.map((s) => budgetsOf(s, tracks, bo)), max = Math.max(...r.ss.map((s) => s.zoom));
      const hi = r.ss.some((s, i) => (bs[i].soft != null ? s.zoom > bs[i].soft + 0.005 : s.zoom > bs[i].sharp * 1.05));
      const softs = bs.map((b) => b.soft).filter((x) => x != null);
      return { a: r.a, b: r.b + step, max, budget: Math.min(...bs.map((b) => b.sharp)), soft: softs.length ? Math.min(...softs) : null,
        how: bs[0].how, kind: bs[0].kind || null, sev: hi ? "HIGH" : "MEDIUM" };
    });
    const top = zs.reduce((m, s) => (s.zoom > m.zoom ? s : m), zs[0]), tb = budgetsOf(top, tracks, bo);
    zoom = { max: +top.zoom.toFixed(3), budget: tb.sharp, soft: tb.soft, how: tb.how, over };
  }
  // the soft allowance in force (__speaker.soft: a jump reframe the sharp budget couldn't pay, a box hold's drift)
  const softRuns = runs(S, step, (s) => s.on && s.soft === true).map((r) => ({ a: r.a, b: +(r.b + step).toFixed(2) }));
  // perMin: over the time his framing is judged (on, out of a corner)
  const judged = onT - cornerT, pm = (k) => (judged > 1e-6 ? +((60 * k) / judged).toFixed(1) : 0);
  return { src, est: src !== "__speaker", on: onT / runtime, off: 1 - onT / runtime, full: kindT > 0 ? fullT / runtime : null,
    fullMin: kindT > 0 && kindT < onT - 1e-6, unmeasured: +unT.toFixed(2), corner: +cornerT.toFixed(2), onSec: onT, moves,
    perMin: pm(moves), thought: moves - joinMoves, joinMoves, thoughtPerMin: pm(moves - joinMoves), joinPerMin: pm(joinMoves),
    judged: +judged.toFixed(2), stretches, longest, aways, takeovers,
    longestAway: aways.reduce((m, x) => Math.max(m, x.dur), 0), hookOff: +hookOff.toFixed(2), zoom, softRuns, changes };
}

// findings from speakerStats: [{kind, sev, text, a, b, dur}]. longForm: a 16:9 film of 2 minutes or more (the face-off
// share applies to long-form only); a, b: the checked range (where a whole-film finding is placed). On a page without
// window.__speaker (st.est) on / off is a guess from __faceRect / __box / a full-bleed plate of him: the hook, away and
// face-off findings say "estimated" and stay MEDIUM (a guess never fails the build); framing is measured either way
export function speakerFindings(st, { longForm = false, a: A = 0, b: B = 0 } = {}) {
  const C = SPEAKER, out = [];
  if (!st || st.none) return out;
  const est = st.est ? "estimated (no window.__speaker): " : "";
  for (const s of st.stretches) {
    if (s.dur <= C.med) continue;
    if (s.declared) continue;                                          // the lens declared a hold: a held frame on purpose
    out.push({ kind: "framing", sev: s.dur > C.high ? "HIGH" : "MEDIUM", a: s.a, b: s.b, dur: s.dur,
      text: `his framing unchanged for ${s.dur.toFixed(1)} s (MEDIUM > ${C.med} s, HIGH > ${C.high} s): push across the thought, pull out, an eased punch on the stressed word, or a slight arc (one every 4-8 s)` });
  }
  for (const r of st.aways) if (r.dur > C.away + 1e-6)
    out.push({ kind: "away", sev: st.est ? "MEDIUM" : "HIGH", a: r.a, b: r.b, dur: r.dur, text: `${est}away from him ${r.dur.toFixed(1)} s (never more than ${C.away} s): split the takeover with a face beat on its takeaway` });
  if (st.hookOff > 0)
    out.push({ kind: "hook", sev: "MEDIUM", a: 0, b: C.hook, dur: st.hookOff, text: `${est}his face is off for ${st.hookOff.toFixed(1)} s of the first ${C.hook} s (the hook opens on his face)` });
  if (longForm && !(st.off >= C.offShare[0] - 0.005 && st.off <= C.offShare[1] + 0.005))
    out.push({ kind: "faceoff", sev: "MEDIUM", a: A, b: B, dur: 0,
      text: `${est}face off for ${Math.round(100 * st.off)} % of the runtime (long-form: ${100 * C.offShare[0]}-${100 * C.offShare[1]} % in takeovers of 4-12 s; kit/refs/SCENES.md §9 "When to remove him")` });
  if (st.zoom) for (const r of st.zoom.over)
    out.push({ kind: "upscale", sev: r.sev || (r.max > r.budget * 1.05 ? "HIGH" : "MEDIUM"), a: r.a, b: r.b, dur: +(r.b - r.a).toFixed(2),
      text: `his footage at ${r.max.toFixed(2)}x over cover (the source allows ${r.budget.toFixed(2)}x sharp` + (r.soft != null ? `, ${r.soft.toFixed(2)}x with mild softening` : "")
        + ` at this render size${r.kind ? ` for its '${r.kind}' footage` : ""}, work/tracks.json): it softens; ease the push or punch less` });
  // the thought pace (P-S4, "holistic, not heavy"): more than 15 thought moves a minute is busy; joins are not counted
  if (st.thoughtPerMin > C.want[1] + 1e-9 && st.judged >= C.paceMin - 1e-6)
    out.push({ kind: "pace", sev: "MEDIUM", a: A, b: B, dur: 0,
      text: `${st.thoughtPerMin} thought moves per minute on him (want ${C.want[0]}-${C.want[1]}: one every 4-8 s; ${st.joinMoves} jump-cut reframes not counted): hold a framing through the thought, move on its turn` });
  return out;
}

// window.__takeovers ([{ a, b, kind, in, out, dropped: [{ speaker, t }] }], kit/hf/trans.js) checked straight from the
// page (P-S3): each takeover 4-12 s (TAKEOVER.len), at least 3 s of his face between two (TAKEOVER.gap), and a template
// shot the takeover dropped (it fell inside [a, b): the template thought he was on there). All MEDIUM: the sampled
// 'away' check gates anything over 12 s, and a dropped shot is said, not judged
export function takeoverFindings(list) {
  const L = (list || []).filter((x) => x && Number.isFinite(+x.a) && Number.isFinite(+x.b)).map((x) => ({ ...x, a: +x.a, b: +x.b })).sort((p, q) => p.a - q.a);
  const out = [], T = TAKEOVER;
  for (const x of L) {
    const d = x.b - x.a, nm = `takeover ${x.kind || ""}`.trim();
    if (d < T.len[0] - 0.05 || d > T.len[1] + 0.05)
      out.push({ kind: "takeover", sev: "MEDIUM", a: x.a, b: x.b, dur: +d.toFixed(2),
        text: `${nm} ${d.toFixed(1)} s (each takeover ${T.len[0]}-${T.len[1]} s: ${d < T.len[0] ? "too short to read as its own scene; merge it or keep him on" : "split it with a face beat on its takeaway"})` });
    const dr = Array.isArray(x.dropped) ? x.dropped.filter((s) => s && Number.isFinite(+s.t)) : [];
    if (dr.length)
      out.push({ kind: "takeover", sev: "MEDIUM", a: x.a, b: x.b, dur: +d.toFixed(2),
        text: `${nm} dropped ${dr.length} template shot${dr.length > 1 ? "s" : ""} of his inside it (${dr.slice(0, 4).map((s) => `${s.speaker || "?"} at ${(+s.t).toFixed(2)} s`).join(", ")}): move the shot to the takeover's end, or the takeover off it` });
  }
  for (let i = 1; i < L.length; i++) {
    const g = L[i].a - L[i - 1].b;
    if (g < T.gap - 0.05)
      out.push({ kind: "takeover", sev: "MEDIUM", a: L[i - 1].b, b: L[i].a, dur: +Math.max(0, g).toFixed(2),
        text: `only ${g.toFixed(1)} s of his face between two takeovers (at least ${T.gap} s: the takeaway line after a takeover is his)` });
  }
  return out;
}

// -> { p50, p90, max, at, share (of samples over DENSITY.med), findings }
export function densityStats(S, step) {
  const D = DENSITY;
  if (!S.length) return { p50: 0, p90: 0, max: 0, at: 0, share: 0, findings: [] };
  const ns = S.map((s) => s.n).sort((a, b) => a - b), q = (p) => ns[Math.min(ns.length - 1, Math.floor(p * ns.length))];
  const peak = S.reduce((m, s) => (s.n > m.n ? s : m), S[0]);
  const findings = [];
  for (const r of runs(S, step, (s) => s.n > D.med)) {
    const dur = r.b - r.a + step;
    if (dur <= D.dur + 1e-6) continue;
    const hi = runs(r.ss, step, (s) => s.n > D.high).some((h) => h.b - h.a + step > D.dur + 1e-6);
    const top = r.ss.reduce((m, s) => (s.n > m.n ? s : m), r.ss[0]);
    findings.push({ kind: "density", sev: hi ? "HIGH" : "MEDIUM", a: r.a, b: r.b + step, dur: +dur.toFixed(2),
      text: `${top.n} visual groups up at ${mmss(top.t)} (more than ${D.med} for ${dur.toFixed(1)} s; HIGH over ${D.high}): one idea per frame, take some off [${(top.labels || []).slice(0, 8).join(", ")}]` });
  }
  return { p50: q(0.5), p90: q(0.9), max: peak.n, at: peak.t, share: S.filter((s) => s.n > D.med).length / S.length, findings };
}

// a bracket (kit/hf/trans.js fold): two entries sharing a pair id (a takeover's in and out, T.cardToGraphic's morph and
// its return), neighbours in time and of one kind, are ONE transition ({ ..., pair, until: the return's t }). window.__trans
// is published folded already; this folds a list that isn't (P-S3: precheck does not depend on the page doing it)
export const foldTrans = (L) => {
  const out = [];
  for (let i = 0; i < L.length; i++) {
    const p = L[i], q = L[i + 1];
    if (p.pair != null && q && q.pair === p.pair && q.kind === p.kind && p.until == null) { out.push({ ...p, until: q.t }); i++; }
    else out.push(p);
  }
  return out;
};

// -> { n, kinds: {kind: count}, whips, repeats: [{a, b, kind}], findings, times }. Brackets count once (foldTrans); a
// repeat after a bracket is named from its return (until), the end next to the second one, as HF.trans.check does
export function transStats(list) {
  const L = foldTrans((list || []).filter((x) => x && Number.isFinite(+x.t))
    .map((x) => Object.assign({ t: +x.t, kind: String(x.kind || "?"), why: x.why || "" }, x.pair != null ? { pair: x.pair } : {},
      x.until != null && Number.isFinite(+x.until) ? { until: +x.until } : {}))
    .sort((a, b) => a.t - b.t));
  const kinds = {};
  L.forEach((x) => (kinds[x.kind] = (kinds[x.kind] || 0) + 1));
  const repeats = [];
  for (let i = 1; i < L.length; i++) if (L[i].kind === L[i - 1].kind && L[i].kind !== "cut")
    repeats.push({ a: L[i - 1].until != null ? L[i - 1].until : L[i - 1].t, b: L[i].t, kind: L[i].kind });
  const whips = L.length ? (kinds.whip || 0) / L.length : 0;
  const findings = repeats.map((r) => ({ kind: "trans", sev: "MEDIUM", a: r.a, b: r.b, dur: 0,
    text: `'${r.kind}' twice in a row (${mmss(r.a)} and ${mmss(r.b)}): vary it, each kind should mean something (kit/refs/SCENES.md §10)` }));
  if (L.length >= 3 && whips > TRANS.whips + 1e-9)
    findings.push({ kind: "trans", sev: "MEDIUM", a: L[0].t, b: L[L.length - 1].t, dur: 0, text: `whips are ${Math.round(100 * whips)} % of the ${L.length} transitions (max ${100 * TRANS.whips} %)` });
  // times: every moment a transition plays (a bracket's return too: the 'still' check counts it as change)
  return { n: L.length, kinds, whips, repeats, findings, times: L.flatMap((x) => (x.until != null ? [x.t, x.until] : [x.t])) };
}

// the layout slot a __speaker sample gives the 35 % gate (canvas pages publish no __box): his kind, and for a card or a
// circle where it sits: left / right (top / bottom on 9:16) or centre, the way precheck names a box slot. Sides are one
// layout (OWNER_DEFAULTS §1: "a card beside the graphic"): precheck merges them with mergeSides and prints the split
export function slotOf(s, FW, FH) {
  if (!s || !s.on || s.kind === "off") return "off (takeover)";
  if (s.kind === "full" || s.kind === "frame" || s.kind === "corner" || !s.rect) return s.kind || "?";
  const wide = FW > FH, c = wide ? (s.rect.x + s.rect.w / 2) / FW : (s.rect.y + s.rect.h / 2) / FH;
  return `${s.kind} ${c < 0.42 ? (wide ? "left" : "top") : c > 0.58 ? (wide ? "right" : "bottom") : "centre"}`;
}
// a box slot (precheck's own names: card left, small card right, ...) with the sides merged the same way; a corner is a
// corner wherever it sits (corner top + corner bottom on 9:16 are one layout, and it is not 'beside' anything)
export const mergeSides = (slot) => (/^corner\b/.test(String(slot)) ? "corner" : String(slot).replace(/ (left|right|top|bottom)$/, " beside"));

// the 35 % layout gate (OWNER_DEFAULTS §1: "No single layout covers more than 35 % of the runtime", where "a card beside
// the graphic" is one layout, so its sides merge). slots: {slot: seconds} in precheck's names (card left, small card
// right, full, off (graphic), ...); contract: the page publishes window.__speaker (built on kit v11).
//   contract   the sides merged over 35 % is HIGH
//   no contract  (a page built before v11) gated per side, as it was: one side over 35 % stays HIGH with the old text;
//              the sides merged over 35 % is MEDIUM. Review 2026-10-22: kit/film/example (card right 27 % + left 23 %)
//              passed before and is the documented smoke test; it is flagged, not failed, until it is rebuilt on the
//              contract, the way an estimated 'away' is capped
// -> { list: [[merged slot, s]] largest first, sides: {merged: {slot: s}}, findings: [{kind, sev, text, a, b, dur}] }
export function layoutGate(slots, runtime, { contract = false, a = 0, b = 0, max = 0.35 } = {}) {
  const merged = {}, sides = {};
  for (const [slot, s] of Object.entries(slots || {})) {
    const k = mergeSides(slot);
    merged[k] = (merged[k] || 0) + s;
    if (k !== slot) sides[k] = { ...(sides[k] || {}), [slot]: s };
  }
  const list = Object.entries(merged).sort((x, y) => y[1] - x[1]), findings = [];
  if (!list.length || !(runtime > 0)) return { list, sides, findings };
  const pc = (s) => Math.round((100 * s) / runtime), vary = "vary it (beside, corner, hero, a takeover, a punch)";
  const split = (k) => (sides[k] ? ` (${Object.entries(sides[k]).sort((x, y) => y[1] - x[1]).map(([s, x]) => `${s.split(" ").pop()} ${pc(x)} %`).join(", ")})` : "");
  const [top, secs] = list[0], [one, oneS] = Object.entries(slots).sort((x, y) => y[1] - x[1])[0];
  if (contract) {
    if (secs / runtime > max) findings.push({ kind: "layout", sev: "HIGH", a, b, dur: secs,
      text: `the speaker is "${top}" for ${pc(secs)} % of the runtime${split(top)} (max ${100 * max} %; left and right count as one): ${vary}` });
  } else if (oneS / runtime > max) {
    findings.push({ kind: "layout", sev: "HIGH", a, b, dur: oneS, text: `the speaker box is "${one}" for ${pc(oneS)} % of the runtime (max ${100 * max} %): ${vary}` });
  } else if (secs / runtime > max) {
    findings.push({ kind: "layout", sev: "MEDIUM", a, b, dur: secs,
      text: `the speaker is "${top}" for ${pc(secs)} % of the runtime${split(top)} (max ${100 * max} %; since 2026-10-22 left and right count as one layout: MEDIUM on a page without window.__speaker, HIGH once it publishes it): ${vary}` });
  }
  return { list, sides, findings };
}
