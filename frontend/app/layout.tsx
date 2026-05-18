import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustGraph",
  description: "LLM-assisted entity resolution and semantic search",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen font-sans antialiased">
        <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center gap-8">
          <span className="text-lg font-semibold tracking-tight text-white">
            Trust<span className="text-indigo-400">Graph</span>
          </span>
          <a href="/" className="text-sm text-gray-400 hover:text-white transition-colors">
            Dashboard
          </a>
          <a href="/entities" className="text-sm text-gray-400 hover:text-white transition-colors">
            Entities
          </a>
          <a href="/resolution" className="text-sm text-gray-400 hover:text-white transition-colors">
            Resolution
          </a>
        </nav>
        <main className="px-6 py-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
