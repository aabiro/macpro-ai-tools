import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Cockpit — Mac Pro 1,1",
  description:
    "Web console for a 2006 Mac Pro running Mac OS X Lion, bridging it to modern AI services.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
