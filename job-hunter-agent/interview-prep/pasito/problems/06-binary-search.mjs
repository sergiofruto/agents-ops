// 06 · Binary Search — pattern: binary search
// nums is sorted ascending with distinct values. Return the index of target, or -1.
// Example: search([-1, 0, 3, 5, 9, 12], 9) → 4
// Goal: O(log n). Watch the loop condition (lo <= hi) and off-by-ones.

export function search(nums, target) {
  // TODO
}

// ── tests: node --test problems/06-binary-search.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('binary search', () => {
  assert.equal(search([-1, 0, 3, 5, 9, 12], 9), 4);
  assert.equal(search([-1, 0, 3, 5, 9, 12], 2), -1);
  assert.equal(search([5], 5), 0);
  assert.equal(search([5], -5), -1);
  assert.equal(search([1, 3], 1), 0);
  assert.equal(search([1, 3], 3), 1);
  assert.equal(search([], 1), -1);
});
