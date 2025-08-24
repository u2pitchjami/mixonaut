#!/usr/bin/env python3
"""2025-08-20 - scripts de managements des torrents."""

from __future__ import annotations

import argparse
from typing import Any, Literal, Protocol, cast

from mixonaut.db.access import execute_write, select_all
from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.beets.path_resolve import resolve_album_path_and_rel
from mixonaut.utils.logger import (
    LoggerProtocol,
    ensure_logger,
    get_logger,
    with_child_logger,
)

LOG = get_logger("manage_decisions")

ALLOWED = {
    "PENDING",
    "ACCEPT",
    "REJECT",
    "DUPLICATE_SOFT",
    "DUPLICATE_HARD",
    "NEEDS_MANUAL",
    "REPLACED",
}


# ——— Types structuraux (mypy) ———
class _BaseArgs(Protocol):
    cmd: Literal["show", "mark", "unset"]


class ShowArgs(_BaseArgs, Protocol):
    cmd: Literal["show"]
    limit: int
    only: str | None


class HashArgs(Protocol):
    hash: list[str] | None
    name: list[str] | None
    path: list[str] | None


class MarkArgs(_BaseArgs, HashArgs, Protocol):
    cmd: Literal["mark"]
    decision: str
    reason: str
    decided_by: str


class UnsetArgs(_BaseArgs, HashArgs, Protocol):
    cmd: Literal["unset"]


@with_child_logger
def _find_hashes_by_name(
    torrent_name: str, logger: LoggerProtocol | None = None
) -> list[str]:
    logger = ensure_logger(logger, __name__)
    rows = (
        select_all(
            "SELECT DISTINCT torrent_hash FROM imported_files WHERE torrent_name = ?",
            (torrent_name,),
            logger=logger,
        )
        or []
    )
    return [r[0] for (r,) in rows]


@with_child_logger
def _find_hashes_by_album_path(
    path: str, logger: LoggerProtocol | None = None
) -> list[str]:
    logger = ensure_logger(logger, __name__)
    resolved = resolve_album_path_and_rel(path)
    if not resolved:
        logger.warning("Chemin non résolvable (hors /imports/): %s", path)
        return []
    _, rel_dir = resolved
    rows = (
        select_all(
            "SELECT DISTINCT torrent_hash FROM imported_files WHERE album_rel_dir = ?",
            (rel_dir,),
            logger=logger,
        )
        or []
    )
    return [r[0] for (r,) in rows]


