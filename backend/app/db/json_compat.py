"""
json_compat.py

Single reusable helper for PostgreSQL JSONB extraction compatibility.
Replaces SQLite's json_extract() with Python-level array/object access.

PostgreSQL/psycopg2 automatically deserializes JSONB columns to Python dicts/lists.
This module provides a uniform interface for extracting JSON values post-query.
"""

from __future__ import annotations
from typing import Any, Sequence


def extract_json_array_element(row: dict, column: str, index: int = 0) -> Any:
    """
    Extract element at `index` from a JSON array column.
    
    Args:
        row: Query result row (dict-like)
        column: Name of the JSON/JSONB column
        index: Array index to extract (default 0)
    
    Returns:
        The extracted value, or None if column is None/missing/not a list
    
    Example:
        # SQLite: json_extract(source_document_ids_json, '$[0]')
        # Becomes: extract_json_array_element(row, 'source_document_ids_json', 0)
    """
    value = row.get(column)
    if value is None:
        return None
    
    # psycopg2 with RealDictCursor auto-deserializes JSONB to Python types
    if isinstance(value, str):
        import json
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    
    if isinstance(value, list) and 0 <= index < len(value):
        return value[index]
    
    return None


def extract_json_path(row: dict, column: str, path: Sequence[str | int]) -> Any:
    """
    Extract nested value from JSON column using path sequence.
    
    Args:
        row: Query result row (dict-like)
        column: Name of the JSON/JSONB column
        path: Sequence of keys/indices to traverse
    
    Returns:
        The extracted value, or None if path doesn't exist
    
    Example:
        # SQLite: json_extract(config_json, '$.process')
        # Becomes: extract_json_path(row, 'config_json', ['process'])
    """
    value = row.get(column)
    if value is None:
        return None
    
    if isinstance(value, str):
        import json
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    
    for key in path:
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and isinstance(key, int) and 0 <= key < len(value):
            value = value[key]
        else:
            return None
    
    return value


def extract_json_field(row: dict, column: str, path: int | str | Sequence[str | int] = 0) -> Any:
    """
    Unified extractor for JSON/JSONB fields from a query row.
    Supports index (e.g. 0), single key (e.g. 'process'), or nested path (e.g. ['process']).
    """
    if isinstance(path, int):
        return extract_json_array_element(row, column, path)
    if isinstance(path, str):
        path = [path]
    return extract_json_path(row, column, path)
