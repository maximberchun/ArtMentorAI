"""Unit tests for vector service core behaviors."""

from __future__ import annotations

import logging

import pytest

from ule.artmentorai_project.services.vector_service import ArtCritique, VectorService, _score_to_level_estimate


class _FakeEmbedding:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


class _FakeEmbeddingModel:
    def embed(self, _text: str):
        yield _FakeEmbedding([0.1, 0.2, 0.3])


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.last_upsert_payload = None

    def upsert(self, *, collection_name: str, points: list) -> None:
        self.last_upsert_payload = {
            'collection_name': collection_name,
            'points': points,
        }


def _build_service() -> VectorService:
    service = VectorService.__new__(VectorService)
    service.logger = logging.getLogger('tests.vector_service')
    service.collection_name = 'test_collection'
    service.embedding_model = _FakeEmbeddingModel()
    service.client = _FakeQdrantClient()
    return service


@pytest.mark.parametrize(
    ('score', 'expected'),
    [
        (1, 1),
        (2, 1),
        (3, 2),
        (5, 3),
        (8, 4),
        (10, 5),
    ],
)
def test_score_to_level_estimate_mapping(score: int, expected: int) -> None:
    """Score buckets should map to expected skill levels."""
    assert _score_to_level_estimate(score) == expected


def test_validate_critique_rejects_non_list_errors() -> None:
    """Validation should reject critiques with non-list technical errors."""
    service = _build_service()
    critique = ArtCritique(
        summary='Solid composition but weak anatomy',
        score=6,
        technical_errors=['line quality'],
        constructive_advice='Practice gesture drawing daily to improve flow and anatomy.',
    )
    critique.technical_errors = 'not-a-list'

    with pytest.raises(TypeError, match='technical_errors must be a list'):
        service._validate_critique(critique)


def test_save_critique_returns_point_id_and_sends_payload() -> None:
    """Saving a valid critique should upsert to Qdrant and return the point id."""
    service = _build_service()
    critique = ArtCritique(
        summary='Good silhouette and readable gesture',
        score=7,
        technical_errors=['foreshortening inconsistency'],
        constructive_advice='Use box primitives to anchor limbs before rendering details.',
    )

    point_id = service.save_critique(
        critique=critique,
        filename='study.png',
        user_id='user-1',
        image_path='images/study.png',
    )

    assert isinstance(point_id, str)
    assert point_id
    assert service.client.last_upsert_payload is not None
    assert service.client.last_upsert_payload['collection_name'] == 'test_collection'


def test_save_critique_wraps_unexpected_client_failures() -> None:
    """Unexpected client exceptions should be normalized to RuntimeError."""

    class _FailingClient(_FakeQdrantClient):
        def upsert(self, *, collection_name: str, points: list) -> None:
            raise ValueError('boom')

    service = _build_service()
    service.client = _FailingClient()
    critique = ArtCritique(
        summary='Strong value grouping but perspective drift',
        score=5,
        technical_errors=['horizon mismatch'],
        constructive_advice='Block perspective lines and check against one horizon.',
    )

    with pytest.raises(RuntimeError, match='Unexpected error in save_critique'):
        service.save_critique(
            critique=critique,
            filename='perspective.png',
            user_id='user-2',
        )
