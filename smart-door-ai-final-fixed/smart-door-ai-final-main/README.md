# 🚪 Smart Door AI

AI-based IoT Smart Door Access Control System using Face Recognition, Liveness Verification, **Supabase (PostgreSQL)**, **Django REST API**, **React Dashboard**, and **ESP32 (Servo / Serial & MQTT)**.

```
smart-door-ai/
├── backend/      Django + DRF + SimpleJWT  (AI pipeline, access control, IoT, Supabase)
├── frontend/     React + Vite + Tailwind dashboard
├── esp32/        Arduino firmware (USB Serial + Servo & Wi-Fi MQTT + Relay)
├── supabase/     Supabase PostgreSQL schema (schema.sql)
├── mosquitto/    MQTT broker config
├── docs/         Architecture, setup, deployment, API, hardware, security, demo
├── docker-compose.yml   Backend + Mosquitto
└── render.yaml          One-click backend deploy on Render
```

## Quick Start (Local)

```bash
# 1) Backend
cd backend
pip install -r requirements.txt
# Edit backend/.env to add your Supabase DATABASE_URL (automatically falls back to local SQLite if blank)
python manage.py migrate && python manage.py seed
python manage.py runserver

# 2) Frontend (new terminal)
cd frontend
npm install && npm run dev                              # http://localhost:5173
```

Login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `backend/.env` (default `admin` / `admin12345`).

## Supabase Database Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Copy your **Transaction Pooler** or **Session Pooler** URI from **Project Settings → Database → Connection string** and set it in `backend/.env`:
   ```env
   DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
   ```
3. Run `python manage.py migrate && python manage.py seed` (or execute `supabase/schema.sql` in the Supabase SQL Editor).
4. **Optional REST Sync**: You can also set `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env` to mirror users, face embeddings, and access logs via Supabase PostgREST when running with a local SQLite cache (`SUPABASE_FALLBACK_SQLITE=1`).

## AI & IoT Modes

| Setting | Values | Meaning |
|---|---|---|
| `AI_BACKEND` | `auto` / `insightface` / `opencv` / `mock` | `auto` uses InsightFace (RetinaFace + ArcFace) if installed, or falls back to real OpenCV Haar + CLAHE/HOG/DCT 512-d face recognition & eye/motion liveness |
| `IOT_MODE` | `demo` / `serial` / `real` | `demo` = virtual timer door, `serial` = USB PySerial to ESP32 Servo (`UNLOCK:<sec>` / `LOCK`), `real` = MQTT to ESP32 |
