"use client";

import type { SolarData, FlareClass } from "@/lib/types";

const FLARE_COLORS: Record<FlareClass, string> = {
  X: "oklch(0.75 0.22 25)",
  M: "oklch(0.78 0.18 40)",
  C: "oklch(0.80 0.15 80)",
  B: "oklch(0.70 0.12 200)",
  A: "oklch(0.45 0 0)",
};

const KP_COLOR = (kp: number | null) => {
  if (!kp) return "oklch(0.45 0 0)";
  if (kp >= 7) return "oklch(0.75 0.22 25)";
  if (kp >= 5) return "oklch(0.78 0.18 40)";
  if (kp >= 4) return "oklch(0.80 0.15 80)";
  return "oklch(0.60 0.12 145)";
};

function KpBar({ kp }: { kp: number | null }) {
  const val = kp ?? 0;
  const pct = Math.min(100, (val / 9) * 100);
  const color = KP_COLOR(kp);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs" style={{ color: "var(--muted-foreground)" }}>
        <span>Kp index</span>
        <span style={{ color }}>{kp != null ? kp.toFixed(1) : "—"}</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <div className="flex justify-between text-xs" style={{ color: "var(--muted-foreground)" }}>
        <span>0</span>
        <span>Quiet</span>
        <span>Storm</span>
        <span>9</span>
      </div>
    </div>
  );
}

function XrayGauge({ cls, flux }: { cls: string; flux: number | null }) {
  const classes = ["A", "B", "C", "M", "X"];
  const idx = classes.indexOf(cls);
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs" style={{ color: "var(--muted-foreground)" }}>
        <span>X-ray flux</span>
        <span style={{ color: FLARE_COLORS[cls as FlareClass] ?? "white" }}>
          Class {cls}
          {flux != null ? ` (${flux.toExponential(1)} W/m²)` : ""}
        </span>
      </div>
      <div className="flex gap-1">
        {classes.map((c, i) => (
          <div
            key={c}
            className="flex-1 h-6 rounded flex items-center justify-center text-xs font-bold transition-all"
            style={{
              background: i <= idx
                ? `${FLARE_COLORS[c as FlareClass]}30`
                : "var(--muted)",
              border: i === idx
                ? `1px solid ${FLARE_COLORS[c as FlareClass]}`
                : "1px solid transparent",
              color: i <= idx
                ? FLARE_COLORS[c as FlareClass]
                : "var(--muted-foreground)",
            }}
          >
            {c}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SolarWidget({ solar }: { solar: SolarData }) {
  const alertColor = solar.alert_level === "CRITICAL" ? "oklch(0.75 0.22 25)"
    : solar.alert_level === "HIGH"   ? "oklch(0.78 0.18 40)"
    : solar.alert_level === "MEDIUM" ? "oklch(0.80 0.15 80)"
    : "oklch(0.60 0.12 145)";

  const isPulsing = solar.alert_level === "CRITICAL" || solar.alert_level === "HIGH";

  return (
    <div
      className={`rounded-lg p-4 space-y-4 ${isPulsing ? "pulse-alert" : ""}`}
      style={{
        background: "var(--card)",
        border: `1px solid ${alertColor}40`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-base">☀</span>
          <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: "var(--muted-foreground)" }}>
            Solar Weather
          </span>
        </div>
        <span
          className="text-xs px-2 py-0.5 rounded font-bold tracking-wider"
          style={{ background: `${alertColor}20`, color: alertColor, border: `1px solid ${alertColor}40` }}
        >
          {solar.alert_level}
        </span>
      </div>

      {/* X-ray gauge */}
      <XrayGauge cls={solar.xray.cls} flux={solar.xray.flux} />

      {/* Kp bar */}
      <KpBar kp={solar.kp.kp} />

      {/* Kp label + wind speed */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div
          className="rounded p-2"
          style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
        >
          <div className="text-xs uppercase tracking-wider mb-1">Geomagnetic</div>
          <div style={{ color: KP_COLOR(solar.kp.kp) }}>{solar.kp.label}</div>
        </div>
        <div
          className="rounded p-2"
          style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
        >
          <div className="text-xs uppercase tracking-wider mb-1">Solar wind</div>
          <div>
            {solar.solar_wind.speed != null
              ? `${solar.solar_wind.speed.toFixed(0)} km/s`
              : "—"}
          </div>
        </div>
      </div>

      {/* Recent flares */}
      {solar.recent_flares.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--muted-foreground)" }}>
            Recent flares (7d)
          </div>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {solar.recent_flares.slice(-6).reverse().map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-xs"
                style={{ color: "var(--muted-foreground)" }}
              >
                <span
                  className="font-bold"
                  style={{ color: FLARE_COLORS[(f.class?.[0] as FlareClass) ?? "A"] ?? "white" }}
                >
                  {f.class}
                </span>
                <span>{f.time?.substring(0, 16) ?? "—"}</span>
                {f.active_region && (
                  <span className="opacity-50">AR{f.active_region}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interpretation */}
      <div
        className="text-xs italic leading-relaxed border-t pt-3"
        style={{
          color: "var(--muted-foreground)",
          borderColor: "var(--border)",
        }}
      >
        {solar.interpretation}
      </div>

      <div className="text-right text-xs" style={{ color: "var(--muted-foreground)", opacity: 0.5 }}>
        {solar.updated?.substring(0, 16)} UTC
      </div>
    </div>
  );
}
