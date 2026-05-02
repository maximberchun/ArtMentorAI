"""Endpoints for artwork analysis with long-term memory (RAG).

This module provides REST endpoints for:
- Artwork critique generation using Gemini AI
- Automatic storage in vector database for future reference
- Multimodal input support (image + optional user comments)
- Error handling that doesn't break the API if vector DB is down
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import AppConfig
from ..db import create_sync_supabase_service_client
from ..exceptions import AIServiceError
from ..models import AnalysisResponse, AuthUser, UserProfile
from ..repositories import (
    ConversationMessageRepository,
    ConversationRepository,
    CritiqueRepository,
    ImageAssetRepository,
    ProgressSnapshotRepository,
    UserProgressRepository,
    VectorSyncJobRepository,
)
from ..repositories.vector_sync_job_repository import ENTITY_CRITIQUE, OP_UPSERT
from ..services import AgentService, ProfileService, StorageService
from ..services.auth_service import AuthService
from ..services.vector_service import ArtCritique, VectorService
from ..models.db_rows import ConversationMessageRow
from ..utils.upload_validation import (
    validate_file_size,
    validate_image_content_type,
    validate_image_file,
)

_bearer = HTTPBearer(auto_error=True)


def _build_current_user_dependency(config: AppConfig) -> Callable[..., Awaitable[AuthUser]]:
    auth = AuthService(config)

    async def _current_user(
        creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    ) -> AuthUser:
        return await auth.verify_access_token(creds.credentials)

    return _current_user


def get_agent_service(config: AppConfig) -> AgentService:
    """Dependency injection for AgentService."""
    return AgentService(config)


def get_vector_service(config: AppConfig) -> VectorService:
    """Dependency injection for VectorService.

    Creates or reuses VectorService instance with proper logger.

    Args:
        config: Application configuration

    Returns:
        VectorService: Initialized vector service instance
    """
    return VectorService(config=config, logger=config.logger)


def get_storage_service(config: AppConfig) -> StorageService:
    """Dependency injection for StorageService."""
    return StorageService(config)


def _format_profile_for_prompt(profile: UserProfile) -> str:
    """Create a compact textual description of the user profile for the agent."""
    parts: list[str] = []

    if profile.goals:
        parts.append('Goals: ' + '; '.join(profile.goals))
    if profile.preferred_styles:
        parts.append('Preferred styles: ' + '; '.join(profile.preferred_styles))
    if profile.disliked_styles:
        parts.append('Disliked styles: ' + '; '.join(profile.disliked_styles))
    if profile.favorite_artists:
        parts.append('Favorite artists: ' + '; '.join(profile.favorite_artists))
    if profile.experience_level:
        parts.append('Experience level: ' + profile.experience_level)

    return ' | '.join(parts)


def _format_portfolio_neighbors_for_prompt(records: list[dict]) -> str | None:
    """Create compact portfolio context text for AI prompt injection."""
    lines: list[str] = []
    for record in records:
        filename = record.get('filename') or 'unknown'
        tags = record.get('tags') or []
        description = record.get('description') or ''
        similarity_score = record.get('similarity_score')
        formatted_tags = ', '.join(tag for tag in tags if isinstance(tag, str))
        similarity_part = (
            f' | Similarity: {similarity_score:.3f}'
            if isinstance(similarity_score, float | int)
            else ''
        )
        line = (
            f'- File: {filename}'
            f' | Tags: {formatted_tags or "none"}'
            f' | Notes: {description or "none"}'
            f'{similarity_part}'
        )
        lines.append(line)
    return '\n'.join(lines) or None


def _merge_memory_context(
    past_critiques: str | None,
    portfolio_context: str | None,
) -> str | None:
    """Combine critique and portfolio memory into one prompt-safe text block."""
    sections: list[str] = []
    if past_critiques and past_critiques.strip():
        sections.append(f'Past critiques:\n{past_critiques.strip()}')
    if portfolio_context and portfolio_context.strip():
        sections.append(
            'Relevant portfolio neighbors:\n'
            f'{portfolio_context.strip()}\n'
            'Instruction: Compare this submission against these related portfolio pieces, '
            'highlighting repeated strengths and recurring mistakes.'
        )
    return '\n\n'.join(sections) if sections else None


def _format_conversation_messages_for_prompt(messages: list[ConversationMessageRow]) -> str | None:
    """Format recent conversation turns for prompt injection."""
    if not messages:
        return None

    role_labels = {'user': 'User', 'assistant': 'Assistant', 'system': 'System'}
    lines: list[str] = []
    for message in reversed(messages):
        normalized = ' '.join(message.content.split())
        if not normalized:
            continue
        label = role_labels.get(message.role, message.role.title())
        lines.append(f'- {label}: {normalized[:800]}')
    return '\n'.join(lines) or None


def _build_assistant_conversation_message(analysis: AnalysisResponse) -> str:
    """Store a compact assistant turn for short-term conversation memory."""
    top_issues = ', '.join(item.title for item in analysis.prioritized_issues[:3]) or 'none listed'
    top_gate = analysis.readiness_gate or 'none'
    first_drill = analysis.targeted_drills[0].name if analysis.targeted_drills else 'none'
    return (
        f'Score: {analysis.score}/10\n'
        f'Prioritized issues: {top_issues}\n'
        f'Readiness gate: {top_gate}\n'
        f'First drill: {first_drill}'
    )


def _build_persistence_summary(analysis: AnalysisResponse) -> str:
    """Derive a compact summary string for legacy persistence fields."""
    if analysis.prioritized_issues:
        ordered = sorted(analysis.prioritized_issues, key=lambda item: item.priority)
        return '; '.join(f'{item.title}: {item.diagnosis}' for item in ordered[:2])
    if analysis.rubric_anchors:
        return '; '.join(analysis.rubric_anchors[:2])
    return analysis.readiness_gate


def _build_persistence_advice(analysis: AnalysisResponse) -> str:
    """Derive practical advice text from targeted drills and readiness gate."""
    if analysis.targeted_drills:
        drills = ' '.join(
            f'{item.name}: {item.objective}. Check: {item.success_check}.'
            for item in analysis.targeted_drills[:2]
        )
        return f'{drills} Gate: {analysis.readiness_gate}'
    return analysis.readiness_gate


def _require_at_least_one_input(
    file: UploadFile | None,
    user_input: str | None,
) -> None:
    """Raise HTTP 422 if neither a file nor a text comment was provided.

    Extracted into a standalone function so the ``raise`` is not sitting
    directly inside a ``try`` block (Ruff TRY301).

    Args:
        file:       The uploaded file, or ``None`` if omitted.
        user_input: The user's text comment, or ``None`` / blank if omitted.

    Raises:
        HTTPException 422: If both inputs are absent.
    """
    if file is None and not (user_input and user_input.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Provide at least an image, a text comment, or both.',
        )


def create_analysis_router(config: AppConfig) -> APIRouter:  # noqa: C901, PLR0915
    """
    Create analysis router with configuration.

    Args:
        config: Application configuration

    Returns:
        APIRouter: Configured router for analysis endpoints
    """
    router = APIRouter(
        prefix='/analysis',
        tags=['Analysis'],
        responses={
            400: {'description': 'Invalid file (extension, MIME type, or empty file)'},
            413: {'description': 'File too large'},
            415: {'description': 'Unsupported media type (only images allowed)'},
            422: {'description': 'Validation error (missing image and text)'},
            500: {'description': 'Server error'},
        },
    )

    # Initialize services
    agent_service = AgentService(config)
    profile_service = ProfileService(config=config, logger=config.logger)
    current_user = _build_current_user_dependency(config)
    try:
        vector_service: VectorService | None = get_vector_service(config)
    except RuntimeError as init_error:
        config.logger.warning(
            'VectorService unavailable at startup: %s. '
            'Continuing without long-term memory until Qdrant is restored.',
            str(init_error),
        )
        vector_service = None
    try:
        storage_service: StorageService | None = get_storage_service(config)
    except RuntimeError as init_error:
        config.logger.warning(
            'StorageService unavailable at startup: %s. Continuing without image persistence.',
            str(init_error),
        )
        storage_service = None

    @router.post(
        '/critique',
        summary='Analyze an artwork',
        description="""Send an image and optional comments for structured feedback with score
        and recommendations""",
    )
    async def critique_artwork(  # noqa: C901, PLR0912, PLR0915
        user: Annotated[AuthUser, Depends(current_user)],
        file: Annotated[
            UploadFile | None, File(description='The artwork image to analyse.')
        ] = None,
        user_input: Annotated[
            str | None,
            Form(description='Optional user comments about their work.'),
        ] = None,
        conversation_id: Annotated[
            str | None,
            Form(description='Optional conversation thread id for short-term memory context.'),
        ] = None,
    ) -> AnalysisResponse:
        """
        Main endpoint for artwork analysis with multimodal input support.

        The endpoint accepts:

        - **Image-only** requests (file provided, no user_input).
        - **Text-only** requests (user_input provided, no file) — for
          analysis of written descriptions or questions.
        - **Image + text** requests (both provided) for fully contextualised
          critiques.

        The authenticated user's id is derived from the Supabase access token
        so that critiques can be associated with a specific artist in the vector database.

        Validation order (fail-fast):

        1. At least one of ``file`` or ``user_input`` must be provided → HTTP 422.
        2. If a file is present, ``content_type`` must start with ``"image/"`` → HTTP 415.
        3. File bytes must not exceed ``MAX_FILE_SIZE_MB`` from .env   → HTTP 413.
        4. Extension and MIME type must be in allowlist                → HTTP 400.
        5. File must not be empty                                      → HTTP 400.

        Database failures are gracefully handled — the API still returns the
        analysis even if the vector DB is temporarily unavailable or could
        not be initialised at startup.

        Args:
            file:       Optional image file to analyse.
            user_input: Optional user comments or description of the artwork.
            user:       Authenticated user identity (from Supabase access token).

        Returns:
            AnalysisResponse: JSON with score, ordered issues, drills, readiness gate, confidence.

        Raises:
            HTTPException 415: Unsupported file type.
            HTTPException 413: File exceeds MAX_FILE_SIZE_MB limit (.env).
            HTTPException 400: Invalid extension / empty file.
            HTTPException 422: Neither image nor text was provided.
            HTTPException 500: Unexpected processing error.
        """
        # Ensure that at least image or text is provided.
        _require_at_least_one_input(file=file, user_input=user_input)

        try:
            # File validation
            image_bytes: bytes | None = None
            mime_type: str | None = None
            image_path: str | None = None

            if file is not None:
                mime_type = validate_image_content_type(file.content_type)

                image_bytes = await file.read()

                validate_file_size(image_bytes, config.upload.max_file_size_mb)

                _extension, mime_type = validate_image_file(
                    filename=file.filename or 'unknown',
                    content_type=mime_type,
                    config=config,
                )
                if storage_service is not None and image_bytes is not None:
                    try:
                        image_path = storage_service.upload_image(
                            user_id=user.user_id,
                            image_bytes=image_bytes,
                            filename=file.filename or 'unknown',
                            mime_type=mime_type,
                        )
                    except RuntimeError as storage_error:
                        config.logger.warning(
                            'Image upload failed for user_id=%s: %s. '
                            'Continuing without persisted image reference.',
                            user.user_id,
                            str(storage_error),
                        )

            # Log the request with context
            config.logger.info(
                'Analyzing input — file: %s | user_input: %s | user_id: %s',
                file.filename if file else 'none',
                'yes' if user_input else 'none',
                user.user_id,
            )

            past_critiques_str: str | None = None
            portfolio_context_str: str | None = None
            conversation_context_str: str | None = None
            active_conversation_id = (
                conversation_id.strip() if conversation_id and conversation_id.strip() else None
            )
            if active_conversation_id:
                try:
                    sb_for_conversation = create_sync_supabase_service_client(config)
                    conversation_repo = ConversationRepository(sb_for_conversation, config.logger)
                    conversation_message_repo = ConversationMessageRepository(
                        sb_for_conversation,
                        config.logger,
                    )
                    conversation = conversation_repo.get_active_for_user(
                        active_conversation_id,
                        user.user_id,
                    )
                    if conversation is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail='Conversation not found.',
                        )
                    recent_messages = conversation_message_repo.list_recent_for_conversation(
                        conversation_id=active_conversation_id,
                        user_id=user.user_id,
                        limit=8,
                    )
                    conversation_context_str = _format_conversation_messages_for_prompt(
                        recent_messages
                    )
                except RuntimeError as conversation_error:
                    config.logger.warning(
                        'Conversation lookup failed for user_id=%s conversation_id=%s: %s. '
                        'Proceeding without short-term conversation memory.',
                        user.user_id,
                        active_conversation_id,
                        str(conversation_error),
                    )

            if vector_service is not None:
                try:
                    # Use the user's own comment as the semantic query when
                    # available; fall back to a generic drawing-error query so
                    # we always attempt to surface relevant history.
                    memory_query = (
                        user_input.strip()
                        if user_input and user_input.strip()
                        else 'technical drawing errors anatomy perspective'
                    )
                    past_records = vector_service.search_similar_critiques(
                        query_text=memory_query,
                        user_id=user.user_id,
                    )
                    if past_records:
                        past_critiques_str = (
                            ''.join(
                                f'- Summary: {r["summary"]} | Advice: {r["advice"]}'
                                for r in past_records
                                if r.get('summary') or r.get('advice')
                            )
                            or None
                        )  # collapse to None if every record had empty fields
                        config.logger.debug(
                            'Injecting %d past critique(s) into prompt for user_id=%s',
                            len(past_records),
                            user.user_id,
                        )
                    else:
                        config.logger.debug(
                            'No past critiques found for user_id=%s — proceeding without memory',
                            user.user_id,
                        )

                    portfolio_neighbors = vector_service.search_similar_portfolio_items(
                        query_text=memory_query,
                        user_id=user.user_id,
                    )
                    if portfolio_neighbors:
                        portfolio_context_str = _format_portfolio_neighbors_for_prompt(
                            portfolio_neighbors
                        )
                        config.logger.debug(
                            'Injecting %d portfolio neighbor(s) into prompt for user_id=%s',
                            len(portfolio_neighbors),
                            user.user_id,
                        )
                    else:
                        config.logger.debug(
                            'No portfolio neighbors found for user_id=%s',
                            user.user_id,
                        )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as memory_error:
                    config.logger.warning(
                        'Memory retrieval failed for user_id=%s: %s. '
                        'Proceeding without history context.',
                        user.user_id,
                        str(memory_error),
                    )
            else:
                config.logger.debug(
                    'VectorService not available; proceeding without memory for user_id=%s',
                    user.user_id,
                )

            # Load optional user profile for personalised critique
            profile_context_str: str | None = None
            try:
                profile = profile_service.get_profile(user.user_id)
            except RuntimeError as e:
                config.logger.warning(
                    'Failed to load profile for user_id=%s: %s. Proceeding without profile.',
                    user.user_id,
                    str(e),
                )
            else:
                if profile is not None:
                    profile_context_str = _format_profile_for_prompt(profile)
                    config.logger.debug(
                        'Injecting profile context into prompt for user_id=%s',
                        user.user_id,
                    )

            # Analyze with Gemini AI agent
            result = await agent_service.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                user_input=user_input,
                past_critiques=_merge_memory_context(
                    past_critiques=past_critiques_str,
                    portfolio_context=portfolio_context_str,
                ),
                profile_context=profile_context_str,
                conversation_context=conversation_context_str,
                has_artwork=image_bytes is not None,
            )

            # Persist critique - Postgres + async Qdrant sync
            analysis_result = AnalysisResponse(**result) if isinstance(result, dict) else result
            if image_bytes is None:
                analysis_result.score = None

            synced_via_pg = False
            try:
                sb = create_sync_supabase_service_client(config)
                image_asset_id = None
                if image_path is not None:
                    img_repo = ImageAssetRepository(sb, config.logger)
                    asset = img_repo.create(
                        user_id=user.user_id,
                        storage_bucket=config.supabase.storage_bucket,
                        storage_object_path=image_path,
                        mime_type=mime_type,
                        original_filename=file.filename if file is not None else None,
                        byte_size=len(image_bytes) if image_bytes else None,
                    )
                    image_asset_id = asset.id
                cr_repo = CritiqueRepository(sb, config.logger)
                artwork_filename = (file.filename if file is not None else None) or 'unknown'
                row = cr_repo.create(
                    user_id=user.user_id,
                    summary=_build_persistence_summary(analysis_result),
                    score=analysis_result.score,
                    rubric_anchors=analysis_result.rubric_anchors,
                    prioritized_issues=[
                        {
                            'title': item.title,
                            'diagnosis': item.diagnosis,
                            'priority': item.priority,
                        }
                        for item in analysis_result.prioritized_issues
                    ],
                    root_causes=analysis_result.root_causes,
                    targeted_drills=[
                        {
                            'name': item.name,
                            'objective': item.objective,
                            'success_check': item.success_check,
                        }
                        for item in analysis_result.targeted_drills
                    ],
                    readiness_gate=analysis_result.readiness_gate,
                    confidence=analysis_result.confidence,
                    tags=[],
                    goals_snapshot=profile_context_str,
                    conversation_id=active_conversation_id,
                    image_asset_id=image_asset_id,
                    artwork_filename=artwork_filename,
                )
                if active_conversation_id:
                    msg_repo = ConversationMessageRepository(sb, config.logger)
                    user_message = (
                        user_input.strip()
                        if user_input and user_input.strip()
                        else 'Please critique the uploaded artwork.'
                    )
                    msg_repo.create(
                        conversation_id=active_conversation_id,
                        user_id=user.user_id,
                        role='user',
                        content=user_message,
                        critique_id=row.id,
                    )
                    msg_repo.create(
                        conversation_id=active_conversation_id,
                        user_id=user.user_id,
                        role='assistant',
                        content=_build_assistant_conversation_message(analysis_result),
                        critique_id=row.id,
                    )
                if analysis_result.score is not None:
                    try:
                        dimension_scores = {
                            'overall_score_1_to_10': analysis_result.score,
                            'prioritized_issue_count': len(analysis_result.prioritized_issues),
                        }
                        ProgressSnapshotRepository(sb, config.logger).create(
                            user_id=user.user_id,
                            critique_id=row.id,
                            rubric_key='critique_quality',
                            rubric_version='1.0',
                            dimension_scores=dimension_scores,
                            aggregate_score=float(analysis_result.score),
                            narrative=_build_persistence_summary(analysis_result),
                        )
                        UserProgressRepository(sb, config.logger).upsert_after_critique(
                            user_id=user.user_id,
                            score=analysis_result.score,
                        )
                    except RuntimeError as progress_error:
                        config.logger.warning(
                            'Progress persistence skipped for user_id=%s: %s',
                            user.user_id,
                            str(progress_error),
                        )
                    VectorSyncJobRepository(sb, config.logger).enqueue(
                        ENTITY_CRITIQUE,
                        row.id,
                        OP_UPSERT,
                    )
                else:
                    config.logger.debug(
                        'Skipping progress and vector sync for unscored text-only critique id=%s',
                        row.id,
                    )
                synced_via_pg = True
                config.logger.info(
                    'Critique persisted to Postgres and queued for Qdrant: id=%s user_id=%s',
                    row.id,
                    user.user_id,
                )
            except RuntimeError as persist_error:
                config.logger.warning(
                    'Postgres critique persistence / enqueue failed: %s',
                    str(persist_error),
                )

            if (
                not synced_via_pg
                and vector_service is not None
                and analysis_result.score is not None
            ):
                try:
                    config.logger.debug('Fallback: store critique directly in Qdrant')
                    artwork_filename = (file.filename if file is not None else None) or 'unknown'
                    critique = ArtCritique.from_analysis_response(
                        analysis_result,
                        goals_snapshot=profile_context_str,
                    )
                    vector_service.save_critique(
                        critique,
                        artwork_filename,
                        user_id=user.user_id,
                        image_path=image_path,
                    )
                    config.logger.info(
                        'Critique stored in vector database (fallback): %s (user_id=%s)',
                        artwork_filename,
                        user.user_id,
                    )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as vector_error:
                    config.logger.warning(
                        'Failed to store critique in vector database: %s. '
                        'Continuing with analysis response.',
                        str(vector_error),
                    )
                    if storage_service is not None and image_path is not None:
                        storage_service.delete_file(image_path)
            elif not synced_via_pg:
                config.logger.debug(
                    'Skipping vector storage (no Postgres, no VectorService) user_id=%s',
                    user.user_id,
                )

            # Always return the analysis even if vector DB operations failed
            return analysis_result  # noqa: TRY300

        except AIServiceError as e:
            config.logger.warning('AI service error: %s (code=%s)', e.message, e.error_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    'error': e.error_code,
                    'message': e.message,
                    'retry_after': e.retry_after,
                },
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            config.logger.exception('Error processing image')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error analyzing image: {e!s}',
            ) from e

    @router.get(
        '/conversations/{conversation_id}/messages',
        summary='Get recent conversation messages',
        description='Return recent user and assistant turns for one conversation',
    )
    async def get_conversation_messages(
        conversation_id: str,
        user: Annotated[AuthUser, Depends(current_user)],
    ) -> list[dict[str, str | None]]:
        """Load recent messages for a user conversation thread."""
        try:
            sb = create_sync_supabase_service_client(config)
            conversation_repo = ConversationRepository(sb, config.logger)
            message_repo = ConversationMessageRepository(sb, config.logger)
            conversation = conversation_repo.get_active_for_user(conversation_id, user.user_id)
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Conversation not found.',
                )
            rows = message_repo.list_recent_for_conversation(
                conversation_id=conversation_id,
                user_id=user.user_id,
                limit=20,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to load conversation messages: {exc!s}',
            ) from exc

        return [
            {
                'id': row.id,
                'role': row.role,
                'content': row.content,
                'created_at': row.created_at.isoformat() if row.created_at else None,
            }
            for row in reversed(rows)
        ]

    @router.post(
        '/conversations',
        summary='Create conversation',
        description='Create a new conversation thread for critique continuity',
    )
    async def create_conversation(
        user: Annotated[AuthUser, Depends(current_user)],
        title: Annotated[str | None, Body(embed=True)] = None,
    ) -> dict[str, str | None]:
        """Create a conversation row and return basic metadata."""
        try:
            sb = create_sync_supabase_service_client(config)
            row = ConversationRepository(sb, config.logger).create(
                user_id=user.user_id,
                title=title.strip() if title and title.strip() else None,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to create conversation: {exc!s}',
            ) from exc

        return {
            'id': row.id,
            'title': row.title,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }

    @router.get(
        '/health',
        summary='Health check',
        description='Check if the analysis service is available',
    )
    async def health_check() -> dict[str, str]:
        """Health check for analysis endpoint."""
        return {
            'status': 'healthy',
            'service': 'ArtMentor AI - Analysis',
        }

    @router.get(
        '/vector-db-health',
        summary='Vector Database health check',
        description='Check if the vector database is accessible',
    )
    async def vector_db_health() -> dict[str, str]:
        """Health check for vector database connection."""
        is_healthy = vector_service.health_check() if vector_service is not None else False
        status_text = 'healthy' if is_healthy else 'unavailable'

        return {
            'status': status_text,
            'service': 'ArtMentor AI - Vector Database',
            'database': 'Qdrant',
        }

    return router
