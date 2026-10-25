import { useEffect, useRef, useState } from "react";
import api from "../api/client.js";
import useWebcam from "../hooks/useWebcam.js";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const REASONS = {
  no_face: "No face detected", too_dark: "Too dark", too_bright: "Too bright", too_blurry: "Too blurry",
  face_too_small: "Move closer", unknown_face: "Unknown face", locked_out: "System locked (too many failures)",
  liveness_failed: "Liveness check failed — blink or move slightly",
};

export default function LiveRecognition() {
  const cam = useWebcam();
  const { capture } = cam;
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const busy = useRef(false);

  useEffect(() => {
    let alive = true;
    api.get("/health")
      .then(({ data }) => { if (alive) setHealth(data); })
      .catch(() => { if (alive) setHealthError("Cannot read backend health status."); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!running) return;
    const tick = async () => {
      if (busy.current) return;
      busy.current = true;
      try {
        const { data: cfg } = await api.get("/settings");
        const n = cfg.liveness_required ? 3 : 1;
        const fd = new FormData();
        for (let i = 0; i < n; i++) {
          const b = await capture();
          if (b) fd.append("image", b, `f${i}.jpg`);
          if (i < n - 1) await sleep(300);
        }
        if (![...fd.keys()].length) return;
        const { data } = await api.post("/faces/recognize", fd);
        setResult(data);
      } catch (e) {
        setResult({ granted: false, reason: e.response?.data?.reason || "error", detail: e.response?.data?.detail || e.response?.data?.message || e.message });
      } finally { busy.current = false; }
    };
    const t = setInterval(tick, 2000);
    return () => clearInterval(t);
  }, [running, capture]);

  const granted = result?.granted;
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Live Recognition</h2>
      {health && !health.face_recognition_available && <div role="alert" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200"><strong>Demo backend only:</strong> this server is using <code>{health.ai_backend}</code>, so real face recognition and enrollment are disabled. Deploy the backend with <code>AI_BACKEND=insightface</code> on a host with enough RAM (about 2 GB or more), then redeploy. The demo mode will not unlock the door.</div>}
      {healthError && <div className="text-sm text-rose-400">{healthError}</div>}
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card space-y-3">
          <video ref={cam.videoRef} className={`aspect-video w-full rounded-lg bg-black ring-4 ${result ? (granted ? "ring-emerald-500" : "ring-rose-500") : "ring-transparent"}`} muted playsInline />
          {cam.error && <div className="text-sm text-rose-400">{cam.error}</div>}
          <div className="flex gap-2">
            {!cam.ready ? <button className="btn-primary" onClick={cam.start}>Start camera</button> : <button className="btn-ghost" onClick={() => { setRunning(false); cam.stop(); }}>Stop camera</button>}
            <button className="btn-primary" disabled={!cam.ready || (health && !health.face_recognition_available)} onClick={() => setRunning((r) => !r)}>{running ? "Pause scan" : "Start scanning"}</button>
          </div>
        </div>
        <div className="card flex min-h-[220px] flex-col items-center justify-center gap-2 text-center">
          {!result && <div className="text-slate-400">{running ? "Scanning…" : "Start the camera, then scanning."}</div>}
          {result && (
            <>
              <div className="text-5xl">{granted ? "✅" : "⛔"}</div>
              <div className="text-xl font-semibold">{granted ? `Welcome, ${result.person}` : "Access denied"}</div>
              <div className="text-sm text-slate-400">
                {granted ? (result.reason === "cooldown" ? "Already unlocked recently" : "Door unlocked") : REASONS[result.reason] || result.reason}
                {!granted && result.detail ? ` — ${result.detail}` : ""}
                {result.retry_after ? ` · retry in ${result.retry_after}s` : ""}
              </div>
              {result.confidence != null && <div className="text-xs text-slate-500">confidence {result.confidence}</div>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
