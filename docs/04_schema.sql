-- =============================================================
-- Reroute: PostgreSQL schema (v1)
-- Notes:
--  * LangGraph checkpoint tables are created by langgraph-checkpoint-postgres
--    (call checkpointer.setup()). Do NOT define them here.
--  * Use Alembic for migrations; this file is the reference design.
--  * Money stored as NUMERIC(12,2) in the trip's currency.
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";

-- ---------- Enums ----------
CREATE TYPE trip_status       AS ENUM ('draft','generating','planned','active','completed','archived');
CREATE TYPE pace_type         AS ENUM ('relaxed','balanced','packed');
CREATE TYPE item_category     AS ENUM ('sightseeing','food','culture','nature','nightlife','shopping','adventure','transport','stay','other');
CREATE TYPE setting_type      AS ENUM ('indoor','outdoor','mixed');
CREATE TYPE transport_mode    AS ENUM ('walk','taxi','bus','train','metro','bike','car');
CREATE TYPE disruption_type   AS ENUM ('weather','closure','hours_conflict','delay','budget_overrun','user_request');
CREATE TYPE severity_type     AS ENUM ('low','medium','high');
CREATE TYPE proposal_status   AS ENUM ('pending','approved','rejected','expired','superseded');
CREATE TYPE run_type          AS ENUM ('plan','replan','chat');
CREATE TYPE run_status        AS ENUM ('queued','running','awaiting_user','completed','failed','cancelled');
CREATE TYPE expense_category  AS ENUM ('stay','food','transport','activities','shopping','other');

-- ---------- Users ----------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT,                         -- null if OAuth-only
    display_name    TEXT NOT NULL,
    google_sub      TEXT UNIQUE,
    home_currency   CHAR(3) NOT NULL DEFAULT 'INR',
    units           TEXT NOT NULL DEFAULT 'metric',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);

-- ---------- Places (cached / seeded catalog) ----------
CREATE TABLE places (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT,                         -- e.g. 'osm:node/123'
    source          TEXT NOT NULL DEFAULT 'seed', -- seed | osm | geoapify | manual
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    country         TEXT NOT NULL DEFAULT 'IN',
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    category        item_category NOT NULL,
    setting         setting_type NOT NULL DEFAULT 'mixed',
    avg_cost        NUMERIC(12,2),                -- per person, local currency
    currency        CHAR(3) NOT NULL DEFAULT 'INR',
    avg_duration_min INT,
    opening_hours   JSONB,                        -- {"mon":[["09:00","17:00"]], ...}; null = unknown
    hours_confidence TEXT NOT NULL DEFAULT 'unknown', -- verified | estimated | unknown
    rating          NUMERIC(3,2),
    tags            TEXT[] NOT NULL DEFAULT '{}',
    description     TEXT,
    image_url       TEXT,
    raw             JSONB,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);
CREATE INDEX idx_places_city_cat ON places(city, category);
CREATE INDEX idx_places_tags ON places USING GIN (tags);

-- ---------- Trips ----------
CREATE TABLE trips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    destination     TEXT NOT NULL,
    dest_lat        DOUBLE PRECISION,
    dest_lng        DOUBLE PRECISION,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    group_size      INT NOT NULL DEFAULT 1 CHECK (group_size > 0),
    budget_total    NUMERIC(12,2) NOT NULL CHECK (budget_total >= 0),
    budget_per_day_cap NUMERIC(12,2),
    currency        CHAR(3) NOT NULL DEFAULT 'INR',
    pace            pace_type NOT NULL DEFAULT 'balanced',
    vibe_tags       TEXT[] NOT NULL DEFAULT '{}',
    notes           TEXT,
    status          trip_status NOT NULL DEFAULT 'draft',
    current_version_id UUID,                      -- FK added below (circular)
    last_checked_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date >= start_date)
);
CREATE INDEX idx_trips_user ON trips(user_id, status);
CREATE INDEX idx_trips_dates ON trips(start_date, end_date);

