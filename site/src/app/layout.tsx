import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LoL Makro",
  description: "League of Legends Mobile Companion",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body style={{ margin: 0, fontFamily: "-apple-system, Segoe UI, sans-serif", background: "#0a1428", color: "#fff" }}>
        {children}
      </body>
    </html>
  );
}
