import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { APP_VERSION, LINKS, NAV_LINKS } from "@/lib/site";
import { container, focusRing } from "./ui/styles";

export function SiteNav() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-bg/85 backdrop-blur">
      <nav aria-label="Main" className={`${container} flex items-center justify-between py-3`}>
        <Link href="/" className={`flex items-center gap-2 rounded font-mono text-sm text-fg-strong ${focusRing}`}>
          <span aria-hidden="true" className="text-accent">
            ◉
          </span>
          biomech_lab <span className="text-fg-subtle">{APP_VERSION}</span>
        </Link>
        <ul className="flex items-center gap-5 font-mono text-xs text-fg-muted">
          {NAV_LINKS.map((l) => (
            <li key={l.href} className={l.href === "/reports" ? "" : "hidden md:block"}>
              <Link href={l.href} className={`rounded hover:text-fg-strong ${focusRing}`}>
                {l.label}
              </Link>
            </li>
          ))}
          <li>
            <a
              href={LINKS.github}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-1 rounded text-fg-strong hover:text-accent ${focusRing}`}
            >
              github
              <ArrowUpRight aria-hidden="true" className="size-3.5" />
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