@with_child_logger
def cmd_mark(
    decision: str,
    reason: str,
    hashes: list[str],
    decided_by: str = "user",
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Marks decisions on one or more hashes.

    Decision to make:
    - PENDING: No action taken yet.
    - ACCEPT: The file is accepted.
    - REJECT: The file is rejected.
    - DUPLICATE_SOFT: The file is marked for soft duplicate removal.
    - DUPLICATE_HARD: The file is marked for hard duplicate removal.
    - NEEDS_MANUAL: Further action required.
    - REPLACED: The file was replaced by another version.

    Args:
        decision (str): The decision to make on the hashes.
        reason (str): A description of why this decision is being made.
        hashes (list[str]): A list of hashes to apply the decision to.
        decided_by (str, optional): Who applied the decision. Defaults to "user".

    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    repo = TorrentRepo(logger=logger)
    for h in hashes:
        repo.set_decision(h, decision=decision, reason=reason, decided_by=decided_by)
        logger.info(
            "✅ Decision %s posée pour hash=%s (reason=%s)", decision, h, reason
        )


@with_child_logger
def cmd_unset(hashes: list[str], logger: LoggerProtocol | None = None) -> None:
    """
    Unset decisions for a list of hashes.

    This command will remove the decisions for each hash in the provided list from the database.

    Parameters
    ----------
    hashes : list[str]
        A list of hashes for which to unset decisions.
    logger : Logger, optional
        The logger to use for logging messages. Defaults to None.

    Returns
    -------
    None
    """
    logger = ensure_logger(logger, __name__)
    for h in hashes:
        execute_write(
            "DELETE FROM torrent_decisions WHERE torrent_hash = ?", (h,), logger=logger
        )
        logger.info("↩️ Decision effacée pour hash=%s", h)


@with_child_logger
def cmd_show(
    limit: int, only: str | None, logger: LoggerProtocol | None = None
) -> None:
    """
    Displays information about the decisions made on torrents.

    Args:
        limit (int): The maximum number of rows to display.
        only (str | None): If specified, displays only decisions matching this value.
            Can be one of 'PENDING', 'ACCEPT', 'REJECT', or any other allowed decision.
            If None, all decisions are displayed.
        logger (Logger | Optional[None]): The logger to use for logging messages.

    Returns:
        None
    """
    logger = ensure_logger(logger, __name__)
    where = ""
    params: tuple[Any, ...] = (limit,)
    if only:
        where = "WHERE ts.decision = ?"
        params = (only, limit)
    rows = (
        select_all(
            f"""
            SELECT ts.torrent_hash, ts.torrent_name, ts.decision, ts.decided_at, ts.ratio, ts.age_days
            FROM v_torrent_status ts
            {where}
            ORDER BY (ts.decided_at IS NULL) ASC, ts.decided_at DESC, ts.torrent_name
            LIMIT ?
            """,
            params,
            logger=logger,
        )
        or []
    )
    if not rows:
        logger.info("Aucune entrée.")
        return
    for h, n, d, at, r, age in rows:
        logger.info(
            "%s | %s | %s | decided=%s | ratio=%.2f | age=%.1f j",
            h,
            n,
            d,
            at,
            (r or 0.0),
            (age or 0.0),
        )


@with_child_logger
def _collect_hashes(args: HashArgs, logger: LoggerProtocol | None = None) -> list[str]:
    """
    Résout la cible en liste de hashes selon les options fournies.
    """
    logger = ensure_logger(logger, __name__)
    hashes: list[str] = []
    if args.hash:
        hashes.extend(args.hash)
    if args.name:
        for n in args.name:
            hashes.extend(_find_hashes_by_name(n, logger))
    if args.path:
        for p in args.path:
            hashes.extend(_find_hashes_by_album_path(p, logger))
    # dédoublonnage simple
    return sorted(set(hashes))


def main() -> None:
    """
    CLI pour marquer/afficher/retirer des décisions sur des torrents (hash/name/path).
    """
    parser = argparse.ArgumentParser(
        description="Marquer des décisions sur des torrents (hash/name/path)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # show
    p_show = sub.add_parser("show", help="Afficher l'état/les décisions")
    p_show.add_argument(
        "--limit", type=int, default=50, help="Nb max de lignes (défaut: 50)"
    )
    p_show.add_argument(
        "--only",
        type=str,
        choices=sorted(ALLOWED),
        help=f"Filtrer par décision ({', '.join(sorted(ALLOWED))})",
    )

    # mark
    p_mark = sub.add_parser("mark", help="Poser une décision sur des torrents")
    p_mark.add_argument(
        "--decision",
        type=str,
        required=True,
        choices=sorted(ALLOWED),
        help=f"Décision ({', '.join(sorted(ALLOWED))})",
    )
    p_mark.add_argument(
        "--reason", type=str, default="", help="Raison/mémo (optionnel)"
    )
    p_mark.add_argument(
        "--decided-by",
        dest="decided_by",
        type=str,
        default="user",
        help="Auteur (défaut: user)",
    )
    p_mark.add_argument("--hash", nargs="+", help="Un ou plusieurs hash")
    p_mark.add_argument(
        "--name", nargs="+", help="Un ou plusieurs noms de torrent (résolus en hash)"
    )
    p_mark.add_argument(
        "--path", nargs="+", help="Un ou plusieurs chemins (résolus en hash)"
    )

    # unset
    p_unset = sub.add_parser("unset", help="Effacer la décision pour des torrents")
    p_unset.add_argument("--hash", nargs="+", help="Un ou plusieurs hash")
    p_unset.add_argument(
        "--name", nargs="+", help="Un ou plusieurs noms de torrent (résolus en hash)"
    )
    p_unset.add_argument(
        "--path", nargs="+", help="Un ou plusieurs chemins (résolus en hash)"
    )

    args = parser.parse_args()

    if args.cmd == "show":
        a = cast(ShowArgs, args)
        cmd_show(limit=a.limit, only=a.only, logger=LOG)
        return

    # mark / unset → collecter les hashes (au moins une cible)
    h = cast(HashArgs, args)
    hashes = _collect_hashes(h, logger=LOG)
    if not hashes:
        LOG.error("Aucun hash résolu depuis --hash/--name/--path.")
        return

    if args.cmd == "mark":
        m = cast(MarkArgs, args)
        cmd_mark(
            decision=m.decision,
            reason=m.reason,
            hashes=hashes,
            decided_by=m.decided_by,
            logger=LOG,
        )
    else:  # "unset"
        cmd_unset(hashes=hashes, logger=LOG)


if __name__ == "__main__":
    main()
