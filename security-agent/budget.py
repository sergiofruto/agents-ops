"""Daily spending cap for Claude calls, with part of it held back for the digest."""
import sqlite3
from datetime import date
from typing import Literal

import config

Job = Literal["digest", "chat", "scan"]


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    # An unknown model is priced like the most expensive one we know, never as free
    price_in, price_out = config.MODEL_PRICES.get(model, max(config.MODEL_PRICES.values()))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class Budget:
    def __init__(self, conn: sqlite3.Connection, cap: float = config.AI_DAILY_CAP_USD,
                 reserve: float = config.AI_DIGEST_RESERVE_USD):
        self.conn, self.cap, self.reserve = conn, cap, reserve

    def spent_today(self, day: date) -> float:
        row = self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM ai_usage WHERE day=?",
                                (day.isoformat(),)).fetchone()
        return float(row[0])

    def _digest_ran(self, day: date) -> bool:
        return self.conn.execute("SELECT 1 FROM ai_usage WHERE day=? AND job='digest' LIMIT 1",
                                 (day.isoformat(),)).fetchone() is not None

    def can_spend(self, job: Job, day: date) -> bool:
        spent = self.spent_today(day)
        if job == "digest" or self._digest_ran(day):
            return spent < self.cap
        return spent < self.cap - self.reserve

    def record(self, job: Job, model: str, input_tokens: int, output_tokens: int, day: date) -> float:
        cost = cost_usd(model, input_tokens, output_tokens)
        self.conn.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)",
                          (day.isoformat(), job, model, input_tokens, output_tokens, cost))
        self.conn.commit()
        return cost
