// 07 · Reverse Linked List — pattern: pointer juggling
// Reverse a singly linked list and return the new head.
// Example: 1 → 2 → 3 → null  becomes  3 → 2 → 1 → null
// Goal: O(n) time, O(1) space iteratively. Bonus: do it recursively too.

export class ListNode {
  constructor(val, next = null) {
    this.val = val;
    this.next = next;
  }
}

export function reverseList(head) {
  // TODO
}

// ── tests: node --test problems/07-reverse-linked-list.mjs ──
import test from 'node:test';
import assert from 'node:assert/strict';
const fromArray = (a) => a.reduceRight((next, v) => new ListNode(v, next), null);
const toArray = (n) => { const out = []; while (n) { out.push(n.val); n = n.next; } return out; };
test('reverse linked list', () => {
  assert.deepEqual(toArray(reverseList(fromArray([1, 2, 3, 4, 5]))), [5, 4, 3, 2, 1]);
  assert.deepEqual(toArray(reverseList(fromArray([1, 2]))), [2, 1]);
  assert.deepEqual(toArray(reverseList(fromArray([1]))), [1]);
  assert.equal(reverseList(null) ?? null, null);
});
