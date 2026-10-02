"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { assessPhoto, type Assessment } from "@/lib/assess";
import type { RawLandmark } from "@/lib/landmarks";
import type { PoseEngine } from "@/lib/pose-engine";
import { AssessmentView } from "./AssessmentView";
import { StageCanvas } from "./StageCanvas";

export const SAMPLES = [
  { id: "warrior2", src: "/samples/warrior2.jpg", label: "Warrior II" },
  { id: "tree", src: "/samples/tree.jpg", label: "Tree" },
  { id: "downdog", src: "/samples/downdog.jpg", label: "Downward Dog" },
] as const;

type State =
  | { status: "idle" }
  | { status: "working" }
  | { status: "error"; message: string }
  | { status: "done"; image: HTMLImageElement; person: RawLandmark[] | null; assessment: Assessment };

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new window.Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Could not load that image."));
    img.src = src;
  });
}

export function PhotoLab() {
  const [tab, setTab] = useState<"samples" | "upload">("samples");
  const [state, setState] = useState<State>({ status: "idle" });
  const [lastSrc, setLastSrc] = useState<string | null>(null);
  const engineRef = useRef<Promise<PoseEngine> | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const engine = engineRef;
    const blob = blobUrlRef;
    return () => {
      engine.current?.then((e) => e.close()).catch(() => {});
      if (blob.current) URL.revokeObjectURL(blob.current);
    };
  }, []);

  function getEngine(): Promise<PoseEngine> {
    engineRef.current ??= import("@/lib/pose-engine")
      .then((m) => m.createImageEngine())
      .catch((err: unknown) => {
        // Only drop the cached promise when engine creation itself failed —
        // not when a later step (e.g. loadImage) in some analyze() call rejects.
        engineRef.current = null;
        throw err;
      });
    return engineRef.current;
  }

  async function analyze(src: string) {
    const id = ++requestIdRef.current;
    setLastSrc(src);
    setState({ status: "working" });
    try {
      const [engine, image] = await Promise.all([getEngine(), loadImage(src)]);
      if (id !== requestIdRef.current) return; // a newer analyze() call superseded this one
      const detection = engine.detectImage(image);
      setState({
        status: "done",
        image,
        person: detection.people[0] ?? null,
        assessment: assessPhoto(detection.people, detection.width, detection.height),
      });
    } catch (e) {
      if (id !== requestIdRef.current) return;
      setState({ status: "error", message: e instanceof Error ? e.message : "Something went wrong." });
    }
  }

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    // Reset so re-selecting the same file still fires a future onChange.
    e.target.value = "";
    if (!file) return;
    // Keep the object URL alive so "Try again" works; release the previous upload's URL.
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    const url = URL.createObjectURL(file);
    blobUrlRef.current = url;
    void analyze(url);
  }

  const tabClass = (active: boolean) =>
    `rounded-md px-3 py-1.5 text-sm ${active ? "bg-neutral-100 text-neutral-900" : "bg-neutral-800"}`;

  return (
    <div className="space-y-6">
      <div role="group" aria-label="Choose input" className="flex gap-2">
        <button type="button" aria-pressed={tab === "samples"} className={tabClass(tab === "samples")} onClick={() => setTab("samples")}>
          Try a sample
        </button>
        <button type="button" aria-pressed={tab === "upload"} className={tabClass(tab === "upload")} onClick={() => setTab("upload")}>
          Upload photo
        </button>
      </div>

      {tab === "samples" ? (
        <div className="grid grid-cols-3 gap-3">
          {SAMPLES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => void analyze(s.src)}
              className="space-y-1 rounded-lg border border-neutral-800 p-2 text-sm hover:border-neutral-500 focus-visible:outline focus-visible:outline-2"
            >
              <Image src={s.src} alt={`${s.label} sample`} width={200} height={200} className="h-32 w-full rounded object-cover" />
              <span>{s.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <label className="block space-y-2 text-sm">
          <span>Full body in frame · Warrior II and Tree facing the camera · Downward Dog from the side</span>
          <input type="file" accept="image/*" onChange={onFile} className="block" />
        </label>
      )}

      {state.status === "working" && <p role="status">Analyzing…</p>}
      {state.status === "error" && (
        <div role="alert" className="space-y-2">
          <p>{state.message}</p>
          {lastSrc && (
            <button type="button" className="rounded-md bg-neutral-800 px-3 py-1.5 text-sm" onClick={() => void analyze(lastSrc)}>
              Try again
            </button>
          )}
        </div>
      )}
      {state.status === "done" && (
        <div className="space-y-4">
          <StageCanvas image={state.image} person={state.person} />
          <AssessmentView assessment={state.assessment} />
        </div>
      )}
    </div>
  );
}
