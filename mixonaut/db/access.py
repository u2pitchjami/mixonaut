"""2025-08-21 - modules de requêtes vers la base sqlite"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any, Union

from mixonaut.db.session import MixonautDBSession
from mixonaut.utils.config import BEETS_DB
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

Scalar = Union[int, float, str, bytes]


def execute_query(
    query: str,
    params: Sequence[Any] | tuple[Any, ...] = (),
    fetch: bool = False,
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Exécute une requête SQL (dans une transaction du with).
    """
    logger = ensure_logger(logger, __name__)
    with MixonautDBSession(db_path=db, logger=logger) as dbs:
        cur = dbs.execute(query, params)
        return list(cur.fetchall()) if fetch else []


def execute_many(
    query: str,
    param_list: list[tuple[Any, ...]],
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> None:
    """
    Executemany atomique (une transaction).
    """
    logger = ensure_logger(logger, __name__)
    if not param_list:
        logger.debug("execute_many: rien à exécuter (param_list vide)")
        return
    with MixonautDBSession(db_path=db, logger=logger) as dbs:
        dbs.executemany(query, param_list)
        logger.debug("execute_many: %d lignes écrites", len(param_list))


def select_all(
    query: str,
    params: Sequence[Any] | tuple[Any, ...] = (),
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Execute a query to retrieve all rows.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the query. Defaults to () if not provided.
        db (str, optional): The path to the SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        list: A list of tuples containing all rows from the result set.
    """
    logger = ensure_logger(logger, __name__)
    return execute_query(query, params=params, fetch=True, db=db, logger=logger)


def select_one(
    query: str,
    params: Sequence[Any] | tuple[Any, ...] = (),
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> sqlite3.Row | None:
    """
    Execute a query to retrieve one row.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the query. Defaults to () if not provided.
        db (str, optional): The path to the SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        tuple or None: A single row from the result set, or None if no rows are found.

    Raises:
        RuntimeError: If any error occurs during execution.
    """
    logger = ensure_logger(logger, __name__)
    result = execute_query(query, params=params, fetch=True, db=db, logger=logger)
    return result[0] if result else None


def execute_write(
    query: str,
    params: Sequence[Any] | tuple[Any, ...] = (),
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> list[sqlite3.Row]:
    """
    Execute une requête d'écriture sur la base spécifiée.

    Args:
        query (str): La requête SQL à exécuter.
        params (tuple): Les paramètres de la requête SQL.
        db (str): Le chemin vers le fichier de base SQLite.
            Defaults to BEETS_DB if not provided.
        logger: Un objet de journalisation. Si pas fourni, un child logger sera créé.

    Returns:
        None

    Raises:
        RuntimeError: Si une erreur se produit pendant l'exécution de la requête.
    """
    logger = ensure_logger(logger, __name__)
    return execute_query(query, params, fetch=False, db=db, logger=logger)


def select_scalar(
    query: str,
    params: Sequence[Any] | tuple[Any, ...] = (),
    db: str = BEETS_DB,
    logger: LoggerProtocol | None = None,
) -> Scalar | None:
    """
    Execute a single SELECT query and return the first column.

    Args:
        query (str): The SQL query to execute.
        params (tuple): A tuple of parameters for the query.
        db (str): The path to the Beets SQLite database file. Defaults to BEETS_DB.
        logger: A logging object. If not provided, a child logger will be created.

    Returns:
        The first column of the result row, or None if no rows are returned.

    Raises:
        sqlite3.Error: If an error occurs during query execution.
    """
    logger = ensure_logger(logger, __name__)
    row = select_one(query, params, db=db, logger=logger)
    return row[0] if row else None
