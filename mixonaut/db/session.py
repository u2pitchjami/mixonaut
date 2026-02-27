# mixonaut/db/session.py
"""
2025-08-22 Gestionnaire de contexte pour une session SQLite Beets.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Literal

from mixonaut.beets_utils.lock.beets_safe import (
    get_current_pid,
    read_lock_pid,
    safe_beets_call,
)
from mixonaut.utils.config import LOCK_FILE
from mixonaut.utils.logger import LoggerProtocol, ensure_logger


class MixonautDBSession:
    """
    Gestionnaire de contexte pour une session SQLite Beets/Mixonaut.

    - Vérifie le verrou via `safe_beets_call`.
    - Ouvre la connexion en __enter__, la ferme en __exit__.
    - Commit si OK, rollback si exception.
    - Supprime le verrou si on est le propriétaire.

    Usage :
        with MixonautDBSession(db_path=BEETS_DB, logger=logger) as db:
            cur = db.conn.cursor()
            cur.execute("SELECT 1")
            rows = cur.fetchall()
    """

    def __init__(
        self,
        db_path: str,
        *,
        timeout: float = 30.0,
        row_factory: bool = True,
        logger: LoggerProtocol | None = None,
    ) -> None:
        self._db_path = db_path
        self._timeout = timeout
        self._use_row_factory = row_factory
        self._logger = ensure_logger(logger, __name__)
        self._conn: sqlite3.Connection | None = None

    # ---------- Properties ----------

    @property
    def conn(self) -> sqlite3.Connection:
        """
        Retourne la connexion SQLite active (non-None dans le bloc `with`).
        """
        assert self._conn is not None, (
            "Connection not initialized (use within a with-block)"
        )
        return self._conn

    # ---------- Context Manager ----------

    def __enter__(self) -> MixonautDBSession:
        log = self._logger

        if not safe_beets_call(logger=log):
            raise sqlite3.OperationalError("safe_beets_call a refusé l'accès à la DB")

        conn = sqlite3.connect(self._db_path, timeout=self._timeout)
        if self._use_row_factory:
            conn.row_factory = sqlite3.Row
        self._conn = conn
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> Literal[False]:
        log = self._logger
        assert self._conn is not None

        try:
            if exc_type is None:
                self._conn.commit()
            else:
                try:
                    self._conn.rollback()
                except sqlite3.Error:
                    log.debug("Rollback a échoué (ignoré).")
        finally:
            try:
                self._conn.close()
            except sqlite3.Error:
                log.debug("Fermeture connexion a échoué (ignoré).")

            # Gestion du verrou
            if read_lock_pid() == get_current_pid():
                try:
                    os.remove(LOCK_FILE)
                except OSError:
                    log.debug("🔓 Verrou déjà absent.")
            else:
                log.warning(
                    "⚠️ Tentative de suppression du verrou non possédé (ignorée)."
                )

        return False  # les exceptions ne sont pas supprimmées

    # ---------- Helpers facultatifs ----------

    def execute(
        self,
        query: str,
        params: Sequence[Any] | tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        """
        Exécute une requête simple et retourne le cursor.
        """
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur

    def executemany(
        self,
        query: str,
        param_list: Sequence[tuple[Any, ...]],
    ) -> sqlite3.Cursor:
        """
        Exécute une requête sur une liste de paramètres (transaction unique).
        """
        cur = self.conn.cursor()
        cur.executemany(query, param_list)
        return cur
