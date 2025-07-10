from pathlib import Path
import tempfile
import shutil
import subprocess
import os
from logic_imports.imports_utils import _copy_tree
from utils.logger import get_logger, with_child_logger

@with_child_logger
def handle_archive(path: str, import_dir: str, logger=None):
    """
    Gère l'extraction et la copie d'une archive vers le dossier d'import.
    """
    name = os.path.basename(path)
    ext = name.lower()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Extraction selon le type d'archive
            if ext.endswith(('.zip', '.tar', '.tar.gz', '.tar.bz2')):
                shutil.unpack_archive(path, tmpdir)
            elif ext.endswith('.rar'):
                subprocess.run(['unrar', 'x', '-y', path, tmpdir], check=True)
            elif ext.endswith('.7z'):
                subprocess.run(['7z', 'x', '-y', f'-o{tmpdir}', path], check=True)
            else:
                logger.warning(f"Format d'archive non supporté : {path}")
                return

            # Choix du nom de dossier
            if is_single_folder_inside(tmp_path):
                folder_name = import_dir
            else:
                base_name = os.path.splitext(name)[0]
                safe_name = base_name.replace(" ", "_").replace("/", "_")
                folder_name = os.path.join(import_dir, safe_name)

            # Copie finale
            _copy_tree(tmpdir, folder_name, logger=logger)
            logger.info(f"Archive extraite et copiée : {path}")

    except (shutil.ReadError, subprocess.CalledProcessError, OSError) as e:
        logger.error(f"Erreur lors du traitement de l’archive {path} : {e}")

            
def is_single_folder_inside(path: Path) -> bool:
    items = list(path.iterdir())
    return len(items) == 1 and items[0].is_dir()