# kit/web: real websites as film material

- `capture.mjs`: stills and element crops of a live site (phone or desktop), for Reels and cards (2026-10-11).
- `record.mjs`: a frame-exact screen recording of a live site for 16:9 films (2026-10-17, films/ai-portfolio): the page
  runs on a virtual clock (performance.now, Date, rAF, timers; every CSS/Web Animation set to the clock each frame),
  so a 4K60 recording is perfectly smooth and the same twice. Steps: scroll, move (or to a selector), click, type, key,
  eval; `--cursor` draws a pointer, `--date` sets the page's clock, `--debug` prints the page's console errors.
  framer-motion / motion sites: the recorder hides `Element.prototype.animate` from them (moved one prototype up, so
  `element.animate()` still works), because their Web-Animation fades set `startTime` from our clock against a frozen
  document timeline: in-view reveals started late and then lost their end value (Argon's sections came out blank).
  A steps file must not share the output's name (`<out>.json` is written next to the video).
