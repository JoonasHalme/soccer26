import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { kellyStake, meanCI } from "./data";

// The SAME golden contract asserted by tests/test_golden.py. If the TS mirrors of
// the Kelly / t-table math drift from the Python originals, this fails (TASK-056).
const golden = JSON.parse(
  fs.readFileSync(path.resolve(process.cwd(), "../tests/golden/staking_clv_golden.json"), "utf8"),
);

describe("Python↔TS golden: Kelly stake", () => {
  for (const c of golden.kelly) {
    it(`p=${c.p} odds=${c.odds} cap=${c.cap_pct}%`, () => {
      const r = kellyStake(c.p, c.odds, c.bankroll, c.fraction, c.cap_pct);
      expect(r.stake).toBeCloseTo(c.stake, 9);          // both round to cents -> exact
      expect(r.capped).toBe(c.capped);
      expect(r.fullKelly).toBeCloseTo(c.full_kelly, 3);
    });
  }
});

describe("Python↔TS golden: mean 95% CI", () => {
  for (const c of golden.mean_ci) {
    it(`n=${c.values.length}`, () => {
      const r = meanCI(c.values)!;
      expect(r).not.toBeNull();
      // Python rounds the CI to 2dp; TS keeps full precision — compare within that.
      for (const k of ["mean", "margin", "low", "high"] as const) {
        expect(Math.abs(r[k] - c[k])).toBeLessThan(0.01);
      }
    });
  }
});
