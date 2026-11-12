/*
 * kit/hf/studio_ui.js: product-like UI cards for the pastel-box kit (kit/hf/studio.js), extracted from films/ai-workflows.
 * HF.studio() attaches them as S.ui. Every time is in seconds (pass W(id) for a word), every position is in page px
 * (1920x1080). Content is always generic and made up: never a real workspace, logo, person or number the speaker didn't say.
 *
 *   ui.message(par, x, y, w, { avatar, color, who, where, text, at })      a Slack-like message (mention: @Name)
 *   ui.badge(par, x, y, n, at)                                             an unread badge that pops
 *   ui.workspace(par, x, y, w, h, { team, channels })                      a chat app window with a sidebar -> { card, main }
 *   ui.thread(par, x, y, { label, status, rows: [[t, text]], at })         the agent's thread: head + ticked rows
 *   ui.pr(par, x, y, w, h, { title, branch, base, by, checks, at, tilt })  a pull-request card (tilts in by default)
 *   ui.stamp(text, x, y, t, { color, out })                                a rubber stamp on FRONT ("PR RAISED")
 *   ui.doc(par, x, y, w, { title, rows: [[k, v]], at, per })                a report card with keyed rows
 *   ui.checklist(par, x, y, w, { title, items, at, per, done: {i: t}, next: {i: t} })   a plan / to-do card
 *   ui.chat(par, x, y, w, h, { title, sub, color })                        an assistant chat -> { card, user(text, t), think(a, b), rows(list) }
 *   ui.toggle(par, x, y, { title, sub, at, onAt, pointerAt, outAt })       a settings switch, clicked by a pointer
 *   ui.column(par, x, y, w, { name, color, at })                           a header card that grows with each add(i, t, icon, text)
 *   ui.hub(par, cx, cy, { at, apps: [{ t, name, icon, dx, dy }] })         the agent orb with apps wired to it
 *   ui.tiles(par, x, y, { people: [[initial, color]], at, per })           a call's video tiles (2x2)
 *   ui.numbered(par, items: [[n, title, color]], { x, y, at, w, gap })     the promise board's numbered cards
 *   ui.note(par, x, y, w, { kicker, title, sub, at })                      a calm correction / heads-up card
 *   ui.lowerThird({ name, accent, pills: [[text, bg, fg]], at, until })    the name title over the face
 *   ui.thinking(par, x, y, a, b)                                           three bouncing dots while an agent thinks
 *   ui.pointer(par, { from: [x, y], to: [x, y], at, dur, clickAt, rideTo, until })   a mouse pointer that glides and clicks
 */
