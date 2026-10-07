import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";
import { HERO_IMAGE, SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });

const description =
  "Upload a yoga pose. Biomech Lab detects 33 body landmarks, measures your joint angles and scores your form, privately in your browser.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Biomech Lab · Score your yoga form in the browser",
  description,
  openGraph: {
    title: "Biomech Lab",
    description,
    images: [{ url: HERO_IMAGE.src, width: HERO_IMAGE.width, height: HERO_IMAGE.height, alt: HERO_IMAGE.alt }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Biomech Lab",
    description,
    images: [HERO_IMAGE.src],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
