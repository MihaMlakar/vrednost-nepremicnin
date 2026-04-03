import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vrednost Nepremičnin — Preverite realno ceno nepremičnine",
  description:
    "Primerjajte oglaševane cene z dejanskimi transakcijami iz GURS evidence trga nepremičnin. Vnesite povezavo z nepremicnine.net in preverite resnico.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="sl" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
