import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Solaris",
  description: "Personal dashboard — agents, markets, jobs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body
        className="min-h-full flex flex-col"
        style={{
          backgroundColor: "#0a0f1e",
          color: "#f1f5f9",
          fontFamily: "var(--font-sans), system-ui, sans-serif",
        }}
      >
        <header className="sticky top-0 z-50 border-b border-[#1a2744] bg-[#0a0f1e]">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="text-[15px] font-bold tracking-[0.08em]"
              style={{
                background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
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
                  className="text-[12.5px] text-[#475569] hover:text-[#f1f5f9] transition-colors"
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
