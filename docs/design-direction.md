# Interface rework — design direction

Consolidated direction from a four-person design panel (junior UI / mid product /
senior visual / design director, 2026-06-06) for reworking the soccer26 interface to
look **genuinely professional**. This is the master plan; the engineering-side
critique it builds on is `docs/frontend-improvement-plan.md` (QW/M/L items, referenced
below). The four reviews were strikingly convergent — what follows is their agreement,
not a compromise.

---

## North star — "an instrument, not an app"

This is a credibility product; its entire value is "you can trust these numbers because
we show our work." Professionalism here means it should read like a **data/finance
publication or a quant terminal**, not a neon betting app. Five principles:

1. **Calm authority over excitement** — confidence via restraint, not gradients and glow.
2. **The data is the hero; chrome recedes** — every decoration must aid comprehension.
3. **Honesty made visible** — caveats, uncertainty, freshness get real visual weight (the caveat *is* the product).
4. **Systematic consistency** — one raw `OVER_2_5`, one dead form, one drifted padding reads as "broken deploy." Nothing may look unfinished anywhere.
5. **Earned, invisible polish** — if the user notices the animation, it's too much.

**Honest read:** the foundation is genuinely strong (tokenised, tabular-nums, good a11y
bones) — already "competent." It misses "premium" by ~20%, and the gap is **discipline,
not a rebuild**: it's turned up about 20% too loud (3 brand accents + 7 stage colours +
a triple radial body wash + glow), has no real type/space scale, soft over-blurred
elevation, and consistency cracks at the edges. The trust pages (calibration,
methodology) ironically look the *least* finished.

---

## The token spec (apply in `Base.astro :root`)

### Colour — one accent, semantic discipline
- **Green is the brand AND the "good/edge" signal**, used like punctuation (≤2 green
  fills per viewport). Slightly desaturate: `--accent: #1fe07a → ~#2bd47f`.
- **Demote magenta + cyan out of the brand** — they read "neon betting app." Keep them
  only as *data-viz / categorical* roles, never as UI chrome or decoration.
- **Body wash: 3 radials → 1** subtle green at ~0.05 (✅ done). Remove per-panel
  top-wash + hero glow stacks (up to 6 overlapping gradients today).
- Distinguish `--neg`(loss red) from magenta so they never collide; lift `--muted`/
  `--muted-2` for AA on small text.

### Stage ramp — single-hue, intensifies toward the Final (replace the rainbow)
cool blue (group) → teal → green → **gold (final)**; third-place = neutral grey
(off-ramp, not "hot"). Encodes progression instead of arbitrary colour.

