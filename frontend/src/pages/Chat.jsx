import { useRef, useState, useEffect } from "react";
import { api } from "../api.js";

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Ask me anything about the latest news I've gathered." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const history = messages.filter((m) => m.role !== "system");
    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res = await api.chat(text, history);
      setMessages([...next, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (err) {
      setError(err.message);
      setMessages([...next, { role: "assistant", content: "Sorry — I couldn't process that request." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page chat-page">
      <header className="page-header">
        <div>
          <h1>Chat</h1>
          <p className="muted">Conversational Q&amp;A grounded in recent news</p>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <div className="chat-window">
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble-${m.role}`}>
            <div className="bubble-role">{m.role}</div>
            <div className="bubble-text">{m.content}</div>
            {m.sources && m.sources.length > 0 && (
              <div className="bubble-sources">
                {m.sources.map((s) => (
                  <a key={s.id} href={s.url} target="_blank" rel="noreferrer" className="source-chip">
                    {s.title}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="bubble bubble-assistant">
            <div className="bubble-role">assistant</div>
            <div className="bubble-text typing">Thinking…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="chat-input" onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What's happening in AI today?"
          disabled={sending}
        />
        <button className="btn" type="submit" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
