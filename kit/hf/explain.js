/* kit/hf/explain.js — explanation visuals that show a mechanism or a ranking (needs core.js).
 *
 *   HF.tokens(K, layer, { x, y, w, data, t, step, temps: [{ at, T }] })   next-word probabilities, step by step
 *   HF.stack(K, layer, { cx, cy, w, layers: [{ label, sub }], t, explodeAt, focus: [{ at, i }], collapseAt })
 *   HF.race(K, layer, { x, y, w, data, t, dur, title })                   leaderboard race with rank swaps
 *
 * Data is always real: HF.tokens takes kit/hf/tools/nexttoken.py output (a real model's top-k), HF.race takes
 * kit/hf/tools/arena_race.py output (Arena snapshots). The model / source line is drawn on screen with the chart.
 * Paper-studio look: ink on paper, one accent, serif headlines, mono labels; everything frame-quantised.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/explain.js needs core.js first");
  const C = HF.C, esc = HF.esc;
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const smooth = (p) => p * p * (3 - 2 * p);
  const showTok = (s) => esc(s.replace(/\n/g, "↵")).replace(/^ /, "·").replace(/ /g, "&nbsp;");

  // ---------------------------------------------------------------- next-word probabilities
  // A sentence at the top (prompt in grey, generated words in ink); under it a card with the top-k candidates as bars
  // on an absolute 0-100 % axis. Each step: rows swap in, bars grow, the winner lights up, the word drops into the
  // sentence. temps: re-weight one step at temperature T (the bars flatten or sharpen; the data's step.temps[T]).
  HF.tokens = function (K, parent, o) {
    const d = o.data, k = Math.min(o.k || 5, d.steps[0].top.length), w = o.w || 1100, step = o.step || 1.3;
    const x = o.x, y = o.y, rowH = o.rowH || 74, labW = o.labW || 220, barW = w - labW - 150, fs = o.fs || 64;
    const wrap = K.el(parent, `left:${x}px;top:${y}px;width:${w}px`);
    const sent = K.el(wrap, `left:0;top:0;width:${w}px;font:400 ${fs}px/1.15 InstrumentSerif,serif;color:${C.ink};white-space:normal`);
    sent.innerHTML = `<span style="color:${C.mute}">${esc(d.prompt)}</span>`;
    const words = d.steps.map((s) => { const sp = document.createElement("span"); sp.style.cssText = "display:none;white-space:pre;opacity:0"; sp.textContent = s.chosen; sent.append(sp); return sp; });
    const caret = document.createElement("span"); caret.style.cssText = `display:inline-block;width:4px;height:${fs * 0.8}px;margin-left:6px;background:${C.acc};vertical-align:-0.08em`; sent.append(caret);
    const top = o.cardTop != null ? o.cardTop : Math.round(fs * 2.6 + 40);
    const card = HF.card(K, wrap, 0, top, w, 96 + k * rowH, "", "padding:0");
    if (o.enter !== false) { K.enter(card, o.t, { y: 30 }); K.enter(sent, o.t - 0.1, { y: 16 }, 0.5); }
    else card.style.opacity = "1";                                          // enter: false = already settled on frame 1 (a hook)
    K.el(card, `left:34px;top:26px;opacity:1`, "next word?", "hf-lbl hf-abs");
    const meta = K.el(card, `right:34px;top:28px;font:500 18px JBMono,monospace;color:${C.mute};white-space:nowrap`, esc(d.model) + " · real probabilities");
    void meta;
    const rows = [];
    for (let r = 0; r < k; r++) {
      const ry = 80 + r * rowH;
      const lab = K.el(card, `left:34px;top:${ry}px;width:${labW - 20}px;height:${rowH - 16}px;display:flex;align-items:center;font:500 30px JBMono,monospace;color:${C.ink};white-space:nowrap;overflow:hidden`);
      const track = K.el(card, `left:${labW + 20}px;top:${ry + 14}px;width:${barW}px;height:${rowH - 44}px;border-radius:10px;background:rgba(27,24,21,.06)`);
      const bar = K.el(track, `left:0;top:0;height:100%;width:${barW}px;border-radius:10px;background:${C.ink2};transform-origin:0 50%;transform:scaleX(0)`);
      const pct = K.el(card, `left:${labW + 30 + barW}px;top:${ry}px;width:110px;height:${rowH - 16}px;display:flex;align-items:center;justify-content:flex-end;font:600 28px Inter,sans-serif;color:${C.ink};font-variant-numeric:tabular-nums`);
      rows.push({ lab, bar, pct, track });
    }
    const tl = K.tl, Q = K.Q;
    const fill = (s, at, list, first) => {                                   // put one distribution on the rows at time `at`
      list.slice(0, k).forEach((c, r) => {
        const R = rows[r], win = c.t === s.chosen;
        if (first) {
          tl.set(R.lab, { innerHTML: showTok(c.t), opacity: 0, x: -16 }, Q(at - 0.01));
          tl.to(R.lab, { opacity: 1, x: 0, duration: 0.25, ease: "power3.out" }, Q(at + r * 0.04));
          tl.set(R.bar, { backgroundColor: C.ink2 }, Q(at - 0.01));
        }
        tl.to(R.bar, { scaleX: Math.max(0.004, c.p), duration: first ? 0.5 : 0.7, ease: first ? "expo.out" : "power3.inOut" }, Q(at + (first ? 0.05 + r * 0.04 : 0)));
        const pv = { v: 0 };
        tl.to(pv, { v: c.p * 100, duration: first ? 0.5 : 0.7, ease: "power3.out", onUpdate: () => { R.pct.textContent = (pv.v < 1 && pv.v > 0 ? "<1" : Math.round(pv.v)) + "%"; } }, Q(at + 0.05));
        if (first && win) tl.set(R.bar, { backgroundColor: C.acc }, Q(at + 0.62));
        if (first && win) tl.fromTo(R.track, { boxShadow: `0 0 0 0 ${C.accTint}` }, { boxShadow: `0 0 0 6px ${C.accTint}`, duration: 0.25 }, Q(at + 0.62));
        if (first) tl.set(R.track, { boxShadow: "none" }, Q(at + step - 0.02));
      });
    };
    d.steps.forEach((s, i) => {
      const at = o.t + 0.5 + i * step;
      if (i > 0) rows.forEach((R) => { tl.to(R.lab, { opacity: 0, x: 16, duration: 0.12 }, Q(at - 0.14)); tl.to(R.bar, { scaleX: 0, duration: 0.12, ease: "power2.in" }, Q(at - 0.14)); });
      fill(s, at, s.top, true);
      tl.set(words[i], { display: "inline-block" }, Q(at + 0.7));            // takes no room (the caret stays at the end) until it lands
      tl.fromTo(words[i], { opacity: 0, y: fs * 1.4, color: C.acc }, { opacity: 1, y: 0, duration: 0.35, ease: "expo.out", immediateRender: false }, Q(at + 0.7));
      tl.to(words[i], { color: C.ink, duration: 0.3 }, Q(at + 1.05));
      K.sfx("click", at + 0.7, -24);
    });
    const tempChip = K.el(card, `left:${w - 330}px;top:${-56}px;padding:8px 16px;border-radius:999px;background:${C.ink};color:#fff;font:500 20px JBMono,monospace;opacity:0;white-space:nowrap`);
    (o.temps || []).forEach((q, j) => {
      const s = d.steps[q.step != null ? q.step : d.steps.length - 1], list = s.temps && s.temps[String(q.T)];
      if (!list) throw new Error(`HF.tokens: no temps["${q.T}"] in the data (run nexttoken.py --temps ${q.T})`);
      tl.set(tempChip, { textContent: `temperature ${q.T}` }, Q(q.at));
      if (j === 0) K.enter(tempChip, q.at, { y: 10 }, 0.3);
      // the same candidates, re-weighted: keep the rows, move the bars
      const byTok = Object.fromEntries(list.map((c) => [c.t, c.p]));
      fill(s, q.at, s.top.map((c) => ({ t: c.t, p: byTok[c.t] != null ? byTok[c.t] : 0 })), false);
      K.sfx("slide", q.at, -24);
    });
    return { wrap, card, sentence: sent, end: o.t + 0.5 + d.steps.length * step };
  };

  // ---------------------------------------------------------------- exploded layer stack
  // Isometric slabs, collapsed into one block, then pulled apart along the vertical with a label per layer
  // (leader line to the right). focus lights one layer (accent) and dims the rest; collapseAt puts them back.
  HF.stack = function (K, parent, o) {
    const L = o.layers, n = L.length, w = o.w || 520, cx = o.cx, cy = o.cy, tl = K.tl, Q = K.Q;
    const thick = o.thick || 22, gap = o.gap || Math.min(130, 520 / n), side = o.labelSide || "right";
    const faceH = w * 0.577;                                                  // the rhombus height of an isometric square
    const wrap = K.el(parent, `left:0;top:0;width:${K.width}px;height:${K.height}px`);
    const slabs = L.map((lay, i) => {
      const g = K.el(wrap, `left:${cx - w / 2}px;top:${cy - faceH / 2}px;width:${w}px;height:${faceH + thick}px;opacity:0`);
      const pts = (dy) => `${w / 2},${dy} ${w},${faceH / 2 + dy} ${w / 2},${faceH + dy} 0,${faceH / 2 + dy}`;
      const fillTop = i === n - 1 ? "#ffffff" : "#fbf8f3", edge = "#d9cfc2";
      g.innerHTML = `<svg width="${w}" height="${faceH + thick}" viewBox="0 0 ${w} ${faceH + thick}" style="position:absolute;left:0;top:0;overflow:visible">` +
        `<polygon points="0,${faceH / 2} ${w / 2},${faceH} ${w / 2},${faceH + thick} 0,${faceH / 2 + thick}" fill="${edge}"/>` +
        `<polygon points="${w / 2},${faceH} ${w},${faceH / 2} ${w},${faceH / 2 + thick} ${w / 2},${faceH + thick}" fill="#c9bdae"/>` +
        `<polygon class="top" points="${pts(0)}" fill="${fillTop}" stroke="rgba(27,24,21,.12)" stroke-width="1.5"/>` +
        `<text x="${w / 2}" y="${faceH / 2 + 10}" text-anchor="middle" font-family="JBMono, monospace" font-size="${Math.round(w / 22)}" fill="${C.mute}" transform="rotate(0)">${esc(lay.tag || "")}</text></svg>`;
      const lx = side === "right" ? cx + w / 2 + 70 : cx - w / 2 - 70 - (o.labelW || 420);
      const lab = K.el(wrap, `left:${lx}px;top:0;width:${o.labelW || 420}px;opacity:0;${side === "right" ? "" : "text-align:right"}`,
        `<div class="hf-serif" style="font-size:${o.fs || 52}px;line-height:1">${esc(lay.label)}</div>` + (lay.sub ? `<div style="margin-top:6px;font:500 22px Inter,sans-serif;color:${C.mute}">${esc(lay.sub)}</div>` : ""));
      const line = K.el(wrap, `left:${side === "right" ? cx + w / 2 - 10 : lx + (o.labelW || 420) + 10}px;top:0;width:70px;height:2px;background:${C.ink2};opacity:0;transform-origin:${side === "right" ? "0" : "100%"} 50%`);
      return { g, lab, line, top: g.querySelector(".top") };
    });
    // y of slab i (0 = bottom) when collapsed (thickness apart) and exploded (gap apart), centred on cy
    const yAt = (i, gp) => cy - faceH / 2 - (i - (n - 1) / 2) * gp;
    slabs.forEach((s, i) => {
      tl.set(s.g, { y: yAt(i, thick) - (cy - faceH / 2) }, 0);
      tl.to(s.g, { opacity: 1, duration: 0.3 }, Q(o.t + (n - 1 - i) * 0.05));
      tl.fromTo(s.g, { y: yAt(i, thick) - (cy - faceH / 2) - 40 }, { y: yAt(i, thick) - (cy - faceH / 2), duration: 0.5, ease: "expo.out", immediateRender: false }, Q(o.t + (n - 1 - i) * 0.05));
    });
    const ex = o.explodeAt != null ? o.explodeAt : o.t + 0.8;
    slabs.forEach((s, i) => {
      const y1 = yAt(i, gap) - (cy - faceH / 2);
      tl.to(s.g, { y: y1, duration: 0.7, ease: "power3.inOut" }, Q(ex + i * 0.03));
      const ly = yAt(i, gap) + faceH / 2 - (o.fs || 52) * 0.6;
      tl.set(s.lab, { y: ly }, 0); tl.set(s.line, { y: yAt(i, gap) + faceH / 2 }, 0);
      tl.fromTo(s.line, { scaleX: 0, opacity: 1 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, Q(ex + 0.55 + i * 0.12));
      tl.fromTo(s.lab, { opacity: 0, x: side === "right" ? -14 : 14 }, { opacity: 1, x: 0, duration: 0.35, ease: "power3.out" }, Q(ex + 0.6 + i * 0.12));
    });
    K.sfx("slide", ex, -23);
    (o.focus || []).forEach((f) => {
      slabs.forEach((s, i) => {
        const on = i === f.i;
        tl.to(s.top, { attr: { fill: on ? C.acc : i === n - 1 ? "#ffffff" : "#fbf8f3" }, duration: 0.25 }, Q(f.at));
        tl.to([s.lab, s.line], { opacity: on ? 1 : 0.32, duration: 0.25 }, Q(f.at));
        tl.to(s.g, { x: on ? (side === "right" ? -18 : 18) : 0, duration: 0.35, ease: "power3.out" }, Q(f.at));
      });
      K.sfx("pop", f.at, -25);
    });
    if (o.focusEnd != null) slabs.forEach((s, i) => { tl.to(s.top, { attr: { fill: i === n - 1 ? "#ffffff" : "#fbf8f3" }, duration: 0.25 }, Q(o.focusEnd)); tl.to([s.lab, s.line], { opacity: 1, duration: 0.25 }, Q(o.focusEnd)); tl.to(s.g, { x: 0, duration: 0.3 }, Q(o.focusEnd)); });
    if (o.collapseAt != null) {
      slabs.forEach((s, i) => {
        tl.to([s.lab, s.line], { opacity: 0, duration: 0.15 }, Q(o.collapseAt));
        tl.to(s.g, { y: yAt(i, thick) - (cy - faceH / 2), x: 0, duration: 0.5, ease: "power3.inOut" }, Q(o.collapseAt + 0.1 + (n - 1 - i) * 0.03));
      });
      K.sfx("hit", o.collapseAt + 0.55, -22);
    }
    return { wrap, slabs };
  };

  // ---------------------------------------------------------------- leaderboard race (pure function of time)
  // Values glide between the data's dates (smoothstep per interval), ranks are re-sorted every frame and the bars
  // glide to their new rows, so an overtake is seen as a physical swap. A lab with no entry on a date fades out.
  HF.raceState = function (data, u) {                                         // u in [0, dates-1] -> [{ name, v, vis }]
    const D = data.dates.length, i0 = Math.max(0, Math.min(D - 2, Math.floor(u))), f = smooth(clamp01(u - i0));
    return data.series.map((s) => {
      const a = s.values[i0], b = s.values[Math.min(D - 1, i0 + 1)];
      const v = a == null && b == null ? null : a == null ? b : b == null ? a : a + (b - a) * f;
      const vis = a == null && b == null ? 0 : a == null ? f : b == null ? 1 - f : 1;
      return { name: s.name, v, vis };
    });
  };
  HF.raceRanks = function (st) {                                              // name -> continuous row (0 = top)
    const live = st.filter((s) => s.v != null && s.vis > 0.001).sort((a, b) => b.v - a.v);   // a lab about to appear isn't ranked yet
    return Object.fromEntries(live.map((s, r) => [s.name, r]));
  };
  HF.race = function (K, parent, o) {
    const d = o.data, n = d.series.length, w = o.w || 1300, rowH = o.rowH || 92, x = o.x, y = o.y, D = d.dates.length;
    const all = d.series.flatMap((s) => s.values.filter((v) => v != null));
    const lo = o.min != null ? o.min : Math.floor((Math.min(...all) - 40) / 50) * 50, hi = o.max != null ? o.max : Math.max(...all);
    const nameW = o.nameW || 230, barMax = w - nameW - 200;
    const wrap = K.el(parent, `left:${x}px;top:${y}px;width:${w}px;height:${n * rowH + 140}px;opacity:0`);
    K.enter(wrap, o.t - 0.4, { y: 30 });
    if (o.title) K.el(wrap, `left:0;top:-90px;font-size:${o.titleFs || 64}px`, o.title, "hf-serif hf-abs");
    const date = K.el(wrap, `right:0;top:${n * rowH + 20}px;font:400 ${o.dateFs || 76}px/1 InstrumentSerif,serif;color:${C.ink2};text-align:right;font-variant-numeric:tabular-nums`);
    K.el(wrap, `left:0;top:${n * rowH + 40}px;font:500 17px JBMono,monospace;color:${C.mute};width:${w - 340}px;white-space:normal`, esc(`${d.metric} · ${d.board} board · ${d.source}`));
    for (let r = 0; r < n; r++) K.el(wrap, `left:0;top:${r * rowH}px;width:40px;height:${rowH - 18}px;display:flex;align-items:center;font:700 26px JBMono,monospace;color:${C.mute}`, String(r + 1));
    const hl = o.highlight || d.series[0].name;
    const bars = d.series.map((s) => {
      const row = K.el(wrap, `left:56px;top:0;width:${w - 56}px;height:${rowH - 18}px`);
      const nm = K.el(row, `left:0;top:0;width:${nameW - 20}px;height:100%;display:flex;align-items:center;font:600 30px Inter,sans-serif;color:${C.ink};white-space:nowrap`, esc(s.name));
      const bar = K.el(row, `left:${nameW}px;top:10px;height:${rowH - 38}px;width:${barMax}px;border-radius:10px;transform-origin:0 50%;background:${s.name === hl ? C.acc : C.ink2}`);
      const val = K.el(row, `left:${nameW + 14}px;top:0;height:100%;display:flex;align-items:center;font:600 28px Inter,sans-serif;color:${C.ink};font-variant-numeric:tabular-nums`);
      void nm;
      return { name: s.name, row, bar, val, y: null };
    });
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const fmtDate = (s) => { const [Y, M, Dd] = s.split("-").map(Number); return `${Dd} ${months[M - 1]} ${Y}`; };
    const ranksAt = (i) => HF.raceRanks(HF.raceState(d, i));
    const T0 = o.t, dur = o.dur || 8;
    // a cue at every change of leader
    let lead = null;
    for (let i = 0; i < D; i++) { const r = ranksAt(i), top = Object.keys(r).find((k) => r[k] === 0); if (lead && top !== lead) K.sfx("pop", T0 + (i - 0.5) * (dur / (D - 1)), -22); lead = top; }
    K.onFrame((t) => {
      const u = clamp01((t - T0) / dur) * (D - 1), st = HF.raceState(d, u);
      // row of each bar: blend the sorted order at the two neighbouring dates by the same smoothstep (swaps glide)
      // rows swap in a short burst in the middle of each interval (read as a move, not as two bars sharing a row)
      const i0 = Math.max(0, Math.min(D - 2, Math.floor(u))), f = smooth(clamp01((u - i0 - 0.3) / 0.4)), rA = ranksAt(i0), rB = ranksAt(i0 + 1), rN = HF.raceRanks(st);
      st.forEach((s, j) => {
        const B = bars[j], a = rA[s.name] != null ? rA[s.name] : rN[s.name], b = rB[s.name] != null ? rB[s.name] : rN[s.name];
        const row = a == null ? n : b == null ? a : a + (b - a) * f;
        B.row.style.transform = `translateY(${(row * rowH).toFixed(1)}px)`;
        B.row.style.opacity = s.vis.toFixed(3);
        const p = s.v == null ? 0 : clamp01((s.v - lo) / (hi - lo));
        B.bar.style.transform = `scaleX(${Math.max(0.01, p).toFixed(4)})`;
        B.val.style.transform = `translateX(${(Math.max(0.01, p) * barMax).toFixed(1)}px)`;
        B.val.textContent = s.v == null ? "" : String(Math.round(s.v));
      });
      date.textContent = fmtDate(d.dates[Math.round(u)]);
    });
    return { wrap, end: T0 + dur };
  };
})(typeof window !== "undefined" ? window : globalThis);
