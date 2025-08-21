from utils.config import QBIT_HOST, QBIT_USER, QBIT_PASS
from utils.logger import with_child_logger
import requests

@with_child_logger
def get_qbit_session(qbit_host: str = QBIT_HOST, qbit_user: str = QBIT_USER, qbit_pass: str = QBIT_PASS, logger=None):
    """
    Initialise une session authentifiée qBittorrent

    :return: session requests ou None si ìhec
    """
    session = requests.Session()

    auth = session.post(f"{qbit_host}/api/v2/auth/login", data={
        "username": qbit_user,
        "password": qbit_pass
    })

    if auth.status_code != 200 or auth.text != "Ok.":
        logger.error("\u274c Authentification échouée qBittorrent")
        return None

    logger.debug("\u2705 Connexion qBit réussie")
    return session

@with_child_logger
def get_completed_music_torrents(session, qbit_host: str = QBIT_HOST, logger=None):
    """
    Récupère les torrents musicaux complétés (100%) depuis qBittorrent
    :param session: session authentifiée qBit
    :param qbit_host: URL de l'interface qBittorrent
    :return: liste de dictionnaires torrents
    """
    try:
        resp = session.get(f"{qbit_host}/api/v2/torrents/info", params={
            "filter": "completed",
            "category": "music"
        })
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"\u274c Erreur lors de la récupération des torrents qBit : {e}")
        return []

# @with_child_logger
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

@with_child_logger
def delete_torrent(session, hash_id: str, qbit_host: str = QBIT_HOST, delete_files=True, logger=None):
    """
    Supprime un torrent donné par son hash depuis qBittorrent
    """
    try:
        session.post(f"{qbit_host}/api/v2/torrents/delete", data={
            "hashes": hash_id,
            "deleteFiles": delete_files
        })
        logger.info(f"\u274c Torrent supprimé : {hash_id}")
    except requests.RequestException as e:
        logger.error(f"\u274c Échec suppression torrent {hash_id} : {e}")

@with_child_logger
def get_torrent_full_info(session, torrent: dict, qbit_host: str = QBIT_HOST, logger=None) -> dict:
    """
    Récupère les infos enrichies d’un torrent : nom, date, ratio, fichiers...
    :param session: session qBit déjà authentifiée
    :param torrent: dictionnaire d’un torrent (extrait de /torrents/info)
    :param qbit_host: hôte qBit
    :return: dict enrichi
    """
    try:
        torrent_hash = torrent.get("hash")
        files_resp = session.get(f"{qbit_host}/api/v2/torrents/files", params={"hash": torrent_hash})
        files_resp.raise_for_status()
        files_data = files_resp.json()

        # Calcul de la taille totale
        total_size = sum(f.get("size", 0) for f in files_data)

        return {
            "hash": torrent_hash,
            "name": torrent.get("name"),
            "save_path": torrent.get("save_path"),
            "added_on": torrent.get("added_on"),
            "completion_on": torrent.get("completion_on"),
            "ratio": torrent.get("ratio"),
            "size": total_size,
            "files": [
                {
                    "name": f.get("name"),
                    "size": f.get("size"),
                    "progress": f.get("progress"),
                    "is_seed": f.get("is_seed", False)
                }
                for f in files_data
            ]
        }

    except requests.RequestException as e:
        logger.error(f"❌ Erreur lors de la récupération des fichiers pour le torrent {torrent.get('name')} : {e}")
        return {}
