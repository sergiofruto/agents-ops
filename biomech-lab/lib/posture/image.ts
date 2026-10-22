import { MAX_SIDE_PX } from "./config";

/** Size that fits `max` on the long side, never upscaling. */
export function targetSize(w: number, h: number, max = MAX_SIDE_PX): { width: number; height: number } {
  const scale = Math.min(1, max / Math.max(w, h));
  return { width: Math.round(w * scale), height: Math.round(h * scale) };
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new window.Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("decode"));
    img.src = src;
  });
}

/**
 * Browser only. Decodes the file, redraws it at `targetSize` and returns the downscaled image
 * and its blob URL (the caller revokes it). Rejects with Error("decode") for unreadable files.
 */
export async function downscaleImage(
  file: File,
  max = MAX_SIDE_PX,
): Promise<{ image: HTMLImageElement; url: string; width: number; height: number }> {
  const original = URL.createObjectURL(file);
  try {
    const src = await loadImage(original);
    const { width, height } = targetSize(src.naturalWidth, src.naturalHeight, max);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("decode");
    ctx.drawImage(src, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.9));
    if (!blob) throw new Error("decode");
    const url = URL.createObjectURL(blob);
    return { image: await loadImage(url), url, width, height };
  } finally {
    URL.revokeObjectURL(original);
  }
}

/** SHA-256 of the file's bytes, hex. Used to spot the same photo on two steps. */
export async function fileFingerprint(file: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}
