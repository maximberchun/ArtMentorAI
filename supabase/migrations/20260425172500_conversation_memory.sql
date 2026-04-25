CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX conversations_user_created_idx ON public.conversations (user_id, created_at DESC)
WHERE
    deleted_at IS NULL;

CREATE TABLE public.conversation_messages (
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

CREATE INDEX conversation_messages_conversation_created_idx ON public.conversation_messages (
    conversation_id,
    created_at DESC
)
WHERE
    deleted_at IS NULL;

ALTER TABLE public.critiques
ADD COLUMN conversation_id UUID REFERENCES public.conversations (id) ON DELETE SET NULL;

ALTER TABLE public.critiques
ALTER COLUMN score DROP NOT NULL;

CREATE INDEX critiques_user_conversation_created_idx ON public.critiques (
    user_id,
    conversation_id,
    created_at DESC
)
WHERE
    deleted_at IS NULL
    AND conversation_id IS NOT NULL;

CREATE TRIGGER conversations_set_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at();

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY conversations_select_own ON public.conversations FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY conversations_insert_own ON public.conversations FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY conversations_update_own ON public.conversations FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY conversations_delete_own ON public.conversations FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY conversation_messages_select_own ON public.conversation_messages FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY conversation_messages_insert_own ON public.conversation_messages FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY conversation_messages_update_own ON public.conversation_messages FOR UPDATE TO authenticated USING (auth.uid() = user_id)
WITH
    CHECK (auth.uid() = user_id);

CREATE POLICY conversation_messages_delete_own ON public.conversation_messages FOR DELETE TO authenticated USING (auth.uid() = user_id);
