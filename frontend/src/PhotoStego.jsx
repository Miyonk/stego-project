import { useState } from "react";

const API = import.meta.env.VITE_API || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

async function post(path, form) {
  const r = await fetch(API + path, { method: "POST", body: form });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : JSON.stringify(d ?? data));
  }
  return data;
}

const STRENGTHS = [
  { id: "subtle", name: "Subtle (16.0)", desc: "Least perceptible (PSNR > 45dB), best for benign channels" },
  { id: "balanced", name: "Balanced (32.0)", desc: "Recommended balance of stealth and lossy compression resilience" },
  { id: "robust", name: "Robust (64.0)", desc: "High tolerance against aggressive JPEG compression (survives Q30)" },
];

export default function PhotoStego() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [secret, setSecret] = useState("Meet at coordinates 37.7749, -122.4194");
  const [pass, setPass] = useState("photo-key-2026");
  const [strength, setStrength] = useState("balanced");
  const [job, setJob] = useState(null);
  const [quality, setQuality] = useState("75");
  const [other, setOther] = useState(null);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const handleFileChange = (e) => {
    const selected = e.target.files[0] ?? null;
    if (preview) {
      URL.revokeObjectURL(preview);
    }
    setFile(selected);
    setPreview(selected ? URL.createObjectURL(selected) : "");
    setJob(null);
    setRes(null);
  };

  const run = async (label, fn) => {
    setErr("");
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  };

  const hide = () => run("Applying Dithered QIM to photo luma...", async () => {
    setRes(null);
    const f = new FormData();
    f.append("file", file);
    f.append("secret", secret);
    f.append("passphrase", pass);
    f.append("strength", strength);
    setJob(await post("/photo/embed", f));
  });

  const recover = () => run("Decoding carrier and checking ECC parity...", async () => {
    const f = new FormData();
    f.append("passphrase", pass);
    f.append("jpeg_quality", quality);
    if (other) {
      f.append("file", other);
    } else {
      f.append("job_id", job.job_id);
    }
    setRes(await post("/photo/extract", f));
  });

  const img = (name) => `${API}/photo/file/${job.job_id}/${name}`;
  const bytes = new TextEncoder().encode(secret).length;

  return (
    <div>
      <section className="panel-card">
        <div className="panel-header">
          <div>
            <div className="panel-title">
              <span className="step-tag">Image Carrier</span>
              <span>Still Photo Steganography</span>
            </div>
            <p className="panel-desc">
              Embed encrypted secrets into custom photos using key-dependent Dither Modulation (DM-QIM).
              Color channels are preserved while data is securely bound to luma luminance.
            </p>
          </div>
        </div>

        <div className="form-grid">
          {/* File Upload Zone */}
          <div className="form-group full-width">
            <label className="form-label">Source Photo (JPEG, PNG, WEBP, BMP)</label>
            <div
              style={{
                border: "2px dashed var(--border-medium)",
                borderRadius: "var(--radius-md)",
                padding: "24px",
                textAlign: "center",
                backgroundColor: "var(--bg-input)",
                cursor: "pointer",
              }}
              onClick={() => document.getElementById("photo-input").click()}
            >
              <input
                id="photo-input"
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={handleFileChange}
              />
              {preview ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                  <img
                    src={preview}
                    alt="Preview"
                    style={{
                      maxHeight: 180,
                      maxWidth: "100%",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-subtle)",
                      boxShadow: "var(--shadow-sm)",
                    }}
                  />
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    Selected: <b>{file.name}</b> ({(file.size / 1024).toFixed(1)} KB) &bull; Click to replace
                  </span>
                </div>
              ) : (
                <div style={{ padding: "16px 0", color: "var(--text-secondary)" }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>Click to browse or drop photo here</div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                    Minimum size 200 &times; 200 pixels
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Secret Input */}
          <div className="form-group full-width">
            <label className="form-label">
              <span>Secret Message</span>
              <span className="count">{bytes} / 100 bytes</span>
            </label>
            <input
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Enter sensitive payload..."
            />
          </div>

          {/* Passphrase */}
          <div className="form-group">
            <label className="form-label">Secret Passphrase</label>
            <input
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              placeholder="Key for encryption and dither seeds..."
            />
          </div>

          {/* Strength Setting */}
          <div className="form-group">
            <label className="form-label">Steganography Profile</label>
            <select value={strength} onChange={(e) => setStrength(e.target.value)}>
              {STRENGTHS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} - {s.desc}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="action-row">
          <button
            className="btn-primary"
            onClick={hide}
            disabled={!!busy || !file || !secret || !pass || bytes > 100}
          >
            {busy ? (
              <>
                <span className="api-pulse" />
                <span>{busy}</span>
              </>
            ) : (
              <span>🔒 Hide Secret in Photo</span>
            )}
          </button>
          <span className="action-hint">
            Employs key-derived pseudorandom dither to prevent periodic histogram comb artifacts.
          </span>
        </div>

        {err && <div className="alert-box error">⚠️ {err}</div>}
      </section>

      {/* Results View */}
      {job && (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="panel-title">
                <span className="step-tag">Inspection</span>
                <span>Visual Fidelity & Difference Analysis</span>
              </div>
              <p className="panel-desc">
                Carrier Dimensions: <b>{job.width} &times; {job.height}</b> &bull; Quality: <b>{job.psnr_db.toFixed(1)} dB PSNR</b> &bull; Repetitions: <b>{job.reps}&times; per bit</b>
              </p>
            </div>
          </div>

          {/* Side by side 3-trio */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 16,
              margin: "18px 0",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <img
                src={img("original")}
                alt="Original"
                style={{ width: "100%", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}
              />
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginTop: 6 }}>
                1. Original Cover
              </div>
            </div>

            <div style={{ textAlign: "center" }}>
              <img
                src={img("stego")}
                alt="Stego"
                style={{ width: "100%", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}
              />
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginTop: 6 }}>
                2. Embedded Stego Photo
              </div>
            </div>

            <div style={{ textAlign: "center" }}>
              <img
                src={img("difference")}
                alt="Difference"
                style={{ width: "100%", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}
              />
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginTop: 6 }}>
                3. Difference Map (20&times; Amplified)
              </div>
            </div>
          </div>

          <div className="download-links">
            <a className="download-btn" href={img("stego")} download="stego_photo.png">
              ⬇️ Download Lossless Stego Photo (.png)
            </a>
          </div>

          {/* Extraction & Compression Attack Section */}
          <h3 style={{ fontSize: 15, marginTop: 24, marginBottom: 8, color: "var(--text-primary)" }}>
            Extraction & Lossy Compression Resilience Test
          </h3>
          <p className="panel-desc" style={{ marginBottom: 14 }}>
            Verify extraction after subjecting the stego image to lossy JPEG compression.
          </p>

          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Simulate JPEG Compression Attack</label>
              <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                <option value="0">Lossless PNG (No Compression)</option>
                <option value="90">JPEG Quality 90 (High Quality)</option>
                <option value="75">JPEG Quality 75 (Standard Web Quality)</option>
                <option value="50">JPEG Quality 50 (Aggressive Compression)</option>
                <option value="30">JPEG Quality 30 (Extreme Compression)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Or upload external image</label>
              <input type="file" accept="image/*" onChange={(e) => setOther(e.target.files[0] ?? null)} />
            </div>
          </div>

          <div className="action-row">
            <button className="btn-secondary" onClick={recover} disabled={!!busy || !pass}>
              {busy ? "Decoding & Extracting..." : "⚡ Recover Hidden Secret"}
            </button>
            <span className="action-hint">
              Tests Reed-Solomon error correction against JPEG quantization tables.
            </span>
          </div>

          {res && (
            <div className="extract-result-box" style={{ marginTop: 18 }}>
              <div className="extract-header">
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
                  {res.jpeg_quality ? `Extracted after JPEG Q=${res.jpeg_quality}:` : "Extracted from source:"}
                </span>
                <span className={`status-chip ${res.recovered ? "clean" : "flagged"}`}>
                  {res.recovered ? "✓ Secret Recovered" : "✗ Extraction Failed"}
                </span>
              </div>
              <div className="secret-display">
                {res.recovered ? res.secret : "Failed to decode secret. Either key was incorrect or lossy compression exceeded parity budget."}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
