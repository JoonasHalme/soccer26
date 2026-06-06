import { describe, it, expect } from "vitest";
import {
  fullKellyFraction, kellyStake, meanCI,
  signed, signedPct, money, pct1, MINUS,
  teamSlug, matchOutcome, computeStandings,
  topDivergences, liveCalibration, wilsonInterval, clvStats,
  validateBets, validateFixtures, validatePredictions,
  loadFixtures, loadBets, loadPredictions,
  type Match, type Prediction, type Bet,
} from "./data";

const mk = (p: Partial<Match> & Pick<Match, "id">): Match => ({
  stage: "GROUP", home: "A", away: "B", status: "SCHEDULED", ...p,
});

// --------------------------------------------------------------------------- //
// Kelly staking (mirrors model/staking.py — see the golden cross-check too)
// --------------------------------------------------------------------------- //
describe("Kelly", () => {
  it("full fraction = (b·p − q)/b", () => {
    // p=0.6, odds=2.0 -> b=1, f*=(0.6-0.4)/1 = 0.2
    expect(fullKellyFraction(0.6, 2.0)).toBeCloseTo(0.2, 10);
  });
  it("no edge or bad inputs → 0", () => {
    expect(fullKellyFraction(0.4, 2.0)).toBe(0); // -EV
    expect(fullKellyFraction(0.6, 1.0)).toBe(0); // odds <= 1
    expect(fullKellyFraction(0, 2.0)).toBe(0);
    expect(fullKellyFraction(1, 2.0)).toBe(0);
  });
  it("fractional stake, rounded to cents", () => {
    // f*=0.2, 0.25 Kelly, bankroll 1000 -> 1000*0.2*0.25 = 50, cap 5% = 50 (not bound)
    const k = kellyStake(0.6, 2.0, 1000, 0.25, 5);
    expect(k.stake).toBe(50);
    expect(k.capped).toBe(false);
    expect(k.fullKelly).toBeCloseTo(0.2, 10);
  });
  it("cap binds the stake", () => {
    // huge edge -> raw exceeds 2% cap -> capped to 20 on a 1000 bankroll
    const k = kellyStake(0.9, 5.0, 1000, 0.25, 2);
    expect(k.capped).toBe(true);
    expect(k.stake).toBe(20);
  });
});

describe("meanCI", () => {
  it("returns null for < 2 points", () => {
    expect(meanCI([])).toBeNull();
    expect(meanCI([5])).toBeNull();
  });
  it("95% t-interval centred on the mean", () => {
    const ci = meanCI([2, 4, 6])!;          // mean 4, sd 2, se 2/sqrt3, t(2)=4.303
    expect(ci.mean).toBeCloseTo(4, 10);
    expect(ci.margin).toBeCloseTo(4.303 * (2 / Math.sqrt(3)), 3);
    expect(ci.low).toBeCloseTo(ci.mean - ci.margin, 10);
    expect(ci.high).toBeCloseTo(ci.mean + ci.margin, 10);
  });
});

describe("formatting", () => {
  it("signed/ signedPct use a real minus glyph", () => {
    expect(signed(4.2)).toBe("+4.2");
    expect(signed(-1.3)).toBe(`${MINUS}1.3`);
    expect(signedPct(-1.3)).toBe(`${MINUS}1.3%`);
    expect(pct1(11.21)).toBe("11.2");
  });
  it("money negatives use the minus glyph", () => {
    expect(money(12.4)).toBe("12.40 EUR");
    expect(money(-12.4)).toBe(`${MINUS}12.40 EUR`);
  });
});

describe("teamSlug", () => {
  it("strips accents, expands &, lowercases", () => {
    expect(teamSlug("Curaçao")).toBe("curacao");
    expect(teamSlug("Bosnia & Herzegovina")).toBe("bosnia-and-herzegovina");
    expect(teamSlug("South Korea")).toBe("south-korea");
  });
});

describe("matchOutcome", () => {
  it("reads 1X2 from the score, null when unplayed", () => {
    expect(matchOutcome(mk({ id: "1", score: { home: 2, away: 0 } }))).toBe("home");
    expect(matchOutcome(mk({ id: "2", score: { home: 1, away: 1 } }))).toBe("draw");
    expect(matchOutcome(mk({ id: "3", score: { home: 0, away: 3 } }))).toBe("away");
    expect(matchOutcome(mk({ id: "4", score: { home: null, away: null } }))).toBeNull();
    expect(matchOutcome(mk({ id: "5" }))).toBeNull();
  });
});

describe("computeStandings", () => {
  it("tallies points/GD and sorts", () => {
    const groups = { A: ["X", "Y", "Z"] };
    const matches: Match[] = [
      mk({ id: "m1", group: "A", status: "FINISHED", home: "X", away: "Y", score: { home: 2, away: 0 } }),
      mk({ id: "m2", group: "A", status: "FINISHED", home: "Z", away: "Y", score: { home: 1, away: 1 } }),
    ];
    const table = computeStandings(matches, groups);
    const A = table.A;
    expect(A[0].team).toBe("X");           // 3 pts, +2 -> top
    expect(A[0].points).toBe(3);
    expect(A[0].gd).toBe(2);
    const Y = A.find((r) => r.team === "Y")!;
    expect(Y.played).toBe(2);
    expect(Y.points).toBe(1);              // 0 + draw
    // every seeded team listed even with no games
    expect(A.map((r) => r.team).sort()).toEqual(["X", "Y", "Z"]);
  });
});

