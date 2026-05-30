import "server-only";
import { db } from "./db";
import type {
  PolymarketStats, PolymarketBet, DotaStats, DotaBet, DotaAnalytics,
  Job, PipelineCounts, JobStatus,
} from "./types";

export async function getPolymarketBets(): Promise<PolymarketBet[]> {
  const rs = await db.execute("SELECT * FROM polymarket_bets ORDER BY id DESC");
  return rs.rows as unknown as PolymarketBet[];
}

export async function getPolymarketStats(): Promise<PolymarketStats> {
  const bets = await getPolymarketBets();
  if (bets.length === 0) return { available: false };
  const won = bets.filter(b => b.status === "won").length;
  const lost = bets.filter(b => b.status === "lost").length;
  const resolved = won + lost;
  const pnl = bets.reduce((a, b) =>
    b.status === "won" ? a + (b.potential_payout - b.virtual_amount)
    : b.status === "lost" ? a - b.virtual_amount : a, 0);
  const wagered = bets.filter(b => b.status === "won" || b.status === "lost")
    .reduce((a, b) => a + b.virtual_amount, 0);
  return {
    available: true,
    is_live: bets.some(b => b.order_id),
    total: bets.length,
    open: bets.filter(b => b.status === "open").length,
    won, lost,
    win_rate: resolved ? Math.round((won / resolved) * 1000) / 10 : 0,
    pnl: Math.round(pnl * 100) / 100,
    roi: wagered ? Math.round((pnl / wagered) * 1000) / 10 : 0,
    recent_bets: bets.slice(0, 5).map(b => ({
      question: b.question, outcome: b.outcome, virtual_amount: b.virtual_amount,
      edge: b.edge, kelly_stake: b.kelly_stake, status: b.status, timestamp: b.timestamp,
    })),
  };
}

export async function getDotaBets(): Promise<DotaBet[]> {
  const rs = await db.execute("SELECT * FROM dota_bets ORDER BY id DESC");
  return rs.rows as unknown as DotaBet[];
}

export async function getDotaStats(): Promise<DotaStats> {
  const bets = await getDotaBets();
  if (bets.length === 0) return { available: false };
  const won = bets.filter(b => b.status === "won").length;
  const lost = bets.filter(b => b.status === "lost").length;
  const resolved = won + lost;
  const pnl = bets.reduce((a, b) =>
    b.status === "won" ? a + (b.potential_payout - b.virtual_amount)
    : b.status === "lost" ? a - b.virtual_amount : a, 0);
  const wagered = bets.filter(b => b.status === "won" || b.status === "lost")
    .reduce((a, b) => a + b.virtual_amount, 0);
  const bt = await db.execute("SELECT model_accuracy, elo_accuracy FROM dota_backtest ORDER BY run_at DESC LIMIT 1");
  const latest = bt.rows[0] as { model_accuracy?: number; elo_accuracy?: number } | undefined;
  return {
    available: true, is_live: false, total: bets.length,
    open: bets.filter(b => b.status === "open").length, won, lost,
    win_rate: resolved ? Math.round((won / resolved) * 1000) / 10 : 0,
    pnl: Math.round(pnl * 100) / 100,
    roi: wagered ? Math.round((pnl / wagered) * 1000) / 10 : 0,
    model_accuracy: latest?.model_accuracy != null ? Math.round(latest.model_accuracy * 1000) / 10 : null,
    elo_accuracy: latest?.elo_accuracy != null ? Math.round(latest.elo_accuracy * 1000) / 10 : null,
    recent_bets: bets.slice(0, 5).map(b => ({
      question: b.question, outcome: b.outcome, virtual_amount: b.virtual_amount,
      edge: b.edge, kelly_stake: b.kelly_stake, status: b.status, timestamp: b.timestamp,
      team_a: b.team_a, team_b: b.team_b, tournament: b.tournament,
    })),
  };
}

export async function getDotaAnalytics(): Promise<DotaAnalytics> {
  const bt = await db.execute("SELECT * FROM dota_backtest ORDER BY run_at DESC");
  const elo = await db.execute("SELECT team_name, elo FROM dota_elo ORDER BY elo DESC LIMIT 100");
  const team_rankings = elo.rows.map(r => ({ name: r.team_name as string, elo: r.elo as number }));
  return {
    backtest_history: bt.rows as unknown as DotaAnalytics["backtest_history"],
    team_rankings,
    roster_available: team_rankings.length > 0,
  };
}

export async function getJobs(): Promise<Job[]> {
  const rs = await db.execute("SELECT * FROM jobs ORDER BY updated_at DESC");
  return rs.rows as unknown as Job[];
}

export async function getPipeline(): Promise<PipelineCounts> {
  const jobs = await getJobs();
  const counts: PipelineCounts = {
    bookmarked: 0, applied: 0, phone: 0, technical: 0, final: 0, offer: 0, rejected: 0,
  };
  for (const j of jobs) {
    const s = j.status as JobStatus;
    if (s in counts) counts[s as keyof PipelineCounts]++;
  }
  return counts;
}
