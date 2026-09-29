import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Biomech Lab",
  description: "Yoga pose scoring from joint angles, measured in your browser.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-950 text-neutral-100 antialiased">{children}</body>
    </html>
  );
}
