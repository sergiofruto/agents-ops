// 05 · Valid Anagram — pattern: frequency count
// Return true if t is a rearrangement of the letters of s.
// Example: isAnagram("anagram", "nagaram") → true
// Goal: O(n) time. Follow-up to discuss: what changes for full Unicode input?

export function isAnagram(s, t) {
  // TODO
}

// ── tests: node --test problems/05-valid-anagram.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
test('valid anagram', () => {
  assert.equal(isAnagram('anagram', 'nagaram'), true);
  assert.equal(isAnagram('rat', 'car'), false);
  assert.equal(isAnagram('a', 'ab'), false);
  assert.equal(isAnagram('aacc', 'ccac'), false);
  assert.equal(isAnagram('', ''), true);
});
