-- Add a durable flag so the welcome / onboarding page is shown exactly once
-- per user — the first time they ever log in — instead of relying on the
-- total_tests_taken == 0 proxy, which re-shows the page whenever a new user
-- logs out before completing a test.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS has_seen_welcome boolean NOT NULL DEFAULT false;

-- Backfill: everyone who already exists in users on the day this ships has
-- either seen onboarding or has moved past the point where it would be
-- useful. Don't re-show it to existing users.
UPDATE public.users SET has_seen_welcome = true WHERE has_seen_welcome = false;
