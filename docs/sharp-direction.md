# Sharp / precise / premium — visual direction

Owner direction: the current UI is **too soft/rounded**, "not sharp enough." This spec
defines a decisive shift to a **sharp, crisp, engineered** look without contradicting the
existing north star in `docs/design-direction.md` ("an instrument, not an app"). Sharpening
*is* the natural next step of that plan: a finance/quant terminal reads as precise because
its corners are tight, its rules are crisp, and its depth is flat — not because it is round
and soft. This is a discipline pass, not a rebuild; almost everything here is a token edit in
`Base.astro :root` plus a handful of per-component radius/border swaps.

**Reference north stars (cited inline below):** Linear (1px inset borders, ~4-step surface
scale, opacity-based depth, no shadow theatre), Stripe Dashboard (4px Elements radius as the
"sharp" baseline), Vercel/Geist (Geist Mono, blueprint-grid hairlines), Bloomberg Terminal
(Neue Haas Grotesk + commissioned finance numerals), The Economist / FT (Econ Sans condensed,
sans-serif tabular data), FiveThirtyEight tables, and Swiss/International-typographic editorial
design (visible grid, hairline rules, uppercase micro-labels). General "premium UI" practice
from the Mantlr/pixeldarts breakdowns of Stripe/Linear/Vercel: hairlines at 0.5–1px low alpha,
a monochrome foundation with "nothing muddy in between," and one rationed accent.

---

## 1. Corner radius — go genuinely sharp

The current system is round: `--radius: 13px`, `--radius-lg: 18px`, and **999px pills/chips/
badges everywhere**. That pill geometry is the single loudest "soft app" tell — fully-round
pills read as consumer/social (Slack unread bubbles), not as an instrument. We square them to
**rounded-rects** and tighten everything else toward the Linear/Stripe 4–8px band, leaning to
the sharp end of it because the owner explicitly wants sharper.

Per-element targets:

| Element | Now | Target | Rationale / reference |
|---|---|---|---|
| Page panels / `.panel` | 13px | **6px** | Stripe Dashboard sits at 4–8px; 6px reads engineered but not brutalist. |
| Data containers / `.table-wrap` | 13px | **4px** | Tables want the tightest corner — they are grids, not cards (FT/FiveThirtyEight). |
| Cards (`.match-card`, stat cards) | 13px | **6px** | One step softer than tables so cards still feel like objects; matches panels. |
| Hero / large surfaces (`--radius-lg`) | 18px | **8px** | Big radii are what reads "soft"; cap the largest at 8px. |
| Inputs / selects / buttons | 9px | **4px** | Crisp controls; Stripe Elements default is 4px. |
| **Pills / chips / nav links** | 999px | **4px** | The headline change: pills → squared rounded-rects. Linear's outlined pills use small radii, not capsules. |
| Badges (`.badge`, `.pill`, `.stage-chip`) | 999px | **3px** | Even tighter than chips — badges are labels/tags, near-rectangular. |
| Code inline, footer `.rg-tag` | 6px | **3px** | Bring incidental chrome into the sharp scale. |
| ProbBar / `.mc-bar` segments | 10px / 999px | **2px** (outer); **0** seg joins | A precise gauge, not a lozenge; square the internal segment boundaries. |
| Small dots (live dot, stage dot) | 999px | **keep 999px** | True circles (status dots, crest, avatars) stay round — a dot is a dot. |
| Focus ring offset shape | — | **follow element** | Ring inherits the new (sharper) radius. |

**Where a little softness still belongs:** genuine circles (status/live dots, the crest,
flag/avatar masks) and nothing else. Everything rectangular goes to the 2–8px scale. Do **not**
go to 0px globally — pure 0 on dark cards reads cheap/brutalist and fights antialiasing on
1px borders; 2–6px keeps it "precision-machined" (Teenage Engineering / Braun) rather than raw.

New tokens:

