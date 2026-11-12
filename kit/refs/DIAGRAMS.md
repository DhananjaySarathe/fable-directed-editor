# Diagrams: when to draw one, which one, and how it reads on the white page

> Kit v11, 2026-10-22 (the owner's "holistic, not heavy": the purpose shown neatly). Rules adapted from
> cathrynlavery/diagram-design 2.6 (MIT): its style guide, connector rules, complexity budgets, routing and motion
> spec, restated here for a 1080p frame and our whitespace look. The geometry gate is a port of its
> `verify-geometry.py` (notice: `kit/hf/lib/diagram-design.LICENSE`). Engine: `kit/hf/diagram.js` style `"flat"`.
> Fixture: `kit/hf/demos/diagram/`. The planning gate (`kit/refs/SCENES.md` → `plan_check.py`) still comes first.

## 1. When to draw

Only when the viewer learns more from the picture than from his sentence: how parts fit, what feeds what, where
the loop goes back. Otherwise pick the plainer scene:

| The passage is | Draw | Not a diagram |
|---|---|---|
| a list he reads out | | a checklist or the takeover `list` kind |
| one claim | | a statement (takeover `type`) |
| A against B | | `HF.compare` |
| steps, a loop, a hub, layers, a tree | **a flat diagram** | |

It is a face-off passage (SCENES.md §9: process, mechanism, relationship or chronology, 5 s or more) built as
`C.takeover(a, b, { kind: "diagram", ... })`, or an `HF.diagram` on a station.

## 2. Pick the type from what the passage does

| What the passage does | Type | How |
|---|---|---|
| ordered steps | process | `layout: "row"` (9:16: `"column"`), edges to the next node |
| a repeat with a way back | loop | a row plus the edge back (`{ from: last, to: first, label }`): it runs under the row, dashed |
| many into one, one into many | hub / fan-in | `layout: "hub", hub: id`; fan-in when most edges end at the hub (it sits on the right) |
| levels | layers | `layout: "column"`, top to bottom |
| parts of a whole | tree | explicit `x` / `y` per node (centres), at most 3 levels on screen |
| before / after | compare | `HF.compare`, not a diagram |
| two axes | quadrant | a card with four cells, not a diagram |

Pass the type as `type` (published in `window.__diagrams`; plan_check budgets by it).

## 3. Budgets (one takeover of 4-12 s)

- At most **5 nodes** on 16:9 (**4** on 9:16, in a column), **6 edges**, **2 focal nodes** (normally 1: the part he
  names), **1** annotation chip, **one** flow token.
- Names are 1-2 words; a sub line a few words; an edge label at most **14 characters**.
- Five boxes fit 1680 px only with short names (about 6 characters at 48 px); longer names, fewer boxes.
- **The deletion test, before building:** can a node go? Can two merge? Can an arrow or a label go?
- Over budget: split it into an overview station and a detail station and let the camera move between them.

The engine says every overrun in the console (`HF.diagram (flat): ...`).

## 4. Geometry (1080p; the engine does all of it)

- A 4 px grid. Boxes at least 176 px tall (9:16: 128, tag inline), at least 112 px apart (9:16: 88), radius 18,
  a 2 px hairline at 16 % ink. One size for every box in a diagram.
- Connectors run straight when their ends line up; otherwise they turn at right angles with r 20 elbows. Never
  diagonal, never curved.
- A connector leaves and enters perpendicular to a side, at least 22 px from a corner. The ports on a side fan out at
  L k / (n + 1), at least 32 px apart: no two connectors ever share a point (a way back between neighbours used to
  land on the way there's start point).
- No line passes behind a box that is not one of its ends: a way back runs **under** the row (a column: on its
  right), a skip forward **over** it (a column: on its left); nested lanes 72 px apart, the longest outside.
- Connectors that fan out of one side turn in order, the outermost first, so no leg crosses another's run.
- Way-back and optional edges are dashed 12/10.
- Edge labels: caps mono kicker on a paper mask, 10 px off the stroke (on a lane, on the side toward the boxes).
- Paint order: lines, then labels, then boxes.
- The block sits inside 120 px margins: the boxes centred across, the whole block centred down.

## 5. Type (whitespace: 3 sizes)

| | Font | Size (9:16) |
|---|---|---|
| kicker: the eyebrow, tags, edge labels | JetBrains Mono 500, caps, 0.14 em, `HC.sub` | 26 px (30) |
| node name | Inter 600, -0.02 em, ink | 48 px (52) |
| sub line | Inter 500, `HC.sub`; mono only for technical values (`1080p`, a command) | 32 px (34) |

No H1 on the diagram: his voice says the title. The eyebrow (`title`) is a few words over the first box.

## 6. Treatments

- A box: white with the hairline, flat.
- **Focal** (`focal: true`, or `dg.highlight(id, t, until)` while he names it): accent tint fill, accent stroke and
  name, lifted to e3 (whitespace README §3: the part he means is raised).
- Input or an outside system (`kind: "input"` / `"external"`): sunk grey (#F5F5F7).
- Optional (`kind: "optional"`): a dashed hairline.
- No other shadow, glow or ring on any box. The accent marks at most the focal node, its way back and the token.

## 7. Motion (on the paused timeline: every frame seeks the same)

- At most 2 items enter in one step (0.48 s); a step is a 16 px rise with opacity. No zoom, bounce or blur on boxes:
  the energy is the camera's (the takeover's push, `dg.focus` / `dg.overview`).
- Edges draw on, at most 2 at once; a label rises with its edge.
- One flow token per diagram, one lap every 3 s or more (`dg.flow([[a, b], [b, c], [c, a]], t)` runs the loop).
- Every reveal lands on his word (`K.W(id)`), never on a beat of its own.
- The end frame is complete and still: a paused frame tells the whole idea.

## 8. Building one

```js
// a takeover (the usual way): on whitespace the diagram is flat by itself
C.takeover(a, b, { kind: "diagram", type: "loop", title: "the loop", in: "fade", out: "fade",
  nodes: [{ id: "build", label: "Build", sub: "HTML + GSAP", mono: true, at: K.W(212) },
          { id: "draft", label: "Draft", sub: "1080p", mono: true, at: K.W(218) },
          { id: "critic", label: "Critic", sub: "checks every frame", focal: true, at: K.W(225) }],
  edges: [["build", "draft", K.W(218)], ["draft", "critic", K.W(225)],
          { from: "critic", to: "build", t: K.W(231), label: "fix what broke", accent: true }],
  flows: [["critic", "build", K.W(233), { period: 3.2 }]] });

// or on a station / layer
const dg = HF.diagram(K, layer, { style: "flat", type: "hub", layout: "hub", hub: "page", title: "one page",
  nodes: [{ id: "page", label: "The page", kind: "input" }, { id: "look", label: "Look" }, { id: "cam", label: "Camera", focal: true }],
  edges: [["page", "look"], ["page", "cam"]] });
dg.show(a, b).reveal("page", t1).reveal(["look", "cam"], t2, 0.24).connect("page", "look", t2).connect("page", "cam", t2 + 0.3);
```

Edges: `[from, to]` or `{ from, to, route: "straight" | "z" | "L" | "under" | "over", dash, label, accent }`. Nodes:
`{ id, label, sub, mono, tag, focal, kind }`; tags number a row or column ("01", ...) unless `steps: false` or a node
names its own (`tag: "L1"`). The rest of the API is the living diagram's (`show`, `reveal`, `connect`, `connectAll`,
`focus`, `overview`, `done` (the tag becomes a check), `highlight`, `note`, `flow`).

## 9. The geometry gate

Every diagram publishes `window.__diagrams` (its boxes and each connector's points, in its view's px).
`HF.diagram.verify(entry)` returns one line per defect: a diagonal segment, a run along a box's border, a line
behind a box that isn't one of its ends, a port within 22 px of a corner, two ports on one side under 32 px apart
(an arriving and a leaving one count too), two connectors within 3 px of each other for more than 11 px, a label on
a box, on another label or on a line. Flat entries carry `gate: true`; circle and card (curves by design) carry only
their end points.

```sh
uv run python kit/hf/demos/diagram/build.py && node kit/hf/demos/diagram/shoot.mjs   # stills, the gate, seek purity
uv run pytest -q tests/test_diagram_flat.py
```

## 10. The old styles

`shape: "circle"` (icon discs) and `"card"` stay the default on every other look and draw exactly what they drew
(a pixel diff of films/expensewaale's two diagrams, 2026-10-22). Two fixes are opt-in there: `margin: 120` (the
boxes, not just their centres, inside the margins) and `ports: "fan"` (an edge and its reverse 32 px apart).
`C.takeover`'s diagram kind passes both.

## 11. Not taken

- From diagram-design: its document-scale type and web fonts, interactive controls, onboarding, brand icons, the
  "paper is warm, never pure white" rule (he chose white), the page-wide "no shadows" rule (the focal box keeps its
  e3), its sketchy filter (`HF.sketch` covers that register).
- From shader-effects-inc/shaders (studied the same day): nothing. It needs WebGPU, which the default software
  render path doesn't have; its grounds turned the white page grey or vanished after encoding while costing
  bitrate, and its dissolve broke type apart. **No shader ground and no grain on the whitespace page**; a lit field,
  a highlight sweep or a soft reveal, if he ever wants one, is CSS and GSAP.
