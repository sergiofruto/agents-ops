"use client";

import { Upload } from "lucide-react";
import { OPEN_UPLOAD_EVENT } from "@/lib/events";
import { buttonSecondary } from "./ui/styles";

export function OpenUploadButton() {
  return (
    <button
      type="button"
      className={buttonSecondary}
      onClick={() => {
        window.dispatchEvent(new Event(OPEN_UPLOAD_EVENT));
        const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
        document.getElementById("analyze")?.scrollIntoView({ behavior });
      }}
    >
      <Upload aria-hidden="true" className="size-4" />
      Upload a photo
    </button>
  );
}
