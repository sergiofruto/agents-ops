CREATE TABLE IF NOT EXISTS polymarket_bets (
  id INTEGER PRIMARY KEY,
  question TEXT, outcome TEXT, price_at_bet REAL, virtual_amount REAL,
  potential_payout REAL, score REAL, edge REAL, kelly_stake REAL,
  status TEXT, timestamp TEXT, order_id TEXT
);
CREATE TABLE IF NOT EXISTS dota_bets (
  id INTEGER PRIMARY KEY,
  question TEXT, outcome TEXT, team_a TEXT, team_b TEXT, tournament TEXT,
  league_tier TEXT, price_at_bet REAL, virtual_amount REAL, potential_payout REAL,
  score REAL, edge REAL, true_prob REAL, elo_prob REAL, form_a REAL, form_b REAL,
  h2h_winrate REAL, h2h_sample INTEGER, kelly_stake REAL, status TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS dota_backtest (
  run_at TEXT PRIMARY KEY,
  days INTEGER, n_teams INTEGER, n_matches INTEGER,
  model_accuracy REAL, elo_accuracy REAL, model_brier REAL, elo_brier REAL,
  calibration_factor REAL
);
CREATE TABLE IF NOT EXISTS dota_elo (
  team_name TEXT PRIMARY KEY,
  elo REAL, snapshot_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  company TEXT, role TEXT, url TEXT, salary_min INTEGER, salary_max INTEGER,
  location TEXT, status TEXT, applied_at TEXT, next_action TEXT, notes TEXT,
  updated_at TEXT, interview_count INTEGER DEFAULT 0
);