(function (root) {
  const HF = root.HF;

  HF.studioUI = function (S) {
    const { K, tl, Q, E, el, FRONT, card, chip, mono, orbI, orbAt, dot, icon, tick, land, leave, pop, fadeOut } = S;
    // the look's tokens (HF.look, kit/hf/core.js): colours and type follow the film's look (pastel, canvas, redline, night)
    const C = HF.C, F = HF.F;
    const ui = {};

    ui.message = (par, x, y, w, o = {}) => {
      const txt = String(o.text || "").replace(/@(\w+)/g, '<span class="mention">@$1</span>');
      const m = card(par, x, y, w, o.h || 170, `<div style="position:absolute;left:28px;top:28px;display:flex;gap:16px">
          <div class="av" style="background:${o.color || "#0f9d8a"}">${o.avatar || "QA"}</div><div><div class="who">${o.who || "QA Tester"}<small>${o.where || "# web-bugs"}</small></div>
          <div class="txt">${txt}</div></div></div>`, "border-radius:24px");
      if (o.at != null) land(m, o.at, { from: o.from || { x: -40, y: 0, scale: 0.95, blur: 8 }, sfx: "pop", db: -20 });
      return m;
    };

    ui.badge = (par, x, y, n, at) => {
      const b = el(par, `left:${x}px;top:${y}px;width:34px;height:34px;border-radius:17px;background:#e5484d;color:#fff;font:800 18px/34px ${F.body};text-align:center`, String(n));
      if (at != null) pop(b, at);
      return b;
    };

    ui.workspace = (par, x, y, w, h, o = {}) => {
      const c = card(par, x, y, w, h);
      const chans = (o.channels || [{ name: "# general" }, { name: "# web-bugs", unread: 3, active: true }]).map((ch) =>
        `<div style="color:${ch.active ? "#fff" : "#aaa6b8"};font:${ch.active ? 800 : 500} 20px ${F.body};padding:10px 20px;${ch.active ? "background:#363245;" : ""}display:flex;justify-content:space-between">${ch.name}${ch.unread ? ` <span style="background:#e5484d;border-radius:12px;padding:2px 9px;font-size:15px">${ch.unread}</span>` : ""}</div>`).join("");
      c.innerHTML = `<div class="tbar"><i></i><i></i><i></i><b>${o.team || "acme · dev"}</b></div>
        <div style="position:absolute;left:0;top:50px;bottom:0;width:200px;background:#211e2b;padding:22px 0">
          <div style="color:#fff;font:800 21px ${F.body};padding:0 20px 20px">${o.team || "acme · dev"}</div>${chans}</div>`;
      const main = el(c, "left:200px;top:50px;right:0;bottom:0");
      return { card: c, main };
    };

    ui.thread = (par, x, y, o = {}) => {
      const th = el(par, `left:${x}px;top:${y}px;right:24px;padding-left:18px;border-left:3px solid ${C.accTint}`);
      const head = el(th, "position:relative;display:flex;align-items:center;gap:12px", `${orbI(30)}<span class="who" style="font-size:21px">${o.label || "Agent"}</span><span style="font:600 19px ${F.body};color:${C.warm}">${o.status || "working…"}</span>`, "");
      if (o.at != null) land(head, o.at, { from: { x: -14, y: 0, scale: 1, blur: 6 }, sfx: "pop", db: -22 });
      (o.rows || []).forEach(([t, text]) => {
        const r = el(th, `position:relative;margin-top:12px;font:500 21px/1 ${F.mono};color:${C.text}`, text, "");
        land(r, t, { from: { x: -12, y: 0, scale: 1, blur: 4 }, sfx: "check", db: -25 });
      });
      return th;
    };

    ui.pr = (par, x, y, w, h, o = {}) => {
      const big = w > 1100;
      const c = card(par, x, y, w, h, `<div style="position:absolute;left:${big ? 48 : 36}px;top:${big ? 44 : 34}px;display:flex;align-items:center;gap:${big ? 16 : 12}px">
          <span class="pill" style="background:${C.ok};color:${C.onFill};font-size:${big ? 32 : 26}px">${tick(big ? 26 : 22, C.onFill)} Open</span>
          <span style="font:700 ${big ? 24 : 22}px ${F.body};color:${C.sub}">Pull request · ${o.by ? "opened by" : "by Agent"}</span>
          ${o.by ? `<span style="display:inline-flex;align-items:center;gap:10px;font:800 24px ${F.body};color:${C.warm}">${orbI(26)}${o.by}</span>` : ""}</div>
        <div style="position:absolute;left:${big ? 48 : 36}px;top:${big ? 118 : 100}px;font:800 ${big ? 54 : 40}px/1.12 ${F.body};color:${C.ink};letter-spacing:-.015em;width:${w - 80}px;white-space:normal">${o.title || "Fix the bug"}</div>
        <div class="mono" style="position:absolute;left:${big ? 48 : 36}px;top:${big ? 212 : 206}px;font-size:${big ? 26 : 24}px;color:${C.sub}"><span style="background:${C.sunk};padding:6px 12px;border-radius:9px">${o.branch || "agent/fix"}</span> → <span style="background:${C.accTint};color:${C.acc};padding:6px 12px;border-radius:9px">${o.base || "main"}</span></div>
        ${o.checks === false ? "" : `<div style="position:absolute;left:${big ? 48 : 36}px;top:${big ? 330 : 272}px;font:700 ${big ? 28 : 24}px ${F.body};color:${C.ok}">✓ ${o.checks || "checks passed"}</div>`}`);
      if (o.at != null) { if (o.tilt === false) land(c, o.at, { from: { y: 50, scale: 0.94, blur: 10 }, sfx: "slide", db: -22 }); else HF.tiltIn(K, c, o.at, { rot: o.rot || 22, dur: 0.6 }); }
      return c;
    };

    ui.stamp = (text, x, y, t, o = {}) => {
      const col = o.color || C.ok;
      const s = el(FRONT, `left:${x}px;top:${y}px;font:400 ${o.size || 110}px/1 ${F.stamp};color:${col};padding:8px 28px 12px;border:10px solid ${col};border-radius:20px;background:${C.plate};box-shadow:0 24px 60px rgba(0,0,0,.2);white-space:nowrap`, text, "hf-abs");
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: 0.05, immediateRender: true }, Q(t));
      tl.fromTo(s, { scale: 2.1, rotation: -14 }, { scale: 1, rotation: -8, duration: sp.duration, ease: sp.ease, immediateRender: true }, Q(t));
      K.sfx("impact/impact__exciting-fast-hit__mixkit-2180", t + 0.05, -13); K.sfx("stamp", t + 0.07, -15);
      if (o.out != null) fadeOut(s, o.out);
      return s;
    };

    ui.doc = (par, x, y, w, o = {}) => {
      const rows = o.rows || [];
      const c = card(par, x, y, w, 100 + rows.length * 92, `<div class="tbar">${orbI(22)}<b>${o.title || "Report"}</b></div>`);
      if (o.at != null) land(c, o.at, { from: { y: 50, scale: 0.94, blur: 10 }, sfx: "slide", db: -22 });
      rows.forEach(([k, v], i) => {
        const r = el(c, `left:36px;top:${80 + i * 92}px;width:${w - 70}px;height:74px;border-radius:14px;background:${C.sunk};display:flex;align-items:center;gap:20px;padding:0 22px;font:500 25px ${F.body};color:${C.text}`,
          `<b style="width:110px;color:${C.acc}">${k}</b> ${v}`);
        land(r, (o.rowsAt != null ? o.rowsAt : (o.at || 0) + 0.4) + i * (o.per || 0.32), { from: { x: -20, y: 0, scale: 1, blur: 6 }, sfx: i ? null : "typing/typing__electronic-typing__mixkit-1397", db: -28 });
      });
      return c;
    };

    // done: { index: time } ticks an item (and dims it); next: { index: time } tags it "next →"
    ui.checklist = (par, x, y, w, o = {}) => {
      const items = o.items || [], gap = o.gap || 132, rh = o.rowH || 112;
      const c = card(par, x, y, w, 86 + items.length * gap + 30, `<div class="tbar">${orbI(22)}<b>${o.title || "Today's plan"}</b></div>`);
      if (o.at != null) land(c, o.at, { from: o.from || { y: 50, scale: 0.94, blur: 10 }, sfx: "slide", db: -22 });
      const done = o.done || {}, next = o.next || {};
      const rows = items.map((t, i) => {
        const r = el(c, `left:32px;top:${86 + i * gap}px;width:${w - 64}px;height:${rh}px;border-radius:18px;background:${C.sunk};display:flex;align-items:center;gap:20px;padding:0 24px;font:600 ${o.size || 28}px ${F.body};color:${C.text}`,
          `<span style="width:42px;height:42px;border-radius:11px;border:3px solid ${C.mute};flex:none;display:flex;align-items:center;justify-content:center"></span><span>${t}</span>`);
        if (o.rowsAt != null) land(r, o.rowsAt + i * (o.per || 0.38), { from: { x: -20, y: 0, scale: 1, blur: 6 }, sfx: i ? null : "typing/typing__electronic-typing__mixkit-1397", db: -27 });
        const bx = r.firstChild;
        if (done[i] != null) { const tt = done[i]; bx.innerHTML = tick(24, C.onFill);
          tl.to(bx, { backgroundColor: C.ok, borderColor: C.ok, duration: 0.15, immediateRender: false }, Q(tt));
          pop(bx.firstChild, tt); K.sfx("check", tt, -24);
          tl.to(r.lastChild, { opacity: 0.45, duration: 0.2, immediateRender: false }, Q(tt + 0.1)); }
        if (next[i] != null) { const nx = el(r, "right:26px;top:33px", `<span class="pill" style="background:${C.accTint};color:${C.acc};font-size:26px">next →</span>`);
          land(nx, next[i], { from: { x: 20, y: 0, scale: 0.9, blur: 4 }, spring: "thrown", sfx: "pop", db: -23 }); }
        return r;
      });
      return { card: c, rows };
    };

    ui.chat = (par, x, y, w, h, o = {}) => {
      const c = card(par, x, y, w, h, `<div class="tbar">${dot(o.color || "#10a37f", 14)}<b style="margin-left:4px">${o.title || "Assistant"}</b>${o.sub ? `<span class="mono" style="margin-left:auto;font-size:15px;color:${C.mute}">${o.sub}</span>` : ""}</div>`);
      if (o.at != null) land(c, o.at, { from: { y: 50, scale: 0.94, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      const api = { card: c };
      // the user's message types itself in from t
      api.user = (text, t, cps = 22) => {
        const u = el(c, `right:30px;top:86px;max-width:${Math.round(w * 0.64)}px;border-radius:22px;padding:18px 24px;background:${C.accTint};font:600 30px ${F.body};color:${C.ink};opacity:0`, "");
        tl.to(u, { opacity: 1, duration: 0.1, immediateRender: false }, Q(t));
        K.typeText(u, text, t, cps, false);
        return u;
      };
      api.think = (a, b) => ui.thinking(c, 30, 210, a, b);
      // rows: [{ t, text, who, color, tagAt }] answer rows that slide in (a pill per row tags who does it)
      api.rows = (list, top = 210) => {
        const rp = el(c, `left:30px;top:${top}px;width:${w - 70}px`);
        return list.map((r, i) => {
          const e = el(rp, `position:relative;margin-top:${i ? 18 : 0}px;height:96px;border-radius:18px;background:${C.sunk};display:flex;align-items:center;justify-content:space-between;padding:0 26px;font:700 30px ${F.body};color:${C.ink}`,
            `<span>${r.text}</span>${r.who ? `<span class="pill" style="background:${r.color || "#10a37f"};color:#fff;font-size:22px;opacity:0">${r.who}</span>` : ""}`, "");
          land(e, r.t, { from: { x: -20, y: 0, scale: 1, blur: 6 }, sfx: i ? null : "typing/typing__electronic-typing__mixkit-1397", db: -27 });
          if (r.who) { const p = e.lastChild, tt = r.tagAt != null ? r.tagAt : r.t + 0.3;
            tl.to(p, { opacity: 1, duration: 0.15, immediateRender: false }, Q(tt));
            tl.fromTo(p, { scale: 0.6 }, { scale: 1, duration: 0.35, ease: HF.spring(HF.SPRING.thrown).ease, immediateRender: false }, Q(tt)); }
          return e;
        });
      };
      return api;
    };

    ui.toggle = (par, x, y, o = {}) => {
      const set = card(par, x, y, 800, 220, `<div style="position:absolute;left:40px;top:44px;font:800 36px ${F.body};color:${C.ink}">${o.title || "Setting"}</div><div style="position:absolute;left:40px;top:104px;font:500 26px ${F.body};color:${C.sub}">${o.sub || ""}</div>`);
      const sw = el(set, `right:40px;top:76px;width:120px;height:66px;border-radius:33px;background:color-mix(in srgb, ${C.mute} 40%, transparent)`);
      const kn = el(sw, "left:6px;top:6px;width:54px;height:54px;border-radius:50%;background:#fff;box-shadow:0 4px 10px rgba(0,0,0,.2)");
      if (o.at != null) land(set, o.at, { from: { y: 40, scale: 0.94, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      let cur = null;
      if (o.onAt != null) {
        tl.to(sw, { backgroundColor: C.ok, duration: 0.2, immediateRender: false }, Q(o.onAt)); tl.to(kn, { x: 54, duration: 0.25, ease: E.in, immediateRender: false }, Q(o.onAt));
        K.sfx("ui/ui__select-click__mixkit-1109", o.onAt, -18);
        if (o.pointerAt != null) {                                              // glides to the knob, clicks, rides it across
          const kx = x + 800 - 40 - 120 + 26, ky = y + 100;
          cur = ui.pointer(par, { from: [kx + 314, ky + 260], to: [kx, ky], at: o.pointerAt, dur: Math.min(1.15, o.onAt - o.pointerAt - 0.1), clickAt: o.onAt - 0.07, rideTo: [kx + 54, ky], until: o.outAt });
        }
      }
      if (o.outAt != null) tl.to(set, { opacity: 0, y: -30, duration: 0.3, immediateRender: false }, Q(o.outAt));
      return { card: set, pointer: cur };
    };

    ui.column = (par, x, y, w, o = {}) => {
      const k = card(par, x, y, w, 150, `<div style="position:absolute;left:40px;top:36px;display:flex;align-items:center;gap:16px">${dot(o.color || C.acc, 30)}<span class="sv" style="font-size:80px">${o.name || ""}</span></div>`);
      if (o.at != null) land(k, o.at, { from: { y: 50, scale: 0.94, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      // an item lands at t; the card grows to hold it (a big empty card reads as a slide)
      const add = (i, t, ic, text) => {
        const r = el(k, `left:40px;top:${170 + i * 118}px;display:flex;align-items:center;gap:22px;font:700 36px ${F.body};color:${C.ink}`,
          `<span style="width:76px;height:76px;border-radius:20px;background:${C.sunk};display:flex;align-items:center;justify-content:center">${icon(ic, 40, C.ink, 2.2)}</span><span>${text}</span>`);
        land(r, t, { from: { x: -20, y: 0, scale: 0.95, blur: 6 }, sfx: "pop", db: -25 });
        tl.to(k, { height: 286 + i * 118, duration: 0.35, ease: E.in, immediateRender: false }, Q(t - 0.1));
        return r;
      };
      return { card: k, add };
    };

    ui.hub = (par, cx, cy, o = {}) => {
      const ob = orbAt(par, cx, cy, o.size || 120);
      if (o.at != null) land(ob, o.at, { from: { y: 0, scale: 0.3, blur: 10 }, spring: "thrown", sfx: null });
      (o.apps || []).forEach((a) => {
        const ln = el(par, `left:${cx}px;top:${cy - 2}px;width:${Math.hypot(a.dx, a.dy) - 160}px;height:4px;border-radius:2px;background:linear-gradient(90deg,#ff9a5c,${C.acc});transform-origin:0 50%;transform:rotate(${Math.atan2(a.dy, a.dx)}rad)`);
        const c = chip(par, cx + a.dx - 150, cy + a.dy - 44, `${icon(a.icon || "chat", 34, C.acc, 2.2)} ${a.name}`, "font-size:32px;padding:20px 30px");
        land(c, a.t, { from: { y: 26, scale: 0.85, blur: 8 }, spring: "thrown", sfx: "pop", db: -23 });
        tl.fromTo(ln, { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: E.in, immediateRender: true }, Q(a.t + 0.1));
      });
      return ob;
    };

    ui.tiles = (par, x, y, o = {}) => {
      const grid = el(par, `left:${x}px;top:${y}px;width:820px;height:520px`);
      (o.people || [["A", "#7c5cff"], ["R", "#0f9d8a"], ["S", "#e2562b"], ["You", "#17161f"]]).forEach(([n, c], i) => {
        const t = card(grid, (i % 2) * 420, Math.floor(i / 2) * 270, 400, 250, `<div style="position:absolute;inset:0;background:linear-gradient(135deg,#2a2638,#3d3656)"></div>
          <div class="av" style="position:absolute;left:50%;top:50%;margin:-40px 0 0 -40px;width:80px;height:80px;border-radius:50%;background:${c};font-size:26px">${n}</div>`, "border-radius:22px");
        if (o.at != null) land(t, o.at + i * (o.per || 0.12), { from: { y: 30, scale: 0.9, blur: 8 }, sfx: i ? null : "slide", db: -23 });
      });
      return grid;
    };

    ui.numbered = (par, items, o = {}) => {
      const w = o.w || 480, gap = o.gap || 40;
      return items.map(([n, ttl, col], i) => {
        const c = card(par, (o.x || 210) + i * (w + gap), o.y || 470, w, o.h || 340, `<div class="sv" style="position:absolute;left:36px;top:26px;font-size:96px;color:${col || C.acc};font-style:italic">${n}</div>
          <div style="position:absolute;left:38px;top:170px;font:800 34px/1.22 ${F.body};color:${C.ink};white-space:normal;width:${w - 80}px">${String(ttl).replace(/\|/g, "<br>")}</div>`);
        if (o.at != null) land(c, o.at + i * 0.12, { from: { y: 60, scale: 0.9, blur: 10 }, spring: "thrown", sfx: i ? null : "slide", db: -22 });
        return c;
      });
    };

    ui.note = (par, x, y, w, o = {}) => {
      const c = card(par, x, y, w, o.h || 300, `<div class="mono" style="position:absolute;left:40px;top:36px;font-size:18px;letter-spacing:.16em;color:${C.acc}">${o.kicker || "HEADS-UP"}</div>
        <div style="position:absolute;left:40px;top:80px;width:${w - 80}px;font:600 34px/1.35 ${F.body};color:${C.ink};white-space:normal">${o.title || ""}</div>
        ${o.sub ? `<div style="position:absolute;left:40px;top:${(o.h || 300) - 90}px;font:500 26px/1.3 ${F.body};color:${C.sub}">${o.sub}</div>` : ""}`, `background:${C.card}`);
      if (o.at != null) land(c, o.at, { from: { y: 30, scale: 0.97, blur: 8 }, sfx: null });
      return c;
    };

    ui.lowerThird = (o = {}) => {
      const pills = (o.pills || []).map(([t, bg, fg]) => `<span class="pill" style="background:${bg || C.plate};color:${fg || C.ink};font-size:22px">${t}</span>`).join("");
      const lt = el(FRONT, `left:${o.x || 110}px;top:${o.y || 790}px`, `<div class="sv" style="font-size:96px;color:#fff;text-shadow:0 6px 30px rgba(0,0,0,.4)">${o.name || ""}${o.accent ? ` <i style="color:${C.onVideo}">${o.accent}</i>` : ""}</div>
        <div style="margin-top:14px;display:flex;gap:14px">${pills}</div>`, "hf-abs");
      if (o.at != null) land(lt, o.at, { from: { y: 30, scale: 1, blur: 10 }, sfx: "slide", db: -24 });
      if (o.until != null) leave(lt, o.until);
      return lt;
    };

    ui.thinking = (par, x, y, a, b) => {
      const th = el(par, `left:${x}px;top:${y}px;height:66px;padding:0 26px;border-radius:22px;background:${C.sunk};display:flex;align-items:center;gap:11px`,
        [0, 1, 2].map(() => `<span style="width:13px;height:13px;border-radius:50%;background:${C.mute};display:inline-block"></span>`).join(""));
      K.show(th, a, b);
      const ds = [...th.children];
      K.onFrame((t) => ds.forEach((d, j) => { const h = Math.max(0, Math.sin(t * 7 - j * 0.9)); d.style.transform = `translateY(${(-9 * h).toFixed(2)}px)`; d.style.opacity = (0.45 + 0.55 * h).toFixed(3); }));
      return th;
    };

    ui.pointer = (par, o = {}) => {
      const [fx, fy] = o.from, [tx, ty] = o.to;
      const cur = el(par, "left:0;top:0;width:46px;height:46px;opacity:0;transform-origin:9px 5px",
        `<svg width="46" height="46" viewBox="0 0 24 24"><path d="M5 3l14 8-6.2 1.6L10 19z" fill="#17161f" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`);
      tl.fromTo(cur, { x: fx - 9, y: fy - 5 }, { x: tx - 9, y: ty - 5, duration: o.dur || 1.0, ease: E.move, immediateRender: true }, Q(o.at));
      tl.to(cur, { opacity: 1, duration: 0.2, immediateRender: false }, Q(o.at));
      if (o.clickAt != null) tl.to(cur, { scale: 0.82, duration: 0.08, yoyo: true, repeat: 1, immediateRender: false }, Q(o.clickAt));
      if (o.rideTo) tl.to(cur, { x: o.rideTo[0] - 9, y: o.rideTo[1] - 5, duration: 0.25, ease: E.in, immediateRender: false }, Q((o.clickAt || o.at) + 0.07));
      if (o.until != null) tl.to(cur, { opacity: 0, duration: 0.2, immediateRender: false }, Q(o.until));
      return cur;
    };

    return ui;
  };
})(window);
