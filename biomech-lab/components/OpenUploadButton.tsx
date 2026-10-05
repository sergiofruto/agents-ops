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
        document.getElementById("lab")?.scrollIntoView({ behavior: "smooth" });
      }}
    >
      <Upload aria-hidden="true" className="size-4" />
      Upload a photo
    </button>
  );
}
