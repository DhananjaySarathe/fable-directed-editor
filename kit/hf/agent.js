/* kit/hf/agent.js: an AI agent's UI, animated, for Reels where the owner wants to SEE the agent work (2026-10-10:
 * "where is the UI? show some kind of animation over there... take the whole screen for that, or a split screen").
 * Dark glass, generic chrome (no product logos: platform names are plain text with a letter tile), text >= 40 px.
 *
 *   const A = HF.agent(S, { colors });          // after HF.reel
 *   A.panel(par, x, y, w, h, { title, live, avatar }) -> { p, body }   a dark app panel; avatar = html (a real mark) or the orb
 *   A.inbox(par, x, y, w, { title, max })        -> { panel, pre(rows), row(t, { title, sub, tag, kind }), title(text, t), clear(t) }
 *   A.chat(par, x, y, w, h, { name, sub })       -> { me(text, t), them(text, t), file(name, meta, t), send(text, t0, t1) }
 *   A.connect(par, x, y, w, names, { title })    -> { set(i, t) }     "Connect" -> "✓ Connected" on its word
 *   A.flood(par, t0, t1, { n, cols, top })       job cards popping in, each stamped APPLIED (one sound for the run)
 *   A.toast(par, y, title, sub, t, until, kind)  a restriction toast (red by default)
 *   A.limits(par, x, y, w, names, { title })     -> { set(i, v, t) }  per-site daily limit rows, a bar fills to v/10
 *   A.counter(par, x, y, size, { color, suffix }) -> { run(from, to, t0, dur) }   a number that counts on its word
 *   A.week(par, x, y, w, h, { title })           -> { add(day, label, t) }   Mon-Fri, interview blocks drop in
 *   A.title(par, x, y, html, t, until, { size }) big kinetic headline (Montserrat 900)
 * Everything is a pure function of timeline time (fromTo / K.onFrame), so any frame seeks exactly.
 */
