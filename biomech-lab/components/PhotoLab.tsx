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
import { buttonSecondary, focusRing, panel } from "./ui/styles";

type State =
  | { status: "idle" }
  | { status: "working" }
  | { status: "error"; message: string }
  | {
      status: "done";
      image: HTMLImageElement;
      person: RawLandmark[] | null;
      assessment: Assessment;
      detectMs: number;
    };

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
      // eslint-disable-next-line react-hooks/purity -- analyze() only runs from event handlers, never during render
      const t0 = performance.now();
      const detection = engine.detectImage(image);
      // eslint-disable-next-line react-hooks/purity -- analyze() only runs from event handlers, never during render
      const detectMs = Math.round(performance.now() - t0);
      setState({
        status: "done",
        image,
        person: detection.people[0] ?? null,
        assessment: assessPhoto(detection.people, detection.width, detection.height),
        detectMs,
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
    `rounded px-3 py-1.5 font-mono text-xs transition-colors ${focusRing} ${
      active ? "bg-accent text-accent-ink" : "text-fg-muted hover:text-fg-strong"
    }`;

  return (
    <div>
      <div role="group" aria-label="Choose input" className="inline-flex rounded-md border border-line bg-surface p-1">
        <button type="button" aria-pressed={tab === "samples"} className={tabClass(tab === "samples")} onClick={() => setTab("samples")}>
          samples
        </button>
        <button type="button" aria-pressed={tab === "upload"} className={tabClass(tab === "upload")} onClick={() => setTab("upload")}>
          upload photo
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
                className={`${panel} overflow-hidden text-left transition-colors hover:border-accent ${focusRing}`}
              >
                <Image
                  src={s.src}
                  alt=""
                  width={640}
                  height={360}
                  sizes="(min-width: 640px) 360px, 100vw"
                  className="aspect-video w-full object-cover brightness-[0.8]"
                />
                <span className="flex items-center justify-between gap-2 px-4 py-3">
                  <span className="text-sm font-medium text-fg-strong">{s.label}</span>
                  <span className="font-mono text-[11px] text-fg-subtle">{viewLabel(POSES[s.id].view).toLowerCase()}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-line-strong bg-surface px-6 py-12 text-center transition-colors hover:border-accent has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-accent">
            <ImageUp aria-hidden="true" className="size-8 text-accent" />
            <span className="font-medium text-fg-strong">Choose a full-body photo</span>
            <span className="max-w-md text-sm text-fg-muted">
              Warrior II and Tree facing the camera, Downward Dog from the side. Processed locally;
              nothing is uploaded.
            </span>
            <input type="file" accept="image/*" onChange={onFile} className="sr-only" />
          </label>
        )}
      </div>

      {state.status === "working" && (
        <p role="status" className="mt-8 flex items-center gap-2 font-mono text-sm text-fg-muted">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-accent" />
          analyzing… the first run downloads the pose model
        </p>
      )}
      {state.status === "error" && (
        <div role="alert" className={`mt-8 flex flex-wrap items-center gap-4 ${panel} border-fail/40 p-5`}>
          <TriangleAlert aria-hidden="true" className="size-5 text-fail" />
          <p className="flex-1 text-fg-strong">{state.message}</p>
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
          <AssessmentView assessment={state.assessment} meta={`detect ${state.detectMs} ms`} />
        </div>
      )}
    </div>
  );
}
