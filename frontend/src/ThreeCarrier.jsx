import { useEffect, useState } from "react";
import "./ThreeCarrier.css";

const API = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";

async function call(path, body) {
  const r = await fetch(API + path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data));
  return data;
}

const fmt = (x, d = 1) => (x == null ? "-" : Number(x).toFixed(d));

function Chip({ name, state }) {
  return <span className={`tc-chip ${state === "ok" ? "tc-ok" : "tc-bad"}`}>{name}: {state === "ok" ? "readable" : "destroyed"}</span>;
}

export default function ThreeCarrier() {
  const [clips, setClips] = useState([]);
  const [opts, setOpts] = useState(null);
  const [clip, setClip] = useState("");
  const [secret, setSecret] = useState("meet at noon, bring the keys");
  const [pass, setPass] = useState("demo-pass");
  const [plan, setPlan] = useState("erasure_2of3");
  const [scenario, setScenario] = useState("kill_video");
  const [job, setJob] = useState(null);
  const [res, setRes] = useState(null);
  const [table, setTable] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([call("/clips?split=test&limit=20"), call("/options3")])
      .then(([c, o]) => { setClips(c); setOpts(o); if (c.length) setClip(c[0].clip_id); })
      .catch((e) => setErr("Cannot reach the 3-carrier API. Start it with: python -m uvicorn api.app3:app --port 8000  (" + e.message + ")"));
  }, []);

  const run = async (label, fn) => {
    setErr(""); setBusy(label);
    try { await fn(); } catch (e) { setErr(e.message); }
    setBusy("");
  };

  const hide = () => run("Hiding in audio, video and image...", async () => {
    setRes(null); setTable(null);
    setJob(await call("/embed3", { clip_id: clip, secret, passphrase: pass, plan }));
  });

  const attack = () => run("Sending through the channel...", async () => {
    setTable(null);
    setRes(await call("/extract3", { job_id: job.job_id, passphrase: pass, scenario }));
  });

  const sweep = () => run("Testing every scenario (about a minute)...", async () => {
    const rows = [];
    for (const s of opts.scenarios) {
      rows.push(await call("/extract3", { job_id: job.job_id, passphrase: pass, scenario: s }));
      setTable([...rows]);
    }
  });

  const planInfo = opts?.plans.find((p) => p.name === plan);

  return (
    <section className="tc">
      <h2>Three carriers: audio + video + image</h2>
      <p className="tc-sub">The secret is cut into pieces with error-correcting parity. Depending on the plan, losing a whole carrier can still be survived.</p>
      {err && <div className="tc-err">{err}</div>}

      <div className="tc-grid">
        <label>Clip
          <select value={clip} onChange={(e) => setClip(e.target.value)}>
            {clips.map((c) => <option key={c.clip_id} value={c.clip_id}>{c.clip_id}</option>)}
          </select>
        </label>
        <label>Plan
          <select value={plan} onChange={(e) => setPlan(e.target.value)}>
            {opts?.plans.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
        </label>
        <label className="tc-wide">Secret (max {opts?.max_secret_bytes ?? 96} bytes)
          <input value={secret} onChange={(e) => setSecret(e.target.value)} maxLength={96} />
        </label>
        <label>Passphrase
          <input value={pass} onChange={(e) => setPass(e.target.value)} />
        </label>
      </div>
      {planInfo && <p className="tc-hint">{planInfo.description}</p>}
      <button onClick={hide} disabled={!!busy || !clip || !opts}>Hide secret</button>
      {busy && <p className="tc-busy">{busy}</p>}

      {job && (
        <div className="tc-card">
          <h3>Hidden: {job.k}-of-{job.n} plan "{job.plan}"</h3>
          <p>Any <b>{job.k}</b> of the <b>{job.n}</b> pieces rebuild the secret. {job.bits_per_carrier} bits per carrier, {job.bits_total} bits in total.</p>
          <ul className="tc-q">
            {job.quality.snr_db != null && <li>Audio SNR <b>{fmt(job.quality.snr_db)} dB</b></li>}
            {job.quality.video_psnr_db != null && <li>Video PSNR <b>{fmt(job.quality.video_psnr_db)} dB</b>, SSIM <b>{fmt(job.quality.video_ssim, 3)}</b></li>}
            {job.quality.image_psnr_db != null && <li>Image PSNR <b>{fmt(job.quality.image_psnr_db)} dB</b></li>}
          </ul>
          <p className="tc-links">
            {job.carriers.map((k) => <a key={k} href={`${API}/download3/${job.job_id}/${k}`}>download {k}</a>)}
          </p>

          <h3>Attack it</h3>
          <div className="tc-row">
            <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {opts.scenarios.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button onClick={attack} disabled={!!busy}>Send and recover</button>
            <button className="tc-ghost" onClick={sweep} disabled={!!busy}>Try all scenarios</button>
          </div>
          <p className="tc-hint">"kill_*" scenarios use deliberately extreme settings that destroy one carrier each. They show the idea, not a typical channel.</p>

          {res && (
            <div className={`tc-result ${res.recovered ? "tc-good" : "tc-fail"}`}>
              <b>{res.recovered ? "Secret recovered" : "Secret lost"}</b> ({res.scenario})
              {res.recovered && <div className="tc-secret">"{res.secret}"</div>}
              <div>{Object.entries(res.carrier_status).map(([k, v]) => <Chip key={k} name={k} state={v} />)}</div>
              {!res.recovered && <div className="tc-hint">Needed {res.needed} readable pieces of {res.of}.</div>}
            </div>
          )}

          {table && (
            <table className="tc-table">
              <thead><tr><th>Scenario</th><th>Audio</th><th>Video</th><th>Image</th><th>Secret</th></tr></thead>
              <tbody>
                {table.map((r) => (
                  <tr key={r.scenario}>
                    <td>{r.scenario}</td>
                    {["audio", "video", "image"].map((k) => (
                      <td key={k}>{r.carrier_status[k] ? (r.carrier_status[k] === "ok" ? "ok" : "destroyed") : "-"}</td>
                    ))}
                    <td className={r.recovered ? "tc-yes" : "tc-no"}>{r.recovered ? "recovered" : "lost"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
}
