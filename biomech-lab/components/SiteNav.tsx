import { ArrowUpRight, PersonStanding } from "lucide-react";
import { LINKS } from "@/lib/site";
import { focusRing } from "./ui/styles";

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#poses", label: "Poses" },
  { href: "#privacy", label: "Privacy" },
];

export function SiteNav() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-paper/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a href="#top" className={`flex items-center gap-2 rounded-md font-display text-lg ${focusRing}`}>
          <PersonStanding aria-hidden="true" className="size-5 text-accent" />
          Biomech Lab
        </a>
        <ul className="flex items-center gap-6 text-sm text-ink-muted">
          {NAV.map((l) => (
            <li key={l.href} className="hidden sm:block">
              <a href={l.href} className={`rounded-md hover:text-ink ${focusRing}`}>
                {l.label}
              </a>
            </li>
          ))}
          <li>
            <a
              href={LINKS.github}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center gap-1 rounded-md font-medium text-ink hover:text-accent ${focusRing}`}
            >
              GitHub
              <ArrowUpRight aria-hidden="true" className="size-4" />
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
