import { useEffect, useState } from "react";
import "./PhotoStego.css";

const API = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";

async function post(path, form) {
  const r = await fetch(API + path, { method: "POST", body: form });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data));
  return data;
}

const STRENGTHS = [
  ["robust", "Robust: survives heavy JPEG, changes the photo more"],
  ["balanced", "Balanced: good default"],
  ["subtle", "Subtle: least visible, can be lost under heavy compression"],
];

export default function PhotoStego() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [secret, setSecret] = useState("meet at noon, bring the keys");
  const [pass, setPass] = useState("photo-pass");
  const [strength, setStrength] = useState("balanced");
  const [job, setJob] = useState(null);
  const [quality, setQuality] = useState("0");
  const [other, setOther] = useState(null);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const run = async (label, fn) => {
    setErr(""); setBusy(label);
    try { await fn(); } catch (e) { setErr(e.message); }
    setBusy("");
  };

  const hide = () => run("Hiding the secret in your photo...", async () => {
    setRes(null);
    const f = new FormData();
    f.append("file", file); f.append("secret", secret);
    f.append("passphrase", pass); f.append("strength", strength);
    setJob(await post("/photo/embed", f));
  });

  const recover = () => run("Reading the secret back...", async () => {
    const f = new FormData();
    f.append("passphrase", pass); f.append("jpeg_quality", quality);
    if (other) f.append("file", other); else f.append("job_id", job.job_id);
    setRes(await post("/photo/extract", f));
  });

  const img = (name) => `${API}/photo/file/${job.job_id}/${name}`;
  const bytes = new TextEncoder().encode(secret).length;

  return (
    <section className="ph">
      <h2>Hide a secret in your own photo</h2>
      <p className="ph-sub">Choose a photo, type a secret and a passphrase. The secret is encrypted, then hidden in the brightness of the picture. Colours stay as they are.</p>
      {err && <div className="ph-err">{err}</div>}

      <div className="ph-grid">
        <label className="ph-wide">Photo (JPG, PNG, BMP or WEBP)
          <input type="file" accept="image/*" onChange={(e) => { setFile(e.target.files[0] ?? null); setJob(null); setRes(null); }} />
        </label>
        {preview && <img className="ph-thumb" src={preview} alt="your photo" />}
        <label className="ph-wide">Secret ({bytes}/100 bytes)
          <input value={secret} onChange={(e) => setSecret(e.target.value)} />
        </label>
        <label>Passphrase
          <input value={pass} onChange={(e) => setPass(e.target.value)} />
        </label>
        <label>Strength
          <select value={strength} onChange={(e) => setStrength(e.target.value)}>
            {STRENGTHS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
          </select>
        </label>
      </div>
      <button onClick={hide} disabled={!!busy || !file || !secret || !pass || bytes > 100}>Hide secret</button>
      {busy && <span className="ph-busy"> {busy}</span>}

      {job && (
        <div className="ph-card">
          <div className="ph-trio">
            <figure><img src={img("original")} alt="original" /><figcaption>Original</figcaption></figure>
            <figure><img src={img("stego")} alt="modified" /><figcaption>With the secret hidden</figcaption></figure>
            <figure><img src={img("difference")} alt="difference" /><figcaption>What changed (magnified 20 times)</figcaption></figure>
          </div>
          <p className="ph-facts">
            Picture quality <b>{job.psnr_db.toFixed(1)} dB</b> (higher means closer to the original; above about 35 dB the change is hard to see).
            {" "}Each bit is stored <b>{job.reps}</b> times. Size {job.width} x {job.height}.
            {job.scaled && <> Your photo was scaled down from {job.original_size[0]} x {job.original_size[1]} to keep it fast.</>}
          </p>
          <p><a href={img("stego")} download>Download the modified photo (PNG)</a></p>

          <h3>Read the secret back</h3>
          <div className="ph-row">
            <label>Share it first as a JPEG at quality
              <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                <option value="0">no compression (PNG)</option>
                <option value="90">90</option><option value="75">75</option>
                <option value="50">50</option><option value="30">30</option>
              </select>
            </label>
            <label>or use another modified image
              <input type="file" accept="image/*" onChange={(e) => setOther(e.target.files[0] ?? null)} />
            </label>
          </div>
          <button onClick={recover} disabled={!!busy || !pass}>Recover the secret</button>
          <p className="ph-hint">Try a wrong passphrase above to see it fail, or a low JPEG quality to see how much compression it survives.</p>
          {res && (
            <div className={`ph-result ${res.recovered ? "ph-good" : "ph-fail"}`}>
              {res.recovered
                ? <><b>Secret recovered</b>{res.jpeg_quality ? ` after JPEG quality ${res.jpeg_quality}` : ""}<div className="ph-secret">"{res.secret}"</div></>
                : <><b>Nothing recovered.</b> Wrong passphrase, a different image, or the picture was compressed too much.</>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
