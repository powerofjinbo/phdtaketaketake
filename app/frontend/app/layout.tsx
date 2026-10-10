import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import FluidBackground from "@/components/FluidBackground";
import PointerGlow from "@/components/PointerGlow";
import SiteFooter from "@/components/SiteFooter";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const displaySerif = Instrument_Serif({
  variable: "--font-display-serif",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "PhDTake — Truth-based PhD advisor matching",
  description:
    "Truth-based PhD advisor matching. Every claim cited, nothing guessed.",
};

export const viewport: Viewport = {
  themeColor: "#06060b",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${displaySerif.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-screen flex-col text-zinc-200">
        {/* Engineered fluid environment — fixed, behind everything, decorative. */}
        <FluidBackground />
        {/* Readability scrim between the fluid (z -1) and the content (z 10). */}
        <div aria-hidden="true" className="page-scrim" />
        {/* Subtle film grain to kill gradient banding. */}
        <div aria-hidden="true" className="grain" />
        <PointerGlow />
        <Nav />
        <main className="relative z-10 flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
