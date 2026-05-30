// ── Polymarket ────────────────────────────────────────────────────────────────

export interface RecentBet {
  question: string;
  outcome: string;
  virtual_amount: number;
  edge: number;
  kelly_stake: number;
  status: "open" | "won" | "lost" | "void";
  timestamp: string;
}

export interface PolymarketStats {
  available: boolean;
  is_live?: boolean;
  total?: number;
  open?: number;
  won?: number;
  lost?: number;
  win_rate?: number;
  pnl?: number;
  roi?: number;
  recent_bets?: RecentBet[];
}

export interface PolymarketBet {
  id: number;
  question: string;
  outcome: string;
  price_at_bet: number;
  virtual_amount: number;
  potential_payout: number;
  score: number;
  edge: number;
  kelly_stake: number;
  status: "open" | "won" | "lost" | "void";
  timestamp: string;
  order_id: string | null;
}

// ── Dota ──────────────────────────────────────────────────────────────────────

export interface DotaRecentBet {
  question: string;
  outcome: string;
  virtual_amount: number;
  edge: number;
  kelly_stake: number;
  status: "open" | "won" | "lost" | "void";
  timestamp: string;
  team_a: string;
  team_b: string;
  tournament: string;
}

export interface DotaStats {
  available: boolean;
  is_live?: boolean;
  total?: number;
  open?: number;
  won?: number;
  lost?: number;
  win_rate?: number;
  pnl?: number;
  roi?: number;
  model_accuracy?: number | null;
  elo_accuracy?: number | null;
  recent_bets?: DotaRecentBet[];
}

export interface DotaBet {
  id: number;
  question: string;
  outcome: string;
  team_a: string;
  team_b: string;
  tournament: string;
  league_tier: string;
  price_at_bet: number;
  virtual_amount: number;
  potential_payout: number;
  score: number;
  edge: number;
  true_prob: number;
  elo_prob: number;
  form_a: number;
  form_b: number;
  h2h_winrate: number;
  h2h_sample: number;
  kelly_stake: number;
  status: "open" | "won" | "lost" | "void";
  timestamp: string;
}

export interface BacktestRow {
  run_at: string;
  days: number;
  n_teams: number;
  n_matches: number;
  model_accuracy: number;
  elo_accuracy: number;
  model_brier: number;
  elo_brier: number;
  calibration_factor: number;
}

export interface TeamRanking {
  name: string;
  elo: number;
}

export interface DotaAnalytics {
  backtest_history: BacktestRow[];
  team_rankings: TeamRanking[];
  roster_available: boolean;
}

// ── Market data ───────────────────────────────────────────────────────────────

export interface BtcData {
  price: number | null;
  change_24h: number | null;
  sparkline: number[];
}

export interface StockItem {
  ticker: string;
  price: number | null;
  change_pct: number | null;
}

export interface FearGreed {
  value: number | null;
  label: string;
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export type JobStatus =
  | "bookmarked"
  | "applied"
  | "phone"
  | "technical"
  | "final"
  | "offer"
  | "rejected";

export interface Job {
  id: number;
  company: string;
  role: string;
  url: string | null;
  salary_min: number | null;
  salary_max: number | null;
  location: string;
  status: JobStatus;
  applied_at: string | null;
  next_action: string | null;
  notes: string | null;
  updated_at: string;
  interview_count: number;
}

export interface Interview {
  id: number;
  job_id: number;
  stage: string;
  scheduled_at: string | null;
  notes: string | null;
  outcome: "pending" | "passed" | "failed";
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export interface PipelineCounts {
  bookmarked: number;
  applied: number;
  phone: number;
  technical: number;
  final: number;
  offer: number;
  rejected: number;
}

// ── Good Morning ──────────────────────────────────────────────────────────────

export interface AgentStatus {
  polymarket: boolean;
  dota: boolean;
}

export interface OvernightStat {
  available: boolean;
  new_bets?: number;
  won?: number;
  lost?: number;
  pnl?: number;
}

export interface MorningTask {
  agent: string;
  action: string;
  label: string;
}

export interface GoodMorningReport {
  date: string;
  agent_status: AgentStatus;
  overnight: {
    polymarket: OvernightStat;
    dota: OvernightStat;
  };
  backtest_today: boolean;
  tasks: MorningTask[];
}

// ── Coordinator ───────────────────────────────────────────────────────────────

export interface CoordinatorAgent {
  id: string;
  name: string;
  enabled: boolean;
  last_run: string | null;
  last_run_ago: string | null;
  last_status: "ok" | "error" | "timeout" | null;
  last_output: Record<string, unknown>;
  tasks: { active: number; done: number; blocked: number; skipped: number };
  blocked: string[];
  schedule: string | null;
  error?: string;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardData {
  polymarket: PolymarketStats;
  dota: DotaStats;
  btc: BtcData;
  stocks: StockItem[];
  fear_greed: FearGreed;
  pipeline: PipelineCounts;
}
