// PLACEHOLDER finance data for the public/deployed build. NOT real numbers.
export interface FinanceSummary {
  net_worth_usd: number;
  goal_name: string;
  goal_target_usd: number;
  goal_progress_pct: number;
  allocation: { label: string; usd: number }[];
}

export const financeMock: FinanceSummary = {
  net_worth_usd: 18750,
  goal_name: "Sample goal — house fund",
  goal_target_usd: 60000,
  goal_progress_pct: 31,
  allocation: [
    { label: "USD cash", usd: 14200 },
    { label: "Money market", usd: 3100 },
    { label: "Crypto", usd: 950 },
    { label: "Other", usd: 500 },
  ],
};
