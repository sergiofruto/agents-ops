// 03 · Valid Palindrome — pattern: two pointers
// Ignoring case and every non-alphanumeric character, does s read the same forwards and backwards?
// Example: isPalindrome("A man, a plan, a canal: Panama") → true
// Goal: O(n) time, O(1) extra space (no building a cleaned copy).

export function isPalindrome(s) {
  // TODO
}

// ── tests: node --test problems/03-valid-palindrome.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('valid palindrome', () => {
  assert.equal(isPalindrome('A man, a plan, a canal: Panama'), true);
  assert.equal(isPalindrome('race a car'), false);
  assert.equal(isPalindrome(' '), true);
  assert.equal(isPalindrome('0P'), false);
  assert.equal(isPalindrome('ab_a'), true);
});