### Data-viz tokens (fix the ProbBar/MatchCard drift)
`--viz-home / --viz-draw / --viz-away` (+ ink) as flat fills, tokenised once (today
they're hard-coded *differently* in ProbBar vs MatchCard). Draw segment uses **light**
ink for contrast; prefix wide segments with `H/D/A` for colour-blind redundancy.

### Type — one modular scale, Sora for display only, cap weight at 700
~22 ad-hoc sizes today. Formalise (16px root): display `--fz-display 2.25rem` / h1
`1.75` / h2 `1.375` (current 1.25 collapses hierarchy — bump it) / stat `1.875` / body
`1rem` / sm `0.875` / xs `0.8125` / micro `0.6875` (one uppercase-label spec). **Drop
all `font-weight:800`** (the loudest "sporty" tell) → cap at 700. Enable
`slashed-zero` + the **true minus `−` (U+2212)** for negatives; one `signed()`/`money()`
formatter in `data.ts` (M-7).

### Elevation — flatten + sharpen
Tighter, lower shadows (✅ `--shadow-md/-lg` halved); depth via **border + surface
step**, not blur. Hover = `translateY(-1px)` + `--shadow-md` + `border-strong`, not a
big shadow bloom. Radii tightened (✅ 16→13 panels, 22→18 hero).

### Spacing — an 8px scale + `.stack`/`.section` utilities
Replace the dozens of inline `margin-top:*` with `--sp-1..16` tokens and a `.section`
utility (one value for section rhythm; one for hero padding — kills the confirmed
3-way hero-padding drift).

### Motion — one language (✅ tokens added: `--ease`, `--dur-fast`, `--dur`)
Replace the 5 ad-hoc durations. Add ONE restrained entrance (`@starting-style` fade-up
on card grids, ≤250ms, reduced-motion-gated). Hover micro-interactions stay; nothing more.

---

## Roadmap (phases — each sits on the previous)

**Phase 0 — Foundation (mostly invisible, drift-proofs everything after):**
motion + spacing + type tokens; globalise duplicated CSS (`.sr-only` ✅, `.hero-chip`,
`.callout`, `.see-all`, `.cards-grid`); a `PageHero` component (QW-5); the formatter
module (M-7); `marketLabel()`/`selectionShort()` so no raw code leaks (✅ partial);
skip link ✅ + focus-visible radius fix ✅; `theme-color` ✅; `data-label` on table `td`s.

**Phase 1 — High-visibility visual upgrades ("now it looks professional"):**
colour-discipline pass (✅ first cut: body wash, nav tint, hero de-gradient, flatter
panels) — finish: demote magenta/cyan, desaturate green, re-ramp stages; elevation
retune ✅; type-scale formalisation; **hero treatment for /calibration + /methodology**
(M-8 — fix the inverted trust-page hierarchy); dashboard primary CTA + reorder (M-3);
kill dead newsletter form ✅; sanitise public empty states (✅ dashboard; finish edges/
matches/outrights/calibration).

**Phase 2 — Polish & delight (restrained):**
mobile dense-table card-collapse (M-1/TASK-023); ProbBar contrast + H/D/A cue (M-2);
card-grid breakpoint smoothing (QW-6); one `@starting-style` entrance (M-6); nav fade
mask + active-into-view (✅ scroll; mask TODO); tooltip tap-to-open + edge-flip (M-5);
equity-curve aspect fix (QW-8) + stage-legend parity (QW-7); flag rendering (M-9).

**Phase 3 — Larger structural:**
mobile bottom tab bar (L-1/TASK-017, "Today · Edges · Matches · Bracket · Track record");
live "command-centre" dashboard (L-2); print stylesheet (light theme *deprioritised* —
dark is part of the brand; ship print only); match-page micro-charts incl. score-matrix
heatmap (L-3). Optional IA rename "Dashboard → Today".

---

## Guardrails — what NOT to do (the trust is fragile)
- **No "you're winning" celebration** — no confetti, count-ups on P/L, flashing VALUE!
  badges, or urgency timers. The pulsing live dot is the ceiling for that kind of motion.
- **No more accent colours** — the pass *reduces* the palette; colour is for signal only.
- **No over-animation / no heavy elevation theatre** (glassmorphism stacks, big drop
  shadows). Depth stays quiet.
- **Don't bury the honesty** — caveats keep visual weight, never demoted to grey fine print.
- **Never let raw data leak** — no `OVER_2_5`, `match_id`, "run python", dead controls.
- **Don't drift toward "tips"** — no "our pick", confidence stars, "lock of the day",
  or sportsbook-logo endorsements. Analysis, not advice — in design *and* copy.
- **Don't gold-plate the model UI ahead of the data** — design honest empty containers
  for CLV/calibration; fill them once the closing-odds capture runs.

---

## Progress log

**Batch 1 — discipline pass (✅):** body wash 3→1 (magenta/cyan out); active nav
green-fill → accent tint; hero title gradient-text → solid + one accent phrase
("graded in public"); `.panel` top-wash removed + shadows flattened; radii 16→13 /
22→18; motion tokens (`--ease`/`--dur-fast`/`--dur`); `theme-color`; skip link +
global `.sr-only`; `:focus-visible` radius fix; nav active-pill scroll-into-view;
`selectionShort()` (no raw codes on dashboard tiles/badge); dead newsletter form →
RSS CTA; dashboard empty-state dev-copy sanitised.

**Batch 2 — tokens + hierarchy (✅):** stage colours re-ramped to a single cool→gold
progression (3rd = neutral grey) — verified on the bracket; **data-viz tokens**
`--viz-home/draw/away` (+ ink) tokenised across ProbBar *and* MatchCard (ends the
hard-coded colour drift; draw uses light ink for contrast); type scale — **h2
1.25→1.4rem** (fixes the collapsed section hierarchy), h1/h3 retuned, `font-weight`
800→700 on h1/stat-value (drops the "sporty" weight), `slashed-zero` on numerics;
**`PageHero` component** created + applied to **/calibration** (gave the flagship
trust page the hero it lacked — M-8) with sanitised empty-state; **stat-cards**
retuned — decorative `::after` top stripe → left-rail accent, **magenta demoted to
neutral**. Build clean (174 pages); verified in-browser (bracket, calibration, match
cards) — visibly more cohesive/editorial.

**Batch 3 — SHARP pass (✅, owner feedback: "corners too rounded, want it sharper"):**
see the dedicated research spec `docs/sharp-direction.md`. Applied: radii **6px panels /
4px controls / 8px hero** (was 13/9/18); **de-pilled every chip/pill/badge/tag** sitewide
(`999px` → `--radius-sm`) keeping only true circular status dots round — the "loudest
soft-app tell"; **crisper higher-contrast hairlines** (`--border` #262c4a → #303863 etc.);
brand crest + prob bars sharpened. Build clean (174 pages); verified — reads markedly sharper/engineered.

**Batch 4 — sharp typographic + elevation follow-up (✅, completes `sharp-direction.md`
moves 4–7):** added **JetBrains Mono** (`@fontsource-variable/jetbrains-mono`, `--font-mono`)
and applied it to **all numerals + micro-labels** — table numeric cells + mono uppercase
headers, stat values/labels, eyebrows, dashboard hero-chip counts + edge-tile %s, the
matchday clock, the exposure strip, match-card scores/probs — the "quant terminal" signal;
**flattened elevation** (`.panel` + `.match-card` → no blur shadow, depth via 1px border +
inset catch-light; hover = border-step + 1px, not a lift/bloom; shadow tokens reserved for
floating layers; **killed the crest glow**); **ruled, denser tables** (row padding
0.7→0.5rem, font 0.92→0.875rem, hairline header rule); **capped weight at 700** everywhere
(brand/score/stat 800→700); tighter h1/h2 tracking (−0.03em); flattened the body wash to
~0.03. Build clean (174 pages); verified — dashboard + edges now read like a precise data
instrument.

**Batch 5 — green calm + mono sweep + column rules (✅, owner feedback):**
- **Green muted** (owner: neon green too bright / eye-straining): `--accent #1fe07a→#2fb672`,
  `--accent-2→#209a5b`, soft/line + body wash recoloured; **bright-green glows removed**
  (group-letter + dashboard hero glows → inset highlight; dashboard hero magenta wash
  dropped, green wash lowered); page-hero washes + OG-card accent recoloured to the muted
  green. Much calmer; still clearly the positive/edge signal.
- **Mono sweep finished** — every remaining Sora-800 display figure is now mono-600 +
  slashed-zero: team/group stat counts, outrights hero-chip + leaderboard %, predict
  scoreboard, methodology ledger values, match-page score/VS/Elo. All numerals sitewide
  are now mono and consistent.
- **Vertical column rules** added to tables (`th/td:not(:last-child) border-right`) — the
  ruled-ledger / spreadsheet look; kept subtle (`--border-soft`) so it reads engineered,
  not wireframe. Verified in-browser (edges table) — owner to confirm the level.

Build clean (174 pages). The sharp/calm direction is essentially complete on desktop.

**Batch 6 — dampen the white (✅, owner: near-white text glared):** `--fg #eef1fb →
#cfd5e4` (softer light grey-blue; still ~12:1 on `--bg`, well above AA), `--muted`/
`--muted-2` nudged to match. Green + column rules confirmed kept. The palette is now
fully calm: muted emerald accent, softened off-white text, dark canvas, mono numerals,
sharp corners, ruled tables. (Near-white literals left where appropriate: prob-bar
draw-segment ink needs light on its slate fill; OG share-card text stays bright.)

**Batch 7 — Phase-2 mobile (✅ core):**
- **Bottom tab bar** — new `MobileNav.astro` (fixed bottom, 5 primary routes
  Today/Edges/Matches/Bracket/Record with inline-SVG icons + mono labels, active state,
  `env(safe-area-inset-bottom)`-aware, `backdrop-filter`). Shows ≤720px; rendered in
  `Base.astro` with footer bottom-padding so content clears it. Top scroller kept for
  secondary routes.
- **Dense-table → card collapse** — global `.table--cards` modifier (≤560px: `thead`
  hidden, rows become bordered cards, each `td` a `data-label:value` row, first cell the
  card heading, column-rules + right-align reset). Applied (class + `data-label`s) to the
  **edges** table (verified — EV/Kelly-stake no longer off-screen), the **outrights**
  9-col table (verified), and the **bets** log (Match reordered to first as the heading).
  CSS-only, no JS. Desktop unaffected (media-query-gated; verified full ruled tables +
  no bottom bar above 720px).

**Batch 8 — table sweep complete (✅):** extended `.table--cards` to **every** remaining
wide table — match-page edges + bets, team-page edges (`.tm-edges`), group-page edges
(`.gr-edges`), and the **bookmaker-odds** table (dynamic columns; `data-label`s use the
team-name vars — verified collapsing on a phone). Group standings (`GroupCard`) left as a
scroll-table on purpose (standings are a compare-grid, not per-row cards). Also fixed the
bookmaker styles' leftover bright-green glow + round corner + 800-weight (now muted/sharp/
mono). Verified mobile (bookmaker + edges collapse cleanly) and desktop (full ruled tables,
no bottom bar). Build clean (174 pages). **Phase-2 mobile is done.**

