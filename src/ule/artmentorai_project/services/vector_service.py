"""Vector Database service for storing and retrieving artwork critiques.

This module provides long-term memory capabilities using Qdrant vector database
and FastEmbed for local embedding generation. Supports both critique records
and portfolio items in a single collection, distinguished by payload ``type``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastembed.embedding import FlagEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..config import AppConfig
    from ..models import AnalysisResponse

# Payload type discriminator for Qdrant points
PAYLOAD_TYPE_CRITIQUE = 'critique'
PAYLOAD_TYPE_PORTFOLIO_ITEM = 'portfolio_item'

# Score 1-10 thresholds for mapping to level estimate 1-5
_LEVEL_THRESHOLD_1 = 2
_LEVEL_THRESHOLD_2 = 4
_LEVEL_THRESHOLD_3 = 6
_LEVEL_THRESHOLD_4 = 8


def _score_to_level_estimate(score: int) -> int:
    """Map 1-10 score to 1-5 level estimate for progress tracking."""
    if score <= _LEVEL_THRESHOLD_1:
        return 1
    if score <= _LEVEL_THRESHOLD_2:
        return 2
    if score <= _LEVEL_THRESHOLD_3:
        return 3
    if score <= _LEVEL_THRESHOLD_4:
        return 4
    return 5


class ArtCritique:
    """Data model for storing artwork critiques in vector database."""

    def __init__(  # noqa: PLR0913
        self,
        summary: str,
        score: int,
        technical_errors: list[str],
        constructive_advice: str,
        *,
        tags: list[str] | None = None,
        goals_snapshot: str | None = None,
    ) -> None:
        """Initialize an ArtCritique.

        Args:
            summary: Summary of the artwork analysis
            score: Score from 1-10
            technical_errors: List of identified technical errors
            constructive_advice: Constructive advice for improvement
            tags: Optional tags (style, medium, subject, etc.)
            goals_snapshot: Optional short text snapshot of user goals at time of critique
        """
        self.summary = summary
        self.score = score
        self.technical_errors = technical_errors
        self.constructive_advice = constructive_advice
        self.tags = tags or []
        self.goals_snapshot = goals_snapshot
        self.timestamp = datetime.now(tz=UTC).isoformat()

    def get_text_for_embedding(self) -> str:
        """Get concatenated text for embedding generation.

        Returns:
            str: Combined text of summary and technical errors
        """
        errors_text = ' '.join(self.technical_errors)
        tags_text = ' '.join(self.tags) if self.tags else ''
        return f'{self.summary} {errors_text} {tags_text}'.strip()

    def to_payload(self, filename: str, user_id: str) -> dict[str, Any]:
        """Build Qdrant payload for this critique (type=critique)."""
        level_estimate = _score_to_level_estimate(self.score)
        return {
            'type': PAYLOAD_TYPE_CRITIQUE,
            'user_id': user_id,
            'critique_id': None,
            'portfolio_item_id': None,
            'filename': filename,
            'score': self.score,
            'summary': self.summary,
            'advice': self.constructive_advice,
            'timestamp': self.timestamp,
            'tags': self.tags,
            'goals_snapshot': self.goals_snapshot or '',
            'level_estimate': level_estimate,
        }

    @classmethod
    def from_analysis_response(
        cls,
        response: AnalysisResponse,
        *,
        tags: list[str] | None = None,
        goals_snapshot: str | None = None,
    ) -> ArtCritique:
        """Create ArtCritique from AnalysisResponse.

        Args:
            response: AnalysisResponse from Gemini
            tags: Optional tags for the critique
            goals_snapshot: Optional user goals snapshot

        Returns:
            ArtCritique: Initialized critique object
        """
        return cls(
            summary=response.summary,
            score=response.score,
            technical_errors=response.technical_errors,
            constructive_advice=response.constructive_advice,
            tags=tags,
            goals_snapshot=goals_snapshot,
        )


class PortfolioRecord:
    """Data model for a portfolio item (uploaded artwork without critique)."""

    def __init__(
        self,
        filename: str,
        user_id: str,
        *,
        tags: list[str] | None = None,
        description: str | None = None,
        image_path: str | None = None,
    ) -> None:
        """Initialize a PortfolioRecord.

        Args:
            filename: Name of the uploaded file
            user_id: Owner user id
            tags: Optional tags (style, medium, subject, etc.)
            description: Optional text description for embedding
            image_path: Optional Supabase Storage object path
        """
        self.filename = filename
        self.user_id = user_id
        self.tags = tags or []
        self.description = description or ''
        self.image_path = image_path
        self.timestamp = datetime.now(tz=UTC).isoformat()

    def get_text_for_embedding(self) -> str:
        """Text used to generate embedding (description + tags)."""
        desc = self.description.strip()
        tags_text = ' '.join(self.tags) if self.tags else ''
        return f'{desc} {tags_text}'.strip() or self.filename

    def to_payload(self) -> dict[str, Any]:
        """Build Qdrant payload for this portfolio item (type=portfolio_item)."""
        return {
            'type': PAYLOAD_TYPE_PORTFOLIO_ITEM,
            'user_id': self.user_id,
            'critique_id': None,
            'portfolio_item_id': None,
            'filename': self.filename,
            'tags': self.tags,
            'description': self.description,
            'image_path': self.image_path,
            'timestamp': self.timestamp,
            'level_estimate': None,  # No score until critiqued
        }


class VectorService:
    """Service for managing vector embeddings and Qdrant interactions.

    Handles:
    - Connection to Qdrant vector database
    - Embedding generation using FastEmbed
    - CRUD operations for artwork critiques
    - Collection management
    """

    DISTANCE_METRIC = Distance.COSINE

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize VectorService.

        Args:
            config: Application config containing Qdrant/embedding runtime settings
            logger: Logger instance for debug info

        Raises:
            RuntimeError: If Qdrant connection fails
        """
        self.logger = logger or logging.getLogger(__name__)
        self.host = config.qdrant_host
        self.port = config.qdrant_port
        self.collection_name = config.qdrant_collection_name
        self.embedding_model_name = config.embedding_model_name
        self.embedding_size = config.embedding_size

        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=config.qdrant_api_key,
                timeout=config.qdrant_timeout_seconds,
            )
            self.logger.debug('Connected to Qdrant at %s:%s', self.host, self.port)

            # Initialize embedding model (downloads on first use)
            self.embedding_model = FlagEmbedding(
                model_name=self.embedding_model_name,
                cache_folder=config.embedding_cache_folder,
            )
            self.logger.debug('Loaded embedding model: %s', self.embedding_model_name)

            # Ensure collection exists
            self._ensure_collection_exists()
            self.logger.info('VectorService initialized with collection: %s', self.collection_name)

        except Exception as e:
            self.logger.exception('Failed to initialize VectorService')
            msg = f'VectorService initialization failed: {e!s}'
            raise RuntimeError(msg) from e

    def _ensure_collection_exists(self) -> None:
        """Ensure that the art_portfolio collection exists.

        Creates collection if it doesn't exist with proper vector parameters.

        Raises:
            RuntimeError: If collection creation fails
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                self.logger.info('Creating collection: %s', self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size,
                        distance=self.DISTANCE_METRIC,
                    ),
                )
                self.logger.info('Collection created: %s', self.collection_name)
            else:
                self.logger.debug('Collection already exists: %s', self.collection_name)

        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Failed to manage collection %s', self.collection_name)
            msg = f'Failed to manage collection {self.collection_name}: {e!s}'
            raise RuntimeError(msg) from e

    def _validate_critique(self, critique: ArtCritique) -> None:
        """Validate critique data before saving.

        Args:
            critique: ArtCritique object to validate

        Raises:
            TypeError: If critique data is invalid
        """
        # Validate technical_errors is a list
        if not isinstance(critique.technical_errors, list):
            msg = f'technical_errors must be a list, got {type(critique.technical_errors)}'
            raise TypeError(msg)

        # Validate list contains only strings
        if not all(isinstance(err, str) for err in critique.technical_errors):
            msg = 'technical_errors must contain only strings'
            raise TypeError(msg)

    def save_critique(
        self,
        critique: ArtCritique,
        filename: str,
        user_id: str,
        image_path: str | None = None,
    ) -> str | None:
        """Save artwork critique to vector database.

        Generates an embedding from the critique text and upserts a point into
        Qdrant.  The ``user_id`` is stored in the payload so that future
        similarity searches can be scoped to a single tenant with a Qdrant
        filter (``must: [{key: "user_id", match: {value: user_id}}]``).

        Args:
            critique: ArtCritique object with analysis data
            filename: Name/ID of the artwork file
            user_id: Unique identifier for the user who owns the critique
            image_path: Optional Supabase Storage object path for the source image
        Returns:
            Optional[str]: Point ID if successful, None if failed

        Raises:
            ValueError: If critique data is invalid
        """
        try:
            # Validate critique data
            self._validate_critique(critique)

            # Generate embedding from critique text
            text_for_embedding = critique.get_text_for_embedding()

            self.logger.debug('Generating embedding for file: %s (user_id: %s)', filename, user_id)

            embeddings_generator = self.embedding_model.embed(text_for_embedding)
            embeddings_list = list(embeddings_generator)
            embedding_vector = embeddings_list[0].tolist()

            point_id = str(uuid4())
            payload = critique.to_payload(filename=filename, user_id=user_id)
            payload['image_path'] = image_path

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding_vector,
                        payload=payload,
                    )
                ],
            )

            self.logger.info(
                'Critique saved to Qdrant: %s (point_id: %s, user_id: %s)',
                filename,
                point_id,
                user_id,
            )
        except TypeError:
            self.logger.exception('Validation error saving critique')
            raise

        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Qdrant error saving critique for %s', filename)
            msg = f'Failed to save critique to Qdrant: {e!s}'
            raise RuntimeError(msg) from e

        except Exception as e:
            self.logger.exception('Unexpected error saving critique for %s', filename)
            msg = f'Unexpected error in save_critique: {e!s}'
            raise RuntimeError(msg) from e
        else:
            return point_id

    @staticmethod
    def _normalize_point_id(point_id: str) -> int | str:
        """Qdrant accepts int or UUID/str; normalize numeric strings to int."""
        try:
            return int(point_id) if point_id.isdigit() else point_id
        except ValueError:
            return point_id

    def delete_points_by_ids(self, point_ids: list[str]) -> None:
        """Remove points by id (idempotent if already absent)."""
        ids: list[int | str] = []
        for pid in point_ids:
            if not pid:
                continue
            ids.append(self._normalize_point_id(pid))
        if not ids:
            return
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=ids),
            )
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Qdrant error deleting points')
            msg = f'Failed to delete points from Qdrant: {e!s}'
            raise RuntimeError(msg) from e

    def upsert_critique_with_stable_id(  # noqa: PLR0913
        self,
        point_id: str,
        critique: ArtCritique,
        filename: str,
        user_id: str,
        image_path: str | None,
        critique_id: str,
    ) -> None:
        """Upsert a critique point using a stable id (Postgres ``critiques.id``). Idempotent."""
        self._validate_critique(critique)
        text_for_embedding = critique.get_text_for_embedding()
        embeddings_list = list(self.embedding_model.embed(text_for_embedding))
        embedding_vector = embeddings_list[0].tolist()
        payload = critique.to_payload(filename=filename, user_id=user_id)
        payload['image_path'] = image_path
        payload['critique_id'] = critique_id
        payload['portfolio_item_id'] = None
        qid = self._normalize_point_id(point_id)
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=qid, vector=embedding_vector, payload=payload)],
            )
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Qdrant error upserting critique id=%s', critique_id)
            msg = f'Failed to upsert critique in Qdrant: {e!s}'
            raise RuntimeError(msg) from e

    def upsert_portfolio_with_stable_id(
        self,
        point_id: str,
        record: PortfolioRecord,
        portfolio_item_id: str,
    ) -> None:
        """Upsert a portfolio item using a stable id (Postgres ``portfolio_items.id``). Idempotent."""  # noqa: E501
        text = record.get_text_for_embedding()
        embeddings_list = list(self.embedding_model.embed(text))
        embedding_vector = embeddings_list[0].tolist()
        payload = record.to_payload()
        payload['portfolio_item_id'] = portfolio_item_id
        payload['critique_id'] = None
        qid = self._normalize_point_id(point_id)
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=qid, vector=embedding_vector, payload=payload)],
            )
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Qdrant error upserting portfolio id=%s', portfolio_item_id)
            msg = f'Failed to upsert portfolio item in Qdrant: {e!s}'
            raise RuntimeError(msg) from e

    def search_similar_critiques(
        self,
        query_text: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar critiques in the vector database.

        Args:
            query_text: Text to search for similar critiques
            limit: Maximum number of results to return
            user_id: Unique identifier for the user to scope search results

        Returns:
            list[dict]: List of similar critiques with scores

        Raises:
            RuntimeError: If search fails
        """
        try:
            # Generate embedding for query
            query_embedding = next(iter(self.embedding_model.embed(query_text))).tolist()

            # Search only critique points and exclude portfolio_item for RAG context
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key='user_id',
                        match=models.MatchValue(value=user_id),
                    ),
                    models.FieldCondition(
                        key='type',
                        match=models.MatchValue(value=PAYLOAD_TYPE_CRITIQUE),
                    ),
                ]
            )
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                query_filter=query_filter,
            )

            results = [
                {
                    'similarity_score': point.score,
                    'filename': point.payload.get('filename'),
                    'score': point.payload.get('score'),
                    'summary': point.payload.get('summary'),
                    'advice': point.payload.get('advice'),
                    'timestamp': point.payload.get('timestamp'),
                    'user_id': point.payload.get('user_id'),
                }
                for point in response.points
            ]

            self.logger.debug('Found %d similar critiques for query', len(results))

        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Error searching critiques')
            msg = f'Failed to search critiques: {e!s}'
            raise RuntimeError(msg) from e
        else:
            return results

    def save_portfolio_items(
        self,
        user_id: str,
        items: list[PortfolioRecord],
    ) -> list[str]:
        """Save multiple portfolio items to the vector database (bulk upsert).

        Each item gets a unique point ID (uuid4). Embeddings are generated from
        description + tags (or filename if no description).

        Args:
            user_id: Owner user id
            items: List of PortfolioRecord instances

        Returns:
            List of point IDs (uuid strings) in the same order as items

        Raises:
            RuntimeError: If Qdrant operations fail
        """
        if not items:
            return []

        point_ids: list[str] = []
        points_batch: list[PointStruct] = []

        for item in items:
            point_id = str(uuid4())
            point_ids.append(point_id)
            text = item.get_text_for_embedding()
            embeddings_list = list(self.embedding_model.embed(text))
            embedding_vector = embeddings_list[0].tolist()
            payload = item.to_payload()
            points_batch.append(PointStruct(id=point_id, vector=embedding_vector, payload=payload))

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points_batch,
            )
            self.logger.info(
                'Saved %d portfolio items to Qdrant for user_id=%s',
                len(points_batch),
                user_id,
            )
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Qdrant error saving portfolio items for user_id=%s', user_id)
            msg = f'Failed to save portfolio items: {e!s}'
            raise RuntimeError(msg) from e

        return point_ids

    @staticmethod
    def _normalize_type_filter(type_filter: str | None) -> str | None:
        if type_filter is None:
            return None
        if type_filter not in {PAYLOAD_TYPE_CRITIQUE, PAYLOAD_TYPE_PORTFOLIO_ITEM}:
            msg = (
                'Invalid type filter. Expected one of: '
                f'{PAYLOAD_TYPE_CRITIQUE}, {PAYLOAD_TYPE_PORTFOLIO_ITEM}.'
            )
            raise ValueError(msg)
        return type_filter

    @staticmethod
    def _payload_matches_user_and_type(
        payload: dict[str, Any],
        *,
        user_id: str,
        type_filter: str | None,
    ) -> bool:
        payload_type = payload.get('type')
        if payload.get('user_id') != user_id:
            return False
        if payload_type not in {PAYLOAD_TYPE_CRITIQUE, PAYLOAD_TYPE_PORTFOLIO_ITEM}:
            return False
        return not (type_filter is not None and payload_type != type_filter)

    def search_user_history(
        self,
        user_id: str,
        limit: int = 100,
        type_filter: str | None = None,
        signed_url_resolver: Callable[[str], str | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve user's history (critiques and/or portfolio items) for dashboard.

        Points are scrolled with user_id filter, optionally filtered by payload type.
        Results are ordered by recency (newest first) based on timestamp in payload.

        Args:
            user_id: User to fetch history for
            limit: Maximum number of points to return
            type_filter: Optional 'critique' or 'portfolio_item' to filter by type
            signed_url_resolver: Optional callback to map image paths to signed URLs

        Returns:
            List of dicts with id, type, filename, timestamp, score (if critique),
            level_estimate, tags, and other payload fields

        Raises:
            RuntimeError: If scroll fails
        """
        normalized_type_filter = self._normalize_type_filter(type_filter)
        must = [
            models.FieldCondition(
                key='user_id',
                match=models.MatchValue(value=user_id),
            ),
        ]
        if normalized_type_filter is not None:
            must.append(
                models.FieldCondition(
                    key='type',
                    match=models.MatchValue(value=normalized_type_filter),
                )
            )
        scroll_filter = models.Filter(must=must)

        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            results: list[dict[str, Any]] = []
            for point in records:
                payload = point.payload or {}
                payload['id'] = str(point.id) if point.id is not None else None
                if not self._payload_matches_user_and_type(
                    payload,
                    user_id=user_id,
                    type_filter=normalized_type_filter,
                ):
                    continue
                image_path = payload.get('image_path')
                if signed_url_resolver is not None and isinstance(image_path, str) and image_path:
                    payload['image_url'] = signed_url_resolver(image_path)
                results.append(payload)

            # Sort by timestamp descending (newest first)
            results.sort(
                key=lambda r: r.get('timestamp') or '',
                reverse=True,
            )
            if limit > 0:
                results = results[:limit]

            self.logger.debug('Retrieved %d history records for user_id=%s', len(results), user_id)
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Error scrolling user history for user_id=%s', user_id)
            msg = f'Failed to retrieve user history: {e!s}'
            raise RuntimeError(msg) from e
        else:
            return results

    def get_point_by_id(
        self,
        point_id: str,
        user_id: str,
        type_filter: str | None = None,
        signed_url_resolver: Callable[[str], str | None] | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a single point by ID (for GET /portfolio/item/{id}).

        Args:
            point_id: Qdrant point ID (string or numeric string)
            user_id: Owner user id to enforce tenant isolation
            type_filter: Optional type discriminator ('critique' or 'portfolio_item')
            signed_url_resolver: Optional callback to map image paths to signed URLs

        Returns:
            Payload dict with id added, or None if not found
        """
        normalized_type_filter = self._normalize_type_filter(type_filter)
        try:
            # Qdrant accepts int or str; keep as string for UUIDs
            try:
                id_val: int | str = int(point_id) if point_id.isdigit() else point_id
            except ValueError:
                id_val = point_id
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id_val],
                with_payload=True,
                with_vectors=False,
            )
        except (ResponseHandlingException, UnexpectedResponse):
            return None
        else:
            if not result:
                return None
            point = result[0]
            payload = dict(point.payload or {})
            if not self._payload_matches_user_and_type(
                payload,
                user_id=user_id,
                type_filter=normalized_type_filter,
            ):
                return None
            payload['id'] = str(point.id)
            image_path = payload.get('image_path')
            if signed_url_resolver is not None and isinstance(image_path, str) and image_path:
                payload['image_url'] = signed_url_resolver(image_path)
            return payload

    def health_check(self) -> bool:
        """Check if Qdrant connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            self.client.get_collections()
        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.warning('Health check failed: %s', e)
            return False
        else:
            return True
