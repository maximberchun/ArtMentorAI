CREATE TABLE IF NOT EXISTS public.user_progress (
    user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    total_xp INTEGER NOT NULL DEFAULT 0,
    current_level INTEGER NOT NULL DEFAULT 1,
    streak_count INTEGER NOT NULL DEFAULT 0,
    streak_last_date DATE,
    badges JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_progress_total_xp_non_negative CHECK (total_xp >= 0),
    CONSTRAINT user_progress_level_min_one CHECK (current_level >= 1),
    CONSTRAINT user_progress_streak_non_negative CHECK (streak_count >= 0)
);

CREATE OR REPLACE FUNCTION public.artmentor_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_progress_set_updated_at ON public.user_progress;
CREATE TRIGGER user_progress_set_updated_at
    BEFORE UPDATE ON public.user_progress
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

ALTER TABLE public.user_progress ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_progress_select_own ON public.user_progress;
CREATE POLICY user_progress_select_own ON public.user_progress
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS user_progress_insert_own ON public.user_progress;
CREATE POLICY user_progress_insert_own ON public.user_progress
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS user_progress_update_own ON public.user_progress;
CREATE POLICY user_progress_update_own ON public.user_progress
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS user_progress_delete_own ON public.user_progress;
CREATE POLICY user_progress_delete_own ON public.user_progress
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
