"""Unit tests for repository row-shape helper functions."""

from __future__ import annotations

import pytest

from ule.artmentorai_project.repositories._rows import single_row_dict


def test_single_row_dict_rejects_multi_row_payload_shape() -> None:
    """Row-shape helper should reject insert/select payloads with multiple rows."""
    with pytest.raises(RuntimeError, match='Expected exactly one Supabase row, got 2'):
        single_row_dict([{'id': 1}, {'id': 2}])