-- ---------- Itinerary versions ----------
-- Every approved change creates a new immutable version.
CREATE TABLE itinerary_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id             UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    version_no          INT  NOT NULL,
    parent_version_id   UUID REFERENCES itinerary_versions(id),
    reason              TEXT NOT NULL,            -- 'Initial plan' | 'Rain replan, Day 2' | 'User edit'
    created_by          TEXT NOT NULL,            -- 'agent:planner' | 'agent:replanner' | 'user'
    proposal_id         UUID,                     -- FK added below
    run_id              UUID,                     -- FK added below
    total_cost          NUMERIC(12,2) NOT NULL DEFAULT 0,
    summary             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, version_no)
);
CREATE INDEX idx_versions_trip ON itinerary_versions(trip_id, version_no DESC);

ALTER TABLE trips
    ADD CONSTRAINT fk_trips_current_version
    FOREIGN KEY (current_version_id) REFERENCES itinerary_versions(id) DEFERRABLE INITIALLY DEFERRED;

-- ---------- Itinerary items ----------
-- Items belong to a version. "stable_key" stays the same across versions for an
-- item that was carried over unchanged, so diffs can match items between versions.
CREATE TABLE itinerary_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      UUID NOT NULL REFERENCES itinerary_versions(id) ON DELETE CASCADE,
    stable_key      UUID NOT NULL DEFAULT gen_random_uuid(),
    day_index       INT  NOT NULL CHECK (day_index >= 1),
    position        INT  NOT NULL CHECK (position >= 0),   -- order within the day
    place_id        UUID REFERENCES places(id),
    title           TEXT NOT NULL,
    category        item_category NOT NULL,
    setting         setting_type NOT NULL DEFAULT 'mixed',
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    est_cost        NUMERIC(12,2) NOT NULL DEFAULT 0,      -- total for group
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    is_locked       BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    -- travel from the PREVIOUS item in the same day
    travel_mode     transport_mode,
    travel_minutes  INT,
    travel_distance_m INT,
    flags           TEXT[] NOT NULL DEFAULT '{}',          -- e.g. {'weather_risk','closes_soon'}
    UNIQUE (version_id, day_index, position)
);
CREATE INDEX idx_items_version_day ON itinerary_items(version_id, day_index, position);
CREATE INDEX idx_items_stable_key ON itinerary_items(stable_key);

-- ---------- Agent runs and event log ----------
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),   -- also LangGraph thread_id
    trip_id         UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            run_type NOT NULL,
    status          run_status NOT NULL DEFAULT 'queued',
    trigger         TEXT NOT NULL DEFAULT 'user',     -- user | monitor | demo
    idempotency_key TEXT,
    input           JSONB NOT NULL DEFAULT '{}',
    output          JSONB,
    error           TEXT,
    model_used      TEXT,
    tokens_in       INT NOT NULL DEFAULT 0,
    tokens_out      INT NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_runs_trip ON agent_runs(trip_id, created_at DESC);
CREATE UNIQUE INDEX uq_runs_idem ON agent_runs(trip_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
-- At most one active run per trip:
CREATE UNIQUE INDEX uq_runs_one_active ON agent_runs(trip_id) WHERE status IN ('queued','running','awaiting_user');

ALTER TABLE itinerary_versions
    ADD CONSTRAINT fk_versions_run FOREIGN KEY (run_id) REFERENCES agent_runs(id) ON DELETE SET NULL;

CREATE TABLE agent_run_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    seq         INT  NOT NULL,                       -- monotonic per run, used for SSE resume (Last-Event-ID)
    type        TEXT NOT NULL,                       -- step | tool_call | tool_result | llm_call | draft | proposal | error | done
    node        TEXT,                                -- graph node name
    message     TEXT,                                -- human-readable line for the timeline
    status      TEXT,                                -- running | done | failed
    payload     JSONB NOT NULL DEFAULT '{}',
    latency_ms  INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, seq)
);
CREATE INDEX idx_run_events_run ON agent_run_events(run_id, seq);

