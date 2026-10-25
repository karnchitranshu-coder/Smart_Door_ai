import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api/client.js";
import useWebcam from "../hooks/useWebcam.js";

const STEPS = [
  "Look straight at the camera",
  "Turn slightly left",
  "Turn slightly right",
  "Tilt chin up a little",
  "Neutral face, good lighting",
];

export default function FaceEnrollment() {
  const [params] = useSearchParams();
  const [people, setPeople] = useState([]);
  const [pid, setPid] = useState(params.get("person") || "");
  const [saved, setSaved] = useState(0);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const [loadError, setLoadError] = useState("");
  const fileRef = useRef(null);
  const cam = useWebcam();

  const refreshUsers = () =>
    api.get("/users").then((u) => setPeople(u.data.results ?? u.data));

  useEffect(() => {
    let alive = true;
    Promise.all([api.get("/users"), api.get("/health")])
      .then(([users, h]) => {
        if (!alive) return;
        setPeople(users.data.results ?? users.data);
        setHealth(h.data);
      })
      .catch((e) => {
        if (alive)
          setLoadError(
            e.response?.data?.detail ||
              "Could not load users/backend status. Check login and API URL."
          );
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const p = people.find((x) => String(x.id) === String(pid));
    setSaved(p ? p.face_samples : 0);
  }, [pid, people]);

  const sendFiles = async (blobs) => {
    setBusy(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("person_id", pid);
      blobs.forEach((b, i) => fd.append("image", b, b.name || `sample_${i}.jpg`));
      try {
        const { data } = await api.post("/faces/enroll", fd);
        setSaved(data.total_samples);
        await refreshUsers();
        const rejCount = data.rejected?.length || 0;
        setMsg({
          ok: data.saved > 0,
          text:
            data.saved > 0
              ? `Saved ${data.saved} sample(s) ✔${rejCount ? ` (${rejCount} rejected)` : ""}`
              : `Rejected: ${data.rejected?.[0]?.reason || "no face"}`,
        });
      } catch (e) {
        const rej = e.response?.data?.rejected?.[0]?.reason;
        const detail = e.response?.data?.detail;
        setMsg({
          ok: false,
          text: detail || `Rejected: ${rej || e.message || "unknown error"}`,
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const capture = async () => {
    const blob = await cam.capture();
    if (!blob) return setMsg({ ok: false, text: "No frame yet — start the camera first." });
    await sendFiles([blob]);
  };

  const onFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    await sendFiles(files);
  };

  const clearSamples = async () => {
    if (!pid) return;
    setBusy(true);
    try {
      await api.delete(`/faces/${pid}`);
      setSaved(0);
      await refreshUsers();
      setMsg({ ok: true, text: "Cleared all face samples for this person." });
    } catch {
      setMsg({ ok: false, text: "Could not clear samples." });
    } finally {
      setBusy(false);
    }
  };

  const step = STEPS[Math.min(saved, STEPS.length - 1)];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Face Enrollment</h2>
        {health && (
          <span className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-300">
            Engine: <strong>{health.ai_backend}</strong>
          </span>
        )}
      </div>
      {health && !health.face_recognition_available && (
        <div role="alert" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
          <strong>Enrollment unavailable:</strong> backend is in <code>{health.ai_backend}</code> mode.
        </div>
      )}
      {loadError && <div role="alert" className="text-sm text-rose-400">{loadError}</div>}
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card space-y-3">
          <video ref={cam.videoRef} className="aspect-video w-full rounded-lg bg-black" muted playsInline />
          {cam.error && <div className="text-sm text-rose-400">{cam.error}</div>}
          <div className="flex flex-wrap gap-2">
            {!cam.ready ? (
              <button className="btn-primary" onClick={cam.start}>Start camera</button>
            ) : (
              <button className="btn-ghost" onClick={cam.stop}>Stop camera</button>
            )}
            <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={onFileUpload} />
            <button
              className="btn-ghost"
              disabled={!pid || busy || (health && !health.face_recognition_available)}
              onClick={() => fileRef.current?.click()}
            >
              📁 Upload photo(s)
            </button>
          </div>
        </div>
        <div className="card space-y-4">
          <select className="input" value={pid} onChange={(e) => setPid(e.target.value)}>
            <option value="">Select a person…</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>{p.full_name} ({p.face_samples} samples)</option>
            ))}
          </select>
          <div>
            <div className="mb-1 flex justify-between text-sm">
              <span>Samples</span>
              <span>{saved} / {STEPS.length}</span>
            </div>
            <div className="h-2 rounded bg-slate-800">
              <div
                className="h-2 rounded bg-indigo-500 transition-all"
                style={{ width: `${Math.min(100, (saved / STEPS.length) * 100)}%` }}
              />
            </div>
          </div>
          <div className="rounded-lg bg-slate-800 p-3 text-sm">
            👉 {saved >= STEPS.length ? "Enrollment complete! You can add more samples." : step}
          </div>
          <div className="flex gap-2">
            <button
              className="btn-primary flex-1"
              disabled={!pid || !cam.ready || busy || (health && !health.face_recognition_available)}
              onClick={capture}
            >
              {busy ? "Processing…" : "Capture webcam sample"}
            </button>
            {saved > 0 && (
              <button className="btn-danger" disabled={busy} onClick={clearSamples}>
                Clear
              </button>
            )}
          </div>
          {msg && <div className={`text-sm ${msg.ok ? "text-emerald-400" : "text-amber-400"}`}>{msg.text}</div>}
        </div>
      </div>
    </div>
  );
}
