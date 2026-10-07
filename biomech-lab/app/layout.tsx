import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { HERO_IMAGE, SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });

const description =
  "In-browser pose analysis: 33 body landmarks become joint angles and an auditable form score for Warrior II, Tree and Downward Dog. Nothing is uploaded.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Biomech Lab · Pose analysis in your browser",
  description,
  openGraph: {
    title: "Biomech Lab",
    description,
    images: [{ url: HERO_IMAGE.src, width: HERO_IMAGE.width, height: HERO_IMAGE.height, alt: HERO_IMAGE.alt }],
  },
  twitter: { card: "summary_large_image", title: "Biomech Lab", description, images: [HERO_IMAGE.src] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
