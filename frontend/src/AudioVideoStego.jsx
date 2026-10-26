import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

async function api(path, body) {
  const res = await fetch(API + path, body ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } : undefined);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : JSON.stringify(d) || res.statusText);
  }
  return data;
}

const fmt = (x, d = 1) => (x === null || x === undefined ? "-" : Number(x).toFixed(d));

function ScoreMeter({ score }) {
  const isFlagged = score > 0.5;
  const pct = Math.min(Math.max(score * 100, 2), 100).toFixed(1);
  return (
    <div className="meter-wrapper">
      <div className="score-meter">
        <div
          className={`score-fill ${isFlagged ? "flagged" : "safe"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="score-number">{score.toFixed(3)}</span>
      <span className={`status-chip ${isFlagged ? "flagged" : "clean"}`}>
        {isFlagged ? "Flagged" : "Safe"}
      </span>
    </div>
  );
}

export default function AudioVideoStego({ onApiStatus }) {
  const [opts, setOpts] = useState({ strategies: [], channels: [] });
  const [clips, setClips] = useState([]);
  const [clip, setClip] = useState("");
  const [strategy, setStrategy] = useState("");
  const [secret, setSecret] = useState("Confidential data payload 2026");
  const [pass, setPass] = useState("quantum-safe-pass");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [res, setRes] = useState(null);

  const [channel, setChannel] = useState("");
  const [pass2, setPass2] = useState("quantum-safe-pass");
  const [exBusy, setExBusy] = useState(false);
  const [exErr, setExErr] = useState("");
  const [out, setOut] = useState(null);

  useEffect(() => {
    Promise.all([api("/options"), api("/clips?split=test&limit=40")])
      .then(([o, c]) => {
        setOpts(o);
        setClips(c);
        if (c.length > 0) setClip(c[0].clip_id);
        setStrategy(o.strategies.includes("adaptive_with_feedback") ? "adaptive_with_feedback" : o.strategies[0] ?? "");
        setChannel(o.channels.includes("mp3_128+h264_crf23") ? "mp3_128+h264_crf23" : o.channels[0] ?? "");
        if (onApiStatus) onApiStatus(true);
      })
      .catch((e) => {
        setError("Cannot connect to backend: " + e.message);
        if (onApiStatus) onApiStatus(false);
      });
  }, [onApiStatus]);

  async function hide() {
    setError("");
    setBusy(true);
    try {
      const r = await api("/embed", { clip_id: clip, secret, passphrase: pass, strategy });
      setRes(r);
      setPass2(pass);
      setOut(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function extract() {
    setExErr("");
    setOut(null);
    setExBusy(true);
    try {
      setOut(await api("/extract", { job_id: res.job_id, passphrase: pass2, channel }));
    } catch (e) {
      setExErr(e.message);
    } finally {
      setExBusy(false);
    }
  }

  const c = res?.detection_clean;
  const s = res?.detection_stego;
  const audioPct = res ? ((res.bits_audio / res.bits) * 100).toFixed(1) : 50;
  const videoPct = res ? ((res.bits_video / res.bits) * 100).toFixed(1) : 50;

  return (
    <div>
      {/* Step 1: Hide Secret */}
      <section className="panel-card">
        <div className="panel-header">
          <div>
            <div className="panel-title">
              <span className="step-tag">Step 1</span>
              <span>Payload & Carrier Configuration</span>
            </div>
            <p className="panel-desc">
              Encrypt secret using AES-256-GCM and adaptively split payload bits between audio & video carriers.
            </p>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label" htmlFor="clip">Carrier Video Clip</label>
            <select id="clip" value={clip} onChange={(e) => setClip(e.target.value)}>
              {clips.map((x) => (
                <option key={x.clip_id} value={x.clip_id}>
                  {x.clip_id} [{x.emotion}]
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="strategy">Allocation Strategy</label>
            <select id="strategy" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              {opts.strategies.map((x) => (
                <option key={x} value={x}>
                  {x.replace(/_/g, " ").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="secret">
              <span>Secret Message</span>
              <span className="count">{secret.length} / 128 chars</span>
            </label>
            <input
              id="secret"
              maxLength={128}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Type hidden payload..."
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="pass">Encryption Passphrase</label>
            <input
              id="pass"
              type="text"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              placeholder="Secret key..."
            />
          </div>
        </div>

        <div className="action-row">
          <button className="btn-primary" onClick={hide} disabled={busy || !clip}>
            {busy ? (
              <>
                <span className="api-pulse" />
                <span>Embedding into Carrier...</span>
              </>
            ) : (
              <span>🔒 Encrypt & Embed Payload</span>
            )}
          </button>
          <span className="action-hint">
            Uses transform-domain QIM with Reed-Solomon protection.
          </span>
        </div>

        {error && <div className="alert-box error">⚠️ {error}</div>}
      </section>

      {/* Step 2: Inspection & Detector Evaluation */}
      {res && (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="panel-title">
                <span className="step-tag">Step 2</span>
                <span>Steganalysis & Cross-Modal Allocation</span>
              </div>
              <p className="panel-desc">
                Job ID: <code>{res.job_id}</code> &bull; Total Encrypted Payload: <b>{res.bits} bits</b>
              </p>
            </div>
          </div>

          {/* Allocation Split Bar */}
          <div className="carrier-split-container">
            <div className="carrier-bar">
              <div className="audio-fill" style={{ width: `${audioPct}%` }} title={`Audio: ${res.bits_audio} bits (${audioPct}%)`} />
              <div className="video-fill" style={{ width: `${videoPct}%` }} title={`Video: ${res.bits_video} bits (${videoPct}%)`} />
            </div>
            <div className="carrier-legend">
              <span className="legend-item">
                <span className="legend-dot" style={{ background: "var(--carrier-audio)" }} />
                <span>Audio Stream: <b>{res.bits_audio} bits</b> ({audioPct}%)</span>
              </span>
              <span className="legend-item">
                <span className="legend-dot" style={{ background: "var(--carrier-video)" }} />
                <span>Video Stream: <b>{res.bits_video} bits</b> ({videoPct}%)</span>
              </span>
            </div>
          </div>

          {/* Quality Metrics */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-val">{fmt(res.quality.snr_db)} <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>dB</span></div>
              <div className="metric-title">Audio SNR</div>
              <div className="metric-desc">Above 20 dB indicates high acoustic fidelity</div>
            </div>

            <div className="metric-card">
              <div className="metric-val">{fmt(res.quality.psnr_db)} <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>dB</span></div>
              <div className="metric-title">Video PSNR</div>
              <div className="metric-desc">Visual transparency benchmark</div>
            </div>

            <div className="metric-card">
              <div className="metric-val">{fmt(res.quality.ssim, 3)}</div>
              <div className="metric-title">Structural Similarity (SSIM)</div>
              <div className="metric-desc">1.0 represents indistinguishable visual match</div>
            </div>
          </div>

          {/* Steganalysis Evaluation Table */}
          <h3 style={{ fontSize: 15, marginTop: 20, marginBottom: 8, color: "var(--text-primary)" }}>
            Multimodal Steganalysis Adversary Risk
          </h3>
          <p className="panel-desc" style={{ marginBottom: 12 }}>
            Scores range from 0.0 (looks completely clean) to 1.0 (anomalies detected). Values &gt; 0.5 are flagged.
          </p>

          {c && s ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Target Modality</th>
                  <th>Original Cover Media</th>
                  <th>Stego Embedded Media</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><b>Audio Detector</b> (STFT Residuals)</td>
                  <td><ScoreMeter score={c.audio} /></td>
                  <td><ScoreMeter score={s.audio} /></td>
                </tr>
                <tr>
                  <td><b>Video Detector</b> (DCT Residuals & Blockiness)</td>
                  <td><ScoreMeter score={c.video} /></td>
                  <td><ScoreMeter score={s.video} /></td>
                </tr>
                <tr>
                  <td><b>Joint Late-Fusion Detector</b></td>
                  <td><ScoreMeter score={c.fused} /></td>
                  <td><ScoreMeter score={s.fused} /></td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="action-hint">Detector weights loading...</div>
          )}

          <div className="download-links">
            <a className="download-btn" href={`${API}/download/${res.job_id}/audio`} download>
              ⬇️ Download Stego Audio (.wav)
            </a>
            <a className="download-btn" href={`${API}/download/${res.job_id}/video`} download>
              ⬇️ Download Stego Video (.mkv)
            </a>
          </div>
        </section>
      )}

      {/* Step 3: Channel Attack & Extraction */}
      {res && (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="panel-title">
                <span className="step-tag">Step 3</span>
                <span>Lossy Channel Transmission & Decryption</span>
              </div>
              <p className="panel-desc">
                Simulate aggressive compression codecs (MP3, H.264/H.265) and verify blind extraction.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label className="form-label" htmlFor="channel">Compression Attack Channel</label>
              <select id="channel" value={channel} onChange={(e) => setChannel(e.target.value)}>
                {opts.channels.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="pass2">Passphrase for Decryption</label>
              <input
                id="pass2"
                value={pass2}
                onChange={(e) => setPass2(e.target.value)}
                placeholder="Receiver passphrase..."
              />
            </div>
          </div>

          <div className="action-row">
            <button className="btn-secondary" onClick={extract} disabled={exBusy}>
              {exBusy ? "Transmitting & Decoding..." : "⚡ Transmit Channel & Extract Payload"}
            </button>
            <span className="action-hint">
              Verifies Reed-Solomon decoding and AES-GCM authentication tag.
            </span>
          </div>

          {exErr && <div className="alert-box error">⚠️ {exErr}</div>}

          {out && (
            <div className="extract-result-box">
              <div className="extract-header">
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
                  Extraction Status:
                </span>
                <span className={`status-chip ${out.recovered ? "clean" : "flagged"}`}>
                  {out.recovered ? "✓ Recovered & Verified" : "✗ Integrity Corrupted"}
                </span>
              </div>
              <div className="secret-display">
                {out.recovered ? out.secret : "Decryption failed: ECC error budget exceeded or incorrect passphrase."}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
