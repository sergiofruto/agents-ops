"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import type { PoseEngine } from "@/lib/pose-engine";
import { canShowResults, flowReducer, initialFlow, type FlowStep, type PhotoState } from "@/lib/posture/flow";
import type { PostureView } from "@/lib/posture/frame";
import { downscaleImage, fileFingerprint } from "@/lib/posture/image";
import { REJECTION_MESSAGE, validateStep } from "@/lib/posture/validate";
import { HeightStep } from "./HeightStep";
import { PhotoStep } from "./PhotoStep";
import { PostureResults } from "./PostureResults";

const VIEWS: PostureView[] = ["front", "side", "back"];
const PREVIOUS: Record<PostureView, FlowStep> = { front: "height", side: "front", back: "side" };

export function PostureCheck() {
  const [flow, dispatch] = useReducer(flowReducer, initialFlow);
  const [candidate, setCandidate] = useState<PhotoState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const engineRef = useRef<Promise<PoseEngine> | null>(null);
  const requestIdRef = useRef(0);
  const urlsRef = useRef(new Set<string>());

  useEffect(() => {
    const engine = engineRef;
    const urls = urlsRef.current;
    return () => {
      engine.current?.then((e) => e.close()).catch(() => {});
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, []);

  function getEngine(): Promise<PoseEngine> {
    engineRef.current ??= import("@/lib/pose-engine")
      .then((m) => m.createImageEngine())
      .catch((err: unknown) => {
        engineRef.current = null;
        throw err;
      });
    return engineRef.current;
  }

  function release(url: string | undefined) {
    if (!url) return;
    URL.revokeObjectURL(url);
    urlsRef.current.delete(url);
  }

  function clearCandidate() {
    release(candidate?.url);
    setCandidate(null);
    setError(null);
  }

  function goTo(step: FlowStep) {
    // Drop any photo still being checked for the step we're leaving.
    requestIdRef.current++;
    setBusy(false);
    clearCandidate();
    dispatch({ type: "goTo", step });
  }

  async function onFile(view: PostureView, file: File) {
    const id = ++requestIdRef.current;
    clearCandidate();
    setBusy(true);
    let url: string | undefined;
    try {
      const [engine, scaled, fingerprint] = await Promise.all([getEngine(), downscaleImage(file), fileFingerprint(file)]);
      url = scaled.url;
      urlsRef.current.add(url);
      if (id !== requestIdRef.current) return release(url);
      const d = engine.detectImage(scaled.image);
      const input = { people: d.people, width: d.width, height: d.height };
      const others = VIEWS.filter((v) => v !== view).flatMap((v) => flow.photos[v]?.fingerprint ?? []);
      const check = validateStep(view, input, { fingerprint, otherFingerprints: others });
      if (!check.ok) {
        release(url);
        setError(REJECTION_MESSAGE[check.reason]);
        return;
      }
      setCandidate({ view, input, url, fingerprint });
    } catch (e) {
      release(url);
      if (id !== requestIdRef.current) return;
      setError(
        e instanceof Error && e.message === "decode"
          ? "We couldn't open that photo. Try a JPG or PNG."
          : "Something went wrong while checking the photo. Try again.",
      );
    } finally {
      if (id === requestIdRef.current) setBusy(false);
    }
  }

  function acceptCandidate(view: PostureView) {
    if (!candidate) return;
    const previous = flow.photos[view]?.url;
    if (previous !== candidate.url) release(previous);
    dispatch({ type: "acceptPhoto", view, photo: candidate });
    setCandidate(null);
    setError(null);
  }

  function reset() {
    urlsRef.current.forEach((u) => URL.revokeObjectURL(u));
    urlsRef.current.clear();
    requestIdRef.current++;
    setCandidate(null);
    setError(null);
    setBusy(false);
    dispatch({ type: "reset" });
  }

  const { step } = flow;

  if (step === "height") {
    return <HeightStep initial={flow.heightCm} onSubmit={(cm) => dispatch({ type: "setHeight", heightCm: cm })} />;
  }

  if (step === "results" && canShowResults(flow) && flow.heightCm !== null) {
    return (
      <PostureResults
        heightCm={flow.heightCm}
        photos={flow.photos as Record<PostureView, PhotoState>}
        onEdit={goTo}
        onReset={reset}
      />
    );
  }

  if (step === "results") return null;

  return (
    <PhotoStep
      key={step}
      view={step}
      candidate={candidate}
      busy={busy}
      error={error}
      onFile={(f) => void onFile(step, f)}
      onUse={() => acceptCandidate(step)}
      onRetake={clearCandidate}
      onBack={() => goTo(PREVIOUS[step])}
    />
  );
}
