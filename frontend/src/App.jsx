import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Chat from "./pages/Chat.jsx";
import Settings from "./pages/Settings.jsx";

function Sidebar() {
  const links = [
    { to: "/", label: "Dashboard", end: true, icon: "▣" },
    { to: "/chat", label: "Chat", icon: "✦" },
    { to: "/settings", label: "Settings", icon: "⚙" },
  ];
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">J</span>
        <div>
          <div className="brand-name">Jarvis</div>
          <div className="brand-sub">Intelligence</div>
        </div>
      </div>
      <nav>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <span className="nav-icon">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">Phase 1 · MVP</div>
    </aside>
  );
}

export default function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
