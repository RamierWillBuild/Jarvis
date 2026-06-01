import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch((e) => setError(e.message));
  }, []);

  async function toggleCategory(cat) {
    const updated = {
      ...settings,
      categories: { ...settings.categories, [cat]: !settings.categories[cat] },
    };
    setSettings(updated);
    await persist({ categories: updated.categories });
  }

  async function setProvider(provider) {
    const updated = { ...settings, llm_provider: provider };
    setSettings(updated);
    await persist({ llm_provider: provider });
  }

  async function persist(payload) {
    setStatus("Saving…");
    setError(null);
    try {
      const saved = await api.updateSettings(payload);
      setSettings(saved);
      setStatus("Saved");
      setTimeout(() => setStatus(null), 1500);
    } catch (e) {
      setError(e.message);
      setStatus(null);
    }
  }

  if (error && !settings) return <div className="page"><div className="alert">{error}</div></div>;
  if (!settings) return <div className="page"><div className="skeleton-block" /></div>;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="muted">Configure news sources and the language model</p>
        </div>
        {status && <span className="save-badge">{status}</span>}
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="card">
        <h2 className="section-title">News categories</h2>
        <p className="muted">Toggle which categories the pipeline gathers and summarizes.</p>
        <div className="toggle-list">
          {Object.entries(settings.categories).map(([cat, on]) => (
            <label key={cat} className="toggle-row">
              <span className={`tag tag-${cat}`}>{cat}</span>
              <input type="checkbox" checked={on} onChange={() => toggleCategory(cat)} />
              <span className={`switch ${on ? "on" : ""}`} aria-hidden />
            </label>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="section-title">LLM provider</h2>
        <p className="muted">Primary provider for summaries and chat. Falls back automatically if unavailable.</p>
        <div className="provider-options">
          {["openai", "ollama"].map((p) => (
            <button
              key={p}
              className={`provider-btn ${settings.llm_provider === p ? "selected" : ""}`}
              onClick={() => setProvider(p)}
            >
              {p === "openai" ? "OpenAI" : "Ollama (local)"}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
