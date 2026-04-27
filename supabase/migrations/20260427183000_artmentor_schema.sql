-- ArtMentorAI unified Supabase schema migration.

-- Shared trigger function
CREATE OR REPLACE FUNCTION public.artmentor_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Core domain tables
CREATE TABLE IF NOT EXISTS public.profiles (
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

CREATE TABLE IF NOT EXISTS public.image_assets (
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

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.critiques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    image_asset_id UUID REFERENCES public.image_assets (id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES public.conversations (id) ON DELETE SET NULL,
    artwork_filename TEXT,
    summary TEXT NOT NULL,
    score SMALLINT,
    technical_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    constructive_advice TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    goals_snapshot TEXT,
    vector_point_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT critiques_score_range CHECK (score IS NULL OR (score >= 1 AND score <= 10))
);

CREATE TABLE IF NOT EXISTS public.portfolio_items (
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

CREATE TABLE IF NOT EXISTS public.progress_snapshots (
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

CREATE TABLE IF NOT EXISTS public.conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations (id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    critique_id UUID REFERENCES public.critiques (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT conversation_messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE TABLE IF NOT EXISTS public.vector_sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_kind TEXT NOT NULL,
    entity_id UUID NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vector_sync_jobs_entity_kind_chk CHECK (entity_kind IN ('critique', 'portfolio_item')),
    CONSTRAINT vector_sync_jobs_operation_chk CHECK (operation IN ('upsert', 'delete')),
    CONSTRAINT vector_sync_jobs_status_chk CHECK (status IN ('pending', 'processing', 'succeeded', 'dead_letter'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS profiles_active_idx ON public.profiles (user_id) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS image_assets_active_path_uidx ON public.image_assets (storage_bucket, storage_object_path)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS image_assets_user_idx ON public.image_assets (user_id)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS critiques_user_created_idx ON public.critiques (user_id, created_at DESC)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS critiques_user_conversation_created_idx ON public.critiques (user_id, conversation_id, created_at DESC)
WHERE deleted_at IS NULL AND conversation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS portfolio_items_user_created_idx ON public.portfolio_items (user_id, created_at DESC)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS progress_snapshots_user_created_idx ON public.progress_snapshots (user_id, created_at DESC)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS conversations_user_created_idx ON public.conversations (user_id, created_at DESC)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS conversation_messages_conversation_created_idx ON public.conversation_messages (conversation_id, created_at DESC)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS vector_sync_jobs_pending_due_idx ON public.vector_sync_jobs (next_attempt_at ASC, created_at ASC)
WHERE status = 'pending';

-- Business logic functions
CREATE OR REPLACE FUNCTION public.artmentor_handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.profiles (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.artmentor_handle_new_user() FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.enqueue_vector_sync(
    p_entity_kind text,
    p_entity_id uuid,
    p_operation text
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF p_entity_kind NOT IN ('critique', 'portfolio_item') THEN
        RAISE EXCEPTION 'enqueue_vector_sync: invalid entity_kind';
    END IF;
    IF p_operation NOT IN ('upsert', 'delete') THEN
        RAISE EXCEPTION 'enqueue_vector_sync: invalid operation';
    END IF;

    IF p_operation = 'upsert' THEN
        DELETE FROM public.vector_sync_jobs
        WHERE entity_kind = p_entity_kind
            AND entity_id = p_entity_id
            AND status = 'pending'
            AND operation = 'upsert';
        INSERT INTO public.vector_sync_jobs (entity_kind, entity_id, operation, status, next_attempt_at)
        VALUES (p_entity_kind, p_entity_id, 'upsert', 'pending', now());
    ELSE
        DELETE FROM public.vector_sync_jobs
        WHERE entity_kind = p_entity_kind
            AND entity_id = p_entity_id
            AND status = 'pending';
        INSERT INTO public.vector_sync_jobs (entity_kind, entity_id, operation, status, next_attempt_at)
        VALUES (p_entity_kind, p_entity_id, 'delete', 'pending', now());
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.enqueue_vector_sync (text, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enqueue_vector_sync (text, uuid, text) TO service_role;

-- Triggers
DROP TRIGGER IF EXISTS profiles_set_updated_at ON public.profiles;
CREATE TRIGGER profiles_set_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

DROP TRIGGER IF EXISTS portfolio_items_set_updated_at ON public.portfolio_items;
CREATE TRIGGER portfolio_items_set_updated_at
    BEFORE UPDATE ON public.portfolio_items
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

DROP TRIGGER IF EXISTS conversations_set_updated_at ON public.conversations;
CREATE TRIGGER conversations_set_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

DROP TRIGGER IF EXISTS user_progress_set_updated_at ON public.user_progress;
CREATE TRIGGER user_progress_set_updated_at
    BEFORE UPDATE ON public.user_progress
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

DROP TRIGGER IF EXISTS vector_sync_jobs_set_updated_at ON public.vector_sync_jobs;
CREATE TRIGGER vector_sync_jobs_set_updated_at
    BEFORE UPDATE ON public.vector_sync_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_handle_new_user();

-- RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.critiques ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.progress_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vector_sync_jobs ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.artmentor_is_owner(p_user_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT auth.uid() = p_user_id;
$$;

DO $$
DECLARE
    tbl text;
    old_policy text;
BEGIN
    -- Drop previous per-action policies if they exist.
    FOREACH old_policy IN ARRAY ARRAY[
        'profiles_select_own', 'profiles_insert_own', 'profiles_update_own', 'profiles_delete_own',
        'image_assets_select_own', 'image_assets_insert_own', 'image_assets_update_own', 'image_assets_delete_own',
        'critiques_select_own', 'critiques_insert_own', 'critiques_update_own', 'critiques_delete_own',
        'portfolio_items_select_own', 'portfolio_items_insert_own', 'portfolio_items_update_own', 'portfolio_items_delete_own',
        'progress_snapshots_select_own', 'progress_snapshots_insert_own', 'progress_snapshots_update_own', 'progress_snapshots_delete_own',
        'user_progress_select_own', 'user_progress_insert_own', 'user_progress_update_own', 'user_progress_delete_own',
        'conversations_select_own', 'conversations_insert_own', 'conversations_update_own', 'conversations_delete_own',
        'conversation_messages_select_own', 'conversation_messages_insert_own', 'conversation_messages_update_own', 'conversation_messages_delete_own'
    ]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.image_assets;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.critiques;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.portfolio_items;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.progress_snapshots;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.user_progress;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.conversations;', old_policy);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.conversation_messages;', old_policy);
    END LOOP;

    FOREACH tbl IN ARRAY ARRAY[
        'profiles',
        'image_assets',
        'critiques',
        'portfolio_items',
        'progress_snapshots',
        'user_progress',
        'conversations',
        'conversation_messages'
    ]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', tbl || '_owner_all', tbl);
        EXECUTE format(
            'CREATE POLICY %I ON public.%I FOR ALL TO authenticated USING (public.artmentor_is_owner(user_id)) WITH CHECK (public.artmentor_is_owner(user_id));',
            tbl || '_owner_all',
            tbl
        );
    END LOOP;
END;
$$;

-- Storage bucket + storage.objects policies
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'artworks',
    'artworks',
    false,
    10485760,
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']::text[]
)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS artworks_select_own ON storage.objects;
DROP POLICY IF EXISTS artworks_insert_own ON storage.objects;
DROP POLICY IF EXISTS artworks_update_own ON storage.objects;
DROP POLICY IF EXISTS artworks_delete_own ON storage.objects;
DROP POLICY IF EXISTS artworks_owner_all ON storage.objects;

CREATE POLICY artworks_owner_all ON storage.objects
FOR ALL TO authenticated
USING (
    bucket_id = 'artworks'
    AND (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
    bucket_id = 'artworks'
    AND (storage.foldername(name))[1] = auth.uid()::text
);