describe("topDivergences", () => {
  it("collapses each market to its largest-|delta| leg and ranks by |delta|", () => {
    const preds = [{
      match_id: "m1", home: "A", away: "B",
      divergences: [
        { market: "1X2", selection: "HOME", model_prob: 0.34, fair_prob: 0.69, delta: -0.35 },
        { market: "1X2", selection: "DRAW", model_prob: 0.28, fair_prob: 0.20, delta: 0.08 },
        { market: "1X2", selection: "AWAY", model_prob: 0.38, fair_prob: 0.11, delta: 0.27 },
        { market: "OVER_UNDER", selection: "OVER_2_5", model_prob: 0.55, fair_prob: 0.50, delta: 0.05 },
      ],
    }] as unknown as Prediction[];
    const rows = topDivergences(preds, []);
    // one row per market (1X2 -> HOME with |−0.35|, OU -> OVER with 0.05)
    expect(rows.length).toBe(2);
    expect(rows[0].selection).toBe("HOME");           // biggest |delta| first
    expect(Math.abs(rows[0].delta)).toBeGreaterThan(Math.abs(rows[1].delta));
  });
});

describe("liveCalibration", () => {
  it("is empty with no results", () => {
    const lc = liveCalibration({}, []);
    expect(lc.nMatches).toBe(0);
    expect(lc.brier).toBeNull();
  });
  it("grades a finished match against its archived prediction", () => {
    const archive = { m1: { home: 0.7, draw: 0.2, away: 0.1 } };
    const matches = [mk({ id: "m1", status: "FINISHED", score: { home: 2, away: 0 } })];
    const lc = liveCalibration(archive, matches);
    expect(lc.nMatches).toBe(1);
    expect(lc.nEvents).toBe(3);
    expect(lc.hitRate).toBe(1);              // top pick (home) correct -> 1.0 (the page ×100)
    expect(lc.brier).toBeGreaterThan(0);
  });
});

describe("CLV reporting (quant A3)", () => {
  it("wilsonInterval: null at n=0, bracketed in [0,100], contains the point", () => {
    expect(wilsonInterval(0, 0)).toBeNull();
    const ci = wilsonInterval(7, 10)!;
    expect(ci.low).toBeGreaterThanOrEqual(0);
    expect(ci.high).toBeLessThanOrEqual(100);
    expect(ci.low).toBeLessThan(70);
    expect(ci.high).toBeGreaterThan(70);
  });
  it("a tiny sample gives a WIDE binomial CI", () => {
    const ci = wilsonInterval(1, 1)!;       // 1/1 = 100% but hugely uncertain
    expect(ci.low).toBeLessThan(50);        // Wilson pulls the lower bound way down
  });
  it("clvStats stake-weights CLV and adds a beat-rate CI", () => {
    const bets = [
      { id: "a", result: "WIN", clv_pct: 2, stake: 100, market: "1X2" },   // big stake, +CLV
      { id: "b", result: "LOSS", clv_pct: -8, stake: 10, market: "1X2" },  // tiny stake, −CLV
    ] as unknown as Bet[];
    const s = clvStats(bets);
    expect(s.rated).toBe(2);
    expect(s.beatRate).toBe(50);            // 1 of 2 has clv_pct > 0
    expect(s.beatRateCI).not.toBeNull();
    expect(s.avgClv).toBeCloseTo(-3, 6);    // plain mean = (2 − 8)/2
    // stake-weighted leans to the heavily-staked positive-CLV bet
    expect(s.stakeWeightedClv!).toBeCloseTo((100 * 2 + 10 * -8) / 110, 6);  // ≈ +1.09
    expect(s.stakeWeightedClv!).toBeGreaterThan(s.avgClv!);
  });
});

// --------------------------------------------------------------------------- //
// Loader validators (TASK-055): malformed artifacts must be rejected loudly
// --------------------------------------------------------------------------- //
describe("loader validators", () => {
  it("validateBets accepts good config, rejects malformed", () => {
    expect(() => validateBets({ starting_bankroll: 100, bets: [] }, "bets.json")).not.toThrow();
    expect(() => validateBets({ bets: [] }, "bets.json")).toThrow(/starting_bankroll/);
    expect(() => validateBets({ starting_bankroll: 1, bets: [{ id: "b1" }] }, "bets.json")).toThrow(/stake/);
    expect(() => validateBets([], "bets.json")).toThrow(/config object/);
  });
  it("validateFixtures requires a matches array of objects with string ids", () => {
    expect(() => validateFixtures({ matches: [{ id: "m1" }], groups: {} }, "f.json")).not.toThrow();
    expect(() => validateFixtures({ groups: {} }, "f.json")).toThrow(/matches/);
    expect(() => validateFixtures({ matches: [{}] }, "f.json")).toThrow(/id/);
  });
  it("validatePredictions requires match_id + probabilities", () => {
    expect(() => validatePredictions({ predictions: [{ match_id: "m1", probabilities: {} }] }, "p.json")).not.toThrow();
    expect(() => validatePredictions({ predictions: [{ match_id: "m1" }] }, "p.json")).toThrow(/probabilities/);
    expect(() => validatePredictions({}, "p.json")).toThrow(/predictions/);
  });
});

// --------------------------------------------------------------------------- //
// Smoke: the REAL build-time artifacts load and validate (catches drift)
// --------------------------------------------------------------------------- //
describe("real artifacts load + validate", () => {
  it("loadFixtures returns the 104-match schedule", () => {
    const fx = loadFixtures();
    expect(Array.isArray(fx.matches)).toBe(true);
    expect(fx.matches.length).toBeGreaterThan(100);
  });
  it("loadBets + loadPredictions don't throw on the live files", () => {
    expect(() => loadBets()).not.toThrow();
    const p = loadPredictions();
    expect(Array.isArray(p.predictions)).toBe(true);
  });
});
