export default function SecurityInsights() {
  return (
    <div>
      <section className="panel-card">
        <div className="panel-header">
          <div>
            <div className="panel-title">
              <span className="step-tag">Research &amp; Diagnostics</span>
              <span>Multimodal Steganalysis Security &amp; AUC Analysis</span>
            </div>
            <p className="panel-desc">
              Detailed breakdown of why statistical detectors achieve high Area Under the ROC Curve (AUC) on transform-domain steganography, and how dither modulation &amp; spatial deblocking restore stealth.
            </p>
          </div>
        </div>

        {/* Core Discovery Cards */}
        <div className="metrics-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
          <div className="metric-card" style={{ borderLeft: "4px solid var(--danger)" }}>
            <div className="metric-title" style={{ color: "var(--danger)", fontSize: 13, textTransform: "uppercase" }}>
              Vulnerability 1: The 8x8 Boundary Seam
            </div>
            <div className="metric-val" style={{ fontSize: 18, marginTop: 6, marginBottom: 6 }}>
              Blockiness: 1.05 &rarr; 2.06
            </div>
            <p className="metric-desc" style={{ fontSize: 12.5, lineHeight: 1.5 }}>
              Independent 8&times;8 block DCT quantization produces step discontinuities across block borders (columns and rows 7, 15, 23, ...).
              Clean images feature a ratio of 1.053 &plusmn; 0.030, while stego media spikes to 2.056 &plusmn; 0.092 with zero distribution overlap.
            </p>
          </div>

          <div className="metric-card" style={{ borderLeft: "4px solid var(--carrier-video)" }}>
            <div className="metric-title" style={{ color: "var(--carrier-video)", fontSize: 13, textTransform: "uppercase" }}>
              Vulnerability 2: Parity Deficit at Zero
            </div>
            <div className="metric-val" style={{ fontSize: 18, marginTop: 6, marginBottom: 6 }}>
              +48% Distortion at &plusmn;&Delta;
            </div>
            <p className="metric-desc" style={{ fontSize: 12.5, lineHeight: 1.5 }}>
              Natural AC coefficients follow a Laplacian distribution peaked at 0. In binary QIM, 0 is an even lattice point (bit 0).
              Every bit 1 is forcibly ejected away from 0 to &plusmn;&Delta;, causing an artificial deficit at 0 and sharp histogram spikes at &plusmn;32 or &plusmn;64.
            </p>
          </div>

          <div className="metric-card" style={{ borderLeft: "4px solid var(--success)" }}>
            <div className="metric-title" style={{ color: "var(--success)", fontSize: 13, textTransform: "uppercase" }}>
              Countermeasure: DM-QIM &amp; Smoothing
            </div>
            <div className="metric-val" style={{ fontSize: 18, marginTop: 6, marginBottom: 6 }}>
              Lattice Dither + Edge Taper
            </div>
            <p className="metric-desc" style={{ fontSize: 12.5, lineHeight: 1.5 }}>
              By shifting the quantization grid with key-derived secret dither in [-&Delta;, +&Delta;) and gently tapering boundary pixels,
              the periodic comb vanishes for any observer without the secret key.
            </p>
          </div>
        </div>

        {/* Detailed Explanation */}
        <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: 18,
              borderRadius: "var(--radius-md)",
              background: "var(--bg-input)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <h4 style={{ fontSize: 14.5, color: "var(--text-primary)", marginBottom: 8 }}>
              1. The Blockiness Discontinuity (<code>dx[:, :, 7::8].mean() / dx.mean()</code>)
            </h4>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              In <code>src/steganalysis/features.py</code>, the video detector measures the difference between column 7 and column 8 across the entire frame.
              Because adjacent blocks are perturbed without continuous spatial interpolation, the seam between blocks is sharply amplified.
              A single decision tree split on blockiness alone yields an instantaneous AUC of <b>1.0000</b>.
            </p>
          </div>

          <div
            style={{
              padding: 18,
              borderRadius: "var(--radius-md)",
              background: "var(--bg-input)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <h4 style={{ fontSize: 14.5, color: "var(--text-primary)", marginBottom: 8 }}>
              2. The Robustness vs. Stealth Trade-Off
            </h4>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              To ensure payloads survive extreme compression channels (such as H.264 CRF 28, H.265 CRF 28, and MP3 64 kbps),
              the embedder was assigned a large perturbation step size (&Delta; = 64.0 with up to 16 repetitions per bit).
              While this achieves 100% recovery under lossy codecs, the modification budget is approximately 10&times; higher than the natural carrier noise floor.
            </p>
          </div>

          <div
            style={{
              padding: 18,
              borderRadius: "var(--radius-md)",
              background: "var(--bg-input)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <h4 style={{ fontSize: 14.5, color: "var(--text-primary)", marginBottom: 8 }}>
              3. Verification of Zero Data Leakage
            </h4>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Leakage diagnostics confirmed that the high AUC is <b>not</b> caused by train/test contamination or actor memorization:
            </p>
            <ul style={{ paddingLeft: 22, marginTop: 6, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              <li>Splits were segregated strictly by actor group (0 shared groups between train and test).</li>
              <li>When trained on shuffled labels (control check), the detector AUC dropped to random chance (0.51 &plusmn; 0.08).</li>
              <li>Cross-dataset evaluation (trained on CREMA-D, evaluated on DIV2K) still yielded AUC &approx; 0.986 - 1.000, proving the detector learns the physical QIM signature.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
