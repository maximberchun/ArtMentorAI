-- ArtMentorAI: Postgres source-of-truth tables (profiles, storage metadata, critiques,
-- portfolio items, progress snapshots). Run via Supabase CLI or SQL editor.

CREATE TABLE public.profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    goals TEXT[] NOT NULL DEFAULT '{}',
    preferred_styles TEXT[] NOT NULL DEFAULT '{}',
    disliked_styles TEXT[] NOT NULL DEFAULT '{}',
    favorite_artists TEXT[] NOT NULL DEFAULT '{}',
    experience_level TEXT NOT NULL DEFAULT 'beginner',
    retain_memory BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX profiles_active_idx ON public.profiles (user_id) WHERE deleted_at IS NULL;

CREATE TABLE public.image_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    storage_bucket TEXT NOT NULL,
    storage_object_path TEXT NOT NULL,
    mime_type TEXT,
    original_filename TEXT,
    byte_size BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX image_assets_active_path_uidx ON public.image_assets (
    storage_bucket,
    storage_object_path
) WHERE deleted_at IS NULL;

CREATE INDEX image_assets_user_idx ON public.image_assets (user_id)
WHERE
    deleted_at IS NULL;

-- persist before / independent of Qdrant
CREATE TABLE public.critiques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    image_asset_id UUID REFERENCES public.image_assets (id) ON DELETE SET NULL,
    artwork_filename TEXT,
    summary TEXT NOT NULL,
    score SMALLINT NOT NULL,
    technical_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    constructive_advice TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    goals_snapshot TEXT,
    vector_point_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT critiques_score_range CHECK (
        score >= 1
        AND score <= 10
    )
);

CREATE INDEX critiques_user_created_idx ON public.critiques (user_id, created_at DESC)
WHERE
    deleted_at IS NULL;

CREATE TABLE public.portfolio_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    image_asset_id UUID NOT NULL REFERENCES public.image_assets (id) ON DELETE RESTRICT,
    filename TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    description TEXT NOT NULL DEFAULT '',
    vector_point_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX portfolio_items_user_created_idx ON public.portfolio_items (user_id, created_at DESC)
WHERE
    deleted_at IS NULL;

CREATE TABLE public.progress_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    critique_id UUID REFERENCES public.critiques (id) ON DELETE SET NULL,
    rubric_key TEXT NOT NULL,
    rubric_version TEXT NOT NULL DEFAULT '1.0',
    dimension_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    aggregate_score NUMERIC(5, 2),
    narrative TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX progress_snapshots_user_created_idx ON public.progress_snapshots (user_id, created_at DESC)
WHERE
    deleted_at IS NULL;


CREATE OR REPLACE FUNCTION public.artmentor_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_set_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

CREATE TRIGGER portfolio_items_set_updated_at
    BEFORE UPDATE ON public.portfolio_items
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.image_assets ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.critiques ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.portfolio_items ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.progress_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY profiles_select_own ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY profiles_insert_own ON public.profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY profiles_delete_own ON public.profiles FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY image_assets_select_own ON public.image_assets FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY image_assets_insert_own ON public.image_assets FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY image_assets_update_own ON public.image_assets FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY image_assets_delete_own ON public.image_assets FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY critiques_select_own ON public.critiques FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY critiques_insert_own ON public.critiques FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY critiques_update_own ON public.critiques FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY critiques_delete_own ON public.critiques FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY portfolio_items_select_own ON public.portfolio_items FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY portfolio_items_insert_own ON public.portfolio_items FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY portfolio_items_update_own ON public.portfolio_items FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY portfolio_items_delete_own ON public.portfolio_items FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY progress_snapshots_select_own ON public.progress_snapshots FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY progress_snapshots_insert_own ON public.progress_snapshots FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY progress_snapshots_update_own ON public.progress_snapshots FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY progress_snapshots_delete_own ON public.progress_snapshots FOR DELETE TO authenticated USING (auth.uid() = user_id);
