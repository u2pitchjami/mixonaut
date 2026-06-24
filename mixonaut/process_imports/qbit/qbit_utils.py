"""
2025-08-24 module de connexion qBit (utils).
"""

from __future__ import annotations

from typing import Any, cast

import requests
from requests import RequestException, Session

from mixonaut.process_imports.models.models import QbtFile, QbtTorrent, TorrentFullInfo
from mixonaut.utils.config import QBIT_HOST, QBIT_PASS, QBIT_USER
from mixonaut.utils.logger import LoggerProtocol, ensure_logger
from mixonaut.utils.safe_cast import safe_float, safe_int, safe_str

# --- Session/auth ------------------------------------------------------------------


def get_qbit_session(
    qbit_host: str = QBIT_HOST,
    qbit_user: str = QBIT_USER,
    qbit_pass: str = QBIT_PASS,
    logger: LoggerProtocol | None = None,
) -> Session | None:
    """
    Initialise une session authentifiée qBittorrent.

    Retourne une Session requests ou None si échec.
    """
    logger = ensure_logger(logger, __name__)
    session = requests.Session()

    try:
        auth = session.post(
            f"{qbit_host}/api/v2/auth/login",
            data={"username": qbit_user, "password": qbit_pass},
            timeout=10,
        )
        if auth.status_code != 200 or auth.text.strip() != "Ok.":
            logger.error(
                "❌ Authentification échouée qBittorrent (status=%s body=%r)",
                auth.status_code,
                auth.text,
            )
            return None
        logger.debug("✅ Connexion qBit réussie")
        return session
    except RequestException as exc:
        logger.error("❌ Connexion qBit impossible: %s", exc)
        return None


# --- Listing torrents ---------------------------------------------------------------


def get_completed_music_torrents(
    session: Session,
    qbit_host: str = QBIT_HOST,
    logger: LoggerProtocol | None = None,
) -> list[QbtTorrent]:
    """
    Récupère les torrents musicaux complétés (100%) depuis qBittorrent.
    """
    logger = ensure_logger(logger, __name__)
    try:
        resp = session.get(
            f"{qbit_host}/api/v2/torrents/info",
            params={"filter": "completed", "category": "music"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
            logger.error("Réponse qBit inattendue: %r", type(data))
            return []

        return cast(list[QbtTorrent], data)

    except RequestException as exc:
        logger.error("Erreur HTTP qBit: %s", exc)
        return []


# --- Suppression d'un torrent -------------------------------------------------------


def delete_torrent(
    session: Session,
    hash_id: str,
    qbit_host: str = QBIT_HOST,
    delete_files: bool = True,
    logger: LoggerProtocol | None = None,
) -> bool:
    """
    Supprime un torrent donné par son hash depuis qBittorrent.

    Retourne True si la requête a réussi (2xx), False sinon.
    """
    logger = ensure_logger(logger, __name__)
    try:
        # L'API qBit accepte généralement "true"/"false" pour deleteFiles
        resp = session.post(
            f"{qbit_host}/api/v2/torrents/delete",
            data={
                "hashes": hash_id,
                "deleteFiles": "true" if delete_files else "false",
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("🗑️ Torrent supprimé : %s (delete_files=%s)", hash_id, delete_files)
        return True
    except RequestException as exc:
        logger.error("❌ Échec suppression torrent %s : %s", hash_id, exc)
        return False


# --- Détails d'un torrent (fichiers, ratio, etc.) ----------------------------------


def get_torrent_full_info(
    torrent: QbtTorrent,
    session: Session,
    qbit_host: str = QBIT_HOST,
    logger: LoggerProtocol | None = None,
) -> TorrentFullInfo | None:
    """
    Récupère les infos enrichies d’un torrent : nom, date, ratio, fichiers, taille totale.
    """
    log = ensure_logger(logger, __name__)
    try:
        # hash obligatoire
        torrent_hash = torrent.get("hash")
        if not isinstance(torrent_hash, str) or not torrent_hash:
            log.error("Torrent sans hash: %r", torrent)
            return None

        resp = session.get(
            f"{qbit_host}/api/v2/torrents/files",
            params={"hash": torrent_hash},
            timeout=10,
        )
        resp.raise_for_status()
        data: Any = resp.json()

        if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
            log.error("Réponse /torrents/files inattendue: %r", type(data))
            return None
        files_json = cast(list[dict[str, Any]], data)

        # Construction typée
        total_size = 0
        files: list[QbtFile] = []
        for f in files_json:
            item: QbtFile = {}
            if (v := f.get("name")) is not None:
                item["name"] = str(v)

            size_val = f.get("size")
            if size_val is not None:
                try:
                    size_int = int(size_val)
                except (TypeError, ValueError):
                    size_int = 0
                item["size"] = size_int
                total_size += size_int

            if (v := f.get("progress")) is not None:
                try:
                    item["progress"] = float(v)
                except (TypeError, ValueError):
                    pass

            item["is_seed"] = bool(f.get("is_seed", False))
            if (v := f.get("path")) is not None:
                item["path"] = str(v)

            files.append(item)

        # Champs essentiels : name + ratio toujours présents dans notre dict de sortie
        name_val = torrent.get("name")
        ratio_val = torrent.get("ratio")

        out: TorrentFullInfo = {
            "hash": torrent_hash,
            "size": total_size,
            "files": files,
            "name": str(name_val) if name_val is not None else "",
            "ratio": float(ratio_val) if ratio_val is not None else 0.0,
        }

        if (v := torrent.get("save_path")) is not None:
            out["save_path"] = str(v)
        if (v := torrent.get("added_on")) is not None:
            if (iv := safe_int(v)) is not None:
                out["added_on"] = iv

        if (v := torrent.get("completion_on")) is not None:
            if (iv := safe_int(v)) is not None:
                out["completion_on"] = iv

        out["name"] = safe_str(torrent.get("name")) or ""
        out["ratio"] = safe_float(torrent.get("ratio")) or 0.0

        return out

    except RequestException as exc:  # pylint: disable=broad-except
        log.error(
            "❌ Erreur lors de la récupération des fichiers pour %r : %s",
            torrent.get("name"),
            exc,
        )
        return None


#
# def extract_files_from_torrent(session, hash_id: str, qbit_host: str = QBIT_HOST,  logger=None):
#     """
#     Récupère les chemins des fichiers d'un torrent donné
#     :return: liste de chemins relatifs (par rapport au dossier racine du torrent)
#     """
#     try:
#         files_resp = session.get(f"{qbit_host}/api/v2/torrents/files", params={"hash": hash_id})
#         files_resp.raise_for_status()
#         files = files_resp.json()
#         return [f["name"] for f in files]
#     except requests.RequestException as e:
#         logger.error(f"\u274c Erreur lors de l'extraction des fichiers du torrent {hash_id} : {e}")
#         return []
