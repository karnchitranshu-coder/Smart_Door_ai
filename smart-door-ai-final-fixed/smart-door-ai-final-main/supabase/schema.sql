-- =============================================================================
-- Smart Door AI — Supabase PostgreSQL Schema
-- =============================================================================
-- How to use:
--   Option 1 (Automatic via Django):
--     Set DATABASE_URL in backend/.env to your Supabase URI (Transaction or Session pooler)
--     and run: python manage.py migrate && python manage.py seed
--
--   Option 2 (Supabase SQL Editor / REST API):
--     Paste this script into the Supabase SQL Editor and click "Run".
-- =============================================================================

-- 1. Enrolled People (Residents, Admins, Guests)
CREATE TABLE IF NOT EXISTS public.door_person (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'resident' CHECK (role IN ('admin', 'resident', 'guest')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Face Profiles (512-d L2-normalized face embeddings)
CREATE TABLE IF NOT EXISTS public.door_faceprofile (
    id BIGSERIAL PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES public.door_person(id) ON DELETE CASCADE,
    embedding JSONB NOT NULL,
    quality DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    image_path VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_door_faceprofile_person_id ON public.door_faceprofile(person_id);

-- 3. Access Event Logs (Granted, Denied, Unknown, Liveness Fail, Lockout, Manual)
CREATE TABLE IF NOT EXISTS public.door_accesslog (
    id BIGSERIAL PRIMARY KEY,
    person_id BIGINT NULL REFERENCES public.door_person(id) ON DELETE SET NULL,
    event_type VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NULL,
    device VARCHAR(60) NOT NULL DEFAULT '',
    detail VARCHAR(255) NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_door_accesslog_event_type ON public.door_accesslog(event_type);
CREATE INDEX IF NOT EXISTS idx_door_accesslog_timestamp ON public.door_accesslog(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_door_accesslog_person_id ON public.door_accesslog(person_id);

-- 4. IoT Devices (ESP32 Door Controllers)
CREATE TABLE IF NOT EXISTS public.door_iotdevice (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL DEFAULT '',
    connection_status VARCHAR(20) NOT NULL DEFAULT 'offline',
    door_state VARCHAR(20) NOT NULL DEFAULT 'locked',
    last_heartbeat TIMESTAMPTZ NULL,
    firmware VARCHAR(40) NOT NULL DEFAULT ''
);

-- 5. System Settings (Key-Value JSON store for thresholds, liveness, durations)
CREATE TABLE IF NOT EXISTS public.door_systemsetting (
    key VARCHAR(60) PRIMARY KEY,
    value JSONB NOT NULL
);

-- Seed default settings
INSERT INTO public.door_systemsetting (key, value) VALUES
    ('match_threshold', '0.45'::jsonb),
    ('unlock_duration', '5'::jsonb),
    ('liveness_required', 'false'::jsonb),
    ('max_failed_attempts', '5'::jsonb),
    ('lockout_seconds', '60'::jsonb),
    ('cooldown_seconds', '3'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- Seed default ESP32 device
INSERT INTO public.door_iotdevice (device_id, name, connection_status, door_state, firmware)
VALUES ('door01', 'Front door ESP32', 'offline', 'locked', '1.0')
ON CONFLICT (device_id) DO NOTHING;
