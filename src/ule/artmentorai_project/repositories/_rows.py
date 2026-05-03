"""Helpers to normalize Supabase/PostgREST row payloads into Pydantic models."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def as_model(model: type[T], row: dict[str, Any] | object) -> T:
    """Parse a single mapping into ``model``."""
    if not isinstance(row, dict):
        msg = 'Supabase row must be a mapping.'
        raise TypeError(msg)
    return model.model_validate(row)


def as_model_list(model: type[T], rows: list[dict[str, Any]] | object | None) -> list[T]:
    """Parse a list of mappings into ``model`` instances."""
    if rows is None:
        return []
    if not isinstance(rows, list):
        msg = 'Supabase data must be a list of mappings.'
        raise TypeError(msg)
    return [model.model_validate(r) for r in rows if isinstance(r, dict)]


def postgrest_returned_rows(data: Any) -> bool:
    """True when PostgREST ``execute().data`` indicates at least one row in the response."""
    if isinstance(data, list):
        return len(data) > 0
    return data is not None


def single_row_dict(data: Any) -> dict[str, Any]:
    """Return the single dict from a PostgREST insert/select response."""
    if data is None:
        msg = 'Expected one row from Supabase but response data was empty.'
        raise RuntimeError(msg)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        if len(data) != 1:
            msg = f'Expected exactly one Supabase row, got {len(data)}.'
            raise RuntimeError(msg)
        row = data[0]
        if not isinstance(row, dict):
            msg = 'Supabase row payload was not an object.'
            raise TypeError(msg)
        return row
    msg = 'Unexpected Supabase response shape.'
    raise TypeError(msg)
