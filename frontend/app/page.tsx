import Link from "next/link";

const API = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getStats() {
  try {
    const res = await fetch(`${API}/pipeline/stats`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function getQuality() {
  try {
    const res = await fetch(`${API}/pipeline/data-quality/latest`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function StatCard({
  label,
  value,
  sub,
  accent = "text-white",
  icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-5 hover:bg-white/[0.05] transition-colors">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">{label}</p>
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-gray-400">
          {icon}
        </div>
      </div>
      <p className={`text-3xl font-bold tabular-nums ${accent}`}>{value ?? "—"}</p>
      {sub && <p className="text-xs text-gray-500 mt-1.5">{sub}</p>}
    </div>
  );
}

function StepCircle({ step, done }: { step: number; done?: boolean }) {
  if (done) {
    return (
      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 mt-0.5 bg-indigo-600/20 text-indigo-400 ring-1 ring-indigo-500/30">
      {step}
    </div>
  );
}

const stepCls =
  "group flex items-start gap-4 bg-white/[0.03] border border-white/[0.07] rounded-2xl p-5 hover:bg-white/[0.05] hover:border-indigo-500/30 transition-all duration-200";

const chevron = (
  <svg
    className="w-4 h-4 text-gray-600 group-hover:text-indigo-400 transition-colors flex-shrink-0 mt-0.5"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={2}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
  </svg>
);

export default async function DashboardPage() {
  const [stats, quality] = await Promise.all([getStats(), getQuality()]);

  const totalEntities = stats?.total_entities?.toLocaleString() ?? "—";
  const activeEntities = stats?.active_entities?.toLocaleString() ?? "—";
  const duplicateMatches = stats?.duplicate_matches?.toLocaleString() ?? "—";
  const needsReview = stats?.needs_review?.toLocaleString() ?? "—";
  const vectorSize = stats?.vector_index_size?.toLocaleString() ?? "—";
  const qualityScore = stats?.data_quality_score
    ? `${Number(stats.data_quality_score).toFixed(1)}%`
    : "—";
  const lastRun = stats?.last_pipeline_run
    ? new Date(stats.last_pipeline_run).toLocaleString()
    : null;

  const checkResults: Record<string, boolean> = quality?.check_results ?? {};
  const hasPipelineData = !!stats;
  const hasEntities = stats && stats.total_entities > 0;
  const hasDuplicates = stats && stats.duplicate_matches > 0;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/60 via-[#0a0a0f] to-purple-950/30 border border-white/[0.07] px-8 py-10">
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-600/10 via-transparent to-purple-600/5 pointer-events-none" />
        <div className="relative">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full">
              LLM-Assisted Entity Resolution
            </span>
            {lastRun && (
              <span className="text-xs text-gray-500">Last run: {lastRun}</span>
            )}
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">TrustGraph Platform</h1>
          <p className="text-gray-400 max-w-xl text-sm leading-relaxed">
            Ingest, deduplicate, and explore corporate entities using AI-powered matching,
            vector semantic search, and a graph knowledge base.
          </p>
          {!hasPipelineData && (
            <div className="mt-5 flex items-center gap-2 text-amber-400 text-sm">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              </svg>
              No pipeline data yet — follow the workflow below to get started.
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      {hasPipelineData && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">Platform Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard label="Total Entities" value={totalEntities} icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 0 0-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 0 1 5.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 0 1 9.288 0" />
              </svg>
            } />
            <StatCard label="Active" value={activeEntities} accent="text-emerald-400" icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
              </svg>
            } />
            <StatCard label="Duplicates" value={duplicateMatches} accent="text-amber-400" icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2m-6 12h8a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-8a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2z" />
              </svg>
            } />
            <StatCard label="Needs Review" value={needsReview} accent="text-rose-400" sub="Pending human review" icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            } />
            <StatCard label="Vector Index" value={vectorSize} sub="Qdrant embeddings" icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2z" />
              </svg>
            } />
            <StatCard label="Quality Score" value={qualityScore} accent="text-indigo-400" icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2zm0 0V9a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v10m-6 0a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2m0 0V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2z" />
              </svg>
            } />
          </div>
        </div>
      )}

      {/* Workflow guide */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">
          {hasPipelineData ? "What to do next" : "Getting Started — follow these steps"}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <a href="http://localhost:8080" target="_blank" rel="noreferrer" className={stepCls}>
            <StepCircle step={1} done={hasPipelineData} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                Run the ETL Pipeline
                <svg className="w-3 h-3 inline ml-1.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6m5-3h6m0 0v6m0-6L10 14" />
                </svg>
              </p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Open Airflow, trigger the trustgraph_etl DAG. It ingests GLEIF data, deduplicates, embeds, and loads everything.
              </p>
            </div>
            {chevron}
          </a>

          <Link href="/entities" className={stepCls}>
            <StepCircle step={2} done={hasEntities} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                Explore Entities
              </p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Search for companies by name or LEI, apply country/status filters, or use natural language semantic search.
              </p>
            </div>
            {chevron}
          </Link>

          <Link href="/resolution" className={stepCls}>
            <StepCircle step={3} done={hasDuplicates} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                Review Duplicates
              </p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Inspect AI-detected duplicate pairs. Accept or reject matches, and use LLM explanations to understand why.
              </p>
            </div>
            {chevron}
          </Link>
        </div>
      </div>

      {/* Quality checks */}
      {quality && Object.keys(checkResults).length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">Data Quality Checks</h2>
          <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
              {Object.entries(checkResults).map(([key, passed]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${passed ? "bg-emerald-500/20" : "bg-rose-500/20"}`}>
                    {passed ? (
                      <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-3 h-3 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                  </span>
                  <span className="text-sm text-gray-300 capitalize">{key.replace(/_/g, " ")}</span>
                  <span className={`ml-auto text-xs font-mono font-medium ${passed ? "text-emerald-400" : "text-rose-400"}`}>
                    {passed ? "PASS" : "FAIL"}
                  </span>
                </div>
              ))}
            </div>
            <div className="border-t border-white/5 pt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <Metric label="Missing Name Rate" value={quality.missing_name_rate !== undefined ? `${(quality.missing_name_rate * 100).toFixed(2)}%` : "—"} />
              <Metric label="Missing Address Rate" value={quality.missing_address_rate !== undefined ? `${(quality.missing_address_rate * 100).toFixed(2)}%` : "—"} />
              <Metric label="Duplicate LEI Count" value={quality.duplicate_lei_count ?? "—"} />
              <Metric label="Pipeline Runtime" value={quality.pipeline_runtime_seconds != null ? `${quality.pipeline_runtime_seconds}s` : "—"} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-mono text-gray-200">{value}</p>
    </div>
  );
}
