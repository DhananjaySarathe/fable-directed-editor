/* kit/hf/emoji.js — animated emoji (Google Noto, Lottie, CC BY 4.0: kit/emoji/README.md) for reaction beats.
 *
 *   HF.emoji(K, parent, "fire", t, { x, y, size, until, loops, speed, from, pop })   an animated emoji lands at t and plays
 *     names: kit/emoji/noto/*.json (fire, rocket, mind-blown, thinking, party, hundred, check, cross, eyes, skull,
 *     joy, sob, money-wings, chart-up, trophy, robot, brain-less: see the folder); until: when it leaves (default t + 3);
 *     loops: how many times it plays (default: as many as fit); from: seconds into its animation to start at. Time the
 *     payoff to the word: mind-blown (2.9 s) braces at 0.25 s, bursts at ~0.4 s, smokes until ~1.4 s, then its head
 *     comes back (a flat face, then a plain one): land it 0.4 s before the word with until about 1.45 s after it lands
 *     and loops: 1 (measured frame by frame, 2026-10-20). Snapshot any other emoji the same way before timing it;
 *     pop: false for no spring entrance
 *
 * Frame-exact: the Lottie player (kit/hf/lib/lottie_light.min.js, MIT) never runs on its own clock; every frame the
 * page's time picks the animation's frame (K.onFrame -> goToAndStop). vendor.py inlines only the emoji a page names
 * (HF.EMOJI) and kit/film's build writes the CC BY credit for them into credits.txt. One per beat, on a reaction that
 * means something (a result, a fail, a "wait what"), never as decoration.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/emoji.js needs core.js first");
  HF.EMOJI = HF.EMOJI || {};

  HF.emoji = function (K, parent, name, t, o = {}) {
    const data = HF.EMOJI[name];
    if (!data) throw new Error(`HF.emoji: no "${name}" on this page (kit/emoji/noto/${name}.json; vendor.py inlines the names a page uses)`);
    const size = o.size || 220, until = o.until != null ? o.until : t + 3, speed = o.speed || 1;
    const box = K.el(parent, `left:${o.x || 0}px;top:${o.y || 0}px;width:${size}px;height:${size}px;opacity:0`);
    let anim = null;
    if (root.lottie) {
      anim = root.lottie.loadAnimation({ container: box, renderer: "svg", loop: false, autoplay: false,
        animationData: JSON.parse(JSON.stringify(data)), rendererSettings: { preserveAspectRatio: "xMidYMid meet" } });
    } else box.textContent = "";                              // no player on the page: the box stays empty (never breaks)
    // HyperFrames' own Lottie adapter seeks every registered animation from its composition's start (0 s on a film page)
    // after the timeline renders, which pins an emoji to its last frame. The kit drives this one from the page clock
    // instead: keep the real seek, and give the adapter a no-op (tested on hyperframes 0.8.134, 2026-10-20).
    const go = anim ? anim.goToAndStop.bind(anim) : null;
    if (anim) anim.goToAndStop = () => {};
    const frames = data.op - data.ip, fps = data.fr || 30, loops = o.loops, skip = (o.from || 0) * fps;
    K.onFrame((now) => {
      if (!anim) return;
      const local = skip + Math.max(0, now - t) * speed * fps;   // frames since it landed (+ the frames it skips)
      const f = loops != null && local >= loops * frames ? frames - 1 : local % frames;
      go(data.ip + f, true);
    });
    const tl = K.tl, Q = K.Q;
    if (o.pop === false) tl.fromTo(box, { opacity: 0 }, { opacity: 1, duration: 0.15, immediateRender: false }, Q(t));
    else {
      const sp = HF.spring ? HF.spring(HF.SPRING.thrown) : { duration: 0.5, ease: "back.out(2)" };
      tl.fromTo(box, { opacity: 0, scale: 0.3, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(t));
    }
    tl.to(box, { opacity: 0, scale: 0.85, duration: 0.25, ease: HF.E ? HF.E.out : "power2.in", immediateRender: false }, Q(until - 0.25));
    if (o.sfx) K.sfx(o.sfx, t + 0.05, o.db != null ? o.db : -20);
    return { box, anim };
  };
})(typeof window !== "undefined" ? window : globalThis);
