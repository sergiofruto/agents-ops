"use client";

import { useEffect, useRef } from "react";
import { toBody } from "@/lib/body";
import { ALL_JOINTS, type Joint, type RawLandmark } from "@/lib/landmarks";

const MAX_WIDTH = 720;

const BONES: [Joint, Joint][] = [
  ["leftShoulder", "rightShoulder"],
  ["leftShoulder", "leftElbow"],
  ["leftElbow", "leftWrist"],
  ["rightShoulder", "rightElbow"],
  ["rightElbow", "rightWrist"],
  ["leftShoulder", "leftHip"],
  ["rightShoulder", "rightHip"],
  ["leftHip", "rightHip"],
  ["leftHip", "leftKnee"],
  ["leftKnee", "leftAnkle"],
  ["rightHip", "rightKnee"],
  ["rightKnee", "rightAnkle"],
];

export function StageCanvas({
  image,
  person,
}: {
  image: HTMLImageElement;
  person: RawLandmark[] | null;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const scale = Math.min(1, MAX_WIDTH / image.naturalWidth);
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    if (!person) return;

    const body = toBody(person, canvas.width, canvas.height);
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#ea580c";
    for (const [a, b] of BONES) {
      if (!body.usable(a) || !body.usable(b)) continue;
      const p = body.point(a);
      const q = body.point(b);
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(q.x, q.y);
      ctx.stroke();
    }
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#ea580c";
    ctx.lineWidth = 2;
    for (const j of ALL_JOINTS) {
      if (!body.usable(j)) continue;
      const p = body.point(j);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }, [image, person]);

  return (
    <canvas
      ref={ref}
      role="img"
      aria-label="Your photo with the detected skeleton"
      className="w-full rounded-2xl border border-line bg-white"
    />
  );
}
