# process_imports/beets_log_parser.py
"""
2020-08-20 module de traitemment de parsing du log beets.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from mixonaut.utils.config import DUP_PREFIX, MOVED_PREFIX, SKIP_PREFIX

_SEP_SPLIT = re.compile(r"\s*;\s*")  # sépare "a; b; c" proprement


def _paths_from_line_after_prefix(line: str, prefix: str) -> list[str]:
    """
    Extrait une ou plusieurs paths après 'duplicate-skip ' ou 'skip '.

    Gère les cas: une path, ou 'path1; path2; path3'.
    """
    payload = line[len(prefix) :].strip()
    # Beets écrit des chemins d'albums (dossiers). S'il y en a plusieurs → séparés par ';'
    parts = [p for p in _SEP_SPLIT.split(payload) if p]
    return parts


def parse_beets_log(lines: Iterable[str]) -> tuple[list[str], list[str], list[str]]:
    """
    Retourne (skipped_paths, duplicate_paths, moved_paths) — tous en chemins **conteneur**.
    """
    skipped: list[str] = []
    duplicates: list[str] = []
    moved: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if line.startswith(SKIP_PREFIX):
            skipped.extend(_paths_from_line_after_prefix(line, SKIP_PREFIX))
        elif line.startswith(DUP_PREFIX):
            duplicates.extend(_paths_from_line_after_prefix(line, DUP_PREFIX))
        elif line.startswith(MOVED_PREFIX):
            # Format: [MOVED]|||<album/track info>|||<dest>|||<source>|||<meta...>
            parts = line.split("|||")
            if len(parts) >= 4:
                source_path = parts[3].strip()
                moved.append(source_path)

    return skipped, duplicates, moved
