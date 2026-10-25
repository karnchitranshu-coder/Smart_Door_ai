# 🚪 Smart Door AI

Face-recognition smart door lock: **Django REST backend** + **React dashboard** + **ESP32 / MQTT** door controller.

```
smart-door-ai/
├── backend/      Django + DRF + SimpleJWT  (AI pipeline, access control, IoT)
├── frontend/     React + Vite + Tailwind dashboard  → deploy on Vercel
├── esp32/        Arduino firmware + wiring
├── mosquitto/    MQTT broker config
├── docs/         architecture, setup, deployment, api, hardware, security, demo
├── docker-compose.yml   backend + Mosquitto
└── render.yaml          one-click backend deploy on Render
```

## Quick start (local)
```bash
# 1) backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-ai.txt # real recognition; needs OpenCV/InsightFace build deps
cp .env.example .env                                    # Windows: copy .env.example .env
#   edit .env -> DEBUG=1, AI_BACKEND=mock (or insightface), ADMIN_PASSWORD=...
python manage.py migrate && python manage.py seed
python manage.py runserver

# 2) frontend (new terminal)
cd frontend
cp .env.example .env                                    # VITE_API_URL=http://localhost:8000
npm install && npm run dev                              # http://localhost:5173
```
Login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `backend/.env` (default `admin` / `admin12345` if unset).

## Real face recognition vs demo mode
- `AI_BACKEND=insightface` uses real InsightFace/ArcFace recognition and needs a host with ~2 GB RAM or more.
- `AI_BACKEND=mock` is only for automated tests/demo API flows. It does **not** perform real face recognition and the app now fails closed instead of unlocking from mock embeddings.
- The Render free blueprint intentionally uses `mock` because its memory is insufficient for InsightFace. Use a suitable VPS/paid host for real recognition.

## Go live → see [docs/deployment.md](docs/deployment.md)
Frontend → **Vercel**, backend → **Render** (or any Docker host). Vercel cannot run the Django/AI backend (serverless: no long-running threads, no MQTT, size limits), so they are deployed separately.

## Modes
| Setting | Values | Meaning |
|---|---|---|
| `AI_BACKEND` | `mock` / `insightface` | fake embeddings (cloud demo) vs real ArcFace |
| `IOT_MODE` | `demo` / `real` | software door vs MQTT → ESP32 |

## Local real-AI Docker setup (recommended for actual recognition)
1. Copy `backend/.env.example` to `backend/.env` and change `SECRET_KEY`, `ADMIN_PASSWORD`, and `DEVICE_API_KEY` to strong random values.
2. Keep `AI_BACKEND=insightface` and `ALLOW_MOCK_RECOGNITION=0`.
3. Run `docker compose up --build` on a machine/VPS with at least about 2 GB RAM. First-time model initialization may take a while and downloads model weights.
4. In `frontend/.env.example`, use `VITE_API_URL=http://localhost:8000` for local development. Run `cd frontend && npm install && npm run dev`.
5. Open `http://localhost:5173`. For an actual door, configure and test MQTT/ESP32 separately; the default `IOT_MODE=demo` is a virtual door only.
