"use client";

import { useState, useEffect, useCallback } from "react";
import type { GoodMorningReport } from "@/lib/types";

// ── WMO weather code → label + symbol ─────────────────────────────────────
const WMO: Record<number, { label: string; symbol: string }> = {
  0: { label: "CLEAR", symbol: "○" },
  1: { label: "MOSTLY CLEAR", symbol: "◌" },
  2: { label: "PARTLY CLOUD", symbol: "◑" },
  3: { label: "OVERCAST", symbol: "●" },
  45: { label: "FOG", symbol: "≈" },
  48: { label: "ICING FOG", symbol: "≈" },
  51: { label: "LIGHT DRIZZLE", symbol: "·" },
  53: { label: "DRIZZLE", symbol: "·" },
  55: { label: "HEAVY DRIZZLE", symbol: "·" },
  61: { label: "LIGHT RAIN", symbol: "▿" },
  63: { label: "RAIN", symbol: "▿" },
  65: { label: "HEAVY RAIN", symbol: "▾" },
  71: { label: "LIGHT SNOW", symbol: "*" },
  73: { label: "SNOW", symbol: "*" },
  75: { label: "HEAVY SNOW", symbol: "✳" },
  80: { label: "SHOWERS", symbol: "▿" },
  81: { label: "SHOWERS", symbol: "▿" },
  82: { label: "HEAVY SHOWERS", symbol: "▾" },
  95: { label: "THUNDERSTORM", symbol: "↯" },
  99: { label: "HAIL STORM", symbol: "↯" },
};

function getWmo(code: number) {
  return WMO[code] ?? { label: "UNKNOWN", symbol: "?" };
}

// ── Clock widget ──────────────────────────────────────────────────────────
function ClockWidget() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const hh = now.getHours().toString().padStart(2, "0");
  const mm = now.getMinutes().toString().padStart(2, "0");
  const ss = now.getSeconds().toString().padStart(2, "0");
  const date = now
    .toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    })
    .toUpperCase();

  return (
    <div
      style={{
        backgroundColor: "#111111",
        border: "1px solid #222222",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "11px",
          letterSpacing: "0.08em",
          color: "#666666",
        }}
      >
        CLOCK
      </span>
      <div>
        <div
          style={{
            fontFamily: "'Doto', var(--font-mono), monospace",
            fontSize: "48px",
            fontWeight: 700,
            color: "#FFFFFF",
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          {hh}:{mm}:{ss}
        </div>
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "14px",
          letterSpacing: "0.06em",
          color: "#666666",
        }}
      >
        {date}
      </span>
    </div>
  );
}

// ── Weather widget (Open-Meteo, Buenos Aires) ─────────────────────────────
interface WeatherData {
  temp: number;
  code: number;
  wind: number;
}

function WeatherWidget() {
  const [wx, setWx] = useState<WeatherData | null>(null);
  const [error, setError] = useState(false);

  const fetchWeather = useCallback(() => {
    fetch(
      "https://api.open-meteo.com/v1/forecast?latitude=-34.6037&longitude=-58.3816&current=temperature_2m,weather_code,wind_speed_10m&wind_speed_unit=kmh&timezone=America%2FArgentina%2FBuenos_Aires",
    )
      .then((r) => r.json())
      .then((d) =>
        setWx({
          temp: Math.round(d.current.temperature_2m),
          code: d.current.weather_code,
          wind: Math.round(d.current.wind_speed_10m),
        }),
      )
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    fetchWeather();
    const id = setInterval(fetchWeather, 10 * 60 * 1000); // refresh every 10 min
    return () => clearInterval(id);
  }, [fetchWeather]);

  const condition = wx ? getWmo(wx.code) : null;

  return (
    <div
      style={{
        backgroundColor: "#111111",
        border: "1px solid #222222",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "11px",
          letterSpacing: "0.08em",
          color: "#666666",
        }}
      >
        WEATHER
      </span>

      {error ? (
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "#333333",
          }}
        >
          [UNAVAILABLE]
        </span>
      ) : !wx ? (
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "#333333",
          }}
        >
          [LOADING...]
        </span>
      ) : (
        <>
          <div>
            <div
              style={{ display: "flex", alignItems: "baseline", gap: "4px" }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "48px",
                  fontWeight: 700,
                  color: "#FFFFFF",
                  letterSpacing: "-0.02em",
                  lineHeight: 1,
                }}
              >
                {wx.temp}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "20px",
                  color: "#666666",
                }}
              >
                °C
              </span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "24px",
                color: "#333333",
                marginTop: "4px",
              }}
            >
              {condition?.symbol}
            </div>
          </div>
          <div>
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "11px",
                letterSpacing: "0.06em",
                color: "#999999",
              }}
            >
              {condition?.label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "11px",
                letterSpacing: "0.06em",
                color: "#666666",
                marginTop: "2px",
              }}
            >
              WIND {wx.wind} KM/H · BUE
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const QUOTES = [
  "Ship it, iterate, improve.",
  "Consistency beats intensity.",
  "One small step every day.",
  "Progress over perfection.",
  "Build momentum, not excuses.",
  "The best time to start was yesterday. The second best is now.",
  "Done is better than perfect.",
];

