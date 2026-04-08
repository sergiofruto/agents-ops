"use client";

import { useEffect, useRef, useState } from "react";
import type { SkyData, StarData, PlanetData } from "@/lib/types";

// Convert alt/az to canvas x/y using stereographic projection
// az: 0=N, 90=E, 180=S, 270=W
// alt: 0=horizon, 90=zenith
function altAzToXY(
  alt: number,
  az: number,
  cx: number,
  cy: number,
  radius: number
): [number, number] {
  // r = 0 at zenith, radius at horizon
  const r = radius * (1 - alt / 90);
  const azRad = ((az - 90) * Math.PI) / 180; // rotate so N is up
  const x = cx + r * Math.cos(azRad);
  const y = cy + r * Math.sin(azRad);
  return [x, y];
}

function magToRadius(mag: number): number {
  // Brighter stars are larger
  if (mag < 0)   return 3.5;
  if (mag < 1)   return 2.8;
  if (mag < 1.5) return 2.3;
  if (mag < 2)   return 1.9;
  if (mag < 2.5) return 1.5;
  if (mag < 3)   return 1.2;
  return 0.9;
}

const PLANET_COLORS: Record<string, string> = {
  Sun:     "#FFD700",
  Moon:    "#E8E8CC",
  Mercury: "#B5A99A",
  Venus:   "#F5E6A0",
  Mars:    "#E87B5A",
  Jupiter: "#C8A878",
  Saturn:  "#D4C494",
  Uranus:  "#7EC8E3",
  Neptune: "#4B70C8",
  Pluto:   "#A08878",
};

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀",
  Mars: "♂", Jupiter: "♃", Saturn: "♄",
  Uranus: "⛢", Neptune: "♆",
};

interface Props {
  sky: SkyData;
  width?: number;
  height?: number;
}

export default function StarMap({ sky, width = 500, height = 500 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hovered, setHovered] = useState<{ name: string; x: number; y: number } | null>(null);

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(cx, cy) - 30;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Scale for retina
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = width  * dpr;
    canvas.height = height * dpr;
    canvas.style.width  = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Background
    const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    bgGrad.addColorStop(0,   "oklch(0.08 0.03 270)");
    bgGrad.addColorStop(0.7, "oklch(0.05 0.02 260)");
    bgGrad.addColorStop(1,   "oklch(0.02 0 0)");
    ctx.fillStyle = bgGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();

    // Clip to circle
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.clip();

    // Altitude rings
    ctx.strokeStyle = "oklch(0.25 0.02 270 / 40%)";
    ctx.lineWidth = 0.5;
    for (const altDeg of [0, 30, 60]) {
      const r = radius * (1 - altDeg / 90);
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Cardinal labels
    ctx.fillStyle = "oklch(0.40 0.04 270)";
    ctx.font = "11px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const cardR = radius + 14;
    ctx.fillText("N", cx,       cy - cardR);
    ctx.fillText("S", cx,       cy + cardR);
    ctx.fillText("E", cx - cardR, cy);
    ctx.fillText("W", cx + cardR, cy);

    // Constellation lines
    ctx.strokeStyle = "oklch(0.35 0.05 220 / 50%)";
    ctx.lineWidth = 0.7;
    ctx.setLineDash([3, 4]);
    for (const { constellation: _c, lines } of sky.constellations) {
      for (const { a, b } of lines) {
        if (!a.visible || !b.visible) continue;
        const [x1, y1] = altAzToXY(a.alt, a.az, cx, cy, radius);
        const [x2, y2] = altAzToXY(b.alt, b.az, cx, cy, radius);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);

    // Stars
    for (const star of sky.stars) {
      if (!star.visible) continue;
      const [x, y] = altAzToXY(star.alt, star.az, cx, cy, radius);
      const r = magToRadius(star.mag);

      // Glow for bright stars
      if (star.mag < 1.5) {
        const glow = ctx.createRadialGradient(x, y, 0, x, y, r * 4);
        glow.addColorStop(0, "oklch(0.90 0.05 220 / 30%)");
        glow.addColorStop(1, "transparent");
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, r * 4, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.fillStyle = `oklch(${0.85 + Math.min(0.1, (3 - star.mag) * 0.02)} 0.04 220)`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Planets
    for (const planet of sky.planets) {
      if (!planet.visible) continue;
      const [x, y] = altAzToXY(planet.alt, planet.az, cx, cy, radius);
      const color = PLANET_COLORS[planet.name] ?? "#FFFFFF";

      // Planet glow
      const glow = ctx.createRadialGradient(x, y, 0, x, y, 12);
      glow.addColorStop(0, color + "60");
      glow.addColorStop(1, "transparent");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI * 2);
      ctx.fill();

      // Planet disc
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, planet.name === "Sun" ? 5 : planet.name === "Moon" ? 4.5 : 3.5, 0, Math.PI * 2);
      ctx.fill();

      // Symbol + name
      const sym = PLANET_SYMBOLS[planet.name] ?? "";
      ctx.fillStyle = color;
      ctx.font = "10px monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillText(`${sym} ${planet.name}`, x + 6, y - 2);
    }

    ctx.restore();

    // Horizon ring
    ctx.strokeStyle = "oklch(0.35 0.05 220 / 60%)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Zenith dot
    ctx.fillStyle = "oklch(0.50 0.05 270 / 60%)";
    ctx.beginPath();
    ctx.arc(cx, cy, 2, 0, Math.PI * 2);
    ctx.fill();
  }, [sky, width, height, cx, cy, radius]);

  // Hover detection
  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Check stars
    for (const star of sky.stars) {
      if (!star.visible) continue;
      const [x, y] = altAzToXY(star.alt, star.az, cx, cy, radius);
      if (Math.hypot(mx - x, my - y) < 6) {
        setHovered({ name: `${star.name} (${star.const}) mag ${star.mag}`, x: mx, y: my });
        return;
      }
    }
    // Check planets
    for (const planet of sky.planets) {
      if (!planet.visible) continue;
      const [x, y] = altAzToXY(planet.alt, planet.az, cx, cy, radius);
      if (Math.hypot(mx - x, my - y) < 10) {
        setHovered({ name: `${planet.name} — alt ${planet.alt.toFixed(1)}° az ${planet.az.toFixed(1)}°`, x: mx, y: my });
        return;
      }
    }
    setHovered(null);
  }

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHovered(null)}
        style={{ cursor: "crosshair", borderRadius: "50%" }}
      />
      {hovered && (
        <div
          className="absolute pointer-events-none z-10 rounded px-2 py-1 text-xs"
          style={{
            left: hovered.x + 10,
            top:  hovered.y - 24,
            background: "oklch(0.12 0 0 / 95%)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
            whiteSpace: "nowrap",
          }}
        >
          {hovered.name}
        </div>
      )}
    </div>
  );
}
