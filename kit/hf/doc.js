/* kit/hf/doc.js — the documentary preset's page (kit/presets/documentary, 2026-10-24). Needs core.js.
 *
 * OPT-IN ONLY: kit/hf/vendor.py inlines this file only into a page whose script calls HF.doc(, and kit/film builds
 * D.doc only for a film with PRESET = "documentary". No other page or look changes when this file changes.
 *
 *   const DC = HF.doc(K, ROOT, { aroll: "aroll", D }); // the "documentary" look, the interview full frame with a slow
 *                                                     // documentary push or pull per shot, window.__speaker published
 *   DC.all();               // everything D.doc carries: cutaways, lower-thirds, chapters, stamps, letterbox, subtitles
 *   DC.broll()  DC.thirds()  DC.chapters()  DC.stamps()  DC.letterbox()  DC.subtitles()     // or one at a time
 *   DC.third(t0, t1, "Priya", "Owner, Café X")        // one lower-third by hand (name + role, a thin rule)
 *   DC.chapter(t, "Attempt one", "Day 1 · 23:10", 2.4) // a black chapter card (serif title, mono sub) over everything
 *   DC.stamp(t, "DAY 1 · 23:10", 3)                    // a time stamp, top left, typed on
 *   DC.results(t0, t1, { title, rows: [[label, value, good?], ...] })   // the results board (a blind test's answer)
 *
 * The rules it keeps (kit/presets/documentary/README.md): he is full frame in his room or off (a cutaway, a chapter
 * card): never cut out, never in a designed world. Type is quiet and small but readable (>= 32 px on the page):
 * Inter caps for names, Instrument Serif for chapters, JetBrains Mono for stamps. Every state is a pure function of
 * time (K.onFrame), so any frame seeks exactly.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/doc.js needs core.js first");

  // the look: night's dark tokens, a warm off-white ink and one muted amber accent (no colour washes, no glows)
  const INTER = "'Inter', sans-serif", JB = "'JBMono', monospace", SERIF = "'InstrumentSerif', serif";
  HF.LOOKS.documentary = HF.LOOKS.documentary || { dark: true, code: "dark",
    C: { paper: "#000000", card: "rgba(12,12,14,.86)", sunk: "rgba(255,255,255,.05)", line: "rgba(255,255,255,.14)", ink: "#F2EEE6", text: "#E4DFD6",
      ink2: "#BDB7AD", sub: "#A39D93", mute: "#8C877F", acc: "#E0B25A", accTint: "rgba(224,178,90,.16)", ok: "#7FC79A", okTint: "rgba(127,199,154,.16)",
      bad: "#E0705A", badTint: "rgba(224,112,90,.16)", warm: "#E0B25A", onFill: "#0B0B0C", onVideo: "#F2EEE6", plate: "rgba(0,0,0,.72)",
      shadow: "0 18px 50px rgba(0,0,0,.55)", shadowSoft: "0 8px 24px rgba(0,0,0,.45)", cardLine: "rgba(255,255,255,.10)" },
    F: { code: JB, body: INTER, mono: JB, display: SERIF, displayWeight: 400, displayTrack: "-0.01em", hand: "'Caveat', cursive", stamp: INTER } };

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const ease = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const fadeIO = (t, a, b, fi = 0.4, fo = 0.4) => (t < a || t > b ? 0 : Math.min(ease((t - a) / fi), ease((b - t) / fo)));

  HF.doc = function (K, ROOT, o = {}) {
    const D = o.D || root.D || {};                                          // pass the page's D: HF.doc(K, ROOT, { aroll, D })
    const DD = D.doc || {};
    const W = K.width, H = K.height, FPS = K.fps;
    HF.look("documentary");
    ROOT.style.background = "#000";
    const layer = (z, extra = "") => K.el(ROOT, `position:absolute;left:0;top:0;width:${W}px;height:${H}px;z-index:${z};pointer-events:none;${extra}`);

    // ---- the interview, full frame: one slow move per shot (a push, then a pull on the next), about the face
    const vid = document.getElementById(o.aroll || "aroll");
    const T = (D.tracks && D.tracks[o.aroll || "aroll"]) || {};
    const cap = clamp(+(T.soft_zoom || T.max_zoom || 1.06), 1.0, 1.3);           // OWNER_DEFAULTS §0: never past x1.3
    const pic = (p) => (p.pic_a != null ? p.pic_a : p.out_a);
    const P = (D.pieces || []).slice().sort((a, b) => pic(a) - pic(b));
    const shots = [];                                                          // a shot = a run of one source, unbroken in time
    P.forEach((p, k) => {
      const last = shots[shots.length - 1], prev = P[k - 1];
      const joined = last && prev && prev.clip === p.clip && Math.abs(prev.src_b - p.src_a) < 1e-3;
      if (joined) { last.b = k + 1 < P.length ? pic(P[k + 1]) : D.total; return; }
      if (last) last.b = pic(p);
      shots.push({ a: pic(p), b: k + 1 < P.length ? pic(P[k + 1]) : D.total, face: p.face || [W / 2, H * 0.4, 300], clip: p.clip });
    });
    shots.forEach((s, k) => {
      const dur = Math.max(0.5, s.b - s.a);
      s.push = clamp(0.012 + 0.0025 * dur, 0.02, Math.min(0.06, cap - 1));    // ~4 % over a 12 s answer: felt, not seen
      s.dir = k % 2 ? -1 : 1;                                                   // push in, then pull out on the next shot
    });
    const shotAt = (t) => shots.find((s) => t >= s.a - 1e-6 && t < s.b) || shots[shots.length - 1];
    const scaleAt = (s, t) => { const u = ease((t - s.a) / Math.max(0.5, s.b - s.a)); return 1 + s.push * (s.dir > 0 ? u : 1 - u); };
    if (vid) {
      vid.style.cssText += `;position:absolute;left:0;top:0;width:${W}px;height:${H}px;object-fit:cover;z-index:2;will-change:transform`;
      if (shots.length) K.onFrame((t) => {
        const s = shotAt(t), k = scaleAt(s, t);
        vid.style.transformOrigin = `${s.face[0]}px ${s.face[1]}px`;
        vid.style.transform = `scale(${k.toFixed(5)})`;
      });
    }

    const covers = [];                                                         // [a, b): spans where he is off (a cutaway, a chapter card)
    const off = (t) => covers.some(([a, b]) => t >= a && t < b);
    window.__speaker = (t) => {
      if (!vid || !shots.length || off(t)) return { on: false, kind: "off", rect: null, face: null, zoom: null, lens: "", track: o.aroll || "aroll", max_zoom: null };
      const s = shotAt(t), k = scaleAt(s, t), sz = s.face[2] * k;
      return { on: true, kind: "full", rect: { x: 0, y: 0, w: W, h: H }, face: { x: s.face[0] - sz / 2, y: s.face[1] - sz * 0.6, w: sz, h: sz * 1.25 },
        zoom: +k.toFixed(4), lens: s.dir > 0 ? "push" : "pull", track: o.aroll || "aroll", max_zoom: +cap.toFixed(4) };
    };

    const L = { broll: layer(5), ex: layer(12), box: layer(20, "") , text: layer(30), card: layer(40) };
    L.box.dataset.decor = "";
    const api = { look: HF.LOOK, shots, covers, layers: L };
    window.__doc = api;                                                       // for checks and debugging

    // ---- v2 type (2026-10-25, the Netflix cut of films/not-ai-made): condensed caps for names and titles (Oswald,
    // copied into the page's assets/fonts by kit/film/doc.py copy_fonts), JetBrains Mono for typed notes, one red accent
    const OSW = "'Oswald', 'Inter', sans-serif", RED = "#E50914", GREEN = "#46D369";
    if (!document.getElementById("doc-fonts")) {
      const st = document.createElement("style");
      st.id = "doc-fonts";
      st.textContent = [500, 600, 700].map((w) => `@font-face{font-family:'Oswald';src:url('assets/fonts/Oswald-${w}.ttf');font-weight:${w};font-display:block}`).join("");
      document.head.append(st);
    }
    const TYPE_SFX = "typing/typing__electronic-typing__mixkit-1397", TYPE_LEN = 2.0;
    const FOCUS_SFX = "camera/camera__camera-auto-focus__mixkit-1436", CHECK_SFX = "ui/ui__modern-click-box-check__mixkit-1120";
    // v3 (2026-10-25): a sound that always plays (keep: the mix never thins it), lined up by its "start", "onset" or
    // "peak" (o.align; else kit/audio/mix.py align_of), cut to o.dur s (a 60 ms fade) when given
    api.cue = (name, t, db, o = {}) => {
      const s = HF.S && HF.S[name];
      window.__CUES = window.__CUES || [];
      window.__CUES.push(Object.assign({ name: s ? s[0] : name, at: Math.round(t * 1000) / 1000, gain_db: db != null ? db : s ? s[1] : -20, keep: true },
        o.align ? { align: o.align } : {}, o.dur ? { dur: Math.round(o.dur * 1000) / 1000 } : {}));
      return api;
    };
    // the music comes UP over a held beat (an exhibit, an explainer, a chapter card): a positive quiet window, which
    // kit/audio/mix.py quiet_env lifts by db dB with ramp s ramps (the owner, 2026-10-25: "The music plays a really
    // important role"); HF.quiet still takes it down
    api.swell = (a, b, db = 6, ramp = 0.5) => {
      window.__QUIET = window.__QUIET || [];
      if (b - a > 0.05) window.__QUIET.push({ a: +a.toFixed(3), b: +b.toFixed(3), depth: +db, ramp });
      return api;
    };
    // text that types on with the typing sound (the Netflix "typed" note); returns the element. The sound lasts as long
    // as the typing (the owner asked for the typing sound: it is kept, never thinned)
    api.typed = (el, t0, text, o = {}) => {
      const cps = o.cps || 38, html = o.html || ((s) => HF.esc(s));
      K.onFrame((t) => { const n = Math.round(clamp((t - t0) * cps, 0, text.length)); const s = text.slice(0, n); if (el._s !== s) { el._s = s; el.innerHTML = html(s); } });
      if (o.sound !== false && text.length) {
        const len = text.length / cps + 0.1;
        for (let k = 0; k * TYPE_LEN < len; k++) api.cue(TYPE_SFX, t0 + k * TYPE_LEN, o.db != null ? o.db : -25, { align: "start", dur: Math.min(TYPE_LEN, len - k * TYPE_LEN) });
      }
      return el;
    };

    // ---- cutaways (kit/film/doc.py: work/broll/bNN.mp4 on the frame grid), full frame over him
    api.broll = (list = DD.broll || []) => {
      list.forEach((b) => {
        const v = document.createElement("video");
        v.id = K.vid("broll");
        v.className = "clip";
        v.src = b.file; v.muted = true; v.playsInline = true;
        v.setAttribute("muted", ""); v.setAttribute("playsinline", "");
        v.dataset.start = b.a.toFixed(4); v.dataset.duration = (b.b - b.a).toFixed(4); v.dataset.mediaStart = "0";
        v.dataset.trackIndex = String(10 + (b.z || 1));
        v.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;object-fit:cover`;
        L.broll.append(v);
        K.show(v, b.a, b.b);
        covers.push([b.a, b.b]);
      });
      return api;
    };

    // ---- name cards (v2, 2026-10-25): the name in condensed caps (Oswald, typed on with the typing sound), a short red
    // bar, the role under it; bottom left inside the safe frame, on a feathered scrim so it reads on any wall
    api.third = (a, b, name, role = "") => {
      const sh = K.el(L.text, `left:0;top:${H - 400}px;width:1150px;height:400px;opacity:0;background:linear-gradient(90deg, rgba(0,0,0,.7) 0%, rgba(0,0,0,.5) 50%, rgba(0,0,0,0) 100%);` +
        "-webkit-mask-image:linear-gradient(180deg, transparent 0%, #000 40%);mask-image:linear-gradient(180deg, transparent 0%, #000 40%)");
      const g = K.el(L.text, `left:120px;top:${H - 290}px;width:1000px;opacity:0`,
        `<div class="dc-bar" style="height:6px;width:0;background:${RED};margin-bottom:18px"></div>` +
        `<div class="dc-name" style="font:600 64px/1 ${OSW};letter-spacing:.03em;text-transform:uppercase;color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.6)"></div>` +
        (role ? `<div class="dc-role" style="margin-top:12px;font:500 32px/1.2 ${INTER};color:${HF.C.ink2};text-shadow:0 2px 12px rgba(0,0,0,.6)">${HF.esc(role)}</div>` : ""));
      g.dataset.group = "third";
      const bar = g.querySelector(".dc-bar"), rl = g.querySelector(".dc-role");
      api.typed(g.querySelector(".dc-name"), a + 0.12, name, { cps: 30 });
      K.onFrame((t) => {
        const v = fadeIO(t, a, b, 0.2, 0.35);
        g.style.opacity = v.toFixed(3); sh.style.opacity = v.toFixed(3);
        g.style.visibility = sh.style.visibility = t >= a && t <= b ? "visible" : "hidden";
        bar.style.width = (ease((t - a) / 0.35) * 84).toFixed(1) + "px";
        if (rl) rl.style.opacity = ease((t - a - 0.12 - name.length / 30) / 0.35).toFixed(3);
      });
      return g;
    };
    api.thirds = (list = DD.thirds || []) => { list.forEach((x) => api.third(x.a, x.b, x.name, x.role)); return api; };

    // ---- chapter cards (v2): black, a small red mono kicker, the title in condensed caps typed on with the typing
    // sound, a slow push; he is off while it is up. `sub` is the kicker ("II · The Awwwards MCP")
    api.chapter = (a, title, sub = "", dur = 2.4) => {
      const b = a + dur;
      const g = K.el(L.card, `left:0;top:0;width:${W}px;height:${H}px;background:#000;opacity:0;display:flex;flex-direction:column;align-items:center;justify-content:center`,
        (sub ? `<div style="margin-bottom:26px;font:500 32px/1 ${JB};letter-spacing:.3em;text-transform:uppercase;color:${RED}">${HF.esc(sub)}</div>` : "") +
        `<div class="dc-ct" style="font:700 132px/1 ${OSW};letter-spacing:.02em;text-transform:uppercase;color:#fff;min-height:132px"></div>`);
      api.typed(g.querySelector(".dc-ct"), a + 0.15, title, { cps: 26 });
      K.onFrame((t) => {                                                      // cut in (a fade showed the held frame
        const v = fadeIO(t, a, b, 0.01, 0.25); g.style.opacity = v.toFixed(3); g.style.visibility = v > 0 ? "visible" : "hidden";   // under it)
        g.style.transform = `scale(${(1 + 0.04 * ease((t - a) / dur)).toFixed(4)})`;
      });
      covers.push([a + 0.05, b - 0.05]);
      return g;
    };

    // ---- the interview camera (v2): keyframes on the zoom of his picture, about his face. keys: [{ t, z, cut, dur }]:
    // at t the zoom goes to z, at once (cut: a punch-cut / zoom-cut) or eased over dur s (a push or pull). Framings:
    // W 1.0, M ~1.15, C ~1.28; never past the track's soft_zoom and x1.3 (OWNER_DEFAULTS §0). Registered after the
    // default one-move-per-shot, so it wins wherever keys exist; window.__speaker reports its zoom.
    api.cam = (keys) => {
      const ks = keys.slice().sort((p, q) => p.t - q.t), capZ = Math.max(1, Math.min(1.3, +(T.soft_zoom || T.max_zoom || 1.3)));
      const zAt = (t) => {
        let z = 1;
        for (const k of ks) {
          if (t < k.t) break;
          z = k.cut ? k.z : z + (k.z - z) * ease((t - k.t) / Math.max(0.01, k.dur || 0.6));
        }
        return clamp(z, 1, capZ);
      };
      api.zAt = zAt;
      if (vid) K.onFrame((t) => {
        const s = shotAt(t);
        if (!s) return;
        vid.style.transformOrigin = `${s.face[0]}px ${s.face[1]}px`;
        vid.style.transform = `scale(${zAt(t).toFixed(5)})`;
      });
      const sp = window.__speaker;
      window.__speaker = (t) => { const r = sp(t); if (r && r.on) { r.zoom = +zAt(t).toFixed(4); r.lens = "doc-cam"; } return r; };
      return api;
    };

    // ---- a filmed screen (v2): the site or capture as an object in the room, the way Netflix shoots a product: a
    // slightly tilted plane, a shallow-focus falloff, grain, a slow dolly; a camera inside it scrolls, pauses and zooms
    // (keys in source px), and marks drawn inside the plane stay on the thing they point at. o: { src | img, srcW,
    // srcH (an img's full height; a video's frame), mediaStart, x, y, w, h (the plane on the page), tilt [rx, ry] deg,
    // keys [{ t, y, z, fx, dur }] (y: the source px at the view's top; z: zoom; fx: the source x to centre) }
    api.screen = (a, b, o = {}) => {
      const g = K.el(L.ex, `left:0;top:0;width:${W}px;height:${H}px;background:${o.bg === false ? "transparent" : o.bg || "#050505"};overflow:hidden`);
      K.show(g, a, b);
      covers.push([a, b]);
      const x = o.x != null ? o.x : 140, y = o.y != null ? o.y : 150, w = o.w || 1100, h = o.h || 690;
      const [rx, ry] = o.tilt || [4, -9];
      const stage = K.el(g, `left:0;top:0;width:${W}px;height:${H}px;perspective:2400px;perspective-origin:${x + w / 2}px ${y + h / 2}px`);
      const plane = K.el(stage, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;overflow:hidden;border-radius:10px;background:#000;` +
        "box-shadow:0 40px 120px rgba(0,0,0,.75), 0 0 0 1px rgba(255,255,255,.06);transform-style:preserve-3d;will-change:transform");
      const s0 = w / o.srcW;
      const world = K.el(plane, `left:0;top:0;width:${o.srcW}px;height:${o.srcH}px;transform-origin:0 0;will-change:transform`);
      if (o.src) world.innerHTML = `<video id="${K.vid("dscr")}" class="clip" src="${o.src}" muted playsinline data-start="${a.toFixed(3)}" data-duration="${(b - a).toFixed(3)}" data-media-start="${(o.mediaStart || 0).toFixed(3)}" data-track-index="${o.track || 6}" style="position:absolute;left:0;top:0;width:${o.srcW}px;height:${o.srcH}px"></video>`;
      else world.innerHTML = `<img src="${o.img}" style="position:absolute;left:0;top:0;width:${o.srcW}px;height:${o.srcH}px" alt="">`;
      // the lens: focus falls off toward the top and bottom edges (a thin band: the owner, 2026-10-25, "you can keep the
      // blur but make sure it won't hide the text"); a soft glass sheen; grain over the whole frame
      const bands = ["top", "bottom"].map((side) => K.el(plane, `left:0;${side}:0;width:${w}px;height:${Math.round(h * (o.dof != null ? o.dof : 0.13))}px;` +
        `backdrop-filter:blur(${o.blur || 3}px);-webkit-backdrop-filter:blur(${o.blur || 3}px);` +
        `-webkit-mask-image:linear-gradient(${side === "top" ? "180deg" : "0deg"}, #000, transparent);mask-image:linear-gradient(${side === "top" ? "180deg" : "0deg"}, #000, transparent)`));
      K.el(plane, `left:0;top:0;width:${w}px;height:${h}px;background:linear-gradient(115deg, rgba(255,255,255,.07) 0%, rgba(255,255,255,0) 38%), radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 62%, rgba(0,0,0,.32) 100%)`);
      // the marks ride above the blur and the sheen (the same camera as the page under them): a highlight is never soft
      const mw = K.el(plane, `left:0;top:0;width:${o.srcW}px;height:${o.srcH}px;transform-origin:0 0;will-change:transform`);
      const marks = K.el(mw, `left:0;top:0;width:${o.srcW}px;height:${o.srcH}px`);
      const mwin = [];
      const gid = "dg" + K.vid("g");
      g.insertAdjacentHTML("beforeend", `<svg width="${W}" height="${H}" style="position:absolute;left:0;top:0;opacity:.13;mix-blend-mode:overlay;pointer-events:none"><filter id="${gid}"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2"/></filter><rect width="${W}" height="${H}" filter="url(#${gid})"/></svg>`);
      const keys = (o.keys || [{ t: a, y: 0, z: 1 }]).slice().sort((p, q) => p.t - q.t);
      const camAt = (t) => {
        let c = { y: keys[0].y || 0, z: keys[0].z || 1, fx: keys[0].fx != null ? keys[0].fx : o.srcW / 2 };
        for (const k of keys) {
          if (t < k.t) break;
          const u = k.cut ? 1 : ease((t - k.t) / Math.max(0.01, k.dur || 0.8));
          c = { y: c.y + ((k.y != null ? k.y : c.y) - c.y) * u, z: c.z + ((k.z || c.z) - c.z) * u, fx: c.fx + ((k.fx != null ? k.fx : c.fx) - c.fx) * u };
        }
        return c;
      };
      const view = (t) => {                                                     // the source -> plane transform at t
        const c = camAt(t), sc = s0 * c.z, vx = w / 2 - c.fx * sc;
        return { sc, tx: Math.min(0, Math.max(w - o.srcW * sc, vx)), ty: -c.y * sc };
      };
      K.onFrame((t) => {
        if (t < a || t > b) return;
        const v = view(t), u = (t - a) / Math.max(0.5, b - a);
        world.style.transform = mw.style.transform = `translate(${v.tx.toFixed(2)}px, ${v.ty.toFixed(2)}px) scale(${v.sc.toFixed(5)})`;
        plane.style.transform = `rotateX(${(rx - 1.5 * u).toFixed(3)}deg) rotateY(${(ry + 3 * u).toFixed(3)}deg) translateZ(${(40 * u).toFixed(1)}px)`;
        const on = Math.max(0, ...mwin.map(([p, q]) => fadeIO(t, p, q, 0.25, 0.25)));   // the blur eases off while a mark is up
        bands.forEach((bd) => { bd.style.opacity = (1 - 0.8 * on).toFixed(3); });
      });
      const sc = { g, plane, world, view };
      // a mark on the thing being pointed at: viewfinder corners that close in, and a typed tag (kind: did | miss | info)
      sc.mark = (t0, t1, r, text = "", kind = "info") => {
        const col = kind === "did" ? GREEN : kind === "miss" ? RED : "#fff";
        mwin.push([t0, t1]);
        const m = K.el(marks, `left:${r[0]}px;top:${r[1]}px;width:${r[2]}px;height:${r[3]}px;opacity:0`);
        const k = Math.max(18, Math.min(r[2], r[3]) * 0.22);
        m.innerHTML = ["0,0", "1,0", "0,1", "1,1"].map((p) => { const [i, j] = p.split(","); return `<div style="position:absolute;${+i ? "right" : "left"}:0;${+j ? "bottom" : "top"}:0;width:${k}px;height:${k}px;` +
          `border-${+i ? "right" : "left"}:6px solid ${col};border-${+j ? "bottom" : "top"}:6px solid ${col}"></div>`; }).join("") +
          (text ? `<div class="dc-tag" style="position:absolute;left:0;top:calc(100% + 18px);padding:10px 18px;background:rgba(0,0,0,.86);border-left:6px solid ${col};font:500 ${Math.round(34 / s0)}px/1.25 ${JB};color:#fff;white-space:nowrap"></div>` : "");
        K.onFrame((t) => {
          const on = t >= t0 && t < t1, u = ease((t - t0) / 0.35);
          m.style.opacity = on ? "1" : "0";
          m.style.transform = `scale(${(1.12 - 0.12 * u).toFixed(4)})`;
        });
        if (text) api.typed(m.querySelector(".dc-tag"), t0 + 0.2, text, { cps: 40 });
        if (kind === "miss") api.cue("hit", t0, -22); else api.cue(FOCUS_SFX, t0, -24, { align: "onset" });   // a focus lock / a thud
        return sc;
      };
      return sc;
    };

    // ---- a typed dossier beside a filmed screen (v2): a kicker, a title, stats, then DID / MISSED lines one by one
    // o: { x, y, w, kicker, title, stats, items: [{ t, kind: "did" | "miss" | "info", text }] }
    api.dossier = (a, b, o = {}) => {
      const g = K.el(L.ex, `left:${o.x != null ? o.x : 1290}px;top:${o.y != null ? o.y : 150}px;width:${o.w || 520}px;opacity:0`);
      K.show(g, a, b); g.style.opacity = "1";
      const kick = K.el(g, `position:relative;font:500 28px/1 ${JB};letter-spacing:.24em;color:${RED};margin-bottom:16px`);
      const ttl = K.el(g, `position:relative;font:700 58px/1.02 ${OSW};text-transform:uppercase;color:#fff;margin-bottom:14px`);
      const st = K.el(g, `position:relative;font:500 30px/1.3 ${JB};color:${HF.C.ink2};margin-bottom:28px`);
      api.typed(kick, a + 0.05, o.kicker || "", { cps: 50, sound: false });
      api.typed(ttl, a + 0.2, o.title || "", { cps: 34 });
      if (o.stats) api.typed(st, a + 0.2 + (o.title || "").length / 34, o.stats, { cps: 50, sound: false });
      (o.items || []).forEach((it) => {
        const col = it.kind === "did" ? GREEN : it.kind === "miss" ? RED : HF.C.ink;
        const row = K.el(g, `position:relative;display:flex;gap:16px;align-items:baseline;margin:0 0 20px;opacity:0`,
          `<span style="font:700 34px/1 ${OSW};color:${col};min-width:118px;flex:none;white-space:nowrap">${it.kind === "did" ? "DID ✓" : it.kind === "miss" ? "MISSED ✕" : ""}</span><span class="dc-it" style="font:500 32px/1.3 ${INTER};color:#fff"></span>`);
        K.show(row, it.t, b); row.style.opacity = "1";
        api.typed(row.querySelector(".dc-it"), it.t + 0.1, it.text, { cps: 45 });
        if (it.kind === "miss") api.cue("hit", it.t, -21); else if (it.kind === "did") api.cue(CHECK_SFX, it.t, -24, { align: "onset" });
      });
      return g;
    };

    // ---- a typed card on black (v2): a field note, a fact, the verdict; lines type one after another
    // lines: [{ text, kind: "kicker" | "big" | "mono" | "body" | "quote", gap, cps }]
    // o.bg "wall" (v3): the case-file wall instead of black: a warm spotlight on dark felt, grain (a long typed card on
    // pure black reads as a dropout for its first second, before the text is up)
    const WALL = "radial-gradient(ellipse 62% 58% at 50% 45%, #2b211b 0%, #15110f 55%, #080707 100%)";
    api.card = (a, b, lines = [], o = {}) => {
      const g = K.el(L.ex, `left:0;top:0;width:${W}px;height:${H}px;background:${o.bg === "wall" ? WALL : o.bg || "#000"};display:flex;flex-direction:column;align-items:${o.align || "center"};justify-content:center;padding:0 200px;box-sizing:border-box`);
      K.show(g, a, b);
      covers.push([a, b]);
      if (o.bg === "wall") {
        const gid = "cg" + K.vid("g");
        g.insertAdjacentHTML("beforeend", `<svg width="${W + 120}" height="${H + 120}" class="cgr" style="position:absolute;left:-60px;top:-60px;opacity:.16;mix-blend-mode:overlay;pointer-events:none"><filter id="${gid}"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2"/></filter><rect width="${W + 120}" height="${H + 120}" filter="url(#${gid})"/></svg>`);
        const gr = g.querySelector(".cgr");
        K.onFrame((t) => { if (t < a || t > b) return; const f = Math.round(t * FPS); gr.style.transform = `translate(${-((f * 37) % 60)}px, ${-((f * 53) % 60)}px)`; });
      }
      const css = { kicker: `font:500 30px/1 ${JB};letter-spacing:.28em;color:${RED};margin-bottom:30px`, big: `font:700 96px/1.04 ${OSW};text-transform:uppercase;color:#fff;margin-bottom:22px`,
        mono: `font:500 40px/1.35 ${JB};color:#fff;background:rgba(255,255,255,.07);padding:14px 24px;margin:10px 0`, body: `font:500 40px/1.3 ${INTER};color:${HF.C.ink2};margin:12px 0`,
        quote: `font:italic 400 72px/1.12 ${SERIF};color:#fff;margin:12px 0` };
      let t = a + (o.lead != null ? o.lead : 0.2);
      lines.forEach((ln) => {
        const e = K.el(g, `position:relative;${css[ln.kind || "body"]};text-align:${o.align === "flex-start" ? "left" : "center"};max-width:1500px`);
        const cps = ln.cps || (ln.kind === "big" ? 28 : ln.kind === "quote" ? 30 : 42);
        const t0 = t;                                                         // (a boxed line stays hidden until it types:
        K.onFrame((tt) => { e.style.visibility = tt >= t0 ? "visible" : "hidden"; });   // no empty grey box before it)
        api.typed(e, t, ln.text, { cps, sound: ln.kind !== "kicker" });
        t += ln.text.length / cps + (ln.gap != null ? ln.gap : 0.35);
      });
      // a wall card settles in as it lands (a felt move: a card that only types reads as frozen), then the slow push
      const settle = (tt) => (o.bg === "wall" ? 1.05 - 0.05 * (1 - Math.pow(1 - clamp((tt - a) / 1.0, 0, 1), 3)) : 1);
      K.onFrame((tt) => { g.style.transform = `scale(${(settle(tt) * (1 + 0.03 * ease((tt - a) / Math.max(0.5, b - a)))).toFixed(4)})`; });
      if (HF.hold) HF.hold(Math.min(t, b - 0.3), b, o.why || "typed card: reading");
      return g;
    };
    // ---- before / after (v3, 2026-10-25: "what all it fixed"): two captures of one place on a filmed plane; the AFTER
    // wipes across the BEFORE behind a red line, each side labelled, then a typed note says what changed.
    // o: { before, after (images of one size), srcW, srcH, view: [x, y, w, h] (the source rect shown; default all),
    //   x, y, w, h (the plane on the page), tilt [rx, ry], wipe: [t0, t1], labels: ["RUN 2", "RUN 3"], note: { t, text, kind } }
    api.compare = (a, b, o = {}) => {
      const g = K.el(L.ex, `left:0;top:0;width:${W}px;height:${H}px;background:${o.bg || "#050505"};overflow:hidden`);
      K.show(g, a, b);
      covers.push([a, b]);
      const [vx, vy, vw, vh] = o.view || [0, 0, o.srcW, o.srcH];
      const w = o.w || 1500, h = o.h || Math.round(w * vh / vw), x = o.x != null ? o.x : (W - w) / 2, y = o.y != null ? o.y : 110;
      const [rx, ry] = o.tilt || [3, -4];
      const stage = K.el(g, `left:0;top:0;width:${W}px;height:${H}px;perspective:2600px;perspective-origin:${x + w / 2}px ${y + h / 2}px`);
      const plane = K.el(stage, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;overflow:hidden;border-radius:8px;background:#000;` +
        "box-shadow:0 40px 120px rgba(0,0,0,.75), 0 0 0 1px rgba(255,255,255,.06);will-change:transform");
      const sc = w / vw;
      const img = (src) => K.el(plane, `left:0;top:0;width:${w}px;height:${h}px;overflow:hidden`,
        `<img src="${src}" alt="" style="position:absolute;left:${-vx * sc}px;top:${-vy * sc}px;width:${o.srcW * sc}px;height:${o.srcH * sc}px">`);
      img(o.before);
      const af = img(o.after);
      const line = K.el(plane, `left:0;top:0;width:6px;height:${h}px;margin-left:-3px;background:${RED};box-shadow:0 0 24px 4px rgba(229,9,20,.55)`);
      const lab = (side) => K.el(g, `left:${side ? x + w - 700 : x}px;top:${y - 58}px;width:700px;text-align:${side ? "right" : "left"};white-space:nowrap;` +
        `font:600 30px/1 ${JB};letter-spacing:.16em;color:${side ? GREEN : HF.C.ink2}`);
      const [w0, w1] = o.wipe || [a + 0.6, a + 1.5];
      const [l0, l1] = o.labels || ["BEFORE", "AFTER"];
      const lb = api.typed(lab(0), a + 0.15, `BEFORE · ${l0}`, { cps: 40, sound: false });
      api.typed(lab(1), w0 + 0.25, `AFTER · ${l1}`, { cps: 40 });
      K.onFrame((t) => {
        if (t < a || t > b) return;
        const p = ease((t - w0) / Math.max(0.1, w1 - w0));               // the AFTER comes in from the right edge
        af.style.clipPath = `inset(0 0 0 ${(100 * (1 - p)).toFixed(3)}%)`;
        line.style.left = (w * (1 - p)).toFixed(1) + "px";
        line.style.opacity = p > 0 && p < 1 ? "1" : "0";
        lb.style.opacity = (1 - 0.6 * p).toFixed(3);
        const u = (t - a) / Math.max(0.5, b - a);
        plane.style.transform = `rotateX(${(rx - 1.2 * u).toFixed(3)}deg) rotateY(${(ry + 2.5 * u).toFixed(3)}deg) scale(${(1 + 0.03 * u).toFixed(4)})`;
      });
      api.cue("whoosh/whoosh__technology-transition-slide__mixkit-3120", w0, -20, { align: "start" });
      if (o.note) {
        const col = o.note.kind === "did" ? GREEN : o.note.kind === "miss" ? RED : "#fff";
        const n = K.el(g, `left:${x}px;top:${y + h + 36}px;width:${w}px;text-align:center;font:600 50px/1.15 ${OSW};letter-spacing:.02em;text-transform:uppercase;color:${col};text-shadow:0 4px 24px rgba(0,0,0,.8)`);
        api.typed(n, o.note.t, o.note.text, { cps: 34 });
        if (o.note.kind === "did") api.cue(CHECK_SFX, o.note.t, -23, { align: "onset" });
      }
      return { g, plane };
    };

    // ---- the explainer (v3, 2026-10-25; the owner: "tell user in Netflix styled animation what is it, what are the
    // features .. What all it fixed ... moving camera to them ... the user must be able to feel not just see it"): a
    // dark evidence wall the camera travels along, led by the red thread that comes from the board. The tool's name
    // slams in on a hit (the score's drop lands there), a definition beat says what the words in it mean, then each
    // feature is a station: its print lit by a spotlight, a number, the name, what it does and what it did in this
    // film's build, typed with the typing sound. It ends pulled back on the whole thread with the one word it fixes.
    // o: { file, name, sub (a line under it), meta, slam (s after a: the hit), print: { img, w, h } (the title print),
    //   define: { t, cols: [[word, text], [word, text]], line }, stations: [{ t (the camera arrives), img | src (+
    //   mediaStart) | imgs: [img, ...], w, h, zoom, origin, num, label, cmd, text, proof, kind: "did" | "info" | "miss",
    //   quote }],
    //   end: { t, kicker, word } }. Times are page seconds; the moves take 0.7 s and end on each t.
    api.explainer = (a, b, o = {}) => {
      const g = K.el(L.card, `left:0;top:0;width:${W}px;height:${H}px;background:#060505;overflow:hidden`);
      K.show(g, a - 1 / FPS, b + 1 / FPS);                                    // a frame over each neighbour: no gap frame
      covers.push([a, b]);
      const ST = o.stations || [], GAP = o.gap || 1500, MV = 0.7, slam = a + (o.slam != null ? o.slam : 0.5);
      // the wall: the title print at (0, 0), the stations to its right, up and down, all pinned on one red thread
      const tp = Object.assign({ w: 980, h: 552 }, o.print || {});
      const P = [{ x: 0, y: 0, w: tp.w, h: tp.h, rot: -1.2, img: tp.img }];
      ST.forEach((s, i) => P.push({ x: (i + 1) * GAP + (o.define ? 360 : 0), y: i % 2 ? 150 : -120, w: s.w || 900, h: s.h || 560, rot: i % 2 ? 1.4 : -1.0, st: s }));
      const X1 = P[P.length - 1].x;
      const stage = K.el(g, `left:0;top:0;width:${W}px;height:${H}px;perspective:1900px;perspective-origin:${W / 2}px ${H / 2}px`);
      const world = K.el(stage, "left:0;top:0;width:10px;height:10px;transform-origin:0 0;transform-style:preserve-3d;will-change:transform");
      // the wall: dark felt (a seeded noise tile, the same on every render) with big soft blotches
      const tile = (() => {
        const c = document.createElement("canvas"); c.width = c.height = 256;
        const x = c.getContext("2d"), im = x.createImageData(256, 256);
        let r = 987654321;
        for (let i = 0; i < im.data.length; i += 4) { r = (r * 16807) % 2147483647; const v = 11 + (r % 13); im.data[i] = v + 3; im.data[i + 1] = v + 1; im.data[i + 2] = v; im.data[i + 3] = 255; }
        x.putImageData(im, 0, 0);
        return c.toDataURL();
      })();
      K.el(world, `left:-4400px;top:-3200px;width:${X1 + 9400}px;height:6400px;background-color:#0d0b0a;background-image:` +
        `radial-gradient(ellipse 1800px 1200px at 30% 45%, rgba(70,44,30,.30), rgba(0,0,0,0)), radial-gradient(ellipse 2200px 1400px at 75% 60%, rgba(60,30,26,.25), rgba(0,0,0,0)), url(${tile});` +
        "background-size:100% 100%, 100% 100%, 256px 256px");
      // the prints (a white border, a pin), the title print first; a station may be a spread of small prints
      const pinAt = (p) => [p.x, p.y - p.h / 2 + 30];
      P.forEach((p, i) => {
        const e = K.el(world, `left:${p.x - p.w / 2}px;top:${p.y - p.h / 2}px;width:${p.w}px;height:${p.h}px;transform:rotate(${p.rot}deg);will-change:filter`);
        const s = p.st || {};
        if (s.imgs) {
          s.imgs.forEach((src, k) => {
            const n = s.imgs.length, fw = p.w * 0.46, fh = fw * 0.75, fx = (k % Math.ceil(n / 2)) * (p.w - fw) / Math.max(1, Math.ceil(n / 2) - 1), fy = k < Math.ceil(n / 2) ? 0 : p.h - fh;
            K.el(e, `left:${fx}px;top:${fy}px;width:${fw}px;height:${fh}px;background:#f3f1ec;padding:10px;box-sizing:border-box;transform:rotate(${((k * 37) % 7) - 3}deg);` +
              "box-shadow:0 18px 34px rgba(0,0,0,.6)", `<img src="${src}" alt="" style="width:100%;height:100%;object-fit:cover;display:block">`);
          });
        } else {
          // a zoom is a bigger box, offset (no transform: the renderer paints a video's frames into the video's own box
          // and ignores a transform on it or on a wrapper, so screen() sizes its video in px the same way)
          const iw = p.w - 32, ih = p.h - 32, z = s.zoom || 1, [ox, oy] = (s.origin || "50% 50%").split(" ").map((v) => parseFloat(v) / 100);
          const box = `position:absolute;left:${(-(iw * z - iw) * ox).toFixed(1)}px;top:${(-(ih * z - ih) * oy).toFixed(1)}px;width:${(iw * z).toFixed(1)}px;height:${(ih * z).toFixed(1)}px;` +
            "object-fit:cover;display:block";
          const media = s.src ? `<video id="${K.vid("xv")}" class="clip" src="${s.src}" muted playsinline data-start="${(s.t - MV - 0.4).toFixed(3)}" data-duration="${(b - s.t + MV + 0.4).toFixed(3)}" ` +
            `data-media-start="${(s.mediaStart || 0).toFixed(3)}" data-track-index="${s.track || 7}" style="${box}"></video>` :
            `<img src="${s.img || p.img}" alt="" style="${box};object-position:${s.pos || "50% 0%"}">`;
          K.el(e, `left:0;top:0;width:${p.w}px;height:${p.h}px;background:#f3f1ec;padding:16px;box-sizing:border-box;box-shadow:0 30px 60px rgba(0,0,0,.65), 0 6px 12px rgba(0,0,0,.4)`,
            `<div style="position:relative;width:100%;height:100%;overflow:hidden">${media}</div>`);
        }
        const [px, py] = pinAt(p);
        K.el(world, `left:${px - 22}px;top:${py - 22}px;width:44px;height:44px;border-radius:50%;background:radial-gradient(circle at 35% 30%, #fff8 0 8%, #d23a2a 22% 60%, #0006 100%);` +
          "box-shadow:6px 10px 10px rgba(0,0,0,.5);z-index:3");
        p.el = e;
      });
      // the thread: in from the left edge (the board's), through every pin, sagging a little; it runs ahead of the camera
      const pts = [[-2700, -1100], ...P.map(pinAt)], dense = [];
      for (let i = 0; i + 1 < pts.length; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[i + 1], mx = (x1 + x2) / 2, my = (y1 + y2) / 2 + Math.hypot(x2 - x1, y2 - y1) * 0.07;
        for (let k = 0; k < 40; k++) { const u = k / 40; dense.push([(1 - u) * (1 - u) * x1 + 2 * u * (1 - u) * mx + u * u * x2, (1 - u) * (1 - u) * y1 + 2 * u * (1 - u) * my + u * u * y2]); }
      }
      dense.push(pts[pts.length - 1]);
      const cum = [0];
      for (let i = 1; i < dense.length; i++) cum.push(cum[i - 1] + Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]));
      const atPin = (k) => cum[Math.min(cum.length - 1, (k + 1) * 40)];          // thread length up to pin k (0 = title)
      const total = cum[cum.length - 1], dpath = dense.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");
      world.insertAdjacentHTML("beforeend", `<svg style="position:absolute;left:0;top:0;overflow:visible;z-index:2" width="10" height="10">` +
        `<path d="${dpath}" stroke="rgba(0,0,0,.5)" stroke-width="12" fill="none" transform="translate(8 14)" class="xs"/>` +
        `<path d="${dpath}" stroke="#c8401f" stroke-width="9" fill="none" class="xs" style="filter:drop-shadow(0 0 7px rgba(229,9,20,.75))"/>` +
        `<path d="${dpath}" stroke="#ff8a5c" stroke-width="3" stroke-dasharray="5 10" fill="none" opacity=".75" class="xh"/></svg>`);
      const thread = [...world.querySelectorAll(".xs")], hi = world.querySelector(".xh");
      // the camera: beats (where it is when), each reached by a 0.7 s move; a slow drift while it holds
      const beats = [{ t: a, x: -1500, y: -300, s: 0.8, yaw: -12, pin: -1 }, { t: slam, x: 0, y: 120, s: 1.04, yaw: 0, pin: 0, title: true }];
      if (o.define) beats.push({ t: o.define.t, x: -400, y: 10, s: 1.0, yaw: 3, pin: 0 });
      ST.forEach((s, i) => beats.push({ t: s.t, x: P[i + 1].x - 400, y: P[i + 1].y + 10, s: 1.0, yaw: i % 2 ? -4 : 4, pin: i + 1 }));
      if (o.end) beats.push({ t: o.end.t, x: X1 / 2, y: 40, s: Math.min(0.42, (W - 300) / (X1 + 1200)), yaw: 0, pin: P.length - 1, end: true });
      const smooth = (x) => { x = clamp(x, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
      const mStart = (j) => (j === 1 ? a : beats[j].t - MV);                  // the move into beat j starts here (the
      const camAt = (t) => {                                                  // first one, the rush, from a)
        let j = 0;
        for (let q = 1; q < beats.length; q++) if (t >= mStart(q)) j = q;
        const N = beats[j];
        if (j === 0 || t >= N.t) return Object.assign({}, N, { v: 0, hold: Math.max(0, t - N.t) });
        const B = beats[j - 1], m0 = mStart(j), u = clamp((t - m0) / Math.max(0.01, N.t - m0), 0, 1);
        const e = j === 1 ? 1 - Math.pow(1 - u, 3) : smooth(u), L2 = (p, q) => p + (q - p) * e;
        return { x: L2(B.x, N.x), y: L2(B.y, N.y), s: Math.exp(L2(Math.log(B.s), Math.log(N.s))), yaw: L2(B.yaw, N.yaw), v: Math.sin(Math.PI * u), hold: -1, from: B, to: N, u };
      };
      const thAt = (t) => {                                                   // the thread's drawn length: it runs ahead
        const c = camAt(t);                                                    // of the camera to the next pin
        if (c.hold >= 0) return atPin(c.pin) + 1;
        return atPin(c.from.pin) + (atPin(c.to.pin) - atPin(c.from.pin)) * clamp(c.u * 1.35, 0, 1);
      };
      // depth: dust in three layers that drift and slide against the wall
      const dust = K.el(g, `left:0;top:0;width:${W}px;height:${H}px`);
      const motes = [...Array(34)].map((_, i) => {
        const d = 0.25 + ((i * 7919) % 100) / 100 * 1.6, r = 2 + d * 4;
        const e = K.el(dust, `left:0;top:0;width:${r * 2}px;height:${r * 2}px;border-radius:50%;background:radial-gradient(circle, rgba(255,236,214,.9), rgba(255,236,214,0) 70%);` +
          `opacity:${(0.12 + 0.25 * ((i * 31) % 10) / 10).toFixed(2)};filter:blur(${(d > 1.2 ? 2.5 : 0.6).toFixed(1)}px)`);
        return { e, d, x0: (i * 5531) % W, y0: (i * 3373) % H, r };
      });
      const light = K.el(g, `left:0;top:0;width:${W}px;height:${H}px`);
      const flash = K.el(g, `left:0;top:0;width:${W}px;height:${H}px;background:#fff;opacity:0`);
      const gid = "xg" + K.vid("g");
      g.insertAdjacentHTML("beforeend", `<svg width="${W + 120}" height="${H + 120}" class="xgr" style="position:absolute;left:-60px;top:-60px;opacity:.14;mix-blend-mode:overlay;pointer-events:none"><filter id="${gid}"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2"/></filter><rect width="${W + 120}" height="${H + 120}" filter="url(#${gid})"/></svg>`);
      const grain = g.querySelector(".xgr");
      // ---- the type over it (screen space, crisp): the title, the definitions, each station's card, the end word; a dark
      // scrim under the text column while a definition or a station is up (the thread and the dust fall away behind it)
      const scrim = K.el(g, `left:0;top:0;width:${W}px;height:${H}px;opacity:0;background:linear-gradient(90deg, rgba(5,4,4,.9) 0%, rgba(5,4,4,.78) 30%, rgba(5,4,4,.35) 42%, rgba(5,4,4,0) 50%)`);
      const T = K.el(g, `left:0;top:0;width:${W}px;height:${H}px`);
      const panel = (t0, t1, css = "") => { const e = K.el(T, `opacity:0;${css}`); K.onFrame((t) => { const v = fadeIO(t, t0, t1, 0.12, 0.2); e.style.opacity = v.toFixed(3); e.style.visibility = v > 0 ? "visible" : "hidden"; }); return e; };
      const line = (par, css, text, t0, cps, sound = true) => api.typed(K.el(par, `position:relative;${css}`), t0, text, { cps, sound });
      const nextT = (t) => { const n = beats.find((x) => x.t > t + 0.01); return n ? n.t - MV + 0.08 : b; };
      const c0 = [...(o.define ? [o.define.t] : []), ...ST.map((s) => s.t)], cards = c0.length ? [[c0[0] - 0.2, nextT(c0[c0.length - 1]) + 0.15]] : [];
      K.onFrame((t) => { const v = Math.max(0, ...cards.map(([p, q]) => fadeIO(t, p, q, 0.3, 0.3))); scrim.style.opacity = v.toFixed(3); });
      const shakes = [], hits = [slam];
      // the title: the kicker, the name slammed in, a red rule, the meta line
      {
        const p = panel(slam - 0.3, nextT(slam), `left:0;top:${H / 2 - 120}px;width:${W}px;text-align:center`);
        line(p, `font:500 32px/1 ${JB};letter-spacing:.32em;color:${RED};margin-bottom:30px`, o.file || "", slam - 0.3, 60, false);
        const nm = K.el(p, `position:relative;display:inline-block;font:700 ${o.nameSize || 200}px/0.95 ${OSW};letter-spacing:.01em;text-transform:uppercase;color:#fff;text-shadow:0 10px 50px rgba(0,0,0,.85)`, HF.esc(o.name || ""));
        const rule = K.el(p, `position:relative;margin:28px auto 26px;height:8px;width:0;background:${RED}`);
        let tm = slam + 0.45;
        if (o.sub) { line(p, `font:600 48px/1.2 ${INTER};color:#fff;margin-bottom:18px;text-shadow:0 4px 24px rgba(0,0,0,.85)`, o.sub, tm, 52, true); tm += o.sub.length / 52 + 0.15; }
        if (o.meta) line(p, `font:500 34px/1.3 ${JB};letter-spacing:.14em;color:${HF.C.ink2}`, o.meta, tm, 46, true);
        K.onFrame((t) => {
          const u = clamp((t - slam) / 0.24, 0, 1);
          nm.style.opacity = t >= slam ? "1" : "0";
          nm.style.transform = `scale(${(1.22 - 0.22 * (1 - Math.pow(1 - u, 3))).toFixed(4)})`;
          rule.style.width = (ease((t - slam - 0.12) / 0.4) * 420).toFixed(1) + "px";
        });
        shakes.push(slam);
      }
      // the definitions: two columns (word, what it means), then the line that ties them
      if (o.define) {
        const d = o.define, t1 = nextT(d.t);
        const p = panel(d.t, t1, `left:120px;top:250px;width:640px`);
        let tt = d.t + 0.05;
        (d.cols || []).forEach(([wd, txt]) => {
          const c = K.el(p, "position:relative;margin-bottom:46px");
          line(c, `font:700 84px/1 ${OSW};text-transform:uppercase;color:#fff`, wd, tt, 30);
          K.el(c, `position:relative;margin:14px 0 14px;height:6px;width:84px;background:${RED}`);
          line(c, `font:500 42px/1.22 ${INTER};color:#e8e3da`, txt, tt + wd.length / 30 + 0.08, 52);
          tt += wd.length / 30 + txt.length / 52 + 0.32;
        });
        if (d.line) line(p, `font:600 44px/1.2 ${INTER};color:#fff;border-left:6px solid ${RED};padding-left:22px`, d.line, tt, 50);
      }
      // the stations
      ST.forEach((s, i) => {
        const t1 = nextT(s.t), col = s.kind === "miss" ? RED : s.kind === "info" ? "#fff" : GREEN;
        const p = panel(s.t - 0.08, t1, `left:120px;top:${s.top || 236}px;width:${s.width || 640}px`);
        line(p, `font:500 32px/1 ${JB};letter-spacing:.2em;color:${RED};margin-bottom:18px`, `${s.num || String(i + 1).padStart(2, "0")} / ${String(ST.length).padStart(2, "0")}`, s.t - 0.05, 60, false);
        line(p, `font:700 ${s.size || 112}px/0.98 ${OSW};text-transform:uppercase;color:#fff;margin-bottom:20px`, s.label || "", s.t, 30);
        let tt = s.t + (s.label || "").length / 30 + 0.06;
        if (s.cmd) { line(p, `display:inline-block;font:500 32px/1 ${JB};color:#fff;background:rgba(255,255,255,.08);border-left:6px solid ${RED};padding:12px 18px;margin-bottom:24px`, s.cmd, tt, 60, false); tt += s.cmd.length / 60 + 0.04; }
        if (s.text) { line(p, `font:500 44px/1.22 ${INTER};color:#ece8e0;margin-bottom:22px`, s.text, tt, 52); tt += s.text.length / 52 + 0.12; }
        if (s.proof) {
          line(p, `font:600 34px/1.3 ${JB};color:${col}`, (s.kind === "did" ? "✓ " : s.kind === "miss" ? "✕ " : "") + s.proof, tt, 46, false);
          api.cue("hit", tt, -24);
        }
        if (s.quote) line(p, `font:italic 400 58px/1.12 ${SERIF};color:#fff;margin-top:26px`, s.quote, s.quoteT || tt + (s.proof || "").length / 46 + 0.15, 34);
        api.cue("whoosh/whoosh__cinematic-whoosh-fast-transition__mixkit-1492", s.t - 0.12, -25, { align: "peak" });
      });
      // the end: pulled back on the whole thread, the one word it fixes
      if (o.end) {
        const e = o.end, p = panel(e.t + 0.15, b + 0.05, `left:0;top:${H / 2 - 170}px;width:${W}px;text-align:center`);
        K.el(p, `position:absolute;left:${W / 2 - 1000}px;top:-170px;width:2000px;height:640px;background:radial-gradient(ellipse at 50% 50%, rgba(0,0,0,.9) 0%, rgba(0,0,0,.75) 40%, rgba(0,0,0,0) 72%)`);
        line(p, `font:500 40px/1 ${JB};letter-spacing:.32em;color:${RED};margin-bottom:24px`, e.kicker || "", e.t + 0.15, 50, false);
        const wd = K.el(p, `position:relative;font:700 ${e.size || 240}px/0.9 ${OSW};text-transform:uppercase;color:#fff;text-shadow:0 10px 60px rgba(0,0,0,.9)`, HF.esc(e.word || ""));
        const tw = e.t + 0.15 + (e.kicker || "").length / 50 + 0.12;
        K.onFrame((t) => { const u = clamp((t - tw) / 0.22, 0, 1); wd.style.opacity = t >= tw ? "1" : "0"; wd.style.transform = `scale(${(1.25 - 0.25 * (1 - Math.pow(1 - u, 3))).toFixed(4)})`; });
        shakes.push(tw); hits.push(tw);
        api.cue("impact/impact__cinematic-whoosh-deep-impact__mixkit-1143", tw, -15, { align: "peak" });
        if (HF.hold) HF.hold(tw + 0.2, b, "explainer: the word it fixes");
      }
      api.cue("whoosh/whoosh__cinematic-tunnel-reverb-woosh__mixkit-1486", a + 0.18, -17, { align: "peak" });
      api.cue("impact/impact__big-cinematic-impact__mixkit-788", slam, -13, { align: "peak" });
      // every frame: the camera, a shake on the hits, the thread, focus and light on the print being looked at
      K.onFrame((t) => {
        if (t < a - 1.5 / FPS || t > b + 1.5 / FPS) return;                   // (the overlap frames are drawn too)
        const c = camAt(t), dr = c.hold > 0 ? Math.min(c.hold, 3) : 0;
        let sx = 0, sy = 0;
        shakes.forEach((h) => { const q = t - h; if (q >= 0 && q < 0.45) { const k = 14 * Math.exp(-q * 9); sx += k * Math.sin(q * 71); sy += k * 0.7 * Math.cos(q * 53); } });
        const s = c.s * (1 + 0.012 * dr), pitch = c.end ? 16 : 9;
        world.style.transform = `translate3d(${(W / 2 + sx).toFixed(2)}px, ${(H / 2 + sy).toFixed(2)}px, 0) rotateX(${pitch}deg) rotateY(${c.yaw.toFixed(3)}deg) scale(${s.toFixed(5)}) translate(${(-c.x - dr * 6).toFixed(2)}px, ${(-c.y).toFixed(2)}px)`;
        const mb = c.v > 0.15 ? c.v * 1.8 : 0;                                // a little motion blur while it travels
        const L0 = thAt(t);
        thread.forEach((pth) => { pth.style.strokeDasharray = `${L0.toFixed(1)} ${total + 10}`; });
        let n = 1;                                                            // the dashed highlight: only as far as it's drawn
        while (n < dense.length && cum[n] <= L0) n++;
        if (hi._n !== n) { hi._n = n; hi.setAttribute("d", dense.slice(0, n).map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("")); }
        // focus: the print the camera is on (or going to) is lit and sharp, the rest dim and soft
        const fpin = c.hold >= 0 ? c.pin : (c.u < 0.5 ? c.from.pin : c.to.pin);
        P.forEach((p, i) => {
          const on = i === fpin, tit = i === 0 && (c.title || (c.to && c.to.title)), fin = c.end || (c.to && c.to.end);
          const [br, bl] = tit ? [0.3, 4] : fin ? [0.5, 1] : on ? [1, 0] : [0.38, 2.5];
          p.el.style.filter = br === 1 && bl + mb < 0.05 ? "none" : `brightness(${br}) blur(${(bl + mb).toFixed(2)}px)`;
        });
        // the light: a soft spot where the camera looks, the edges falling away
        light.style.background = `radial-gradient(ellipse 62% 70% at ${c.title ? 50 : c.end ? 50 : 66}% 50%, rgba(0,0,0,0) 0%, rgba(0,0,0,.28) 55%, rgba(0,0,0,.72) 100%)`;
        motes.forEach((m) => {
          const px = ((m.x0 - c.x * m.d * 0.35 + t * 9 * m.d) % W + W) % W, py = ((m.y0 - c.y * m.d * 0.3 - t * 5) % H + H) % H;
          m.e.style.transform = `translate(${px.toFixed(1)}px, ${py.toFixed(1)}px)`;
        });
        let fl = 0;
        hits.forEach((h) => { const q = t - h; if (q >= 0 && q < 0.16) fl = Math.max(fl, 0.42 * (1 - q / 0.16)); });
        const q0 = t - a; if (q0 >= 0 && q0 < 0.2) fl = Math.max(fl, 0.5 * (1 - q0 / 0.2));
        flash.style.opacity = fl.toFixed(3);
        const f = Math.round(t * FPS);
        grain.style.transform = `translate(${-((f * 37) % 60)}px, ${-((f * 53) % 60)}px)`;
      });
      return { g, world, beats, P };
    };

    api.chapters = (list = DD.chapters || []) => { list.forEach((c) => api.chapter(c.a, c.title, c.sub, c.dur)); return api; };

    // ---- time stamps: "DAY 1 · 23:10", typed on at the top left
    api.stamp = (a, text, dur = 3.0) => {
      const b = a + dur;
      const g = K.el(L.text, `left:120px;top:110px;opacity:0;font:500 34px/1 ${JB};letter-spacing:.16em;color:${HF.C.ink};text-shadow:0 2px 12px rgba(0,0,0,.7)`, "");
      g.dataset.group = "stamp";
      K.onFrame((t) => {
        const n = Math.round(clamp((t - a) / 0.6, 0, 1) * text.length);
        g.textContent = text.slice(0, n);
        g.style.opacity = fadeIO(t, a, b, 0.05, 0.4).toFixed(3);
        g.style.visibility = t >= a && t <= b ? "visible" : "hidden";
      });
      return g;
    };
    api.stamps = (list = DD.stamps || []) => { list.forEach((s) => api.stamp(s.a, s.text, s.dur)); return api; };

    // ---- letterbox: thin 2.39:1 bars, eased in and out over each span
    api.letterbox = (spans = DD.letterbox || []) => {
      const bar = Math.round((H - W / 2.39) / 2);
      const top = K.el(L.box, `left:0;top:0;width:${W}px;height:${bar}px;background:#000;transform-origin:top`);
      const bot = K.el(L.box, `left:0;top:${H - bar}px;width:${W}px;height:${bar}px;background:#000;transform-origin:bottom`);
      K.onFrame((t) => {
        const v = Math.max(0, ...spans.map(([a, b]) => fadeIO(t, a, b, 0.8, 0.8)));
        top.style.transform = bot.style.transform = `scaleY(${v.toFixed(4)})`;
      });
      return api;
    };

    // ---- subtitles: one quiet line at the bottom, the spoken words (D.doc.subtitles = the cut's caption groups)
    api.subtitles = (caps = DD.subtitles || []) => {
      const g = K.el(L.text, `left:${W / 2 - 800}px;width:1600px;top:${H - 150}px;text-align:center;font:500 40px/1.3 ${INTER};color:#fff;` +
        "text-shadow:0 2px 6px rgba(0,0,0,.85),0 0 22px rgba(0,0,0,.6)", "", "hf-abs cap");
      K.onFrame((t) => {
        const c = caps.find((x) => t >= x.t && t < x.e);
        const txt = c ? c.text : "";
        if (g.textContent !== txt) g.textContent = txt;
        g.style.visibility = txt ? "visible" : "hidden";
      });
      return api;
    };

    // ---- the results board: a title and rows that land one by one (a blind test's answer)
    api.results = (a, b, o2 = {}) => {
      const rows = o2.rows || [];
      const g = K.el(L.card, `left:${W / 2 - 620}px;top:${H / 2 - 90 - rows.length * 48}px;width:1240px;opacity:0;padding:56px 64px;` +
        `background:${HF.C.card};box-shadow:${HF.C.shadow};border:1px solid ${HF.C.line};border-radius:6px`,
        `<div style="font:400 72px/1.05 ${SERIF};color:${HF.C.ink};margin-bottom:28px">${HF.esc(o2.title || "")}</div>` +
        rows.map(([l, v, good]) => `<div class="dc-row" style="display:flex;justify-content:space-between;align-items:baseline;padding:18px 0;border-top:1px solid ${HF.C.line};opacity:0">` +
          `<span style="font:500 38px/1.2 ${INTER};color:${HF.C.text}">${HF.esc(l)}</span>` +
          `<span style="font:700 44px/1 ${JB};color:${good === true ? HF.C.ok : good === false ? HF.C.bad : HF.C.ink}">${HF.esc(v)}</span></div>`).join(""));
      g.dataset.group = "results";
      const rs = [...g.querySelectorAll(".dc-row")];
      const per = Math.min(0.9, (b - a - 1.2) / Math.max(1, rs.length));
      K.onFrame((t) => {
        const v = fadeIO(t, a, b, 0.5, 0.5);
        g.style.opacity = v.toFixed(3); g.style.visibility = v > 0 ? "visible" : "hidden";
        rs.forEach((r, k) => { r.style.opacity = ease((t - a - 0.6 - k * per) / 0.35).toFixed(3); });
      });
      covers.push([a + 0.3, b - 0.3]);
      return g;
    };

    api.all = () => {
      api.broll(); api.letterbox(); api.thirds(); api.stamps(); api.chapters(); api.subtitles();
      if (DD.results) api.results(DD.results.a, DD.results.b, DD.results);
      return api;
    };
    return api;
  };
})(typeof window !== "undefined" ? window : globalThis);
