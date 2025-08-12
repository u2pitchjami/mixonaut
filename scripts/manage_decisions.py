#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Optional

from utils.logger import get_logger, with_child_logger
from db.access import select_all, execute_write
from db.torrent_repo import TorrentRepo
from logic_imports.path_resolve import resolve_album_path_and_rel  # déjà fourni plus haut

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

def _find_hashes_by_name(torrent_name: str, logger) -> list[str]:
    rows = select_all(
        "SELECT DISTINCT torrent_hash FROM imported_files WHERE torrent_name = ?",
        (torrent_name,), logger=logger
    ) or []
    return [r[0] for (r,) in rows]

def _find_hashes_by_album_path(path: str, logger) -> list[str]:
    resolved = resolve_album_path_and_rel(path)
    if not resolved:
        logger.warning("Chemin non résolvable (hors /imports/): %s", path)
        return []
    _, rel_dir = resolved
    rows = select_all(
        "SELECT DISTINCT torrent_hash FROM imported_files WHERE album_rel_dir = ?",
        (rel_dir,), logger=logger
    ) or []
    return [r[0] for (r,) in rows]

@with_child_logger
def cmd_mark(decision: str,
             reason: str,
             hashes: list[str],
             decided_by: str = "user",
             logger=None) -> None:
    repo = TorrentRepo(logger=logger)
    for h in hashes:
        repo.set_decision(h, decision=decision, reason=reason, decided_by=decided_by)
        logger.info("✅ Decision %s posée pour hash=%s (reason=%s)", decision, h, reason)

@with_child_logger
def cmd_unset(hashes: list[str], logger=None) -> None:
    for h in hashes:
        execute_write("DELETE FROM torrent_decisions WHERE torrent_hash = ?", (h,), logger=logger)
        logger.info("↩️ Decision effacée pour hash=%s", h)

@with_child_logger
def cmd_show(limit: int, only: Optional[str], logger=None) -> None:
    where = ""
    params: tuple = (limit,)
    if only:
        where = "WHERE ts.decision = ?"
        params = (only, limit)
    rows = select_all(
        f"""
        SELECT ts.torrent_hash, ts.torrent_name, ts.decision, ts.decided_at, ts.ratio, ts.age_days
        FROM v_torrent_status ts
        {where}
        ORDER BY ts.decided_at DESC NULLS LAST, ts.torrent_name
        LIMIT ?
        """,
        params, logger=logger
    ) or []
    if not rows:
        logger.info("Aucune entrée.")
        return
    for h, n, d, at, r, age in rows:
        logger.info("%s | %s | %s | decided=%s | ratio=%.2f | age=%.1f j", h, n, d, at, (r or 0.0), (age or 0.0))

def _collect_hashes(args, logger) -> list[str]:
    """Résout la cible en liste de hashes selon les options fournies."""
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
    parser = argparse.ArgumentParser(description="Marquer des décisions sur des torrents (hash/name/path).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # mark
    p_mark = sub.add_parser("mark", help="Poser une décision")
    p_mark.add_argument("--decision", required=True, choices=sorted(ALLOWED), help="Décision à poser")
    p_mark.add_argument("--reason", default="", help="Raison (texte libre)")
    p_mark.add_argument("--by", dest="decided_by", default="user", help="Auteur de la décision")
    p_mark.add_argument("--hash", nargs="*", help="Un ou plusieurs torrent_hash")
    p_mark.add_argument("--name", nargs="*", help="Un ou plusieurs torrent_name qBit")
    p_mark.add_argument("--path", nargs="*", help="Un ou plusieurs chemins album (host ou /app/imports/...)")

    # unset
    p_unset = sub.add_parser("unset", help="Effacer la décision (revenir à PENDING)")
    p_unset.add_argument("--hash", nargs="*", help="Un ou plusieurs torrent_hash")
    p_unset.add_argument("--name", nargs="*", help="Un ou plusieurs torrent_name qBit")
    p_unset.add_argument("--path", nargs="*", help="Un ou plusieurs chemins album (host ou /app/imports/...)")

    # show
    p_show = sub.add_parser("show", help="Lister les décisions récentes")
    p_show.add_argument("--limit", type=int, default=50)
    p_show.add_argument("--only", choices=sorted(ALLOWED), help="Filtrer par décision spécifique")

    args = parser.parse_args()

    if args.cmd == "show":
        cmd_show(limit=args.limit, only=args.only, logger=LOG)
        return

    # mark / unset → collecter les hashes
    hashes = _collect_hashes(args, logger=LOG)
    if not hashes:
        LOG.error("Aucun hash résolu depuis --hash/--name/--path.")
        return

    if args.cmd == "mark":
        cmd_mark(decision=args.decision, reason=args.reason, hashes=hashes, decided_by=args.decided_by, logger=LOG)
    elif args.cmd == "unset":
        cmd_unset(hashes=hashes, logger=LOG)

if __name__ == "__main__":
    main()