```css
--radius:    6px;  /* was 13px — panels, cards */
--radius-sm: 4px;  /* was 9px  — inputs, chips, nav, table-wrap */
--radius-lg: 8px;  /* was 18px — hero / largest only */
--radius-xs: 3px;  /* NEW — badges, tags, inline code */
--radius-pill: 4px;/* NEW — replaces literal 999px on chips/nav/pills */
/* keep 999px ONLY for true circles (dots, crest, avatars) */
```

---

## 2. Borders & hairlines — crisp, higher-contrast, "engineered"

Today's borders are the muddy low-contrast blue-greys the owner is reacting to:
`--border #262c4a`, `--border-soft #1c2138`, `--border-strong #353d66` — all sit only a few
points off the surfaces, so edges read as a smudge, not a line. Premium dark UIs (Linear,
Vercel) earn their crispness from **clean, slightly-higher-contrast 1px hairlines** —
"nothing muddy in between" (Mantlr on Stripe/Linear/Vercel). Linear specifically gives cards
presence through **1px inset borders**, not fills.

Moves:

- **Lift border contrast and neutralise the hue.** The blue-violet tint in the borders is
  part of what reads "soft/murky." Shift toward cooler near-neutral slate so lines read as
  *drawn*, not *glowing*:
  ```css
  --border-soft:   #20253c;  /* was #1c2138 — quiet dividers, table rows */
  --border:        #313a5e;  /* was #262c4a — default object edge, +contrast */
  --border-strong: #46507e;  /* was #353d66 — emphasis / hover */
  --hairline:      rgba(190, 200, 230, 0.10); /* NEW — alpha rule for overlays/insets */
  ```
  This is a contrast lift (~1.5–2× delta vs surface), not a brightness blowout — keep it
  restrained so it stays "instrument," not "wireframe."
- **All structural lines are crisp 1px.** No sub-pixel blur, no gradient-fade rules where a
  line is doing structural work. The decorative fade rule (`.section-head .rule`) may stay as
  an editorial flourish, but table/panel/row borders become solid 1px hairlines.
- **Use grid lines as an aesthetic (Swiss / blueprint-grid, Vercel).** Add visible **column
  separators** in dense tables (`td { border-right: 1px solid var(--border-soft) }` on
  numeric columns, last cell excepted) so tabular data reads as a ruled ledger. This is the
  FiveThirtyEight / FT "ruled table" look and directly buys "engineered."
- **Inset 1px top-highlight, sparingly.** A single `inset 0 1px 0 rgba(255,255,255,0.04)` on
  raised cards gives a crisp catch-light edge (Linear's inset-border trick) — far sharper than
  a blur shadow. Drop the existing card top-gradient wash (`linear-gradient(180deg, --elev …)`)
  in favour of this hairline.

---

## 3. Elevation — flat + bordered, depth without blur

The plan already halved shadows; finish the job. A sharp UI signals depth through
**surface-step + 1px border + a tight 1px contact shadow**, never soft bloom. Linear models
this exactly: opacity-based hierarchy and a narrow surface stack, *no* heavy drop shadows.

- **Default cards/panels: zero blur-shadow.** Depth = `background: --surface` (one step above
  canvas) + `1px var(--border)` + optional inset top-highlight. Replace `box-shadow: --shadow`
  on `.panel` and `--shadow-md` on `.match-card` with **none**.
- **Reserve shadow for truly floating layers only** (dropdowns, tooltips, modals, sticky
  header on scroll). Make those a tight, dark, low-spread contact shadow rather than the
  current soft halos:
  ```css
  --shadow:    0 1px 0 rgba(0,0,0,0.5);              /* hairline contact, not a glow */
  --shadow-md: 0 4px 12px -6px rgba(0,0,0,0.6);      /* floating layers only */
  --shadow-lg: 0 12px 28px -14px rgba(0,0,0,0.65);   /* modals only */
  ```
- **Hover = sharpen, don't lift.** Replace `translateY(-3px)` + shadow bloom on cards with a
  **border-colour step to `--border-strong`** (and at most `translateY(-1px)`). The card gets
  *crisper* on hover, not floatier — consistent with the "earned, invisible polish" guardrail.
- **Kill the green box-shadow glow on the crest** (`0 4px 14px -4px rgba(31,224,122,0.6)`) and
  any remaining glow — glow is the antithesis of sharp. The crest can keep its fill + a 1px
  inset highlight only.

---

## 4. Typography — make the pairing pull its weight toward "sharp"

Inter is a strong sharp choice (it's literally Linear's typeface, set 510/590). **Sora,
however, is geometric-friendly and slightly soft** — its roundness on display headings and
big stat numerals quietly works *against* the sharpening. Two options, in order of preference:

- **Recommended:** keep Inter for body, switch display to **Inter Display / Inter tight**
  (one family, tighter tracking) and introduce a **mono for all numerals/labels**. One sans
  family reads more disciplined and Swiss; Bloomberg/FT/Economist all run a single grotesque
  for everything (Neue Haas Grotesk; Econ Sans). This drops Sora.
- **If Sora stays** (lower-effort), confine it to large display headings only and never to
  numerals — numerals must move to mono.

Concrete typographic moves:

- **Add a mono for numerals, codes, and micro-labels.** This is the highest-leverage "quant
  terminal" lever. Use **Geist Mono** (Vercel's; compressed, sharp terminals, pairs cleanly
  with Inter) or **JetBrains Mono / IBM Plex Mono** as fallback — all have tabular figures by
  default.
  ```css
  --font-mono: "Geist Mono", "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  ```
  Apply to: stat values, table numeric cells (`td.num`), odds/edge/xG figures, kickoff
  timestamps, eyebrow/micro-labels. Keep `tabular-nums slashed-zero` and the true minus
  `−` (U+2212) already planned in M-7. Mono numerals are *the* signal that says "data
  instrument" (Bloomberg's commissioned finance numerals are the canonical reference).
