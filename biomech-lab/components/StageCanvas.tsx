"use client";

import { useEffect, useRef } from "react";
import type { RawLandmark } from "@/lib/landmarks";
import { overlayGeometry } from "@/lib/overlay";

const MAX_WIDTH = 720;
const ACCENT = "#22d3ee";
const BG = "#0b0f14";

export function StageCanvas({ image, person }: { image: HTMLImageElement; person: RawLandmark[] | null }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const scale = Math.min(1, MAX_WIDTH / image.naturalWidth);
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    ctx.filter = "brightness(0.65) saturate(0.5)";
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    ctx.filter = "none";
    if (!person) return;

    const g = overlayGeometry(person, canvas.width, canvas.height);
    ctx.lineCap = "round";
    ctx.lineWidth = 3;
    ctx.strokeStyle = ACCENT;
    for (const b of g.bones) {
      ctx.beginPath();
      ctx.moveTo(b.x1, b.y1);
      ctx.lineTo(b.x2, b.y2);
      ctx.stroke();
    }
    ctx.fillStyle = BG;
    ctx.lineWidth = 2;
    for (const j of g.joints) {
      ctx.beginPath();
      ctx.arc(j.x, j.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }, [image, person]);

  return (
    <canvas
      ref={ref}
      role="img"
      aria-label="Your photo with the detected skeleton"
      className="w-full rounded-md border border-line bg-bg"
    />
  );
}