**Batch 9 — finishing touches (✅):**
- **Entrance motion** — one restrained `main` fade-up on load (`page-rise` keyframe,
  `prefers-reduced-motion`-gated). The single tasteful "settles in" touch.
- **`PageHero` retrofit** — globalised the `.hero-chip`/`.hero-chips` styles (were
  redeclared on 6 pages, with drift) into `Base.astro`, then converted the **groups
  (cyan), outrights (gold), bracket (violet)** heroes to the shared `PageHero`
  component (unified padding/gradient — fixes the confirmed 3-different-padding drift;
  deleted ~3 duplicated hero CSS blocks). Verified outrights + dashboard chips render
  via the global styles.
- **True-minus formatter (M-7)** — `signed()`/`signedPct()`/`money()` (real `−` U+2212)
  in `data.ts`, applied to the P/L, ROI, and CLV displays on `/bets` and the dashboard
  bankroll cards so negatives align cleanly in the mono columns.

Build clean (174 pages). **The redesign is essentially complete.**

**Intentionally left:** the **dashboard** hero (bespoke big landing hero), the **team**
and **group/[id]** heroes (custom flag/stat layouts) keep their own structure — they use
the global `.hero-chip` and the shared tokens, so they're consistent without forcing them
through `PageHero`. A full inline-margin → `.section`-utility sweep was judged low-payoff
code-cleanup and deferred (the spacing reads consistent as-is).

**Remaining (per the phases above + `sharp-direction.md`):** retrofit
groups/outrights/bracket/team heroes to `PageHero`; finish demoting magenta/cyan + green
desaturation; spacing scale + `.stack`/`.section` utilities; `signed()`/`money()` +
true-minus formatter (M-7); mono numerals + flat-elevation/ruled-tables (sharp follow-up);
`@starting-style` entrance; then Phase 2 mobile (table→card collapse, bottom tab bar) +
dashboard primary-CTA/reorder (M-3).
