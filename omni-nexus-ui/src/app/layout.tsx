import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Omni-Agent Trading Nexus",
  description:
    "Autonomous Swarm Financial Execution Engine & Consensus Pipeline — multi-agent AI trading system with Human-in-the-Loop safety.",
  keywords: [
    "trading",
    "AI agents",
    "LangGraph",
    "swarm intelligence",
    "financial analysis",
  ],
  openGraph: {
    title: "Omni-Agent Trading Nexus",
    description:
      "Autonomous multi-agent financial analysis and execution system powered by a LangGraph swarm.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Omni-Agent Trading Nexus",
    description:
      "Autonomous multi-agent financial analysis and execution system.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans bg-[#050810] text-slate-200 overflow-x-hidden">{children}</body>
    </html>
  );
}
