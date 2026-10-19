# Solutions — open only after your own attempt

Say out loud: the brute force, why it's slow, the better idea, then the time and space cost.

## 01 · Two Sum — O(n) / O(n)
```js
export function twoSum(nums, target) {
  const seen = new Map(); // value → index
  for (let i = 0; i < nums.length; i++) {
    const need = target - nums[i];
    if (seen.has(need)) return [seen.get(need), i];
    seen.set(nums[i], i);
  }
  return [];
}
```
Brute force is two nested loops, O(n²). Check the map *before* you insert, so an element is never paired with itself (`[3,3]`).

## 02 · Valid Parentheses — O(n) / O(n)
```js
export function isValid(s) {
  const pairs = { ')': '(', ']': '[', '}': '{' };
  const stack = [];
  for (const c of s) {
    if (c in pairs) {
      if (stack.pop() !== pairs[c]) return false;
    } else {
      stack.push(c);
    }
  }
  return stack.length === 0;
}
```
Edge cases: a closing bracket first (`]`, where pop returns undefined), and leftover openers (`(`).

## 03 · Valid Palindrome — O(n) / O(1)
```js
const isAlnum = (c) => /[a-z0-9]/i.test(c);
export function isPalindrome(s) {
  let l = 0, r = s.length - 1;
  while (l < r) {
    if (!isAlnum(s[l])) { l++; continue; }
    if (!isAlnum(s[r])) { r--; continue; }
    if (s[l].toLowerCase() !== s[r].toLowerCase()) return false;
    l++; r--;
  }
  return true;
}
```
The quick version, `s.toLowerCase().replace(/[^a-z0-9]/g, '')` compared with its reverse, works fine but uses O(n) memory. Mention it, then write the two-pointer version.

## 04 · Best Time to Buy and Sell Stock — O(n) / O(1)
```js
export function maxProfit(prices) {
  let min = Infinity, best = 0;
  for (const p of prices) {
    min = Math.min(min, p);
    best = Math.max(best, p - min);
  }
  return best;
}
```
The idea: the best sale on day i always buys at the lowest price seen so far.

## 05 · Valid Anagram — O(n) / O(k)
```js
export function isAnagram(s, t) {
  if (s.length !== t.length) return false;
  const count = new Map();
  for (const c of s) count.set(c, (count.get(c) ?? 0) + 1);
  for (const c of t) {
    const n = count.get(c);
    if (!n) return false;
    count.set(c, n - 1);
  }
  return true;
}
```
Sorting both strings is O(n log n). For lowercase-only input, a fixed `Array(26)` is the classic answer. For the Unicode follow-up, a Map plus `for...of` iterates by code point, but grapheme clusters (emoji) would need `Intl.Segmenter`.

## 06 · Binary Search — O(log n) / O(1)
```js
export function search(nums, target) {
  let lo = 0, hi = nums.length - 1;
  while (lo <= hi) {
    const mid = lo + ((hi - lo) >> 1);
    if (nums[mid] === target) return mid;
    if (nums[mid] < target) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}
```
Writing `lo + (hi - lo) / 2` avoids overflow in other languages, and it's worth mentioning even in JS.

## 07 · Reverse Linked List — O(n) / O(1)
```js
export function reverseList(head) {
  let prev = null, cur = head;
  while (cur) {
    const next = cur.next;
    cur.next = prev;
    prev = cur;
    cur = next;
  }
  return prev;
}
// recursive, O(n) stack:
// if (!head || !head.next) return head;
// const newHead = reverseList(head.next);
// head.next.next = head; head.next = null; return newHead;
```

## 08 · Climbing Stairs — O(n) / O(1)
```js
export function climbStairs(n) {
  let a = 1, b = 1; // ways(0), ways(1)
  for (let i = 2; i <= n; i++) [a, b] = [b, a + b];
  return b;
}
```
ways(n) = ways(n-1) + ways(n-2), which is Fibonacci. Naive recursion recomputes subproblems, so it's O(2ⁿ). Memoizing it, or this bottom-up loop, makes it O(n).
