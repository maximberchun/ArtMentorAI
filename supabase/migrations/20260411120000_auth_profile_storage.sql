-- Auth + Storage: profile row on signup (email/password and OAuth), private artworks bucket,
-- and RLS on storage.objects scoped to {user_id}/... paths (matches API StorageService layout).

-- -----------------------------------------------------------------------------
-- 1) Auto-create public.profiles when a row is inserted into auth.users
-- -----------------------------------------------------------------------------

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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_handle_new_user();

-- -----------------------------------------------------------------------------
-- 2) Storage bucket for artwork (private; API may use service role; clients use JWT + policies)
-- -----------------------------------------------------------------------------

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'artworks',
    'artworks',
    false,
    10485760,
    ARRAY[
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp'
    ]::text[]
)
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3) storage.objects policies: first path segment must equal auth.uid() (see StorageService paths)
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS artworks_select_own ON storage.objects;

DROP POLICY IF EXISTS artworks_insert_own ON storage.objects;

DROP POLICY IF EXISTS artworks_update_own ON storage.objects;

DROP POLICY IF EXISTS artworks_delete_own ON storage.objects;

CREATE POLICY artworks_select_own ON storage.objects FOR SELECT TO authenticated USING (
    bucket_id = 'artworks'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY artworks_insert_own ON storage.objects FOR INSERT TO authenticated
WITH
    CHECK (
        bucket_id = 'artworks'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY artworks_update_own ON storage.objects FOR UPDATE TO authenticated USING (
    bucket_id = 'artworks'
    AND (storage.foldername(name))[1] = auth.uid()::text
)
WITH
    CHECK (
        bucket_id = 'artworks'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY artworks_delete_own ON storage.objects FOR DELETE TO authenticated USING (
    bucket_id = 'artworks'
    AND (storage.foldername(name))[1] = auth.uid()::text
);
