# Smart Door AI fixes applied

## Important deployment limitation
The free Render blueprint remains configured with `AI_BACKEND=mock` because the project documents that InsightFace needs about 2 GB RAM. Mock embeddings are not real face recognition. In this version, mock mode is blocked from face enrollment and door access by default; this prevents a fake/demo backend from pretending to authenticate a real person.

## Changes
- Added a friendly JSON response at the backend root (`/`) instead of a root 404.
- Expanded `/api/health` with AI dependency/readiness indicators and an explicit demo-mode warning.
- Made mock mode fail closed for enrollment and recognition unless explicitly enabled for automated tests.
- Updated the automated test setup to opt in to mock behavior only inside tests.
- Added `backend/.env.example` and `frontend/.env.example`.
- Updated Docker Compose to install the real InsightFace dependencies for local/VPS use.
- Added visible warnings and clearer API error messages in the face enrollment and live recognition screens.
- Documented the difference between Render demo mode and real AI mode.

## Real AI deployment
Use a machine/VPS with at least about 2 GB RAM, set `AI_BACKEND=insightface` and `ALLOW_MOCK_RECOGNITION=0`, configure strong secrets, and run `docker compose up --build`. The default ESP32/door mode is still `demo`; hardware requires separate MQTT/ESP32 configuration.
