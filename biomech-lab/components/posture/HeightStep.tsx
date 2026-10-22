"use client";

import { useState, type FormEvent } from "react";
import { HEIGHT_MAX_CM, HEIGHT_MIN_CM } from "@/lib/posture/config";
import { validHeight } from "@/lib/posture/validate";
import { buttonPrimary, focusRing, panel } from "../ui/styles";

export function HeightStep({ initial, onSubmit }: { initial: number | null; onSubmit: (cm: number) => void }) {
  const [value, setValue] = useState(initial === null ? "" : String(initial));
  const [error, setError] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    const cm = validHeight(value);
    if (cm === null) return setError(true);
    onSubmit(cm);
  }

  return (
    <form onSubmit={submit} className={`${panel} max-w-md p-6`} noValidate>
      <p className="font-mono text-xs uppercase tracking-[0.14em] text-fg-subtle">before you start</p>
      <label htmlFor="height" className="mt-2 block text-lg font-semibold text-fg-strong">
        Your height
      </label>
      <div className="mt-4 flex items-center gap-3">
        <input
          id="height"
          inputMode="numeric"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(false);
          }}
          aria-invalid={error}
          aria-describedby="height-note"
          className={`w-28 rounded-md border border-line-strong bg-bg px-3 py-2 font-mono text-fg-strong ${focusRing}`}
          placeholder="175"
        />
        <span className="font-mono text-sm text-fg-muted">cm</span>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-fail">
          Enter a whole number between {HEIGHT_MIN_CM} and {HEIGHT_MAX_CM}.
        </p>
      )}
      <p id="height-note" className="mt-3 text-sm text-fg-muted">
        Used only to turn measurements into centimeters. Stays on your device.
      </p>
      <button type="submit" className={`${buttonPrimary} mt-6`}>
        Continue
      </button>
    </form>
  );
}
