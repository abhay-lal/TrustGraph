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
    value >= 0.85 ? "bg-emerald-500" : value >= 0.65 ? "bg-amber-500" : "bg-gray-600";
  return (
    <div className="flex items-center gap-3">
      <span className="w-32 text-xs text-gray-500 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-white/[0.05] rounded-full h-1.5">
        <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${Math.max(pct, 2)}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  if (decision === "same_entity")
    return (
      <span className="bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20 px-2.5 py-1 rounded-full text-xs font-medium">
        Same Entity
      </span>
    );
  if (decision === "needs_review")
    return (
      <span className="bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/20 px-2.5 py-1 rounded-full text-xs font-medium">
        Needs Review
      </span>
    );
  return (
    <span className="bg-gray-700/50 text-gray-400 ring-1 ring-white/10 px-2.5 py-1 rounded-full text-xs font-medium">
      Different
    </span>
  );
}

function MatchCard({ match, onReview }: { match: Match; onReview: (id: string, d: string) => void }) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explLoading, setExplLoading] = useState(false);
  const [reviewed, setReviewed] = useState<string | null>(match.reviewer_decision || null);

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

  const score = Math.round(match.final_score * 100);

  return (
    <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl overflow-hidden hover:border-white/10 transition-colors">
      {/* Card header */}
      <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <DecisionBadge decision={match.decision} />
          <div className="flex items-center gap-1.5">
            <div className="w-20 h-1.5 bg-white/[0.06] rounded-full">
              <div
                className={`h-1.5 rounded-full ${score >= 85 ? "bg-amber-500" : score >= 65 ? "bg-yellow-600" : "bg-gray-600"}`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-xs text-gray-500 font-mono">{score}% match</span>
          </div>
        </div>

        {reviewed && (
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5 ${
              reviewed === "accepted"
                ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20"
                : "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/20"
            }`}
          >
            {reviewed === "accepted" ? (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            {reviewed === "accepted" ? "Match accepted" : "Match rejected"}
          </span>
        )}
      </div>

      {/* Side-by-side records */}
      <div className="grid grid-cols-2 divide-x divide-white/5 px-5 py-4">
        <div className="pr-5">
          <p className="text-[10px] font-semibold text-indigo-400 uppercase tracking-widest mb-1.5">Record A</p>
          <p className="text-sm font-semibold text-white">{match.name_a}</p>
          <p className="text-xs text-gray-600 font-mono mt-0.5">{match.lei_a}</p>
        </div>
        <div className="pl-5">
          <p className="text-[10px] font-semibold text-purple-400 uppercase tracking-widest mb-1.5">Record B</p>
          <p className="text-sm font-semibold text-white">{match.name_b}</p>
          <p className="text-xs text-gray-600 font-mono mt-0.5">{match.lei_b}</p>
        </div>
      </div>

      {/* Score bars */}
      <div className="px-5 pb-4 space-y-2">
        <ScoreBar label="Name similarity" value={match.name_similarity || 0} />
        <ScoreBar label="Address" value={match.address_similarity || 0} />
        <ScoreBar label="Embedding" value={match.embedding_similarity || 0} />
        <ScoreBar label="Country match" value={match.country_match || 0} />
        <ScoreBar label="Jurisdiction" value={match.jurisdiction_match || 0} />
      </div>

      {/* Reason codes */}
      {codes.length > 0 && (
        <div className="px-5 pb-4 flex flex-wrap gap-1.5">
          {codes.map((c) => (
            <span key={c} className="bg-white/[0.04] text-gray-400 text-xs px-2.5 py-0.5 rounded-full border border-white/[0.06]">
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* LLM explanation */}
      {explanation && (
        <div className="mx-5 mb-4 bg-indigo-950/40 border border-indigo-500/20 rounded-xl px-4 py-3">
          <p className="text-[10px] font-semibold text-indigo-400 uppercase tracking-widest mb-1.5">LLM Explanation</p>
          <p className="text-sm text-gray-300 leading-relaxed">{explanation}</p>
        </div>
      )}

      {/* Actions */}
      <div className="px-5 pb-4 flex items-center gap-2 border-t border-white/5 pt-3">
        <button
          onClick={getExplanation}
          disabled={explLoading || !!explanation}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] hover:bg-white/[0.07] disabled:opacity-40 border border-white/[0.07] rounded-lg text-xs text-gray-300 transition-colors"
        >
          {explLoading ? (
            <>
              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Thinking…
            </>
          ) : explanation ? (
            <>
              <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Explained
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Explain with AI
            </>
          )}
        </button>

        {!reviewed && (
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => review("accepted")}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 font-medium transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Accept
            </button>
            <button
              onClick={() => review("rejected")}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 rounded-lg text-xs text-rose-300 font-medium transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Reject
            </button>
          </div>
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
    setLoading(true);
    const decision = filter === "all" ? "" : filter;
    fetch(`${API}/entity-resolution/matches?${decision ? `decision=${decision}&` : ""}limit=50`)
      .then((r) => r.json())
      .then(setMatches)
      .catch(() => setMatches([]))
      .finally(() => setLoading(false));
  }, [filter]);

  const handleReview = (id: string, decision: string) => {
    setMatches((prev) => prev.map((m) => (m.id === id ? { ...m, reviewer_decision: decision } : m)));
  };

  const reviewed = matches.filter((m) => m.reviewer_decision).length;
  const pending = matches.filter((m) => !m.reviewer_decision).length;

  const FILTERS = [
    { key: "all", label: "All matches" },
    { key: "same_entity", label: "Same entity" },
    { key: "needs_review", label: "Needs review" },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Entity Resolution Review</h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-detected duplicate pairs. Review each match and accept or reject it.
          </p>
        </div>

        {matches.length > 0 && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-500">
              <span className="text-emerald-400 font-semibold">{reviewed}</span> reviewed
            </span>
            <span className="text-gray-700">·</span>
            <span className="text-gray-500">
              <span className="text-amber-400 font-semibold">{pending}</span> pending
            </span>
          </div>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-white/[0.03] border border-white/[0.07] rounded-xl p-1 w-fit">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              filter === key
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/30"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white/[0.03] border border-white/[0.05] rounded-2xl h-48" />
          ))}
        </div>
      ) : matches.length === 0 ? (
        <div className="py-24 text-center bg-white/[0.02] border border-white/[0.05] rounded-2xl">
          <div className="w-14 h-14 rounded-full bg-gray-800/80 flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 0 2-2h2a2 2 0 0 0 2 2" />
            </svg>
          </div>
          <p className="text-gray-400 font-semibold mb-1">
            {filter === "all" ? "No duplicate matches found" : `No "${filter.replace("_", " ")}" matches`}
          </p>
          <p className="text-sm text-gray-600 mb-4">
            {filter === "all"
              ? "Run the ETL pipeline first to detect duplicate candidates."
              : "Try switching to \"All matches\" to see other results."}
          </p>
          {filter === "all" && (
            <a
              href="http://localhost:8080"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Open Airflow to run pipeline
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6m5-3h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((m) => (
            <MatchCard key={m.id} match={m} onReview={handleReview} />
          ))}
        </div>
      )}
    </div>
  );
}
