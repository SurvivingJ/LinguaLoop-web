-- Daily Test Loads table
-- Caches the computed daily test load per user per language per day
-- so it remains stable throughout the day.

CREATE TABLE IF NOT EXISTS daily_test_loads (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    language_id INTEGER NOT NULL,
    load_date DATE NOT NULL DEFAULT CURRENT_DATE,
    test_ids JSONB NOT NULL,                          -- [{test_id, slot_type, test_type, original_percentage}]
    completed_test_ids JSONB DEFAULT '[]'::jsonb,     -- [test_id, ...]
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, language_id, load_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_loads_lookup
    ON daily_test_loads(user_id, language_id, load_date);

-- RLS policies live in migrations/enable_rls_on_user_owned_tables.sql
-- (dtl_own_data / dtl_service_role / dtl_admin_view). RLS is enabled there too.
