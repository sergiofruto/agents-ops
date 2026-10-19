// 02 · Valid Parentheses — pattern: stack
// Given a string of only ()[]{} characters, return true if every bracket closes in the right order.
// Example: isValid("([]{})") → true, isValid("(]") → false
// Goal: O(n) time.

export function isValid(s) {
  // TODO
}

// ── tests: node --test problems/02-valid-parentheses.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('valid parentheses', () => {
  assert.equal(isValid('()'), true);
  assert.equal(isValid('()[]{}'), true);
  assert.equal(isValid('([]{})'), true);
  assert.equal(isValid('(]'), false);
  assert.equal(isValid('([)]'), false);
  assert.equal(isValid('('), false);
  assert.equal(isValid(']'), false);
  assert.equal(isValid(''), true);
});
