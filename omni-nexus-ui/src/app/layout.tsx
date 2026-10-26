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
  title: "Omni-Agent Trading Nexus | AI Quant Workbench",
  description:
    "Autonomous Multi-Agent Financial Execution Engine & Consensus Pipeline powered by LangGraph and MCP.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans bg-[#F4F6F9] text-slate-900 overflow-x-hidden selection:bg-teal-500/15 selection:text-teal-900">
        {children}
      </body>
    </html>
  );
}
