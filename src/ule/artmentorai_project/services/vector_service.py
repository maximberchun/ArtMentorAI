"""Vector Database service for storing and retrieving artwork critiques.

This module provides long-term memory capabilities using Qdrant vector database
and FastEmbed for local embedding generation.
"""

import logging
from datetime import UTC, datetime

from fastembed.embedding import FlagEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from ..models import AnalysisResponse


class ArtCritique:
    """Data model for storing artwork critiques in vector database."""

    def __init__(
        self,
        summary: str,
        score: int,
        technical_errors: list[str],
        constructive_advice: str,
    ) -> None:
        """Initialize an ArtCritique.

        Args:
            summary: Summary of the artwork analysis
            score: Score from 1-10
            technical_errors: List of identified technical errors
            constructive_advice: Constructive advice for improvement
        """
        self.summary = summary
        self.score = score
        self.technical_errors = technical_errors
        self.constructive_advice = constructive_advice
        self.timestamp = datetime.now(tz=UTC).isoformat()

    def get_text_for_embedding(self) -> str:
        """Get concatenated text for embedding generation.

        Returns:
            str: Combined text of summary and technical errors
        """
        errors_text = ' '.join(self.technical_errors)
        return f'{self.summary} {errors_text}'

    @classmethod
    def from_analysis_response(
        cls,
        response: AnalysisResponse,
    ) -> 'ArtCritique':
        """Create ArtCritique from AnalysisResponse.

        Args:
            response: AnalysisResponse from Gemini

        Returns:
            ArtCritique: Initialized critique object
        """
        return cls(
            summary=response.summary,
            score=response.score,
            technical_errors=response.technical_errors,
            constructive_advice=response.constructive_advice,
        )


class VectorService:
    """Service for managing vector embeddings and Qdrant interactions.

    Handles:
    - Connection to Qdrant vector database
    - Embedding generation using FastEmbed
    - CRUD operations for artwork critiques
    - Collection management
    """

    COLLECTION_NAME = 'art_portfolio'
    EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
    EMBEDDING_SIZE = 384
    DISTANCE_METRIC = Distance.COSINE

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6333,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize VectorService.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            logger: Logger instance for debug info

        Raises:
            RuntimeError: If Qdrant connection fails
        """
        self.logger = logger or logging.getLogger(__name__)
        self.host = host
        self.port = port

        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                host=host,
                port=port,
                timeout=10.0,
            )
            self.logger.debug('Connected to Qdrant at %s:%s', host, port)

            # Initialize embedding model (downloads on first use)
            self.embedding_model = FlagEmbedding(
                model_name=self.EMBEDDING_MODEL,
                cache_folder='./embeddings_cache',
            )
            self.logger.debug('Loaded embedding model: %s', self.EMBEDDING_MODEL)

            # Ensure collection exists
            self._ensure_collection_exists()
            self.logger.info('VectorService initialized with collection: %s', self.COLLECTION_NAME)

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

            if self.COLLECTION_NAME not in collection_names:
                self.logger.info('Creating collection: %s', self.COLLECTION_NAME)
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_SIZE,
                        distance=self.DISTANCE_METRIC,
                    ),
                )
                self.logger.info('Collection created: %s', self.COLLECTION_NAME)
            else:
                self.logger.debug('Collection already exists: %s', self.COLLECTION_NAME)

        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Failed to manage collection %s', self.COLLECTION_NAME)
            msg = f'Failed to manage collection {self.COLLECTION_NAME}: {e!s}'
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
    ) -> str | None:
        """Save artwork critique to vector database.

        Generates embeddings from critique text and stores in Qdrant
        with metadata about the analysis.

        Args:
            critique: ArtCritique object with analysis data
            filename: Name/ID of the artwork file

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
            self.logger.debug('Generating embedding for file: %s', filename)

            embeddings_generator = self.embedding_model.embed(text_for_embedding)
            embeddings_list = list(embeddings_generator)
            embedding_vector = embeddings_list[0].tolist()

            # Create point for Qdrant
            point_id = hash(filename) % (10**8)  # Generate consistent ID from filename

            payload = {
                'filename': filename,
                'score': critique.score,
                'summary': critique.summary,
                'advice': critique.constructive_advice,
                'timestamp': critique.timestamp,
            }

            # Upsert point to Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding_vector,
                        payload=payload,
                    )
                ],
            )

            self.logger.info('Critique saved to Qdrant: %s (point_id: %s)', filename, point_id)
            return str(point_id)

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

    def search_similar_critiques(
        self,
        query_text: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar critiques in the vector database.

        Args:
            query_text: Text to search for similar critiques
            limit: Maximum number of results to return

        Returns:
            list[dict]: List of similar critiques with scores

        Raises:
            RuntimeError: If search fails
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.embed(query_text).tolist()

            # Search in Qdrant
            search_results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
            )

            # Format results
            results = [
                {
                    'similarity_score': result.score,
                    'filename': result.payload.get('filename'),
                    'score': result.payload.get('score'),
                    'summary': result.payload.get('summary'),
                    'advice': result.payload.get('advice'),
                    'timestamp': result.payload.get('timestamp'),
                }
                for result in search_results
            ]

            self.logger.debug('Found %d similar critiques for query', len(results))

        except (ResponseHandlingException, UnexpectedResponse) as e:
            self.logger.exception('Error searching critiques')
            msg = f'Failed to search critiques: {e!s}'
            raise RuntimeError(msg) from e
        else:
            return results

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
