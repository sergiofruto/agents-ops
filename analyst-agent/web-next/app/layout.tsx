import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Analyst",
  description: "Hermetic Intelligence System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark h-full">
      <body className="min-h-full flex flex-col" style={{ background: "var(--background)", color: "var(--foreground)" }}>
        {/* Deep-space radial gradient */}
        <div
          className="fixed inset-0 -z-10 pointer-events-none"
          aria-hidden
          style={{
            background:
              "radial-gradient(ellipse 70% 50% at 30% 20%, oklch(0.15 0.06 280 / 30%) 0%, transparent 60%)," +
              "radial-gradient(ellipse 50% 40% at 80% 80%, oklch(0.12 0.04 200 / 20%) 0%, transparent 60%)",
          }}
        />

        {/* Sticky navbar */}
        <header
          className="sticky top-0 z-50 border-b"
          style={{
            borderColor: "var(--border)",
            background: "oklch(0.06 0 0 / 85%)",
            backdropFilter: "blur(8px)",
          }}
        >
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <Link href="/" className="flex items-center gap-3 group">
              <span className="text-xl">⬡</span>
              <span
                className="text-sm font-semibold tracking-widest uppercase"
                style={{ color: "var(--primary)", letterSpacing: "0.18em" }}
              >
                The Analyst
              </span>
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                Hermetic Intelligence System
              </span>
            </Link>

            <nav className="flex items-center gap-6 text-xs tracking-wider uppercase">
              <Link href="/" style={{ color: "var(--muted-foreground)" }} className="hover:text-white transition-colors">
                Dashboard
              </Link>
              <Link href="/chat" style={{ color: "var(--muted-foreground)" }} className="hover:text-white transition-colors">
                Chat
              </Link>
              <Link href="/briefs" style={{ color: "var(--muted-foreground)" }} className="hover:text-white transition-colors">
                Briefs
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6">
          {children}
        </main>

        <footer className="border-t py-3 text-center text-xs" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
          "As above, so below; as below, so above." — The Emerald Tablet
        </footer>
      </body>
    </html>
  );
}
