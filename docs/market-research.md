# Market Research — soccer26

*Market-viability + competitor-landscape report. Date: 2026-06-06. Tournament kicks off 2026-06-11.*

**Scope:** Is there a real market for a transparent, auditable, World-Cup-focused
betting-analysis app, and is there competition? This is a demand-and-positioning
report (who else exists, how big is the audience, where the white space is). For the
model-vs-state-of-the-art methodology critique, see the companion `docs/competitive-research.md`.

**Product recap:** soccer26 is a solo-built WC2026 forecasting web app — Elo + Poisson
(Dixon-Coles) → de-vigged value edges → a SHA-256-hashed, CLV-graded public bet log.
Positioning is deliberately honest: "analysis, not tips"; well-calibrated, beats a naive
baseline, but "beats the market" is **not** yet proven. **Not** a licensed sportsbook;
**no** affiliate relationships.

---

## 1. Direct competitors — public soccer forecast models

These publish match/tournament probabilities from a model, and in some cases value/edge analysis.

- **Nate Silver — Silver Bulletin / PELE.** The single most important competitor and the
  inheritor of the post-538 audience. Silver took his forecasting franchise to a Substack
  after leaving 538 in 2023; ABC formally shut down 538 in March 2025 and pulled its
  archives in May 2026, vacating the "data-journalism forecast" niche. For WC2026 he
  launched **PELE** ("Predictive Elo with Lineup Equilibria"), an international-soccer model
  blending match results, player market values, and historical economic/geographic data,
  running **100,000 simulations** for the World Cup forecast (Spain/Argentina co-favourites
  ~17%). Methodology is **published**; the model code is **not** open-source. Monetization is
  a tiered Substack — the public forecast is free, the "advanced" sections are **paywalled to
  paying subscribers**. This is a large, monetized, credible, general-interest operation —
  but it is **not** betting-focused: no value-edge layer, no CLV bet log, no auditable ledger.
  ([PELE rankings](https://www.natesilver.net/p/pele-international-football-rankings-soccer-ratings-projections) ·
  [PELE methodology](https://www.natesilver.net/p/pele-methodology) ·
  [538 shutdown — Nieman Lab](https://www.niemanlab.org/2025/03/fivethirtyeight-is-shutting-down-as-part-of-broader-cuts-at-abc-and-disney/))

- **Opta Analyst "Supercomputer" (Stats Perform).** The dominant *free* headline forecast.
  Opta Power Rankings (10,000+ men's clubs, 183 FIFA nations) blended with **betting-market
  odds**, Monte-Carlo simulated (25,000 WC2026 sims; Spain 16.1%). Huge built-in media reach
  via The Analyst and syndication to outlets worldwide. Methodology is **described** but the
  model is proprietary; the underlying data is **paid/enterprise** (broadcasters, bookmakers,
  analytics firms). Strength: brand, scale, free distribution. Weakness for our purposes: it
  **blends in the market**, so it can't claim to *beat* the market, and it publishes **no
  value edges and no graded bet log**. ([Opta WC2026](https://theanalyst.com/articles/who-will-win-2026-fifa-world-cup-predictions-opta-supercomputer) ·
  [Power Rankings](https://theanalyst.com/articles/who-are-the-best-football-team-in-the-world-opta-power-rankings))

- **clubelo.com.** Football-specific Elo, fully **free**, with a CSV/API and transparent
  methodology — but **club**, not international, and it's a ratings/probability source, **no
  value or CLV layer**. The closest spiritual cousin to soccer26's rating engine.
  ([clubelo](http://clubelo.com/))

- **eloratings.net (World Football Elo).** Free national-team Elo with match-importance and
  MoV weighting; rankings only, **no markets, no betting layer**.
  ([Wikipedia](https://en.wikipedia.org/wiki/World_Football_Elo_Ratings))

- **Infogol (Opta-powered).** xG-based match model → 1X2 + **value tips** ("footballs" sizing
  the discrepancy). This is the nearest *value-flagging* analogue, but it's app/media-funded,
  not transparent/auditable, and **no published CLV record**.
  ([Timeform/Infogol](https://www.timeform.com/football))

- **football-data.co.uk.** Not a model — the canonical free historical results + multi-book
  closing/opening odds CSVs. It's the *dataset* everyone (including soccer26) backtests on,
  i.e. infrastructure, not a competitor.
  ([football-data](https://www.football-data.co.uk/data.php))

- **Open-source WC/football models (penaltyblog, epl-prediction-lab, et al.).** Free, fully
  transparent (code on GitHub), some SHA-commit pre-kickoff probabilities — the **same
  auditability discipline** soccer26 uses. But they are libraries/repos, not consumer
  products: no UI, no curated edges, no marketed CLV track record, near-zero general audience.
  ([penaltyblog](https://github.com/martineastwood/penaltyblog))

- **Pinnacle (resources).** Not a model — a sharp, low-margin book whose **closing line is
  the de-facto "true probability" benchmark**. It is the standard soccer26 measures itself
  *against*, not a forecast competitor; it also publishes the betting-education content that
  defines the CLV vocabulary. ([Pinnacle CLV](https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting))

- **Prediction markets — Polymarket & Kalshi.** Not forecast *publishers* but a fast-growing
  competing source of "probabilities" — and increasingly a place people *act* on them.
  Polymarket's WC-winner market has booked **~$1.6B** in trades since opening; Kalshi's
  WC-winner market handled **$87.5M** as of early June and is projected toward ~$253M by the
  final; total US WC prediction-market volume is forecast at **~$2.37B** (Kalshi alone ~$1.47B).
  These markets are themselves a real-time, liquid "model" of tournament probabilities and a
  *benchmark soccer26 can be graded against* — but they offer **no methodology, no edge
  analysis, no calibration story**. ([DeFiRate odds](https://defirate.com/prediction-markets/world-cup-odds/) ·
  [DeFiRate $2.5B forecast](https://defirate.com/news/forecast-world-cup-prediction-market-volume-could-hit-2-5-billion/) ·
  [RotoWire](https://www.rotowire.com/article/world-cup-prediction-markets-how-to-trade-on-the-biggest-sporting-event-117042))

## 2. Indirect / adjacent competitors

- **CLV trackers — Pikkit, Betstamp, Unabated.** This is the **closest adjacent category** to
  soccer26's bet-log/CLV pillar, and it's already commercialized and at scale. **Pikkit**:
  100,000+ bettors, auto-syncs 30+ books, computes CLV on every bet; **Pikkit Pro ≈ $40/mo**
  (or ~$300/yr). **Betstamp**: bet tracking + odds comparison + CLV across 50+ books and
  prediction markets, "verified records." Crucially these track **the user's own** bets — they
  do **not** publish a *forecaster's* model-driven, pre-committed, publicly-graded record.
  That's the gap soccer26 sits in. ([Pikkit CLV](https://pikkit.com/closing-line-value) ·
  [Pikkit Pro review](https://www.pinnacleoddsdropper.com/blog/pikkit-pro-review) ·
  [Betstamp](https://betstamp.com/tracking))

- **Tipster / "tout" platforms & paid Substacks.** A large, mature market for paid picks
  (BetQL, countless Substacks/Discords/Telegram tipsters). Demonstrates clear
  willingness-to-pay but is reputationally **toxic** (cherry-picked records, no auditability) —
  the *opposite* of soccer26's "honest, auditable, analysis-not-tips" stance, which is the
  whole differentiation. ([BetQL](https://betql.co/) ·
  [subscription betting models](https://innosoft-group.com/subscription-based-betting-models-explained-are-they-the-future-of-sports-betting/))

- **Fantasy / bracket games.** Massive casual audience (~85M fantasy players across US/Canada
  by 2025) — adjacent demand for "who will win" content and a plausible top-of-funnel, but a
  different (entertainment, not edge) use-case. A free "Beat the Model" leaderboard is the
  natural bridge into this audience. ([market context](https://innosoft-group.com/subscription-based-betting-models-explained-are-they-the-future-of-sports-betting/))

- **Sports-media prediction columns** (ESPN, The Athletic, BBC, betting-affiliate sites). High
  reach, low rigor, **affiliate-monetized** — they compete for *attention* but not on
  transparency or CLV.

## 3. Market demand, size & regulatory constraints

**Demand is real and arguably growing.** Three independent signals:

1. **The post-538 vacancy is genuine.** ABC killed 538 and de-listed its archives; Silver
   Bulletin proved the audience follows a credible, transparent forecaster onto a paid
   newsletter. There is a demonstrated appetite for "honest probabilities with a methodology."
2. **Prediction-market explosion.** ~$2.37B forecast US WC volume across Kalshi/Polymarket
   shows enormous mainstream interest in *probabilistic* takes on this exact event — a far
   larger, more data-curious audience than the old tipster world.
3. **Proven willingness-to-pay among sharps.** VIP bettors are tiny but whale-heavy (PointsBet:
   ~0.5% of customers, >70% of revenue in 2019–20); Pikkit's 100k+ users at ~$40/mo proves
   data-curious bettors *do* pay for analytics and CLV. Americans wager an estimated **$673.6B/yr**
   in unregulated markets — the underlying betting population is huge.
   ([WTP/market signals](https://innosoft-group.com/subscription-based-betting-models-explained-are-they-the-future-of-sports-betting/))

**But the directly-addressable niche is narrow.** soccer26 targets the intersection of
(a) soccer-specific, (b) transparency/CLV-motivated, (c) WC2026-timed users — a sliver of the
above totals, and structurally **seasonal** (a World Cup is a 5-week event, then a multi-year
trough). General-interest forecast eyeballs largely go to Opta (free, massive reach) and
Silver (brand); paying customers for *analytics* largely go to Pikkit/Betstamp.

**Regulatory / compliance constraints (favorable for a non-licensed, non-affiliate operator).**
Publishing **analysis and probabilities is protected information/editorial content**, not
bookmaking — soccer26 takes no wagers and holds no stakes, so it does **not** need a UKGC/state
gambling licence. The relevant rules are consumer-protection, not gambling-operator, law:
- **FTC §5** (truthful, non-deceptive claims) — the "analysis, not tips," "beats-the-market-not-
  proven" honesty is exactly the right posture; avoid any implied guaranteed-profit claim.
- **FTC affiliate-disclosure rules** — only bite **if** soccer26 ever adds affiliate links;
  currently N/A, but a clear "no affiliate relationships" statement is itself a trust asset.
- **Responsible-gambling framing** (age-gating language, RG/helpline footer) is best practice
  and already shipped.
- The live legal turbulence is around **prediction markets** (Kalshi/Polymarket sports
  contracts are being litigated as possible unlicensed betting) — a content/analysis site is
  well clear of that exposure. ([FTC affiliate](https://termly.io/resources/articles/ftc-affiliate-disclosure/) ·
  [prediction-market litigation](https://news.bloomberglaw.com/legal-exchange-insights-and-commentary/us-courts-to-determine-fate-of-online-sports-prediction-markets) ·
  [gambling marketing law](https://www.fortismedia.com/en/articles/gambling-marketing-laws/))

## 4. Gaps & positioning — the defensible white space

Mapping the field, **no single competitor combines all four** of soccer26's pillars:

| Capability | Silver/PELE | Opta | clubelo | Infogol | Pikkit/Betstamp | OSS models | **soccer26** |
|---|---|---|---|---|---|---|---|
| Published methodology | ✅ | partial | ✅ | ✗ | n/a | ✅ | ✅ |
| De-vigged **value edges** | ✗ | ✗ | ✗ | ✅ | ✗ | rare | ✅ |
| Public **CLV-graded bet log** | ✗ | ✗ | ✗ | ✗ | own bets only | ✗ | ✅ |
| **Tamper-evident** (hash ledger) | ✗ | ✗ | ✗ | ✗ | ✗ | some | ✅ |
| Consumer-grade **UI/product** | ✅ | ✅ | ✗ | ✅ | ✅ | ✗ | ✅ |

**The credible white space:** *the only consumer product that pre-commits its own forecasts
(SHA-256 ledger), flags de-vigged value edges, and then grades itself in public against the
closing line — honestly.* Opta blends the market (can't claim edge); Silver doesn't do
betting/CLV; Infogol gives tips but no audited record; Pikkit/Betstamp grade *your* bets, not a
*forecaster's*; OSS models have the rigor but no product. soccer26 = **rigor + product + radical
honesty** in one place.

**Defensible vs. commoditized:**
- **Commoditized (don't compete here):** the raw rating/probability number — Opta, Silver,
  clubelo, and the prediction markets all produce one, several with vastly more data and reach.
  A solo Elo+Poisson will not out-predict Opta's market-blended supercomputer.
- **Defensible:** the **auditable track record itself** — a long, tamper-evident, CLV-graded
  ledger is a *time-built moat* nobody can clone retroactively, and it's precisely what the
  tipster industry can't/won't produce. The **honesty positioning** ("we haven't proven we beat
  the market, here's the receipts") is brand-defensible in a field built on overclaiming.
  Secondary moats: **WC2026 SEO** (173 pages of per-team/group landing pages already live) and
  **niche focus** (one tournament, done thoroughly) where generalists are shallow.

## 5. Verdict

**A real but small and seasonal niche — viable as a credibility/portfolio project and a
modest audience play, not as VC-scale revenue.** The demand is genuine (post-538 vacancy +
a ~$2.4B prediction-market frenzy proves mainstream appetite for soccer probabilities, and
Pikkit's 100k paying users prove the data-curious *will* pay for CLV analytics), and the
competitive map has a real gap: nobody else ships rigor + a consumer product + a tamper-evident,
publicly-graded CLV record together. But the field around each *individual* pillar is crowded
by far better-resourced players (Opta's free reach, Silver's brand, Pikkit/Betstamp's traction),
the directly-addressable audience is a thin slice that largely empties after the final, and the
killer asset — a long, market-beating CLV ledger — is **still empty** (0 closing-odds snapshots
captured), so the single most important and only truly defensible differentiator is **unproven
and unbuilt until the closing-odds capture cadence runs**. Realistic outcome for a solo build:
a respected, well-trafficked-during-the-Cup transparency site that earns trust and SEO,
optionally a small paid tier or tip-jar/newsletter post-tournament if (and only if) the CLV
record turns out positive — a defensible reputation asset, not a business.

---

### Competitor table (summary)

| Name | Type | Transparency | Monetization | Strength | Weakness (vs soccer26) |
|---|---|---|---|---|---|
| **Silver Bulletin / PELE** | Direct (general forecast) | Methodology public, code closed | Tiered Substack (paywalled "advanced") | Brand, post-538 audience, 100k-sim rigor | No value edges, no CLV, no bet log |
| **Opta "Supercomputer"** | Direct (free headline) | Described, proprietary, **blends market** | Free PR; paid enterprise data | Massive reach + brand, free | Can't claim "beats market"; no edges/CLV |
| **clubelo.com** | Direct (ratings) | Fully open, CSV/API | Free | Transparent, clean Elo | Clubs not nations; no betting/CLV layer |
| **eloratings.net** | Direct (ratings) | Open methodology | Free | National-team Elo, long history | Rankings only; no markets/value |
| **Infogol** | Direct (value tips) | Opaque (Opta-powered) | App/media | xG model + value flags | Not auditable; no published CLV |
| **football-data.co.uk** | Infrastructure | Raw data | Free | Canonical odds/results dataset | Not a competitor — a data source |
| **OSS models (penaltyblog…)** | Direct (code) | Fully open, some hash-commit | Free / OSS | Same auditability rigor | No product, UI, or audience |
| **Pinnacle** | Benchmark | Sharp odds + edu content | Sportsbook margin | Closing line = the benchmark | Not a forecaster; the line to beat |
| **Polymarket / Kalshi** | Direct (market probs) | None (price only) | Trading fees/spread | ~$2.4B WC volume; live, liquid | No method/edge/calibration story |
| **Pikkit / Betstamp** | Adjacent (CLV trackers) | Tracks *user's* bets | ~$40/mo (Pikkit Pro) | 100k+ users, real CLV product | Grades your bets, not a forecaster's record |
| **Tipsters / paid Substacks** | Adjacent (picks) | Usually none | Subscriptions | Proven willingness-to-pay | Untrustworthy — soccer26's foil |
