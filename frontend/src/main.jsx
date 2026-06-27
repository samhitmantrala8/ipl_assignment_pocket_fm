import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";
const PAGE_SIZE = 3;

function App() {
  const [tab, setTab] = useState("matches");
  const [season, setSeason] = useState(2026);
  const seasons = useApi("/v1/seasons");

  return (
    <main className="min-h-screen bg-stone-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                IPL Platform API
              </p>
              <h1 className="mt-1 text-3xl font-bold">Matches, points and squads</h1>
            </div>
            <label className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
              <span className="font-semibold">Season</span>
              <select
                value={season}
                onChange={(event) => setSeason(Number(event.target.value))}
                className="rounded border border-slate-300 bg-white px-2 py-1"
              >
                {(seasons.data?.data ?? [{ year: season }]).map((item) => (
                  <option key={item.year} value={item.year}>
                    {item.year}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <nav className="flex gap-2">
            {[
              ["matches", "Matches"],
              ["points", "Points Table"],
              ["teams", "Teams"]
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`rounded-md border px-4 py-2 text-sm font-semibold transition ${
                  tab === id
                    ? "border-emerald-700 bg-emerald-700 text-white"
                    : "border-slate-200 bg-white text-slate-700 hover:border-emerald-300"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {tab === "matches" && <Matches season={season} />}
        {tab === "points" && <PointsTable season={season} />}
        {tab === "teams" && <Teams season={season} />}
      </section>
    </main>
  );
}

function Matches({ season }) {
  const [matches, setMatches] = useState([]);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const sentinelRef = useRef(null);

  const hasMore = pagination ? page < pagination.totalPages : false;

  const loadMatches = useCallback(
    async (nextPage, replace = false) => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({
          page: String(nextPage),
          pageSize: String(PAGE_SIZE)
        });
        if (status) params.set("status", status);
        const response = await fetch(`${API_BASE}/v1/seasons/${season}/matches?${params}`);
        if (!response.ok) throw new Error("Unable to load matches");
        const payload = await response.json();
        setMatches((current) => (replace ? payload.data : [...current, ...payload.data]));
        setPagination(payload.pagination);
        setPage(nextPage);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [season, status]
  );

  useEffect(() => {
    loadMatches(1, true);
  }, [loadMatches]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadMatches(page + 1);
        }
      },
      { rootMargin: "160px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loadMatches, loading, page]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Matches / Results</h2>
          <p className="text-sm text-slate-600">
            Server-side pagination with infinite scroll on the client.
          </p>
        </div>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="live">Live</option>
          <option value="upcoming">Upcoming</option>
        </select>
      </div>

      <div className="grid gap-3">
        {matches.map((match) => (
          <article key={match.matchNumber} className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-500">
                  Match {match.matchNumber} · {formatDate(match.matchDate)}
                </p>
                <h3 className="mt-1 text-lg font-bold">
                  {match.teams.home.code} vs {match.teams.away.code}
                </h3>
                <p className="text-sm text-slate-600">
                  {match.venue.name}, {match.venue.city}
                </p>
              </div>
              <StatusBadge status={match.status} />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <TeamScore team={match.teams.home} />
              <TeamScore team={match.teams.away} />
            </div>
            <p className="mt-3 text-sm font-medium text-slate-700">
              {match.resultSummary ?? "Result pending"}
            </p>
          </article>
        ))}
      </div>

      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <div ref={sentinelRef} className="flex h-12 items-center justify-center text-sm text-slate-500">
        {loading ? "Loading more matches..." : hasMore ? "Scroll for more" : "End of list"}
      </div>
    </div>
  );
}

function PointsTable({ season }) {
  const { data, loading, error } = useApi(`/v1/seasons/${season}/points-table`);
  const rows = data?.data ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">Points Table</h2>
        <p className="text-sm text-slate-600">
          Served from a TTL-cached standings read model.
        </p>
      </div>
      {loading && <Loading />}
      {error && <ErrorMessage message={error} />}
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              {["Rank", "Team", "P", "W", "L", "NR", "Pts", "NRR"].map((heading) => (
                <th key={heading} className="px-4 py-3 font-semibold">
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.team.code}>
                <td className="px-4 py-3 font-bold">{row.rank}</td>
                <td className="px-4 py-3">
                  <div className="font-semibold">{row.team.name}</div>
                  <div className="text-xs text-slate-500">{row.team.code}</div>
                </td>
                <td className="px-4 py-3">{row.played}</td>
                <td className="px-4 py-3">{row.won}</td>
                <td className="px-4 py-3">{row.lost}</td>
                <td className="px-4 py-3">{row.noResult}</td>
                <td className="px-4 py-3 font-bold">{row.points}</td>
                <td className="px-4 py-3">{row.netRunRate.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Teams({ season }) {
  const { data, loading, error } = useApi(`/v1/seasons/${season}/teams`);
  const [selectedCode, setSelectedCode] = useState("CSK");
  const selected = useApi(`/v1/seasons/${season}/teams/${selectedCode}`);

  useEffect(() => {
    if (!data?.data?.length) return;
    setSelectedCode((current) => current || data.data[0].code);
  }, [data]);

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <aside className="space-y-3">
        <div>
          <h2 className="text-xl font-bold">Teams</h2>
          <p className="text-sm text-slate-600">Team profiles and season squads.</p>
        </div>
        {loading && <Loading />}
        {error && <ErrorMessage message={error} />}
        <div className="grid gap-2">
          {(data?.data ?? []).map((team) => (
            <button
              key={team.code}
              type="button"
              onClick={() => setSelectedCode(team.code)}
              className={`rounded-md border px-4 py-3 text-left text-sm transition ${
                selectedCode === team.code
                  ? "border-emerald-700 bg-emerald-50"
                  : "border-slate-200 bg-white hover:border-emerald-300"
              }`}
            >
              <span className="block font-bold">{team.name}</span>
              <span className="text-slate-500">{team.homeCity}</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="rounded-md border border-slate-200 bg-white p-5">
        {selected.loading && <Loading />}
        {selected.error && <ErrorMessage message={selected.error} />}
        {selected.data?.data && <TeamProfile team={selected.data.data} />}
      </section>
    </div>
  );
}

function TeamProfile({ team }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-emerald-700">{team.code}</p>
          <h3 className="text-2xl font-bold">{team.name}</h3>
          <p className="text-slate-600">{team.homeCity}</p>
        </div>
        <div className="rounded-md bg-slate-100 px-3 py-2 text-sm">
          Captain: <span className="font-bold">{team.captain?.name}</span>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {team.squad.map((player) => (
          <div key={player.id} className="rounded-md border border-slate-200 p-4">
            <div className="font-bold">{player.name}</div>
            <div className="mt-1 text-sm text-slate-600">{player.country}</div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">{player.role}</span>
              {player.isOverseas && (
                <span className="rounded bg-sky-100 px-2 py-1 text-sky-800">Overseas</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TeamScore({ team }) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <div className="font-bold">{team.name}</div>
      <div className="mt-1 text-sm text-slate-600">
        {team.score ? `${team.score.runs}/${team.score.wickets} (${team.score.overs})` : "Yet to bat"}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    completed: "bg-slate-900 text-white",
    live: "bg-red-600 text-white",
    upcoming: "bg-amber-100 text-amber-900"
  };
  return (
    <span className={`rounded px-2 py-1 text-xs font-bold uppercase ${styles[status]}`}>
      {status}
    </span>
  );
}

function useApi(path) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const url = useMemo(() => `${API_BASE}${path}`, [path]);

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: "" });
    fetch(url)
      .then((response) => {
        if (!response.ok) throw new Error("Request failed");
        return response.json();
      })
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: "" });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return state;
}

function Loading() {
  return <p className="rounded-md bg-white p-3 text-sm text-slate-600">Loading...</p>;
}

function ErrorMessage({ message }) {
  return <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{message}</p>;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

createRoot(document.getElementById("root")).render(<App />);