const mono: React.CSSProperties = { fontFamily: "var(--font-mono), monospace" };

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        ...mono,
        fontSize: "11px",
        letterSpacing: "0.08em",
        color: "#666666",
      }}
    >
      {children}
    </span>
  );
}

function WaterTracker() {
  const [cups, setCups] = useState(0);
  const WATER_KEY = `solaris_water_${todayKey()}`;

  useEffect(() => {
    const saved = localStorage.getItem(WATER_KEY);
    if (saved) setCups(Number(saved));
  }, [WATER_KEY]);

  function toggle(i: number) {
    const next = i < cups ? i : i + 1;
    setCups(next);
    localStorage.setItem(WATER_KEY, String(next));
  }

  const segments = Array.from({ length: 8 }, (_, i) => i);

  return (
    <div>
      <Label>HYDRATION</Label>
      {/* Segmented bar — Nothing signature viz */}
      <div style={{ display: "flex", gap: "2px", marginTop: "8px" }}>
        {segments.map((i) => (
          <button
            key={i}
            onClick={() => toggle(i)}
            title={`Cup ${i + 1}`}
            style={{
              flex: 1,
              height: "12px",
              backgroundColor: i < cups ? "#5B9BF6" : "#222222",
              border: "none",
              cursor: "pointer",
              transition: "background-color 150ms",
            }}
          />
        ))}
      </div>
      <div
        style={{
          ...mono,
          fontSize: "11px",
          color: "#666666",
          marginTop: "6px",
        }}
      >
        {cups} / 8
      </div>
    </div>
  );
}

function AgentDots({ status }: { status: Record<string, boolean> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      {Object.entries(status).map(([name, running]) => (
        <div
          key={name}
          style={{ display: "flex", alignItems: "center", gap: "8px" }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: running ? "#4A9E5C" : "#333333",
              flexShrink: 0,
            }}
          />
          <span
            style={{
              ...mono,
              fontSize: "11px",
              letterSpacing: "0.06em",
              color: running ? "#E8E8E8" : "#666666",
            }}
          >
            {name.toUpperCase()}
          </span>
        </div>
      ))}
    </div>
  );
}

