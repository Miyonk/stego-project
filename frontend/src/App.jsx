import { useEffect, useState } from "react";
import AudioVideoStego from "./AudioVideoStego.jsx";
import PhotoStego from "./PhotoStego.jsx";
import ThreeCarrier from "./ThreeCarrier.jsx";
import SecurityInsights from "./SecurityInsights.jsx";
import "./App.css";

const API = import.meta.env.VITE_API || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

const TABS = [
  { id: "av", label: "🎧🎬 Audio + Video Lab", desc: "Adaptive cross-modal payload allocation & joint detector evaluation" },
  { id: "photo", label: "🖼️ Photo Carrier", desc: "Dithered QIM embedding in custom still photographs" },
  { id: "tri", label: "🌐 Tri-Modal Parity", desc: "3-Carrier distributed steganography with erasure coding" },
  { id: "security", label: "🛡️ Security & AUC Insights", desc: "Mathematical diagnostics on detector AUC and QIM artifacts" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("av");
  const [apiOnline, setApiOnline] = useState(null);

  useEffect(() => {
    fetch(`${API}/options`)
      .then((r) => {
        if (r.ok) setApiOnline(true);
        else setApiOnline(false);
      })
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon">🛡️</div>
          <div>
            <h1 className="brand-title">Cross-Modal Stego Lab</h1>
            <p className="brand-subtitle">
              Adaptive Steganography & Multimodal Steganalysis Framework
            </p>
          </div>
        </div>

        {/* Live Status Pill */}
        <div>
          {apiOnline === null ? (
            <div className="api-badge">
              <span className="api-pulse" style={{ color: "var(--text-tertiary)" }} />
              <span>Checking Backend...</span>
            </div>
          ) : apiOnline ? (
            <div className="api-badge online">
              <span className="api-pulse" />
              <span>API Online (127.0.0.1:8000)</span>
            </div>
          ) : (
            <div className="api-badge offline">
              <span className="api-pulse" />
              <span>API Offline &bull; Run <code>python -m uvicorn api.app3:app --port 8000</code></span>
            </div>
          )}
        </div>
      </header>

      {/* Tabs Navigation */}
      <nav className="tabs-container" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main Tab Content */}
      <main>
        {activeTab === "av" && <AudioVideoStego onApiStatus={(s) => setApiOnline(s)} />}
        {activeTab === "photo" && <PhotoStego />}
        {activeTab === "tri" && <ThreeCarrier />}
        {activeTab === "security" && <SecurityInsights />}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div>
          <b>Adaptive Cross-Modal Steganography Against Multimodal Steganalysis</b> &bull; AES-256-GCM + Reed-Solomon + QIM
        </div>
        <div>
          Python 3.11+ / React 19 / Vite 8
        </div>
      </footer>
    </div>
  );
}
