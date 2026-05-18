"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Match {
  id: string;
  lei_a: string;
  lei_b: string;
  name_a: string;
  name_b: string;
  name_similarity: number;
  address_similarity: number;
  embedding_similarity: number;
  country_match: number;
  jurisdiction_match: number;
  final_score: number;
  decision: string;
  reason_codes?: string | string[];
  reviewer_decision?: string;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.85 ? "bg-emerald-500" : value >= 0.65 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-36 text-gray-400 text-xs">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-300 w-10 text-right">
        {value.toFixed(3)}
      </span>
    </div>
  );
}

function decisionBadge(decision: string) {
  if (decision === "same_entity")
    return (
      <span className="bg-amber-900 text-amber-300 px-2 py-0.5 rounded text-xs font-medium">
        Same Entity
      </span>
    );
  if (decision === "needs_review")
    return (
      <span className="bg-yellow-900 text-yellow-300 px-2 py-0.5 rounded text-xs font-medium">
        Needs Review
      </span>
    );
  return (
    <span className="bg-gray-700 text-gray-300 px-2 py-0.5 rounded text-xs font-medium">
      Different
    </span>
  );
}

function MatchCard({ match, onReview }: { match: Match; onReview: (id: string, d: string) => void }) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explLoading, setExplLoading] = useState(false);
  const [reviewed, setReviewed] = useState(match.reviewer_decision || null);

  let codes: string[] = [];
  try {
    codes =
      typeof match.reason_codes === "string"
        ? JSON.parse(match.reason_codes)
        : match.reason_codes || [];
  } catch {}

  const getExplanation = async () => {
    setExplLoading(true);
    try {
      const res = await fetch(`${API}/llm/explain-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name_a: match.name_a,
          name_b: match.name_b,
          name_similarity: match.name_similarity,
          address_similarity: match.address_similarity,
          embedding_similarity: match.embedding_similarity,
          country_match: match.country_match,
          jurisdiction_match: match.jurisdiction_match,
          final_score: match.final_score,
          decision: match.decision,
          reason_codes: codes,
        }),
      });
      const data = await res.json();
      setExplanation(data.explanation);
    } catch {
      setExplanation("Failed to generate explanation.");
    } finally {
      setExplLoading(false);
    }
  };

  const review = async (decision: "accepted" | "rejected") => {
    await fetch(`${API}/entity-resolution/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ match_id: match.id, decision }),
    });
    setReviewed(decision);
    onReview(match.id, decision);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {decisionBadge(match.decision)}
          <span className="text-xs font-mono text-gray-400">
            score: {match.final_score.toFixed(3)}
          </span>
        </div>
        {reviewed && (
          <span
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              reviewed === "accepted"
                ? "bg-emerald-900 text-emerald-300"
                : "bg-rose-900 text-rose-300"
            }`}
          >
            {reviewed === "accepted" ? "Accepted" : "Rejected"}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 divide-x divide-gray-800 px-5 py-4">
        <div className="pr-4">
          <p className="text-xs text-gray-500 mb-1">Record A</p>
          <p className="text-sm font-medium text-white">{match.name_a}</p>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{match.lei_a}</p>
        </div>
        <div className="pl-4">
          <p className="text-xs text-gray-500 mb-1">Record B</p>
          <p className="text-sm font-medium text-white">{match.name_b}</p>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{match.lei_b}</p>
        </div>
      </div>

      <div className="px-5 pb-4 space-y-2">
        <ScoreBar label="Name similarity" value={match.name_similarity || 0} />
        <ScoreBar label="Address similarity" value={match.address_similarity || 0} />
        <ScoreBar label="Embedding similarity" value={match.embedding_similarity || 0} />
        <ScoreBar label="Country match" value={match.country_match || 0} />
        <ScoreBar label="Jurisdiction match" value={match.jurisdiction_match || 0} />
      </div>

      {codes.length > 0 && (
        <div className="px-5 pb-3 flex flex-wrap gap-1">
          {codes.map((c) => (
            <span key={c} className="bg-gray-800 text-gray-300 text-xs px-2 py-0.5 rounded-full">
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {explanation && (
        <div className="px-5 pb-4">
          <p className="text-xs text-gray-500 mb-1 font-medium">LLM Explanation</p>
          <p className="text-sm text-gray-300 bg-gray-800 rounded-lg px-4 py-3 leading-relaxed">
            {explanation}
          </p>
        </div>
      )}

      <div className="px-5 pb-4 flex items-center gap-3">
        <button
          onClick={getExplanation}
          disabled={explLoading || !!explanation}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 rounded-lg text-xs text-gray-300 transition-colors"
        >
          {explLoading ? "Explaining…" : explanation ? "Explained" : "Explain with LLM"}
        </button>
        {!reviewed && (
          <>
            <button
              onClick={() => review("accepted")}
              className="px-3 py-1.5 bg-emerald-800 hover:bg-emerald-700 rounded-lg text-xs text-emerald-200 transition-colors"
            >
              Accept Match
            </button>
            <button
              onClick={() => review("rejected")}
              className="px-3 py-1.5 bg-rose-900 hover:bg-rose-800 rounded-lg text-xs text-rose-200 transition-colors"
            >
              Reject Match
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function ResolutionPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "same_entity" | "needs_review">("all");

  useEffect(() => {
    const decision = filter === "all" ? "" : filter;
    fetch(
      `${API}/entity-resolution/matches?${decision ? `decision=${decision}&` : ""}limit=50`
    )
      .then((r) => r.json())
      .then(setMatches)
      .catch(() => setMatches([]))
      .finally(() => setLoading(false));
  }, [filter]);

  const handleReview = (id: string, decision: string) => {
    setMatches((prev) =>
      prev.map((m) => (m.id === id ? { ...m, reviewer_decision: decision } : m))
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Entity Resolution Review</h1>
          <p className="text-sm text-gray-400 mt-1">
            Side-by-side comparison of duplicate candidates
          </p>
        </div>
        <div className="flex gap-2">
          {(["all", "same_entity", "needs_review"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f
                  ? "bg-indigo-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {f === "all" ? "All" : f === "same_entity" ? "Same Entity" : "Needs Review"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-500">Loading matches…</div>
      ) : matches.length === 0 ? (
        <div className="py-16 text-center text-gray-500">
          <p className="text-lg mb-2">No matches found</p>
          <p className="text-sm">Run the ETL pipeline to detect duplicate candidates.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((m) => (
            <MatchCard key={m.id} match={m} onReview={handleReview} />
          ))}
        </div>
      )}
    </div>
  );
}