function OvernightStats({
  overnight,
}: {
  overnight: GoodMorningReport["overnight"];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {Object.entries(overnight).map(([agent, stats]) => (
        <div
          key={agent}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
          }}
        >
          <Label>{agent.toUpperCase()}</Label>
          {stats.available ? (
            <span
              style={{
                ...mono,
                fontSize: "13px",
                color: (stats.pnl ?? 0) >= 0 ? "#4A9E5C" : "#D71921",
              }}
            >
              {(stats.pnl ?? 0) >= 0 ? "+" : ""}${stats.pnl?.toFixed(2)}
            </span>
          ) : (
            <span style={{ ...mono, fontSize: "11px", color: "#333333" }}>
              —
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function MissionControl() {
  const [report, setReport] = useState<GoodMorningReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningAgent, setRunningAgent] = useState<string | null>(null);
  const [doneAgents, setDoneAgents] = useState<Set<string>>(new Set());

  const quote = QUOTES[new Date().getDate() % QUOTES.length];

  useEffect(() => {
    fetch("/api/good-morning")
      .then((r) => r.json())
      .then(setReport)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  async function runTask(agent: string, action: string) {
    setRunningAgent(agent);
    try {
      if (action === "start") {
        await fetch(`/api/good-morning/start/${agent}`, { method: "POST" });
      } else if (action === "backtest") {
        await fetch("/api/good-morning/backtest", { method: "POST" });
      }
      setDoneAgents((prev) => new Set(prev).add(`${agent}:${action}`));
    } finally {
      setRunningAgent(null);
    }
  }

  return (
    <div
      style={{
        backgroundColor: "#111111",
        border: "1px solid #222222",
        borderRadius: "12px",
        padding: "24px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <span
          style={{
            ...mono,
            fontSize: "11px",
            letterSpacing: "0.08em",
            color: "#999999",
          }}
        >
          MISSION CONTROL
        </span>
        {report && (
          <span style={{ ...mono, fontSize: "11px", color: "#666666" }}>
            {report.date}
          </span>
        )}
      </div>

      {loading ? (
        <span style={{ ...mono, fontSize: "12px", color: "#666666" }}>
          [LOADING...]
        </span>
      ) : !report ? (
        <span style={{ ...mono, fontSize: "12px", color: "#666666" }}>
          [FLASK OFFLINE]
        </span>
      ) : (
        <>
          {/* Clock + Weather widgets */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              marginTop: "24px",
            }}
          >
            <ClockWidget />
            <WeatherWidget />
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "32px",
            }}
          >
            {/* Left column — actions + quote */}
            <div
              style={{ display: "flex", flexDirection: "column", gap: "24px" }}
            >
              {/* Actions */}
              <div>
                <Label>ACTIONS</Label>
                {report.tasks.length === 0 ? (
                  <div
                    style={{
                      ...mono,
                      fontSize: "12px",
                      color: "#4A9E5C",
                      marginTop: "8px",
                    }}
                  >
                    [ALL SYSTEMS RUNNING]
                  </div>
                ) : (
                  <div
                    style={{
                      marginTop: "8px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "2px",
                    }}
                  >
                    {report.tasks.map((t, i) => {
                      const key = `${t.agent}:${t.action}`;
                      const done = doneAgents.has(key);
                      const busy = runningAgent === t.agent;
                      return (
                        <div
                          key={i}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 0",
                            borderBottom: "1px solid #222222",
                          }}
                        >
                          <span
                            style={{
                              ...mono,
                              fontSize: "12px",
                              color: done ? "#333333" : "#E8E8E8",
                              textDecoration: done ? "line-through" : "none",
                            }}
                          >
                            {t.label}
                          </span>
                          <button
                            disabled={busy || done}
                            onClick={() => runTask(t.agent, t.action)}
                            style={{
                              ...mono,
                              fontSize: "11px",
                              letterSpacing: "0.06em",
                              color: done
                                ? "#333333"
                                : busy
                                  ? "#666666"
                                  : "#E8E8E8",
                              border: `1px solid ${done ? "#222222" : "#333333"}`,
                              background: "transparent",
                              padding: "4px 12px",
                              borderRadius: "999px",
                              cursor: done || busy ? "default" : "pointer",
                              transition: "border-color 150ms, color 150ms",
                            }}
                          >
                            {done ? "DONE" : busy ? "..." : "RUN"}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Quote */}
              <div>
                <Label>TODAY</Label>
                <p
                  style={{
                    fontFamily: "var(--font-sans), system-ui",
                    fontSize: "13px",
                    color: "#999999",
                    marginTop: "8px",
                    fontStyle: "italic",
                    lineHeight: 1.5,
                  }}
                >
                  &ldquo;{quote}&rdquo;
                </p>
              </div>
            </div>

            {/* Right column — agents + overnight + water */}
            <div
              style={{ display: "flex", flexDirection: "column", gap: "24px" }}
            >
              {/* Agent status */}
              <div>
                <Label>AGENTS</Label>
                <div
                  style={{
                    marginTop: "8px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  {(
                    Object.entries(report.agent_status) as [string, boolean][]
                  ).map(([name, running]) => (
                    <div
                      key={name}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <span
                        style={{
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          backgroundColor: running ? "#4A9E5C" : "#333333",
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          fontFamily: "var(--font-mono), monospace",
                          fontSize: "11px",
                          letterSpacing: "0.06em",
                          color: running ? "#E8E8E8" : "#666666",
                        }}
                      >
                        {name.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Overnight P&L */}
              <div>
                <Label>OVERNIGHT</Label>
                <div style={{ marginTop: "8px" }}>
                  <OvernightStats overnight={report.overnight} />
                </div>
              </div>

              {/* Water */}
              <WaterTracker />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
