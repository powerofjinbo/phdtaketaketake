import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import FluidBackground from "@/components/FluidBackground";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PhDTake — Truth-based PhD advisor matching",
  description:
    "Truth-based PhD advisor matching. Every claim cited, nothing guessed.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="relative min-h-screen flex flex-col text-zinc-200">
        {/* Engineered fluid environment — fixed, behind everything, decorative. */}
        <FluidBackground />
        {/* Readability scrim — a fixed, subtle darkening layer that sits between
            the fluid (z-index -1) and the content (z-index 10) so text stays
            WCAG-legible over the brightest parts of the animation. */}
        <div aria-hidden="true" className="page-scrim" />
        <Nav />
        <main className="relative z-10 flex-1">{children}</main>
      </body>
    </html>
  );
}
