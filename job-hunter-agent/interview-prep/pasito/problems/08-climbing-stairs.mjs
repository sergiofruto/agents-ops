// 08 · Climbing Stairs — pattern: intro DP
// You climb n steps, taking 1 or 2 steps at a time. How many distinct ways reach the top?
// Example: climbStairs(3) → 3  (1+1+1, 1+2, 2+1)
// Goal: O(n) time, O(1) space. Be ready to explain why naive recursion is O(2^n).

export function climbStairs(n) {
  // TODO
}

// ── tests: node --test problems/08-climbing-stairs.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('climbing stairs', () => {
  assert.equal(climbStairs(1), 1);
  assert.equal(climbStairs(2), 2);
  assert.equal(climbStairs(3), 3);
  assert.equal(climbStairs(5), 8);
  assert.equal(climbStairs(45), 1836311903);
});
