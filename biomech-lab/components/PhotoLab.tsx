"use client";

import Image from "next/image";
import { ImageUp, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { assessPhoto, type Assessment } from "@/lib/assess";
import { OPEN_UPLOAD_EVENT } from "@/lib/events";
import type { RawLandmark } from "@/lib/landmarks";
import { POSES } from "@/lib/poses";
import type { PoseEngine } from "@/lib/pose-engine";
import { viewLabel } from "@/lib/pose-summaries";
import { SAMPLES } from "@/lib/samples";
import { AssessmentView } from "./AssessmentView";
import { StageCanvas } from "./StageCanvas";
import { buttonSecondary, card, focusRing } from "./ui/styles";

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

  useEffect(() => {
    const openUpload = () => setTab("upload");
    window.addEventListener(OPEN_UPLOAD_EVENT, openUpload);
    return () => window.removeEventListener(OPEN_UPLOAD_EVENT, openUpload);
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
    `rounded-full px-4 py-2 text-sm font-medium transition-colors ${focusRing} ${
      active ? "bg-ink text-paper" : "text-ink-muted hover:text-ink"
    }`;

  return (
    <div>
      <div role="group" aria-label="Choose input" className="inline-flex rounded-full border border-line bg-white p-1">
        <button type="button" aria-pressed={tab === "samples"} className={tabClass(tab === "samples")} onClick={() => setTab("samples")}>
          Samples
        </button>
        <button type="button" aria-pressed={tab === "upload"} className={tabClass(tab === "upload")} onClick={() => setTab("upload")}>
          Upload a photo
        </button>
      </div>

      <div className="mt-6">
        {tab === "samples" ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {SAMPLES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => void analyze(s.src)}
                className={`${card} overflow-hidden text-left transition-colors hover:border-ink ${focusRing}`}
              >
                <Image
                  src={s.src}
                  alt={`${s.label} sample photo`}
                  width={640}
                  height={360}
                  sizes="(min-width: 640px) 360px, 100vw"
                  className="aspect-video w-full object-cover"
                />
                <span className="flex items-center justify-between gap-2 px-4 py-3">
                  <span className="font-medium">{s.label}</span>
                  <span className="text-sm text-ink-subtle">{viewLabel(POSES[s.id].view)}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-line-strong bg-white px-6 py-12 text-center transition-colors hover:border-ink focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent">
            <ImageUp aria-hidden="true" className="size-8 text-accent" />
            <span className="font-medium">Choose a full-body photo</span>
            <span className="max-w-md text-sm text-ink-muted">
              Warrior II and Tree facing the camera, Downward Dog from the side. Your photo stays on
              your device.
            </span>
            <input type="file" accept="image/*" onChange={onFile} className="sr-only" />
          </label>
        )}
      </div>

      {state.status === "working" && (
        <p role="status" className="mt-8 flex items-center gap-2 text-ink-muted">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin text-accent" />
          Analyzing your pose… The first run downloads the pose model.
        </p>
      )}
      {state.status === "error" && (
        <div role="alert" className={`mt-8 flex flex-wrap items-center gap-4 ${card} p-5`}>
          <TriangleAlert aria-hidden="true" className="size-5 text-fail" />
          <p className="flex-1">{state.message}</p>
          {lastSrc && (
            <button type="button" className={buttonSecondary} onClick={() => void analyze(lastSrc)}>
              <RotateCcw aria-hidden="true" className="size-4" />
              Try again
            </button>
          )}
        </div>
      )}
      {state.status === "done" && (
        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.15fr_1fr]">
          <StageCanvas image={state.image} person={state.person} />
          <AssessmentView assessment={state.assessment} />
        </div>
      )}
    </div>
  );
}
