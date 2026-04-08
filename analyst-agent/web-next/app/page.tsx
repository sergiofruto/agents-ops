import { fetchSky, fetchSolar, fetchStatus, fetchBriefs } from "@/lib/api";
import type { SkyData, SolarData, StatusData, BriefSummary } from "@/lib/types";
import StarMapClient from "@/components/StarMapClient";
import SolarWidget from "@/components/SolarWidget";
import Link from "next/link";

const THREAT_COLORS: Record<string, string> = {
  CRITICAL: "oklch(0.75 0.22 25)",
  HIGH:     "oklch(0.78 0.18 40)",
  MEDIUM:   "oklch(0.80 0.15 80)",
  LOW:      "oklch(0.60 0.12 145)",
  INFO:     "oklch(0.45 0 0)",
};

function ThreatBadge({ level }: { level: string }) {
  const color = THREAT_COLORS[level] ?? "oklch(0.45 0 0)";
  return (
    <span
      className="inline-block text-xs px-2 py-0.5 rounded font-bold tracking-widest uppercase"
      style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
    >
      {level}
    </span>
  );
}

function AspectRow({ a }: { a: { planet_a: string; planet_b: string; aspect: string; nature: string; orb: number; theme: string | null } }) {
  const isStress = a.nature === "tense";
  return (
    <div
      className="flex flex-col gap-0.5 py-2 border-b last:border-0"
      style={{ borderColor: "var(--border)" }}
    >
      <div className="flex items-center gap-2 text-xs">
        <span style={{ color: isStress ? "oklch(0.78 0.18 40)" : "oklch(0.60 0.12 145)" }}>
          {isStress ? "▲" : "◆"}
        </span>
        <span className="font-medium">{a.planet_a}</span>
        <span style={{ color: "var(--muted-foreground)" }}>{a.aspect}</span>
        <span className="font-medium">{a.planet_b}</span>
        <span className="ml-auto text-xs" style={{ color: "var(--muted-foreground)" }}>
          orb {a.orb.toFixed(1)}°
        </span>
      </div>
      {a.theme && (
        <div className="text-xs pl-4 leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
          {a.theme}
        </div>
      )}
    </div>
  );
}

