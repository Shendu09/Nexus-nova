"""Helper utilities for novaml."""

from __future__ import annotations
import re
from typing import Any


def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to max length."""
    return text[:max_length] if len(text) > max_length else text


def normalize_log_line(line: str) -> str:
    """Normalize a log line for consistent processing."""
    # Remove ANSI color codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    line = ansi_escape.sub('', line)
    # Strip whitespace
    line = line.strip()
    return line


def extract_timestamp(line: str) -> str | None:
    """Extract ISO timestamp from log line."""
    pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    match = re.search(pattern, line)
    return match.group(0) if match else None


def extract_level(line: str) -> str | None:
    """Extract log level from line."""
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL"]
    line_upper = line.upper()
    for level in levels:
        if level in line_upper:
            return level
    return None


def batch_list(items: list, batch_size: int) -> list[list]:
    """Batch a list into chunks."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Merge two dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result
