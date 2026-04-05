-- Outbox-style jobs: async, idempotent sync from Postgres entities to Qdrant.

CREATE TABLE public.vector_sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    entity_kind TEXT NOT NULL,
    entity_id UUID NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vector_sync_jobs_entity_kind_chk CHECK (
        entity_kind IN ('critique', 'portfolio_item')
    ),
    CONSTRAINT vector_sync_jobs_operation_chk CHECK (operation IN ('upsert', 'delete')),
    CONSTRAINT vector_sync_jobs_status_chk CHECK (
        status IN ('pending', 'processing', 'succeeded', 'dead_letter')
    )
);

CREATE INDEX vector_sync_jobs_pending_due_idx ON public.vector_sync_jobs (next_attempt_at ASC, created_at ASC)
WHERE
    status = 'pending';

CREATE TRIGGER vector_sync_jobs_set_updated_at
    BEFORE UPDATE ON public.vector_sync_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.artmentor_set_updated_at ();

-- Atomically replace coalescable pending upserts and serialize delete vs upsert
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

REVOKE ALL ON FUNCTION public.enqueue_vector_sync (text, uuid, text)
FROM
    PUBLIC;

GRANT EXECUTE ON FUNCTION public.enqueue_vector_sync (text, uuid, text) TO service_role;

ALTER TABLE public.vector_sync_jobs ENABLE ROW LEVEL SECURITY;