export default async function DashboardPage() {
  const [sky, solar, status, briefs] = await Promise.all([
    fetchSky()  as Promise<SkyData  | null>,
    fetchSolar()  as Promise<SolarData | null>,
    fetchStatus() as Promise<StatusData | null>,
    fetchBriefs(5) as Promise<BriefSummary[]>,
  ]);

  const moonEmoji: Record<string, string> = {
    "New Moon": "🌑", "Waxing Crescent": "🌒", "First Quarter": "🌓",
    "Waxing Gibbous": "🌔", "Full Moon": "🌕", "Waning Gibbous": "🌖",
    "Last Quarter": "🌗", "Waning Crescent": "🌘",
  };
  const moonIcon = sky ? (moonEmoji[sky.moon_phase] ?? "☽") : "☽";

  return (
    <div className="space-y-6">
      {/* Status bar */}
      {status && (
        <div
          className="flex flex-wrap items-center gap-4 rounded-lg px-4 py-3 text-xs"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <span className="font-semibold tracking-widest uppercase" style={{ color: "var(--primary)" }}>
            ⬡ {status.agent}
          </span>
          <span style={{ color: "var(--muted-foreground)" }}>
            Signals: <strong style={{ color: "var(--foreground)" }}>{status.stats.total_signals}</strong>
          </span>
          <span style={{ color: "var(--muted-foreground)" }}>
            CVEs: <strong style={{ color: "var(--foreground)" }}>{status.stats.total_cves}</strong>
            {status.stats.kev_cves > 0 && (
              <span style={{ color: "oklch(0.78 0.18 40)" }}> ({status.stats.kev_cves} KEV)</span>
            )}
          </span>
          <span style={{ color: "var(--muted-foreground)" }}>
            Briefs: <strong style={{ color: "var(--foreground)" }}>{status.stats.total_briefs}</strong>
          </span>
          {status.latest_brief && (
            <span className="flex items-center gap-2">
              <span style={{ color: "var(--muted-foreground)" }}>Latest:</span>
              <ThreatBadge level={status.latest_brief.threat_level} />
            </span>
          )}
          <span className="ml-auto flex items-center gap-2" style={{ color: "var(--muted-foreground)" }}>
            {sky?.mercury_retrograde && (
              <span style={{ color: "oklch(0.78 0.18 40)" }}>☿ Hg Retrograde</span>
            )}
            <span>{moonIcon} {sky?.moon_phase}</span>
          </span>
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Star Map — takes 2 columns */}
        <div
          className="lg:col-span-2 rounded-lg p-4"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold tracking-widest uppercase" style={{ color: "var(--muted-foreground)" }}>
              Sky Now — {sky?.observer.lat.toFixed(2)}°N {sky?.observer.lon.toFixed(2)}°E
            </div>
            <div className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {sky?.utc.substring(0, 16)} UTC
            </div>
          </div>

          {sky ? (
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Canvas map */}
              <div className="flex justify-center">
                <StarMapClient sky={sky} />
              </div>

              {/* Aspects sidebar */}
              <div className="flex-1 min-w-0">
                <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--muted-foreground)" }}>
                  Active Aspects
                </div>
                <div className="space-y-0">
                  {sky.aspects.slice(0, 8).map((a, i) => (
                    <AspectRow key={i} a={a} />
                  ))}
                </div>

                {sky.mercury_retrograde && (
                  <div
                    className="mt-3 rounded p-2 text-xs"
                    style={{
                      background: "oklch(0.78 0.18 40 / 10%)",
                      border: "1px solid oklch(0.78 0.18 40 / 30%)",
                      color: "oklch(0.82 0.16 40)",
                    }}
                  >
                    ☿ Mercury retrograde — do not sign agreements; expect comms failures
                  </div>
                )}

                {/* Dominant themes */}
                {sky.tense_aspects.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--muted-foreground)" }}>
                      Dominant Sky Themes
                    </div>
                    <div className="space-y-1">
                      {(status?.sky?.dominant_themes ?? []).map((t, i) => (
                        <div key={i} className="text-xs leading-relaxed flex gap-2" style={{ color: "var(--muted-foreground)" }}>
                          <span style={{ color: "var(--primary)" }}>•</span>
                          <span>{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-xs" style={{ color: "var(--muted-foreground)" }}>
              Sky data unavailable — start the Flask API
            </div>
          )}
        </div>

        {/* Right column: Solar + latest brief */}
        <div className="space-y-6">
          {solar ? (
            <SolarWidget solar={solar} />
          ) : (
            <div
              className="rounded-lg p-4 text-xs text-center"
              style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}
            >
              Solar data unavailable
            </div>
          )}

          {/* Latest brief */}
          {status?.latest_brief && (
            <Link href={`/briefs/${status.latest_brief.id}`} className="block group">
              <div
                className="rounded-lg p-4 space-y-2 transition-colors"
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--border)",
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--primary)")}
                onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-widest" style={{ color: "var(--muted-foreground)" }}>
                    Latest Brief
                  </span>
                  <ThreatBadge level={status.latest_brief.threat_level} />
                </div>
                <div className="text-xs font-medium leading-relaxed">
                  {status.latest_brief.title}
                </div>
                <div className="text-xs leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                  {status.latest_brief.summary}
                </div>
                <div className="text-xs" style={{ color: "var(--muted-foreground)", opacity: 0.6 }}>
                  {status.latest_brief.created_at.substring(0, 16)} UTC
                </div>
              </div>
            </Link>
          )}
        </div>
      </div>

      {/* Recent briefs list */}
      {briefs.length > 0 && (
        <div
          className="rounded-lg p-4"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-widest" style={{ color: "var(--muted-foreground)" }}>
              Recent Briefs
            </div>
            <Link href="/briefs" className="text-xs" style={{ color: "var(--primary)" }}>
              All briefs →
            </Link>
          </div>
          <div className="space-y-2">
            {briefs.map(b => (
              <Link key={b.id} href={`/briefs/${b.id}`} className="block">
                <div
                  className="flex items-center gap-3 py-2 border-b last:border-0 text-xs transition-colors"
                  style={{ borderColor: "var(--border)" }}
                >
                  <ThreatBadge level={b.threat_level} />
                  <span className="flex-1 truncate">{b.title}</span>
                  <span style={{ color: "var(--muted-foreground)", flexShrink: 0 }}>
                    {b.created_at.substring(0, 16)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
