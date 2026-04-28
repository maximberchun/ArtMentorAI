"""Unit tests for vector sync job repository boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from ule.artmentorai_project.repositories.vector_sync_job_repository import (
    VectorSyncJobRepository,
)


def test_vector_sync_try_claim_returns_none_when_no_pending_row_updated() -> None:
    """Claim should return None when another worker has already claimed the job."""
    client = MagicMock()
    repo = VectorSyncJobRepository(client)
    (
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value
    ) = SimpleNamespace(data=[])

    result = repo.try_claim('job-1')

    assert result is None


def test_vector_sync_try_claim_returns_job_on_successful_claim() -> None:
    """Claim should return parsed job row when update+fetch both succeed."""
    client = MagicMock()
    repo = VectorSyncJobRepository(client)
    update_chain = client.table.return_value.update.return_value.eq.return_value.eq.return_value
    update_chain.execute.return_value = SimpleNamespace(data=[{'id': 'job-1'}])
    (
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value
    ) = SimpleNamespace(
        data=[
            {
                'id': 'job-1',
                'entity_kind': 'critique',
                'entity_id': 'crit-1',
                'operation': 'upsert',
                'status': 'processing',
            }
        ]
    )

    claimed = repo.try_claim('job-1')

    assert claimed is not None
    assert claimed.id == 'job-1'
    assert claimed.status == 'processing'