-- ---------- Disruptions ----------
CREATE TABLE disruption_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id         UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    run_id          UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    type            disruption_type NOT NULL,
    severity        severity_type NOT NULL DEFAULT 'medium',
    day_index       INT,
    window_start    TIMESTAMPTZ,
    window_end      TIMESTAMPTZ,
    affected_stable_keys UUID[] NOT NULL DEFAULT '{}',
    summary         TEXT NOT NULL,                   -- "Rain 80% on Day 2, 2-6pm"
    source          TEXT NOT NULL,                   -- open-meteo | ors | rule | demo | user
    data            JSONB NOT NULL DEFAULT '{}',
    fingerprint     TEXT NOT NULL,                   -- dedupe key, e.g. hash(type+day+items+window)
    is_simulated    BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, fingerprint)
);
CREATE INDEX idx_disruptions_trip ON disruption_events(trip_id, resolved_at);

-- ---------- Replan proposals (HITL) ----------
CREATE TABLE replan_proposals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id             UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    run_id              UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    base_version_id     UUID NOT NULL REFERENCES itinerary_versions(id),
    status              proposal_status NOT NULL DEFAULT 'pending',
    reason              TEXT NOT NULL,
    explanation         TEXT,
    disruption_ids      UUID[] NOT NULL DEFAULT '{}',
    -- diff: [{"op":"replace|remove|add|move","day":2,"stable_key":"...","before":{...},"after":{...}}]
    diff                JSONB NOT NULL,
    proposed_items      JSONB NOT NULL,              -- full proposed itinerary for the affected days
    cost_delta          NUMERIC(12,2) NOT NULL DEFAULT 0,
    time_delta_min      INT NOT NULL DEFAULT 0,
    items_changed       INT NOT NULL DEFAULT 0,
    alternatives_of     UUID REFERENCES replan_proposals(id),   -- when user asks "show alternatives"
    resulting_version_id UUID REFERENCES itinerary_versions(id),
    decided_at          TIMESTAMPTZ,
    decision_note       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_proposals_trip_status ON replan_proposals(trip_id, status);

ALTER TABLE itinerary_versions
    ADD CONSTRAINT fk_versions_proposal FOREIGN KEY (proposal_id) REFERENCES replan_proposals(id) ON DELETE SET NULL;

-- ---------- Expenses ----------
CREATE TABLE expenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id         UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_stable_key UUID,                            -- optional link to a planned item
    category        expense_category NOT NULL,
    amount          NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency        CHAR(3) NOT NULL DEFAULT 'INR',
    amount_in_trip_currency NUMERIC(12,2) NOT NULL,
    description     TEXT,
    spent_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_expenses_trip ON expenses(trip_id, spent_at);

-- ---------- Chat ----------
CREATE TABLE chat_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id     UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    run_id      UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    role        TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',        -- e.g. {"proposal_id": "..."}
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_trip ON chat_messages(trip_id, created_at);

-- ---------- External API cache ----------
CREATE TABLE api_cache (
    cache_key   TEXT PRIMARY KEY,                    -- e.g. 'weather:22.57,88.36:2026-11-20'
    provider    TEXT NOT NULL,
    response    JSONB NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_api_cache_expiry ON api_cache(expires_at);

-- ---------- updated_at trigger ----------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_trips_updated BEFORE UPDATE ON trips FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================
-- Reference JSON shapes
-- =============================================================
-- places.opening_hours:
--   {"mon":[["09:00","17:00"]],"tue":[["09:00","17:00"]],"sun":[]}   -- empty list = closed
--
-- replan_proposals.diff element:
--   {"op":"replace","day":2,"stable_key":"<uuid>",
--    "before":{"title":"Victoria Memorial gardens","start":"14:00","end":"16:00","cost":100},
--    "after": {"title":"Indian Museum","place_id":"<uuid>","start":"14:00","end":"16:00","cost":150},
--    "why":"Outdoor stop during 80% rain window"}
