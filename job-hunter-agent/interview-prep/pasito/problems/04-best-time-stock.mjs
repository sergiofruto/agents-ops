// 04 · Best Time to Buy and Sell Stock — pattern: running min (one pass)
// prices[i] is the price on day i. Buy once, sell once later. Return the max profit (0 if none).
// Example: maxProfit([7, 1, 5, 3, 6, 4]) → 5 (buy at 1, sell at 6)
// Goal: O(n) time, O(1) space.

export function maxProfit(prices) {
  // TODO
}

// ── tests: node --test problems/04-best-time-stock.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('max profit', () => {
  assert.equal(maxProfit([7, 1, 5, 3, 6, 4]), 5);
  assert.equal(maxProfit([7, 6, 4, 3, 1]), 0);
  assert.equal(maxProfit([1]), 0);
  assert.equal(maxProfit([2, 4, 1]), 2);
  assert.equal(maxProfit([3, 2, 6, 5, 0, 3]), 4);
});