- **Tracking: tighten display, open micro-labels.** Sharp = tight headings + wide caps labels:
  - h1/h2/display: `letter-spacing: -0.03em` (was -0.025/-0.02) — crisper, more grotesque.
  - Uppercase micro-labels (`.eyebrow`, `.stat-label`, `th`): `letter-spacing: 0.12–0.16em`,
    `font-weight: 600`, `font-size: 0.6875rem` (the "micro" step from the type plan). Swiss
    editorial uppercase labels are a free "engineered" win.
- **Cap weight at 700, kill 800.** The plan already flags `font-weight:800` as the "sporty"
  tell; it survives in `.brand` (800), `.mc-score` (800), `.mc-vstag` (800), `.mc-name` foot.
  Drop all to 700. Sharp comes from *contrast and tracking*, not fat weights.
- **Lower body line-height a touch** for density: `1.55 → 1.5` on body, `1.7 → 1.55` on
  `.prose` (still readable; reads tighter/more tabular).

---

## 5. Density, grid & layout — tighter, aligned, visibly structured

Sharp UIs look *engineered* because their structure is visible and their alignment is exact.

- **Tighten the grid gutter and card padding one notch.** `.grid { gap: 1rem → 0.75rem }`;
  `.panel { padding: 1.25rem 1.4rem → 1rem 1.15rem }`; `.match-card` padding to `0.85rem 1rem`.
  Denser = more terminal-like (Linear's instrument-panel density).
- **Tighten table row height** for a ledger feel: `th, td { padding: 0.7rem 0.95rem →
  0.5rem 0.8rem }`, `font-size: 0.92rem → 0.875rem`. Add the vertical column rules from §2.
  This is the FiveThirtyEight / FT dense-table aesthetic.
- **Make structure an aesthetic, not just a divider.** Lean into the existing `.section-head`
  rule, add a **thin top rule above each major section** and align everything to the 8px
  spacing scale already planned (`--sp-1..16`). Visible rules + exact alignment = Swiss.
- **Right-align all numerics** (already done via `td.num`) and extend the mono+tabular
  treatment to every figure on cards so columns of numbers line up perfectly across the page.
- **Snap to the column grid.** The existing 12-col mental model is fine; the win is *visible*
  alignment — same left edge for eyebrow, heading, and content; no drifted padding (a stated
  guardrail). Sharpness is as much about zero drift as it is about corners.

---

## 6. Colour & surfaces — precise, not murky

Keep the dark theme — it's part of the brand — but make it read *precise*. Murkiness comes
from low-contrast borders (fixed in §2) and slightly muddy mid-surfaces.

- **Crisp the surface steps.** Keep the deep canvas, but make each surface step a clearly
  legible move so layering reads as deliberate (Linear's narrow-but-distinct 4-step stack).
  Minor lift on the muddy middle:
  ```css
  --bg:        #090b12;   /* was #0a0c14 — a hair deeper canvas */
  --surface:   #11152a → #12172c;  /* keep, but ensure ≥ one clear step over bg-2 */
  ```
  The key is *clear deltas between steps*, not new hues.
- **Drop the ambient body wash entirely (or push to ~0.03).** The single green radial is the
  last bit of "atmosphere"; a sharp instrument has a *flat* canvas. Reducing/removing it makes
  every hairline and number pop. (Plan already cut 3→1; this finishes it.)
- **Accent restraint — one rationed green.** Continue the planned magenta/cyan demotion to
  data-viz-only and the slight green desaturation (`#1fe07a → ~#2bd47f`). Linear rations its
  accent to one primary action per screen; hold to ≤2 green fills per viewport. Sharp UIs are
  near-monochrome with a single status colour cutting through.
- **No gradients on chrome.** Remove the card top-gradient, the crest gradient can stay (it's a
  logo mark) but flatten any panel/hero gradients to solid fills. Gradients read soft.

---

## 7. The 7 highest-impact moves (soft → sharp)

Ordered by impact-per-effort. Each is a developer-applies token/CSS value with its reference.

1. **Square the pills.** `999px → 4px` on `.pill`, `.badge` (3px), `.stage-chip`, nav links,
   `.mc-vstag`. *Single biggest perceptual shift.* (Linear outlined pills use small radii, not
   capsules; fully-round = consumer/social.)
2. **Tighten all rectangular radii.** `--radius 13→6`, `--radius-lg 18→8`, `--radius-sm 9→4`,
   add `--radius-xs 3`. (Stripe Dashboard 4–8px band.)
3. **Crisp, higher-contrast 1px hairlines.** `--border #262c4a→#313a5e`,
   `--border-soft→#20253c`, `--border-strong→#46507e`; neutralise the blue tint. (Linear 1px
   inset borders; Mantlr "nothing muddy in between.")
4. **Flatten elevation.** Remove `box-shadow` from `.panel`/`.match-card`; depth = surface +
   1px border (+ optional 1px inset highlight); shadows reserved for floating layers only;
   hover = border-strong, not lift. (Linear opacity-based depth, no shadow theatre.)
5. **Mono numerals + uppercase micro-labels.** Add `--font-mono` (Geist Mono) on all figures,
   `td.num`, timestamps, eyebrows; tabular + slashed-zero + true minus. (Bloomberg finance
   numerals; Vercel Geist Mono; Economist/FT data sans.)
6. **Tighten display tracking, cap weight 700.** `letter-spacing -0.03em` on h1/h2/display;
   drop every `font-weight:800` to 700; consider Inter Display in place of Sora. (Linear Inter
   510/590; Swiss grotesque.)
7. **Ruled, denser tables + flat canvas.** Add 1px column rules, tighten row padding
   (`0.5rem 0.8rem`) and body density; drop/near-zero the ambient body wash so hairlines and
   numbers pop. (FiveThirtyEight / FT ruled tables; Swiss visible grid.)

---

## Token diff (before → after)

| Token / property | Before | After | Where |
|---|---|---|---|
| `--radius` | `13px` | `6px` | panels, cards |
| `--radius-sm` | `9px` | `4px` | inputs, chips, nav, table-wrap |
| `--radius-lg` | `18px` | `8px` | hero / largest only |
| `--radius-xs` | — | `3px` (new) | badges, tags, inline code |
| `--radius-pill` | `999px` (literal) | `4px` (new) | chips, nav, `.pill` |
| pill/badge/chip radius | `999px` | `3–4px` | `.pill .badge .stage-chip .mc-vstag` |
| true-circle radius | `999px` | `999px` (keep) | dots, crest, avatars |
| `--border` | `#262c4a` | `#313a5e` | default object edge |
| `--border-soft` | `#1c2138` | `#20253c` | dividers, table rows |
| `--border-strong` | `#353d66` | `#46507e` | hover / emphasis |
| `--hairline` | — | `rgba(190,200,230,0.10)` (new) | inset/overlay rules |
| `--shadow` | `0 1px 2px rgba(0,0,0,.4)` | `0 1px 0 rgba(0,0,0,.5)` | hairline contact |
| `--shadow-md` | `0 6px 16px -8px …` | `0 4px 12px -6px rgba(0,0,0,.6)` | floating only |
| `--shadow-lg` | `0 14px 32px -16px …` | `0 12px 28px -14px rgba(0,0,0,.65)` | modals only |
| `.panel` box-shadow | `var(--shadow)` | `none` (border + surface) | panels |
| `.match-card` box-shadow | `var(--shadow-md)` | `none`; hover → border-strong | cards |
| card hover | `translateY(-3px)` + bloom | `translateY(-1px)` + border-strong | cards |
| `--font-display` | Sora Variable | Inter Display (rec.) / Sora display-only | headings |
| `--font-mono` | — | `"Geist Mono", "JetBrains Mono", ui-mono…` (new) | numerals, labels |
| h1/h2/display tracking | `-0.025em / -0.02em` | `-0.03em` | headings |
| micro-label tracking | `0.07–0.16em` | `0.12–0.16em`, 600wt, 0.6875rem | eyebrow, `.stat-label`, `th` |
| `font-weight: 800` | brand, score, vstag | `700` (all) | drop the sporty weight |
| body `line-height` | `1.55` | `1.5` | density |
| `.prose` line-height | `1.7` | `1.55` | density |
| `.grid` gap | `1rem` | `0.75rem` | layout density |
| `.panel` padding | `1.25rem 1.4rem` | `1rem 1.15rem` | density |
| `th, td` padding | `0.7rem 0.95rem` | `0.5rem 0.8rem` | ruled-table density |
| table `font-size` | `0.92rem` | `0.875rem` | density |
| numeric column rules | none | `1px var(--border-soft)` right rule | ruled tables |
| body background wash | green radial @0.05 | remove or `@0.03` | flat canvas |
| card top-gradient | `linear-gradient(180deg,--elev…)` | inset `0 1px 0 rgba(255,255,255,.04)` | crisp catch-light |
| crest glow | `0 4px 14px -4px rgba(31,224,122,.6)` | inset highlight only, no glow | kill glow |
| `--accent` | `#1fe07a` | `#2bd47f` (desat, per existing plan) | restraint |

---

## How far to push it

**Push it ~80–90% of the way — commit to the sharp end, stop just short of brutalist.**

- **Do** square the pills to 3–4px, go to 6px panels / 4px controls, lift border contrast,
  flatten shadows, and add mono numerals. These are the moves that read as "sharp/premium" and
  they're reversible token edits. This lands the owner's ask decisively.
- **Don't** go to literal 0px everywhere, pure-black canvas, or hard 1px high-contrast white
  grid lines on every cell — that tips from "precision instrument" into "raw/brutalist/
  wireframe," which fights the credibility-and-calm guardrails in `design-direction.md`
  ("calm authority," "earned invisible polish," depth stays quiet). A 2–6px radius scale and
  *slightly* lifted slate hairlines keep it Braun/Teenage-Engineering precise rather than harsh.
- **Sequence:** ship moves 1–4 (radii + pills + borders + flat elevation) first — they're pure
  token/CSS swaps, low risk, and deliver ~70% of the perceived sharpness in one batch. Then 5–7
  (mono numerals, tracking/weight, ruled tables) as a typographic follow-up, since the mono
  font needs adding and touches numerals across components.

If after batch 1 the owner still wants "sharper," the next dial is: panels `6→4px`, badges
`3→2px`, and add the full vertical column rules everywhere — but validate in-browser first;
each step toward 0 trades warmth/credibility for edge.
