import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PlacidWay AI Knowledge Assistant",
  description:
    "Explore the seven approved PlacidWay sources. Treatment information and pricing with evidence you can read.",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
