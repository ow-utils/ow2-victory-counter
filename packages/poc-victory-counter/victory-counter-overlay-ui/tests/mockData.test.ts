import test from "node:test";
import assert from "node:assert";

import { mockTimeline, summarizeEvents } from "../src/mockData";

test("summarizeEvents aggregates victories/defeats/draws", () => {
  const summary = summarizeEvents(mockTimeline);
  assert.strictEqual(summary.victories, 5);
  assert.strictEqual(summary.defeats, 3);
  assert.strictEqual(summary.draws, 1);
  assert.strictEqual(summary.total, 9);
});

test("summarizeEvents returns zeros for empty history", () => {
  const summary = summarizeEvents([]);
  assert.deepStrictEqual(summary, { victories: 0, defeats: 0, draws: 0, total: 0 });
});
