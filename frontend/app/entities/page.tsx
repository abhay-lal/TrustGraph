"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import GraphPanel from "@/components/GraphPanel";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Entity {
  lei: string;
  legal_name: string;
  normalized_name?: string;
  country?: string;
  jurisdiction?: string;
  entity_status?: string;
  registration_status?: string;
  legal_address?: string;
  headquarters_address?: string;
  managing_lou?: string;
}

interface Duplicate {
  lei_a: string;
  lei_b: string;
  name_a: string;
  name_b: string;
  final_score: number;
  decision: string;
}

interface Relationship {
  rel_type: string;
  target_label: string;
  target_lei: string;
  target_type: string;
}

function statusColor(status?: string) {
  if (!status) return "bg-gray-800 text-gray-400";
  if (status === "ACTIVE") return "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20";
  if (status === "INACTIVE") return "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/20";
  return "bg-gray-800 text-gray-400";
}

function Skeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="bg-white/[0.03] border border-white/[0.05] rounded-xl px-4 py-3 h-14" />
      ))}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div>
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`text-sm text-gray-200 ${mono ? "font-mono text-xs" : ""}`}>{value || "—"}</p>
    </div>
  );
}

function EntityProfile({ entity, onNavigate }: { entity: Entity; onNavigate: (lei: string) => void }) {
  const [duplicates, setDuplicates] = useState<Duplicate[] | null>(null);
  const [relationships, setRelationships] = useState<Relationship[] | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [tab, setTab] = useState<"info" | "graph" | "duplicates">("info");

  const loadDuplicates = async () => {
    if (duplicates) return;
    const res = await fetch(`${API}/entities/${entity.lei}/duplicates`);
    setDuplicates(await res.json());
  };

  const loadRelationships = async () => {
    if (relationships) return;
    const res = await fetch(`${API}/entities/${entity.lei}/relationships`);
    setRelationships(await res.json());
  };

  const generateReport = async () => {
    setReportLoading(true);
    try {
      const res = await fetch(`${API}/llm/verification-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lei: entity.lei }),
      });
      const data = await res.json();
      setReport(data.report);
    } catch {
      setReport("Failed to generate report.");
    } finally {
      setReportLoading(false);
    }
  };

  let addr = entity.legal_address || "";
  try {
    const parsed = JSON.parse(addr);
    addr = [parsed.line1, parsed.city, parsed.postal].filter(Boolean).join(", ") || "";
  } catch {}

  const TABS = [
    { key: "info", label: "Details" },
    { key: "graph", label: "Graph" },
    { key: "duplicates", label: "Duplicates" },
  ] as const;

  return (
    <div className="bg-white/[0.03] border border-indigo-500/30 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-5 pb-4 border-b border-white/5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">{entity.legal_name}</h2>
            <p className="text-xs text-gray-500 font-mono mt-0.5">{entity.lei}</p>
          </div>
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColor(entity.entity_status)}`}>
            {entity.entity_status || "UNKNOWN"}
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-0.5 mt-4">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => {
                setTab(key);
                if (key === "duplicates") loadDuplicates();
                if (key === "graph") loadRelationships();
              }}
              className={`px-4 py-1.5 text-sm rounded-lg transition-all ${
                tab === key
                  ? "bg-indigo-600/20 text-indigo-300 font-medium"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        {tab === "info" && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
            <Field label="Country" value={entity.country} />
            <Field label="Jurisdiction" value={entity.jurisdiction} />
            <Field label="Registration Status" value={entity.registration_status} />
            <Field label="Legal Address" value={addr || "Not available"} />
            <Field label="Managing LOU" value={entity.managing_lou} mono />
          </div>
        )}

        {tab === "graph" && (
          <div>
            {relationships && relationships.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {relationships.map((r, i) => (
                  <button
                    key={i}
                    onClick={() => r.target_lei && onNavigate(r.target_lei)}
                    disabled={!r.target_lei}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border border-indigo-700/50 text-indigo-300 hover:bg-indigo-900/30 transition-colors disabled:opacity-40 disabled:cursor-default"
                  >
                    <span className="text-gray-500 text-[10px] uppercase tracking-wide">{r.rel_type.replace(/_/g, " ")}</span>
                    <span>→</span>
                    {r.target_label}
                  </button>
                ))}
              </div>
            )}
            <GraphPanel lei={entity.lei} onNodeClick={onNavigate} />
          </div>
        )}

        {tab === "duplicates" && (
          <div>
            {!duplicates ? (
              <div className="py-6 text-center text-gray-500 text-sm">Loading duplicates…</div>
            ) : duplicates.length === 0 ? (
              <div className="py-6 text-center">
                <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-sm text-gray-400 font-medium">No duplicates found</p>
                <p className="text-xs text-gray-600 mt-1">This record has no detected duplicate candidates.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {duplicates.map((d, i) => {
                  const other = d.lei_a === entity.lei ? d.lei_b : d.lei_a;
                  const otherName = d.lei_a === entity.lei ? d.name_b : d.name_a;
                  const pct = Math.round(d.final_score * 100);
                  return (
                    <div key={i} className="flex items-center justify-between bg-white/[0.03] rounded-xl px-4 py-3 border border-white/5">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-white truncate">{otherName}</p>
                        <p className="text-xs text-gray-500 font-mono">{other}</p>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                        <div className="flex items-center gap-1.5">
                          <div className="w-16 h-1 bg-gray-800 rounded-full">
                            <div
                              className={`h-1 rounded-full ${pct >= 85 ? "bg-amber-400" : "bg-yellow-600"}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono text-gray-400">{pct}%</span>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          d.decision === "same_entity"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-yellow-500/15 text-yellow-400"
                        }`}>
                          {d.decision.replace("_", " ")}
                        </span>
                        <button
                          onClick={() => onNavigate(other)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors whitespace-nowrap"
                        >
                          View →
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer — LLM report */}
      <div className="px-6 pb-5 border-t border-white/5 pt-4">
        {!report ? (
          <div className="flex items-center gap-3">
            <button
              onClick={generateReport}
              disabled={reportLoading}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-medium text-white transition-colors"
            >
              {reportLoading ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generating…
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Generate LLM Verification Report
                </>
              )}
            </button>
            <p className="text-xs text-gray-600">Uses GPT to analyze this entity&apos;s data quality and risk flags</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2z" />
                </svg>
                Verification Report
              </h3>
              <button onClick={() => setReport(null)} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                Dismiss
              </button>
            </div>
            <div className="text-sm text-gray-300 bg-white/[0.03] border border-white/5 rounded-xl p-4 leading-relaxed whitespace-pre-wrap font-mono text-xs">
              {report}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function EntitiesPage() {
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("");
  const [status, setStatus] = useState("");
  const [useNL, setUseNL] = useState(false);
  const [results, setResults] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useCallback(
    async (overrideQuery?: string) => {
      const q = overrideQuery !== undefined ? overrideQuery : query;
      setLoading(true);
      setHasSearched(true);
      setSelected(null);
      try {
        let entities: Entity[] = [];
        if (useNL && q) {
          const res = await fetch(`${API}/semantic-search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              query: q,
              country: country || undefined,
              entity_status: status || undefined,
              use_llm_parser: true,
            }),
          });
          const data = await res.json();
          entities = data.results || [];
        } else {
          const params = new URLSearchParams();
          if (q) params.set("query", q);
          if (country) params.set("country", country);
          if (status) params.set("entity_status", status);
          params.set("limit", "30");
          const res = await fetch(`${API}/entities/search?${params}`);
          entities = await res.json();
        }
        setResults(entities);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [query, country, status, useNL]
  );

  // Auto-load all entities on mount
  useEffect(() => {
    search("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = useCallback(async (lei: string) => {
    const res = await fetch(`${API}/entities/${lei}`);
    if (res.ok) {
      const entity = await res.json();
      setSelected(entity);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Entity Search</h1>
        <p className="text-sm text-gray-500 mt-1">
          Search by company name or LEI identifier. Click any result to view its full profile.
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder={useNL ? 'e.g. "active fintech companies in Germany"' : "Company name, LEI identifier…"}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06] transition-all"
            />
          </div>
          <input
            type="text"
            placeholder="Country (US, DE…)"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="w-40 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/60 transition-all"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500/60 transition-all"
          >
            <option value="">Any status</option>
            <option value="ACTIVE">Active only</option>
            <option value="INACTIVE">Inactive only</option>
          </select>
          <button
            onClick={() => search()}
            disabled={loading}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl text-sm font-semibold text-white transition-colors shadow-lg shadow-indigo-900/20"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        <label className="flex items-center gap-2.5 text-sm cursor-pointer group w-fit">
          <div className="relative">
            <input
              type="checkbox"
              checked={useNL}
              onChange={(e) => setUseNL(e.target.checked)}
              className="sr-only"
            />
            <div
              className={`w-8 h-4.5 rounded-full transition-colors ${useNL ? "bg-indigo-600" : "bg-gray-700"}`}
              style={{ height: "18px" }}
            >
              <div
                className={`absolute top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform ${useNL ? "translate-x-4" : "translate-x-0.5"}`}
              />
            </div>
          </div>
          <span className={`transition-colors ${useNL ? "text-indigo-300" : "text-gray-500 group-hover:text-gray-400"}`}>
            Natural language search
            <span className="ml-1.5 text-xs text-gray-600">(powered by GPT + Qdrant)</span>
          </span>
        </label>
      </div>

      {/* Selected entity profile */}
      {selected && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Selected Entity</p>
            <button
              onClick={() => setSelected(null)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Close
            </button>
          </div>
          <EntityProfile entity={selected} onNavigate={navigate} />
        </div>
      )}

      {/* Results */}
      <div>
        {loading ? (
          <Skeleton />
        ) : (
          <>
            {hasSearched && (
              <p className="text-xs text-gray-600 mb-3">
                {results.length === 0
                  ? "No entities found"
                  : `${results.length} result${results.length !== 1 ? "s" : ""}${query ? ` for "${query}"` : ""}`}
              </p>
            )}

            {results.length === 0 && hasSearched && (
              <div className="py-16 text-center bg-white/[0.02] border border-white/[0.05] rounded-2xl">
                <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                  </svg>
                </div>
                <p className="text-gray-400 font-medium mb-1">No entities found</p>
                <p className="text-sm text-gray-600">Try a different name or LEI, or clear the filters.</p>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-1.5">
                {results.map((e) => (
                  <button
                    key={e.lei}
                    onClick={() => setSelected(e)}
                    className={`w-full text-left rounded-xl px-4 py-3.5 border transition-all duration-150 hover:bg-white/[0.04] ${
                      selected?.lei === e.lei
                        ? "bg-indigo-600/10 border-indigo-500/40"
                        : "bg-white/[0.02] border-white/[0.05] hover:border-white/10"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-white truncate">{e.legal_name}</p>
                        <p className="text-xs text-gray-600 font-mono mt-0.5">{e.lei}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {e.country && (
                          <span className="text-xs text-gray-400 bg-white/5 px-2 py-0.5 rounded font-mono">
                            {e.country}
                          </span>
                        )}
                        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusColor(e.entity_status)}`}>
                          {e.entity_status || "UNKNOWN"}
                        </span>
                        <svg className="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
