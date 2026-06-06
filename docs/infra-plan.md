# Infra plan — git → Cloudflare Pages → automated capture

**Goal:** turn soccer26 from a single-Windows-machine, manually-operated, version-control-less
project into a **reproducible, auto-deploying, self-capturing** platform — so the June-11
closing-odds data (the credibility moat) lands without depending on one PC being on, and the site
is finally live + indexable.

**The key architectural fact:** the Python stack (numpy/scipy/pandas) **cannot run in a host's build
step** (Cloudflare/Netlify/Vercel build images don't have it). So the architecture is **decoupled**:

```
 Python data-gen (CI or local)  ──commits JSON──▶  git  ──auto-trigger──▶  Cloudflare builds the Astro site
```

The host only builds the static site from **committed** JSON. This is also what makes the SHA-256
ledger meaningful: the hashed `predictions.json` is in a public repo, so the tamper-evidence becomes
externally verifiable (the TASK-050 "external anchor" roadmap item — a free bonus).

Legend: **[ME]** = I can do it now in-repo · **[YOU]** = needs your account/click.

---

## Phase 0 — Decisions (you, 2 min)

1. **Repo visibility:** **public recommended.** Public repos get *free unlimited* GitHub Actions
   minutes (vs a monthly cap on private), AND a public repo is what makes the ledger externally
   verifiable — on-brand for a transparency project. Nothing sensitive is committed (`.env` stays
   ignored; the API key goes in Secrets, never the repo). Choose private only if you want the bets
   log hidden.
2. **Repo name** (e.g. `soccer26`), and a **Cloudflare account** (free).
3. **Rotate the exposed `ODDS_API_KEY`** (TASK-051) — you'll add the *new* key to GitHub Secrets in
   Phase 4, so the old surfaced one never matters.

---

## Phase 1 — Version control + reproducibility

- **[ME]** Un-ignore the build artifact: remove `site/public/data/predictions.json` from
  `.gitignore` (it's what the ledger hashes and the host builds from; everything else the site reads
  is already committable). Confirm `.env` + `model/data/*.csv` (the 49k-row training CSV) stay
  ignored — the matchday pipeline runs from the committed `ratings.json`/`calibration.json`/
  `confederation_offsets.json`, so the CSV is **not** needed in CI (commit it later only if you want
  full from-scratch re-training reproducibility — TASK-040).
- **[ME]** Pin Python deps: `model/requirements.txt` `>=` → compatible-release (`numpy~=2.1`, …) or a
  frozen `requirements.lock`, so a fresh CI runner can't silently shift model outputs (which would
  break the ledger for non-tampering reasons). Confirm `site/package-lock.json` is committed (for
  `npm ci`).
- **[ME]** `git init`, sane first commit of the whole tree (code + committed JSON + docs).
- **[YOU]** Create the GitHub repo and push (`git remote add origin … ; git push -u origin main`).

**Verify:** `git status` clean; `predictions.json` tracked; `.env` NOT tracked.

---

## Phase 2 — Hosting (you, ~10 min)

- **[YOU]** Cloudflare Pages → "Connect to Git" → the repo. Settings:
  - **Root directory:** `site`
  - **Build command:** `npm run build`
  - **Output directory:** `dist`
  - **Environment variable:** `SITE_URL = https://<project>.pages.dev` (the free subdomain works
    immediately; swap a real domain in later — Cloudflare DNS is free).
- Pages auto-deploys on every push to `main`.

**Verify:** site loads at the `.pages.dev` URL; `/sitemap-index.xml`, `/robots.txt`, and the OG/
canonical tags now show the real absolute URL (no more `soccer26.example.com`).

**Why Cloudflare:** unlimited bandwidth/requests + 500 builds/mo free (Netlify cut free build-minutes;
Vercel meters builds). Bandwidth-unlimited matters for the tournament traffic spike.

---

## Phase 3 — CI quality gate (every push)

