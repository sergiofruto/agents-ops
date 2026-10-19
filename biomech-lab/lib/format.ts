const WORDS: Record<number, string> = { 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five" };

/** Spells out small counts ("Three"); falls back to the digit for anything else. */
export function countWord(n: number): string {
  return WORDS[n] ?? String(n);
}
