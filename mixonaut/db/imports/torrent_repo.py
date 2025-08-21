# db/torrent_repo.py
"""
Repository pour accéder/mettre à jour l'état des torrents/fichiers Mixonaut.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mixonaut.db.access import (
    execute_many,
    execute_write,
    select_all,
    select_one,
    select_scalar,
)


class TorrentState(str, Enum):
    """
    TorrentState enumeration represents the different states that a torrent can have.
    """

    UNKNOWN = "UNKNOWN"
    KNOWN_NOT_IMPORTED = "KNOWN_NOT_IMPORTED"
    IMPORTED = "IMPORTED"
    IMPORTED_AND_DELETED = "IMPORTED_AND_DELETED"


@dataclass(frozen=True)
class QbitFile:
    """
    Represents a file associated with a torrent in qBit.

    Attributes:
        path (str): The relative path of the file as reported by qBit.
        size (int): The size of the file in bytes.
    """

    path: str  # chemin relatif renvoyé par qBit
    size: int


class TorrentRepo:
    """
    Couche d'accès/écriture sur imported_files via db.access.
    """

    def __init__(self, logger):
        """
        Couche d'accès/écriture sur imported_files via db.access.
        """
        self.logger = logger

    # ---------- State ----------
    def get_state(self, torrent_hash: str) -> TorrentState:
        """
        Retourne l'état du torrent en DB sans requêter qBit.
        """
        total = int(
            select_scalar(
                "SELECT COUNT(*) FROM imported_files WHERE torrent_hash = ?",
                (torrent_hash,),
                logger=self.logger,
            )
            or 0
        )

        if total == 0:
            state = TorrentState.UNKNOWN
            self.logger.debug("State %s → %s (total=0)", torrent_hash, state)
            return state

        remaining = int(
            select_scalar(
                "SELECT COUNT(*) FROM imported_files WHERE torrent_hash = ? AND imported_in_beets_at IS NULL",
                (torrent_hash,),
                logger=self.logger,
            )
            or 0
        )

        if remaining > 0:
            state = TorrentState.KNOWN_NOT_IMPORTED
            self.logger.debug(
                "State %s → %s (remaining=%d)", torrent_hash, state, remaining
            )
            return state

        cleaned = int(
            select_scalar(
                "SELECT COUNT(*) FROM imported_files WHERE torrent_hash = ? AND auto_cleaned = 1",
                (torrent_hash,),
                logger=self.logger,
            )
            or 0
        )

        state = (
            TorrentState.IMPORTED_AND_DELETED if cleaned > 0 else TorrentState.IMPORTED
        )
        self.logger.debug("State %s → %s (cleaned=%d)", torrent_hash, state, cleaned)
        return state

    # ---------- Upserts ----------
    def upsert_file_row(
        self,
        *,
        torrent_hash: str,
        torrent_name: str,
        file_path: str,
        file_name: str,
        size: int,
        added_on: int | None,
        completion_on: int | None,
        ratio: float | None,
    ) -> None:
        """
        UPSERT d'une ligne fichier liée à un torrent (idempotent).
        """
        execute_write(
            """
            INSERT INTO imported_files (
                path, name, size, last_seen,
                torrent_hash, torrent_name, torrent_added_on, torrent_completion_on, torrent_ratio
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            ON CONFLICT(torrent_hash, path, name) DO UPDATE SET
                size = excluded.size,
                last_seen = CURRENT_TIMESTAMP,
                torrent_name = excluded.torrent_name,
                torrent_added_on = excluded.torrent_added_on,
                torrent_completion_on = excluded.torrent_completion_on,
                torrent_ratio = excluded.torrent_ratio,
                torrent_save_path = COALESCE(excluded.torrent_save_path, torrent_save_path)
            """,
            (
                file_path,
                file_name,
                int(size or 0),
                torrent_hash,
                torrent_name,
                added_on,
                completion_on,
                ratio,
            ),
            logger=self.logger,
        )

    def bulk_add_useful_files(
        self,
        *,
        torrent_hash: str,
        torrent_name: str,
        files: Iterable[QbitFile],
        added_on: int | None,
        completion_on: int | None,
        ratio: float | None,
        save_path: str | None,  # ← NOUVEAU
    ) -> int:
        """
        Ajoute plusieurs fichiers en un seul requête.

        :param files: Liste de QbitFile.
        :return: Nombre d'entités affectées.
        """
        values = []
        for fobj in files:
            fname = fobj.path.rsplit("/", 1)[-1]
            album_rel_dir = str(Path(fobj.path).parent).replace(
                "\\", "/"
            )  # parent(path)
            values.append(
                (
                    fobj.path,
                    fname,
                    int(fobj.size or 0),
                    torrent_hash,
                    torrent_name,
                    added_on,
                    completion_on,
                    ratio,
                    save_path,
                    album_rel_dir,
                )
            )

        query = """
        INSERT INTO imported_files (
            path, name, size, last_seen,
            torrent_hash, torrent_name, torrent_added_on, torrent_completion_on, torrent_ratio,
            torrent_save_path, album_rel_dir
        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(torrent_hash, path, name) DO UPDATE SET
            size = excluded.size,
            last_seen = CURRENT_TIMESTAMP,
            torrent_name = excluded.torrent_name,
            torrent_added_on = excluded.torrent_added_on,
            torrent_completion_on = excluded.torrent_completion_on,
            torrent_ratio = excluded.torrent_ratio,
            torrent_save_path = COALESCE(excluded.torrent_save_path, torrent_save_path),
            album_rel_dir = excluded.album_rel_dir
        """
        execute_many(query, values, logger=self.logger)
        self.logger.debug(
            "bulk_add_useful_files hash=%s → %d lignes", torrent_hash, len(values)
        )
        return len(values)

    # Sélection des fichiers à *stager* (non importés & non déjà stagés)
    def list_files_to_stage(self, limit: int) -> list[dict]:
        """
        Renvoie une liste de dictionnaires contenant les informations sur les fichiers qui doivent être stagers. Les
        fichiers sont triés par ordre croissant de leur date de fin de conversion (le plus récent en haut).

        :param limit: Nombre maximum de lignes à renvoyer.
        :return: Liste de dictionnaires contenant les informations sur les fichiers à stager.
        """
        rows = select_all(
            """
            SELECT id, torrent_hash, torrent_name, path, name, size, torrent_save_path
            FROM imported_files
            WHERE imported_in_beets_at IS NULL
              AND staged_for_import_at IS NULL
            ORDER BY torrent_completion_on DESC, id ASC
            LIMIT ?
            """,
            (limit,),
            logger=self.logger,
        )
        return [
            {
                "id": r[0],
                "torrent_hash": r[1],
                "torrent_name": r[2],
                "relpath": r[3],
                "name": r[4],
                "size": r[5],
                "save_path": r[6],  # peut être None si ancien enregistrement (on gère)
            }
            for r in rows or []
        ]

    def mark_staged_ok(self, file_id: int) -> None:
        """
        Marque un fichier comme étant *stager*.

        :param file_id: L'ID du fichier à marquer.
        """
        execute_write(
            "UPDATE imported_files SET staged_for_import_at=CURRENT_TIMESTAMP, staging_error=NULL WHERE id=?",
            (file_id,),
            logger=self.logger,
        )

    def mark_staged_error(self, file_id: int, err: str) -> None:
        """
        Mettre à jour le fichier dans DB en signalant une erreur de staging.
        """
        execute_write(
            "UPDATE imported_files SET staging_error=? WHERE id=?",
            (err[:400], file_id),
            logger=self.logger,
        )

    # ---------- Updates ----------
    def mark_imported_in_beets_by_hash(self, torrent_hash: str) -> int:
        """
        Marque importés tous les fichiers d'un torrent; retourne nb lignes MAJ.
        """
        updated = select_scalar(
            """
            SELECT COUNT(*) FROM imported_files
            WHERE torrent_hash = ? AND imported_in_beets_at IS NULL
            """,
            (torrent_hash,),
            logger=self.logger,
        )
        if not updated:
            self.logger.info(
                "Aucun fichier à marquer importé pour hash=%s", torrent_hash
            )
            return 0

        execute_write(
            """
            UPDATE imported_files
            SET imported_in_beets_at = CURRENT_TIMESTAMP
            WHERE torrent_hash = ? AND imported_in_beets_at IS NULL
            """,
            (torrent_hash,),
            logger=self.logger,
        )
        self.logger.info(
            "mark_imported_in_beets_by_hash hash=%s → %s", torrent_hash, updated
        )
        return int(updated or 0)

    def update_ratio_for_hash(self, torrent_hash: str, ratio: float) -> None:
        """
        Updated docstring for the method.

        Updates the ratio of a given torrent. If no matching row is found, an error will be raised.
        """
        execute_write(
            "UPDATE imported_files SET torrent_ratio = ? WHERE torrent_hash = ?",
            (ratio, torrent_hash),
            logger=self.logger,
        )

    # ---------- Queries utiles ----------
    def list_distinct_torrent_names_ready_for_deletion(
        self, min_ratio: float, min_age_days: int
    ) -> list[str]:
        """
        Retourne une liste de nom de torrents pour lesquels un rapport de téléchargement minimum a été atteint et l'âge
        minimum depuis la mise à jour du torrent est dépassé.
        """
        rows = select_one(
            """
            SELECT GROUP_CONCAT(DISTINCT torrent_name)
            FROM imported_files
            WHERE auto_cleaned = 0
              AND imported_in_beets_at IS NOT NULL
              AND (
                torrent_ratio >= ?
                OR (julianday('now') - julianday(datetime(torrent_added_on, 'unixepoch'))) >= ?
              )
            """,
            (min_ratio, min_age_days),
            logger=self.logger,
        )
        if not rows or not rows[0]:
            return []
        return rows[0].split(",")

    def mark_cleaned_by_name(self, torrent_name: str) -> None:
        """
        Marque un torrent comme nettoyé.
        """
        execute_write(
            "UPDATE imported_files SET auto_cleaned = 1 WHERE torrent_name = ?",
            (torrent_name,),
            logger=self.logger,
        )

    # Ajouts dans TorrentRepo
    def set_decision(
        self,
        torrent_hash: str,
        decision: str,
        reason: str = "",
        decided_by: str = "auto",
    ) -> None:
        """
        Inscrit la décision.
        """
        execute_write(
            """
            INSERT INTO torrent_decisions (torrent_hash, decision, reason, decided_by)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(torrent_hash) DO UPDATE SET
            decision=excluded.decision,
            reason=excluded.reason,
            decided_at=CURRENT_TIMESTAMP,
            decided_by=excluded.decided_by
            """,
            (torrent_hash, decision, reason, decided_by),
            logger=self.logger,
        )

    def get_decision(self, torrent_hash: str) -> str | None:
        """
        Renvoie la décision associée au hash du torrent.
        """
        row = select_one(
            "SELECT decision FROM torrent_decisions WHERE torrent_hash=?",
            (torrent_hash,),
            logger=self.logger,
        )
        return row[0] if row else None

    def list_for_cleanup(
        self, min_ratio: float, min_age_days: int
    ) -> list[tuple[str, str]]:
        """
        Liste des torrents candidats pour supprimer après analyse ratio et âge.

        Args:
            min_ratio (float): Ratio minimum pour être considéré
            min_age_days (int): Jours minimum pour être considéré

        Returns:
            list: Liste de tuples (hash, name) à supprimer
        """
        rows = select_all(
            """
            SELECT DISTINCT ifs.torrent_hash, ifs.torrent_name
            FROM imported_files ifs
            JOIN torrent_decisions td ON td.torrent_hash = ifs.torrent_hash
            WHERE td.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
            AND ifs.imported_in_beets_at IS NULL
            AND (
                ifs.torrent_ratio >= ?
                OR (julianday('now') - julianday(datetime(ifs.torrent_added_on,'unixepoch'))) >= ?
            )
            """,
            (min_ratio, min_age_days),
            logger=self.logger,
        )
        return [(h, n) for h, n in rows or []]
