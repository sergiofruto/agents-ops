import { container } from "./ui/styles";

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className={`${container} flex flex-wrap justify-between gap-2 py-8 font-mono text-xs text-fg-muted`}>
        <p>educational feedback, not medical advice</p>
        <p>pose detection by MediaPipe · © 2026 Sergio Fruto</p>
      </div>
    </footer>
  );
}
