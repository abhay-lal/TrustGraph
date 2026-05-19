import type { Metadata } from "next";
import "./globals.css";
import NavClient from "@/components/NavClient";

export const metadata: Metadata = {
  title: "TrustGraph",
  description: "LLM-assisted entity resolution and semantic search",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0a0a0f] text-gray-100 min-h-screen font-sans antialiased">
        <NavClient />
        <main className="px-6 py-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
