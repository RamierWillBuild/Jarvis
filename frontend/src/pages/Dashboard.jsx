import { useEffect, useState } from "react";
import { api } from "../api.js";

function groupByCategory(articles) {
  const map = {};
  for (const a of articles) {
    (map[a.category] = map[a.category] || []).push(a);
  }
  return map;
}

export default function Dashboard() {
  const [briefing, setBriefing] = useState(null);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [b, a] = await Promise.allSettled([
        api.getLatestBriefing(),
        api.getArticles(),
      ]);
      setBriefing(b.status === "fulfilled" ? b.value : null);
      setArticles(a.status === "fulfilled" ? a.value : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runPipeline() {
    setRunning(true);
    setError(null);
    try {
      await api.runPipeline();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  const grouped = groupByCategory(articles);
  const categories = Object.keys(grouped).sort();

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Daily Briefing</h1>
          <p className="muted">
            {briefing ? `Generated ${new Date(briefing.created_at).toLocaleString()}` : "Your intelligence summary"}
          </p>
        </div>
        <button className="btn" onClick={runPipeline} disabled={running}>
          {running ? "Running…" : "↻ Refresh news"}
        </button>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="card briefing-card">
        {loading ? (
          <div className="skeleton-block" />
        ) : briefing ? (
          <>
            <div className="card-eyebrow">{briefing.article_count} articles synthesized</div>
            <p className="briefing-text">{briefing.content}</p>
          </>
        ) : (
          <div className="empty">
            <p>No briefing yet.</p>
            <button className="btn" onClick={runPipeline} disabled={running}>
              Generate the first briefing
            </button>
          </div>
        )}
      </section>

      <h2 className="section-title">Top articles by category</h2>
      {categories.length === 0 && !loading && (
        <p className="muted">No articles fetched yet.</p>
      )}

      <div className="category-grid">
        {categories.map((cat) => (
          <div key={cat} className="card category-card">
            <div className="category-head">
              <span className={`tag tag-${cat}`}>{cat}</span>
              <span className="muted small">{grouped[cat].length}</span>
            </div>
            <ul className="article-list">
              {grouped[cat].slice(0, 5).map((a) => (
                <li key={a.id}>
                  <a href={a.url} target="_blank" rel="noreferrer" className="article-title">
                    {a.title}
                  </a>
                  {a.summary && <p className="article-summary">{a.summary}</p>}
                  <div className="article-meta">
                    <span>{a.source}</span>
                    {a.score > 0 && <span>▲ {a.score}</span>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