(function (root) {
  const HF = root.HF || (root.HF = {});
  const CSS = `
    .ag-p { position: absolute; border-radius: 40px; background: rgba(19,19,27,.94); overflow: hidden;
      box-shadow: 0 40px 100px rgba(0,0,0,.55), inset 0 0 0 1.5px rgba(255,255,255,.08); }
    .ag-h { position: absolute; left: 0; top: 0; right: 0; height: 104px; display: flex; align-items: center; gap: 18px; padding: 0 34px;
      border-bottom: 1.5px solid rgba(255,255,255,.07); font: 800 42px/1 Inter, sans-serif; color: #f4f4f6; white-space: nowrap; }
    .ag-live { margin-left: auto; font: 600 30px/1 JBMono, monospace; letter-spacing: .12em; }
    .ag-row { position: absolute; left: 22px; right: 22px; height: 112px; border-radius: 26px; display: flex; align-items: center; gap: 22px;
      padding: 0 24px; background: rgba(255,255,255,.04); font-family: Inter, sans-serif; color: #f4f4f6; white-space: nowrap; }
    .ag-tile { width: 68px; height: 68px; border-radius: 18px; flex: none; display: flex; align-items: center; justify-content: center;
      font: 900 36px/1 Inter, sans-serif; color: #0b0b12; }
    .ag-t1 { font: 800 40px/1.1 Inter, sans-serif; }
    .ag-t2 { font: 600 36px/1.2 Inter, sans-serif; color: rgba(244,244,246,.6); }
    .ag-tag { margin-left: auto; padding: 14px 22px; border-radius: 999px; font: 800 32px/1 Inter, sans-serif; white-space: nowrap; }
    .ag-b { position: absolute; max-width: 74%; padding: 22px 30px; border-radius: 34px; font: 600 42px/1.25 Inter, sans-serif; }
    .ag-card { position: absolute; border-radius: 26px; background: #1d1d28; color: #f4f4f6; box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.08); overflow: hidden; }
    .ag-stamp { position: absolute; padding: 10px 20px; border: 5px solid; border-radius: 14px; font: 900 40px/1 Montserrat, Inter, sans-serif;
      letter-spacing: .04em; transform: rotate(-9deg); white-space: nowrap; }
    .ag-title { position: absolute; font: 900 92px/1.04 Montserrat, Inter, sans-serif; letter-spacing: -0.02em; color: #fff; }
  `;
  HF.agent = function (S, o = {}) {
    const { K, tl, Q, E, el, land, leave } = S;
    if (!document.getElementById("ag-css")) { const st = document.createElement("style"); st.id = "ag-css"; st.textContent = CSS; document.head.append(st); }
    const C = Object.assign({ go: "#3ddc84", stop: "#ff4757", warn: "#ffd166", blue: "#4c8dff", me: "#2f6bff", ink: "#f4f4f6",
      dim: "rgba(244,244,246,.6)", tiles: { LinkedIn: "#4c8dff", Wellfound: "#f4f4f6", Naukri: "#5ea8ff", Indeed: "#8aa8ff", "Cold mail": "#ff9b5e" } }, o.colors || {});
    const A = { C };
    const esc = (s) => HF.esc(String(s));
    const tile = (name, col) => `<span class="ag-tile" style="background:${col || C.tiles[name] || "#9aa0ff"}">${esc(name[0])}</span>`;
    const show = (e, t, from, sfx = null, db = -24) => land(e, t, { from: from || { y: 30, scale: 0.94, blur: 8 }, spring: "snappy", sfx, db });

    A.panel = (par, x, y, w, h, z = {}) => {
      const p = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px`, "", "ag-p");
      p.dataset.over = "1";
      // z.avatar: html for the contact picture (a real product's mark, e.g. from kit/web/capture.mjs); default the orb
      el(p, "", `${z.avatar || S.orbI(40)}<span>${esc(z.title || "Instinct")}</span>${z.live === false ? "" : `<span class="ag-live" data-decor="1" style="color:${C.go}">● LIVE</span>`}`, "ag-h");
      const body = el(p, `left:0;top:104px;width:${w}px;height:${h - 104}px;overflow:hidden`);
      return { p, body };
    };

    // (HF.E.in is the entrance/move ease, decelerating; HF.E.out is the exit ease, accelerating)
    // ---------------------------------------------------------------- an inbox that fills: newest row on top, the rest slide down
    A.inbox = (par, x, y, w, z = {}) => {
      const max = z.max || 6, rowH = 126, h = 104 + 24 + max * rowH;
      const P = A.panel(par, x, y, w, h, { title: z.title || "Inbox", live: false });
      const head = el(P.p, "position:absolute;right:34px;top:32px;font:800 38px/1 Inter;color:rgba(244,244,246,.6);white-space:nowrap", "");
      const rows = [];
      const api = { panel: P.p };
      api.title = (text, t, col) => { tl.set(head, { textContent: text, color: col || C.dim }, Q(t)); tl.set(head, { textContent: "" }, 0); };
      api.row = (t, r) => {
        const go = r.kind === "go";
        const e = el(P.body, `top:24px`, `${tile(r.tile || r.title, go ? C.go : "#2a2a36")}<div><div class="ag-t1">${esc(r.title)}</div>${r.sub ? `<div class="ag-t2">${esc(r.sub)}</div>` : ""}</div>` +
          `<span class="ag-tag" style="background:${go ? "rgba(61,220,132,.18)" : "rgba(255,255,255,.07)"};color:${go ? C.go : "rgba(244,244,246,.55)"}">${esc(r.tag || (go ? "Interview" : "No reply"))}</span>`, "ag-row");
        if (!go) e.querySelector(".ag-tile").style.color = "rgba(244,244,246,.6)";
        // rows slide by `top` (their entrance tweens own x/y/scale)
        rows.forEach((q, k) => tl.to(q, { top: 24 + (rows.length - k) * rowH, duration: 0.22, ease: E.in, immediateRender: false }, Q(t)));
        rows.forEach((q, k) => { if (rows.length - k >= max) tl.to(q, { opacity: 0, duration: 0.15, immediateRender: false }, Q(t)); });
        rows.push(e);
        land(e, t, { from: { y: -60, scale: 0.96, blur: 6 }, spring: "snappy", sfx: r.sfx === undefined ? null : r.sfx, db: r.db || -24 });
        return e;
      };
      // rows already there on frame 1 (oldest first), placed directly: no tweens at time 0 (a seek to 0 doesn't render them)
      api.pre = (list) => list.forEach((r, k) => {
        const e = el(P.body, `top:${24 + (list.length - 1 - k) * rowH}px`, `${tile(r.tile || r.title, "#2a2a36")}<div><div class="ag-t1">${esc(r.title)}</div>${r.sub ? `<div class="ag-t2">${esc(r.sub)}</div>` : ""}</div>` +
          `<span class="ag-tag" style="background:rgba(255,255,255,.07);color:rgba(244,244,246,.55)">${esc(r.tag || "No reply")}</span>`, "ag-row");
        e.querySelector(".ag-tile").style.color = "rgba(244,244,246,.6)";
        rows.push(e);
      });
      api.clear = (t) => { rows.forEach((q) => tl.to(q, { opacity: 0, x: -60, duration: 0.2, ease: E.out, immediateRender: false }, Q(t))); rows.length = 0; };
      return api;
    };

    // ---------------------------------------------------------------- a chat thread with the agent (generic messenger chrome)
    A.chat = (par, x, y, w, h, z = {}) => {
      const P = A.panel(par, x, y, w, h, { title: z.name || "Instinct", live: z.live, avatar: z.avatar });
      const inner = el(P.body, `left:0;top:0;width:${w}px;height:4000px`);
      const barH = z.input === false ? 0 : 118;
      const room = h - 104 - barH - 20;
      let cur = 26, scroll = 0;
      const place = (bh, t) => {
        const top = cur; cur += bh + 18;
        if (cur > room + scroll) { scroll = cur - room; tl.to(inner, { y: -scroll, duration: 0.3, ease: E.in, immediateRender: false }, Q(t)); }
        return top;
      };
      const lines = (text, maxW) => Math.max(1, Math.ceil((String(text).length * 23.5) / (maxW - 60)));
      const bubble = (text, t, me, extra = "") => {
        const maxW = w * 0.74, bh = lines(text, maxW) * 52 + 44, top = place(bh, t);
        const e = el(inner, `top:${top}px;${me ? "right:26px" : "left:26px"};background:${me ? C.me : "#262633"};color:#fff;${extra}`, esc(text), "ag-b");
        land(e, t, { from: { y: 26, scale: 0.9, blur: 4 }, spring: "snappy", sfx: null });
        return e;
      };
      let input = null, ty = null;
      if (barH) {
        input = el(P.p, `left:22px;right:22px;bottom:22px;height:${barH - 30}px;border-radius:999px;background:rgba(255,255,255,.07);` +
          "display:flex;align-items:center;padding:0 34px;font:600 40px/1 Inter;color:#fff;white-space:nowrap",
          `<span class="ty"></span><span class="ph" style="color:rgba(244,244,246,.38)">Message</span><span style="margin-left:auto;width:62px;height:62px;border-radius:50%;background:${C.me};display:flex;align-items:center;justify-content:center"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg></span>`);
        ty = input.querySelector(".ty");
      }
      const api = { panel: P.p };
      api.me = (text, t) => bubble(text, t, true);
      api.them = (text, t) => bubble(text, t, false);
      api.file = (name, meta, t, ic = "file") => {
        const bh = 128, top = place(bh, t);
        const e = el(inner, `top:${top}px;right:26px;width:${Math.min(620, w * 0.72)}px;height:${bh}px;border-radius:30px;background:${C.me};display:flex;align-items:center;gap:22px;padding:0 26px;color:#fff;white-space:nowrap`,
          `<span style="width:80px;height:80px;border-radius:20px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;flex:none">${HF.icon(ic, 44, "#fff", 2.4)}</span>` +
          `<div><div style="font:800 40px/1.1 Inter">${esc(name)}</div><div style="font:600 36px/1.3 Inter;color:rgba(255,255,255,.75)">${esc(meta)}</div></div>`);
        land(e, t, { from: { y: -260, x: 80, scale: 0.8, rotation: 6, blur: 8 }, spring: "thrown", sfx: "pop", db: -20 });
        return e;
      };
      // types into the input bar from t0, sends at t1 (the bubble lands, the bar clears)
      api.send = (text, t0, t1) => {
        if (!ty) return api.me(text, t1);
        const ph = input.querySelector(".ph");
        tl.set(ph, { opacity: 0 }, Q(t0));
        K.typeText(ty, text, t0, Math.max(6, text.length / Math.max(0.15, t1 - t0 - 0.08)), false);
        tl.set(ty, { opacity: 0 }, Q(t1)); tl.set(ph, { opacity: 1 }, Q(t1));
        K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", t1 - 0.02, -20);
        return api.me(text, t1);
      };
      return api;
    };

    // ---------------------------------------------------------------- connect the sites (one row per platform)
    A.connect = (par, x, y, w, names, z = {}) => {
      const rowH = 132, h = 104 + 24 + names.length * rowH;
      const P = A.panel(par, x, y, w, h, { title: z.title || "Instinct · setup", live: false });
      const btns = names.map((nm, k) => {
        const r = el(P.body, `top:${24 + k * rowH}px`, `${tile(nm)}<div class="ag-t1">${esc(nm)}</div>` +
          `<span class="ag-tag" style="background:transparent;box-shadow:inset 0 0 0 2.5px rgba(244,244,246,.3);color:${C.ink}">Connect</span>`, "ag-row");
        return r.querySelector(".ag-tag");
      });
      return { panel: P.p, set(i, t) {
        const b = btns[i];
        tl.set(b, { textContent: "✓ Connected", background: "rgba(61,220,132,.18)", boxShadow: "none", color: C.go }, Q(t));
        tl.fromTo(b, { scale: 1.25 }, { scale: 1, duration: 0.3, ease: HF.spring(HF.SPRING.thrown).ease, immediateRender: false }, Q(t));
        tl.set(b, { textContent: "Connect" }, 0);
        K.sfx("check", t, -22);
      } };
    };

    // ---------------------------------------------------------------- applications flooding out (the "Apply." drop)
    A.flood = (par, t0, t1, z = {}) => {
      const roles = z.roles || ["Product Designer", "Frontend Dev", "Data Analyst", "SDE II", "UX Researcher", "Backend Eng", "PM Intern", "ML Engineer",
        "QA Engineer", "Growth Analyst", "iOS Dev", "DevOps", "Content Lead", "Full-stack", "Design Intern", "Ops Analyst"];
      const sites = ["LinkedIn", "Wellfound", "Naukri", "Indeed", "Cold mail"];
      const n = z.n || 12, cols = z.cols || 2, cw = (960 - (cols - 1) * 24) / cols, ch = 196, top = z.top || 300;
      const step = (t1 - t0) / n;
      for (let k = 0; k < n; k++) {
        const cx = 60 + (k % cols) * (cw + 24), cy = top + Math.floor(k / cols) * (ch + 18), site = sites[k % sites.length];
        const c = el(par, `left:${cx}px;top:${cy}px;width:${cw}px;height:${ch}px`,
          `<div style="position:absolute;left:24px;top:26px;display:flex;align-items:center;gap:16px">${tile(site)}<div><div class="ag-t1" style="font-size:38px">${esc(roles[k % roles.length])}</div>` +
          `<div class="ag-t2">${esc(site)}</div></div></div>`, "ag-card");
        c.dataset.over = "1";
        const st = el(c, `right:22px;bottom:16px;color:${C.go};border-color:${C.go};font-size:32px;padding:8px 16px`, "APPLIED", "ag-stamp");   // under the text block
        const t = t0 + k * step;
        land(c, t, { from: { y: 50, scale: 0.85, blur: 8 }, spring: "snappy", sfx: null });
        tl.fromTo(st, { scale: 2.2, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.16, ease: E.in, immediateRender: true }, Q(t + 0.12));
      }
      K.sfx(z.sfx || "stamp", t0 + 0.12, -20, true);
    };

    // ---------------------------------------------------------------- a restriction toast
    A.toast = (par, y, title, sub, t, until, kind = "stop") => {
      const col = kind === "stop" ? C.stop : kind === "warn" ? C.warn : C.go;
      const n = el(par, `left:60px;top:${y}px;width:960px;height:150px;border-radius:34px;background:rgba(30,12,16,.94);box-shadow:0 30px 70px rgba(0,0,0,.5), inset 0 0 0 2px ${col}`,
        `<div style="position:absolute;left:26px;top:31px;width:88px;height:88px;border-radius:24px;background:${col};display:flex;align-items:center;justify-content:center;font:900 52px/1 Inter;color:#fff">!</div>` +
        `<div style="position:absolute;left:140px;top:30px;font:800 42px/1.1 Inter;color:#fff;white-space:nowrap">${esc(title)}</div>` +
        `<div style="position:absolute;left:140px;top:84px;font:600 36px/1.2 Inter;color:rgba(255,200,205,.8);white-space:nowrap">${esc(sub)}</div>`);
      n.dataset.over = "1";
      land(n, t, { from: { x: 120, scale: 0.92, blur: 8 }, spring: "snappy", sfx: "ui/ui__wrong-answer-fail-notification__mixkit-946", db: -19 });
      if (until != null) leave(n, until);
      return n;
    };

    // ---------------------------------------------------------------- per-site daily limits
    A.limits = (par, x, y, w, names, z = {}) => {
      const rowH = 132, h = 104 + 24 + names.length * rowH;
      const P = A.panel(par, x, y, w, h, { title: z.title || "Daily limit · per site", live: false });
      const rows = names.map((nm, k) => {
        const r = el(P.body, `top:${24 + k * rowH}px`, `${tile(nm)}<div class="ag-t1" style="width:250px">${esc(nm)}</div>` +
          `<div style="position:relative;flex:1;height:18px;border-radius:9px;background:rgba(255,255,255,.08)"><div class="fill" style="position:absolute;left:0;top:0;height:18px;width:100%;border-radius:9px;background:${C.go};transform-origin:0 50%;transform:scaleX(0)"></div></div>` +
          `<span class="v" style="width:150px;text-align:right;font:900 48px/1 Inter;color:rgba(244,244,246,.35)">0</span>`, "ag-row");
        return { fill: r.querySelector(".fill"), v: r.querySelector(".v") };
      });
      return { panel: P.p, set(i, v, t) {
        const r = rows[i];
        tl.to(r.fill, { scaleX: Math.min(1, v / 10), duration: 0.32, ease: E.in, immediateRender: false }, Q(t));
        tl.set(r.v, { textContent: v + "/day", color: C.go }, Q(t)); tl.set(r.v, { textContent: "0" }, 0);
        K.sfx("check", t, -24);
      } };
    };

    // ---------------------------------------------------------------- a counter that runs on its word
    A.counter = (par, x, y, size, z = {}) => {
      const e = el(par, `left:${x - 1500}px;top:${y}px;width:3000px;text-align:center;font:400 ${size}px/0.9 Anton, Inter, sans-serif;color:${z.color || C.go};white-space:nowrap;${z.style || ""}`, "0");
      e.dataset.over = "1";
      return { el: e, run(f0, f1, t0, dur) {
        K.onFrame((t) => { const u = Math.max(0, Math.min(1, (t - t0) / dur)); e.textContent = String(Math.round(f0 + (f1 - f0) * (1 - Math.pow(1 - u, 3)))) + (z.suffix || ""); });
      } };
    };

    // ---------------------------------------------------------------- a working week, interview blocks drop in
    A.week = (par, x, y, w, h, z = {}) => {
      const P = A.panel(par, x, y, w, h, { title: z.title || "Calendar · this week", live: false });
      const days = ["Mon", "Tue", "Wed", "Thu", "Fri"], cw = (w - 44 - 4 * 14) / 5, colsTop = 26;
      const cols = days.map((d, k) => {
        const cx = 22 + k * (cw + 14);
        el(P.body, `left:${cx}px;top:${colsTop}px;width:${cw}px;text-align:center;font:800 38px/1 Inter;color:rgba(244,244,246,.6)`, d);
        el(P.body, `left:${cx}px;top:${colsTop + 56}px;width:${cw}px;height:${h - 104 - colsTop - 80}px;border-radius:22px;background:rgba(255,255,255,.04)`);
        return { cx, n: 0 };
      });
      return { panel: P.p, add(day, label, t) {
        const c = cols[day], by = colsTop + 72 + c.n * 150; c.n++;
        const b = el(P.body, `left:${c.cx + 8}px;top:${by}px;width:${cw - 16}px;height:136px;border-radius:18px;background:rgba(61,220,132,.2);box-shadow:inset 4px 0 0 ${C.go};` +
          "padding:14px 12px;font:800 36px/1.15 Inter;color:#fff;white-space:pre-line", esc(label));   // label "Interview\n11:00"
        land(b, t, { from: { y: -120, scale: 0.9, blur: 6 }, spring: "thrown", sfx: null });
        return b;
      } };
    };

    A.title = (par, x, y, html, t, until, z = {}) => {
      const e = el(par, `left:${x}px;top:${y}px;font-size:${z.size || 92}px;${z.style || ""}`, html, "ag-title");
      e.dataset.over = "1";
      land(e, t, { from: z.from || { y: 40, scale: 0.94, blur: 10 }, spring: "snappy", sfx: z.sfx === undefined ? null : z.sfx, db: z.db || -22 });
      if (until != null) leave(e, until);
      return e;
    };
    return A;
  };
})(typeof window !== "undefined" ? window : globalThis);
