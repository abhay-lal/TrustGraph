"use client";

import { useState, useCallback } from "react";
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

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${color}`}
    >
      {text}
    </span>
  );
}

function statusColor(status?: string) {
  if (!status) return "bg-gray-700 text-gray-300";
  if (status === "ACTIVE") return "bg-emerald-900 text-emerald-300";
  if (status === "INACTIVE") return "bg-rose-900 text-rose-300";
  return "bg-gray-700 text-gray-300";
}

function EntityProfile({
  entity,
  onNavigate,
}: {
  entity: Entity;
  onNavigate: (lei: string) => void;
}) {
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
    addr = [parsed.line1, parsed.city, parsed.postal].filter(Boolean).join(", ");
  } catch {}

  return (
    <div className="bg-gray-900 border border-indigo-800 rounded-xl mt-2 overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-gray-800 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">{entity.legal_name}</h2>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{entity.lei}</p>
        </div>
        <Badge text={entity.entity_status || "UNKNOWN"} color={statusColor(entity.entity_status)} />
      </div>

      <div className="flex border-b border-gray-800">
        {(["info", "graph", "duplicates"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "duplicates") loadDuplicates();
              if (t === "graph") loadRelationships();
            }}
            className={`px-4 py-2 text-sm capitalize transition-colors ${
              tab === t
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="p-5">
        {tab === "info" && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <Field label="Country" value={entity.country} />
            <Field label="Jurisdiction" value={entity.jurisdiction} />
            <Field label="Reg. Status" value={entity.registration_status} />
            <Field label="Address" value={addr} className="col-span-2 md:col-span-3" />
            <Field label="Managing LOU" value={entity.managing_lou} />
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
                    className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                      r.target_lei
                        ? "border-indigo-700 text-indigo-300 hover:bg-indigo-900 cursor-pointer"
                        : "border-gray-700 text-gray-400 cursor-default"
                    }`}
                  >
                    <span className="text-gray-500">{r.rel_type.replace(/_/g, " ")} →</span>{" "}
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
              <p className="text-gray-500 text-sm">Loading...</p>
            ) : duplicates.length === 0 ? (
              <p className="text-gray-500 text-sm">No duplicate candidates found.</p>
            ) : (
              <div className="space-y-2">
                {duplicates.map((d, i) => {
                  const other = d.lei_a === entity.lei ? d.lei_b : d.lei_a;
                  const otherName = d.lei_a === entity.lei ? d.name_b : d.name_a;
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3"
                    >
                      <div>
                        <p className="text-sm text-white">{otherName}</p>
                        <p className="text-xs text-gray-500 font-mono">{other}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span
                          className={`text-xs font-mono ${
                            d.decision === "same_entity"
                              ? "text-amber-400"
                              : "text-yellow-600"
                          }`}
                        >
                          {d.final_score.toFixed(3)}
                        </span>
                        <Badge
                          text={d.decision.replace("_", " ")}
                          color={
                            d.decision === "same_entity"
                              ? "bg-amber-900 text-amber-300"
                              : "bg-yellow-900 text-yellow-300"
                          }
                        />
                        <button
                          onClick={() => onNavigate(other)}
                          className="text-xs text-indigo-400 hover:underline"
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

      <div className="px-5 pb-5 border-t border-gray-800 pt-4">
        {!report ? (
          <button
            onClick={generateReport}
            disabled={reportLoading}
            className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 rounded-lg text-sm font-medium text-white transition-colors"
          >
            {reportLoading ? "Generating…" : "Generate LLM Verification Report"}
          </button>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-300">Verification Report</h3>
              <button onClick={() => setReport(null)} className="text-xs text-gray-500 hover:text-gray-300">
                Close
              </button>
            </div>
            <pre className="text-xs text-gray-300 whitespace-pre-wrap bg-gray-800 rounded-lg p-4 leading-relaxed">
              {report}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  className,
}: {
  label: string;
  value?: string | null;
  className?: string;
}) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className="text-gray-200">{value || "—"}</p>
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
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState<Entity | null>(null);

  const search = useCallback(async () => {
    setLoading(true);
    setSearched(true);
    setSelected(null);
    try {
      let entities: Entity[] = [];
      if (useNL && query) {
        const res = await fetch(`${API}/semantic-search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            country: country || undefined,
            entity_status: status || undefined,
            use_llm_parser: true,
          }),
        });
        const data = await res.json();
        entities = data.results || [];
      } else {
        const params = new URLSearchParams();
        if (query) params.set("query", query);
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
  }, [query, country, status, useNL]);

  const navigate = useCallback(
    async (lei: string) => {
      const res = await fetch(`${API}/entities/${lei}`);
      if (res.ok) {
        const entity = await res.json();
        setSelected(entity);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    []
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Entity Search</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <div className="flex flex-col md:flex-row gap-3">
          <input
            type="text"
            placeholder={useNL ? 'e.g. "active fintech companies in Germany"' : "Search by name, LEI…"}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="text"
            placeholder="Country (e.g. US)"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="w-32 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">Any status</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
          <button
            onClick={search}
            disabled={loading}
            className="px-5 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 rounded-lg text-sm font-medium text-white transition-colors"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        <label className="flex items-center gap-2 mt-3 text-sm text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={useNL}
            onChange={(e) => setUseNL(e.target.checked)}
            className="accent-indigo-500"
          />
          Use natural language / semantic search (LLM-parsed)
        </label>
      </div>

      {selected && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm text-gray-400 font-medium">Selected Entity</h2>
            <button onClick={() => setSelected(null)} className="text-xs text-gray-500 hover:text-gray-300">
              ✕ Close
            </button>
          </div>
          <EntityProfile entity={selected} onNavigate={navigate} />
        </div>
      )}

      {searched && (
        <div>
          <p className="text-xs text-gray-500 mb-3">{results.length} result(s)</p>
          {results.length === 0 ? (
            <div className="text-gray-500 text-sm py-8 text-center">No entities found.</div>
          ) : (
            <div className="space-y-2">
              {results.map((e) => (
                <button
                  key={e.lei}
                  onClick={() => setSelected(e)}
                  className={`w-full text-left bg-gray-900 border rounded-lg px-4 py-3 hover:border-indigo-700 transition-colors ${
                    selected?.lei === e.lei ? "border-indigo-600" : "border-gray-800"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{e.legal_name}</p>
                      <p className="text-xs text-gray-500 font-mono">{e.lei}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {e.country && (
                        <span className="text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                          {e.country}
                        </span>
                      )}
                      <Badge
                        text={e.entity_status || "UNKNOWN"}
                        color={statusColor(e.entity_status)}
                      />
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
