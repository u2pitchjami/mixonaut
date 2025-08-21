"""
2020-08-20 module utils.
"""

# import os
# import shutil
# from pathlib import Path

# from mixonaut.utils.config import BEETS_IMPORT_PATH
# from mixonaut.utils.logger import LoggerProtocol, ensure_logger, with_child_logger

# @with_child_logger
# def _copy_tree(src_dir, dest_dir, logger=None):
#     for root, dirs, files in os.walk(src_dir):
#         for name in files:
#             rel_path = os.path.relpath(os.path.join(root, name), src_dir)
#             logger.debug(f"Copie de {name} de {root} vers {dest_dir}")
#             dest = os.path.join(dest_dir, rel_path)
#             logger.debug(f"Destination : {dest}")
#             os.makedirs(os.path.dirname(dest), exist_ok=True)
#             shutil.copy2(os.path.join(root, name), dest)

# @with_child_logger
# def extract_torrent_name(import_path: str, base_path: str = BEETS_IMPORT_PATH, logger=None) -> str:
#     """
#     Extrait le nom du dossier racine d’un import Beets, correspondant au torrent_name.
#     """
#     path = Path(import_path).resolve()
#     base = Path(base_path).resolve()

#     try:
#         relative = path.relative_to(base)
#         return relative.parts[0]  # Le premier dossier après /app/imports/
#     except ValueError:
#         raise ValueError(f"Le chemin {import_path} n’est pas sous {base_path}")
