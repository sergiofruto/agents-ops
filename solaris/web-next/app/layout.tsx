import type { Metadata } from "next";
import { Space_Grotesk, Space_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
});

const spaceMono = Space_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Solaris",
  description: "Personal dashboard — agents, markets, jobs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${spaceGrotesk.variable} ${spaceMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col" style={{ backgroundColor: "#000000", color: "#E8E8E8", fontFamily: "var(--font-sans), system-ui, sans-serif" }}>

        {/* Sticky navbar */}
        <header className="sticky top-0 z-50" style={{ borderBottom: "1px solid #222222", backgroundColor: "#000000" }}>
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="transition-colors"
              style={{ fontFamily: "var(--font-mono), monospace", fontSize: "13px", fontWeight: 700, letterSpacing: "0.08em", color: "#FFFFFF" }}
            >
              SOLARIS
            </Link>

            <nav className="flex items-center gap-8">
              {[
                { href: "/", label: "HOME" },
                { href: "/polymarket", label: "POLYMARKET" },
                { href: "/dota", label: "DOTA 2" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="transition-colors hover:text-white"
                  style={{ fontFamily: "var(--font-mono), monospace", fontSize: "11px", fontWeight: 400, letterSpacing: "0.08em", color: "#666666" }}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <TooltipProvider>
          <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-8">
            {children}
          </main>
        </TooltipProvider>
      </body>
    </html>
  );
}
