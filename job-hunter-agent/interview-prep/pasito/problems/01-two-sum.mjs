// 01 · Two Sum — pattern: hash map
// Given nums and target, return the indices [i, j] of the two numbers that add up to target.
// Exactly one solution exists; you may not use the same element twice.
// Example: twoSum([2, 7, 11, 15], 9) → [0, 1]
// Goal: O(n) time.

export function twoSum(nums, target) {
  // TODO
}

// ── tests: node --test problems/01-two-sum.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
const sorted = (a) => [...(a ?? [])].sort((x, y) => x - y);
test('two sum', () => {
  assert.deepEqual(sorted(twoSum([2, 7, 11, 15], 9)), [0, 1]);
  assert.deepEqual(sorted(twoSum([3, 2, 4], 6)), [1, 2]);
  assert.deepEqual(sorted(twoSum([3, 3], 6)), [0, 1]);
  assert.deepEqual(sorted(twoSum([-1, -2, -3, -4, -5], -8)), [2, 4]);
});
