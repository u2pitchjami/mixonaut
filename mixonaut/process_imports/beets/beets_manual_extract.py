from __future__ import annotations
import os
import re
from utils.config import BEETS_LOGS, BEETS_MANUAL_LIST
from utils.logger import with_child_logger
from db.imports.torrent_repo import TorrentRepo
from db.access import select_all
from process_imports.beets.beets_log_parser import parse_beets_log  # ton parser déjà fourni plus haut
from process_imports.beets.path_resolve import resolve_album_path_and_rel  # helpers robustes

_SEP_SPLIT = re.compile(r"\s*;\s*")

@with_child_logger
def extract_manual_imports_and_decisions(logger=None):
    """
    - Parse le log Beets
    - Écrit BEETS_MANUAL_LIST (format Beets: /app/imports/...) avec une ligne par chemin
    - Pose des décisions DB (NEEDS_MANUAL / DUPLICATE_SOFT) via *host mapping* interne
    - Vide le log Beets
    - Retourne un dict {"skips":[host], "duplicates":[host], "moved":[host]}
    """
    if not os.path.isfile(BEETS_LOGS):
        logger.warning("Fichier log introuvable : %s", BEETS_LOGS)
        return {"skips": [], "duplicates": [], "moved": []}

    with open(BEETS_LOGS, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Chemins conteneur (/app/imports/...)
    skipped_c, duplicates_c, moved_c = parse_beets_log(lines)

    # Écriture MANUAL_LIST en *format Beets*
    entries = []
    for p in skipped_c:
        entries.append(f"[skip] {p}")
    for p in duplicates_c:
        entries.append(f"[duplicate] {p}")

    if entries:
        os.makedirs(os.path.dirname(BEETS_MANUAL_LIST), exist_ok=True)
        with open(BEETS_MANUAL_LIST, "a", encoding="utf-8") as out:
            for e in entries:
                out.write(e + "\n")
        # dédoublonnage
        with open(BEETS_MANUAL_LIST, "r", encoding="utf-8") as fin:
            uniq = sorted(set(line.strip() for line in fin if line.strip()))
        with open(BEETS_MANUAL_LIST, "w", encoding="utf-8") as fout:
            for line in uniq:
                fout.write(line + "\n")

    # Pose décisions DB via mapping conteneur -> host + rel (interne)
    repo = TorrentRepo(logger=logger)
    def _decide(container_paths, decision, reason):
        for p in container_paths:
            resolved = resolve_album_path_and_rel(p)  # renvoie (host_path, rel_dir) ou None
            if not resolved:
                logger.warning("Chemin Beets ignoré (hors /imports/): %s", p)
                continue
            _, rel_dir = resolved
            rows = select_all(
                "SELECT DISTINCT torrent_hash FROM imported_files WHERE album_rel_dir = ?",
                (rel_dir,), logger=logger
            ) or []
            for (thash,) in rows:
                repo.set_decision(thash, decision=decision, reason=reason, decided_by="auto")
                logger.info("Decision %s posée pour hash=%s (rel=%s)", decision, thash, rel_dir)

    _decide(skipped_c, "NEEDS_MANUAL", "beets:skip")
    _decide(duplicates_c, "DUPLICATE_SOFT", "beets:duplicate")

    # Pour l'appelant, on retourne des chemins *host* (process_successful_imports les accepte aussi)
    def _to_host_list(cont_list):
        out = []
        for p in cont_list:
            r = resolve_album_path_and_rel(p)
            if r:
                out.append(str(r[0]))
        return out

    skips_h = _to_host_list(skipped_c)
    duplicates_h = _to_host_list(duplicates_c)
    moved_h = _to_host_list(moved_c)

    # Vide le log
    open(BEETS_LOGS, "w", encoding="utf-8").close()

    logger.info("Beets: %d skip(s), %d duplicate(s), %d moved.", len(skips_h), len(duplicates_h), len(moved_h))
    return {"skips": skips_h, "duplicates": duplicates_h, "moved": moved_h}
