const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-bold ${accent ?? "text-white"}`}>{value ?? "—"}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

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
    : "No runs yet";

  const checkResults: Record<string, boolean> = quality?.check_results ?? {};

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Pipeline Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">Last run: {lastRun}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Entities" value={totalEntities} />
        <StatCard label="Active Entities" value={activeEntities} accent="text-emerald-400" />
        <StatCard label="Duplicate Matches" value={duplicateMatches} accent="text-amber-400" />
        <StatCard label="Needs Review" value={needsReview} accent="text-rose-400" />
        <StatCard label="Vector Index Size" value={vectorSize} sub="Qdrant collection" />
        <StatCard
          label="Data Quality Score"
          value={qualityScore}
          accent="text-indigo-400"
        />
      </div>

      {quality && Object.keys(checkResults).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-widest">
            Quality Checks
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(checkResults).map(([key, passed]) => (
              <div key={key} className="flex items-center gap-2 text-sm">
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    passed ? "bg-emerald-400" : "bg-rose-400"
                  }`}
                />
                <span className="text-gray-300">
                  {key.replace(/_/g, " ")}
                </span>
                <span className={`ml-auto font-mono text-xs ${passed ? "text-emerald-400" : "text-rose-400"}`}>
                  {passed ? "PASS" : "FAIL"}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-gray-800 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-400">
            <div>
              <span className="block text-xs text-gray-500">Missing Name Rate</span>
              <span>{quality.missing_name_rate !== undefined
                ? `${(quality.missing_name_rate * 100).toFixed(2)}%`
                : "—"}</span>
            </div>
            <div>
              <span className="block text-xs text-gray-500">Missing Address Rate</span>
              <span>{quality.missing_address_rate !== undefined
                ? `${(quality.missing_address_rate * 100).toFixed(2)}%`
                : "—"}</span>
            </div>
            <div>
              <span className="block text-xs text-gray-500">Duplicate LEI Count</span>
              <span>{quality.duplicate_lei_count ?? "—"}</span>
            </div>
            <div>
              <span className="block text-xs text-gray-500">Pipeline Runtime</span>
              <span>{quality.pipeline_runtime_seconds != null
                ? `${quality.pipeline_runtime_seconds}s`
                : "—"}</span>
            </div>
          </div>
        </div>
      )}

      {!stats && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p className="text-lg mb-2">No pipeline data yet</p>
          <p className="text-sm">
            Run the Airflow DAG at{" "}
            <a
              href="http://localhost:8080"
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 underline"
            >
              localhost:8080
            </a>{" "}
            to ingest data.
          </p>
        </div>
      )}
    </div>
  );
}