- **[ME]** `.github/workflows/ci.yml` mirroring `scripts/check.ps1` on Linux:

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r model/requirements.txt
      - run: python -m pytest tests/ -q
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: npm, cache-dependency-path: site/package-lock.json }
      - run: npm --prefix site ci
      - run: npm --prefix site run test
      - run: npm --prefix site run build
        env: { SITE_URL: https://example.pages.dev }
```

- **[YOU]** Branch-protect `main` so a red build blocks merge. (Lets you finally use PR branches /
  worktrees instead of serialising edits.)

---

## Phase 4 — Automated closing-odds capture (the moat)

Split into a **safe always-on job** and a **deliberate credit-spending job** so the API budget
(~490 credits/mo) is never blown.

- **[YOU]** Add the rotated key as repo secret `ODDS_API_KEY`.
- **[ME]** `.github/workflows/capture.yml` — **Job A, hourly, quota-safe** (the critical one):

```yaml
name: capture-closing
on:
  schedule: [{ cron: '7 * * * *' }]   # hourly; capture_closing self-gates → spends a credit ONLY near kickoff
  workflow_dispatch: {}
permissions: { contents: write }
concurrency: capture-closing
jobs:
  capture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r model/requirements.txt
      - env: { ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }} }
        run: python model/capture_closing.py     # writes closing_odds into fixtures.json (only when due)
      - run: python model/publish_live.py         # cheap, no API
      - name: Commit if changed
        run: |
          git config user.name  "soccer26-bot"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add fixtures/fixtures.json site/public/data/live.json
          git diff --cached --quiet || (git commit -m "data: closing-odds capture $(date -u +%FT%TZ)" && git push)
```

`capture_closing.py` already only spends a request when a match is within `--within-hours` of
kickoff and not freshly captured, so an hourly cron costs ~0 credits until matchdays — the moat
captures itself, machine-independent.

- **[ME]** `.github/workflows/refresh.yml` — **Job B, `workflow_dispatch` (manual) + optional
  tournament cron**: `fetch_odds → anchor → predict → simulate → fetch_results → settle → commit`.
  This **spends credits** (`fetch_odds`/`fetch_results` hit the API every run), so it's manual by
  default; the committed JSON auto-deploys via Cloudflare.
  - ⚠️ **Prerequisite before cron-ing Job B:** `fetch_results.py` spends a credit every run, so an
    unguarded hourly cron would blow the budget pre-tournament. Add a small **"only-if-active" gate**
    (reuse `capture_closing.capture_plan` — only fetch results when a match kicked off in the last
    ~3h). Small task; do it before scheduling Job B. Until then, trigger Job B manually on matchdays.

- **[YOU]** **Belt-and-suspenders for the June 11 openers:** keep the local Windows Task Scheduler
  job (`scripts/capture-closing.ps1`) running too — GitHub scheduled crons can be delayed under load
  and pause after 60 days of repo inactivity. Two independent captures of the first wave is cheap
  insurance for irreplaceable data.

---

## Phase 5 — Edge cache + fast rebuilds (nice-to-have)

- **[ME]** `site/public/_headers` so Cloudflare's edge absorbs the live-poll fan-out and caches
  hashed assets:

```
/data/live.json
  Cache-Control: public, max-age=30, stale-while-revalidate=30
/_astro/*
  Cache-Control: public, max-age=31536000, immutable
```
  (Then drop `cache: "no-store"` from the `live.json` poller in `index.astro` so the CDN can serve it.)
- **[ME, later]** OG-render caching (the ~30s satori step re-runs every build) — defer; only matters
  once Job B is cron-driven.

---

## Risks / rollback

- **Committing `predictions.json`** means each `predict` run produces a diff the Action commits →
  triggers a Cloudflare build. Intended. (If capture-only commits cause noisy rebuilds, scope the
  Cloudflare build to ignore data-only paths later.)
- **Bot push vs manual push** can race on a solo repo — use `git pull --rebase` locally; rare.
- **Everything here is additive and reversible.** No model/site logic changes — only version control,
  hosting, CI, and scheduling. If a workflow misbehaves, disable it in the Actions tab; the local
  `.ps1` path still works unchanged.

## Suggested order (½–1 day)

**1.** Phase 1 + 2 (live + indexable). → **2.** Phase 4 Job A + secret (moat self-captures before
June 11). → **3.** Phase 3 CI + branch protection. → **4.** Phase 5 headers. → **5.** Job B gate +
cron when ready. **Non-negotiable for a 5-day ship: Phases 1, 2, 4-Job-A.**

## Who does what

- **[ME] now:** un-ignore `predictions.json`, pin deps, `git init` + first commit, write `ci.yml` /
  `capture.yml` / `refresh.yml` / `_headers`, add the `fetch_results` quota-gate.
- **[YOU]:** create the GitHub repo + push, connect Cloudflare Pages + set `SITE_URL`, add the
  rotated `ODDS_API_KEY` secret, branch-protect `main`, keep the local capture job as backup.
