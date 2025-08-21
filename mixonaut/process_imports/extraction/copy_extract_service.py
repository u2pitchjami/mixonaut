"""
2020-08-20 module de copie des extractions dans le dossiers d'imports de beets.
"""

# services/copy_extract_service.py
from __future__ import annotations

import shutil
import tarfile
import zipfile
from pathlib import Path

from mixonaut.process_imports.extraction.extract_cue import split_cue_and_convert_ffmpeg


class CopyExtractService:
    """
    Copie/extrait les fichiers listés par la DB vers le dossier imports (idempotent).
    """

    def __init__(self, default_source_root: Path, imports_root: Path, repo, logger):
        """
        Copie/extrait les fichiers listés par la DB vers le dossier imports (idempotent).
        """
        self.default_source_root = Path(default_source_root)
        self.imports_root = Path(imports_root)
        self.repo = repo
        self.logger = logger

    def _src_abs(self, relpath: str, save_path: str | None) -> Path:
        # priorité au save_path propagé depuis qBit
        base = Path(save_path) if save_path else self.default_source_root
        return (base / relpath).resolve()

    def _dst_abs(self, relpath: str) -> Path:
        # on préserve l’arbo torrent
        return (self.imports_root / relpath).resolve()

    def _safe_copy(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return
        tmp = dst.with_suffix(dst.suffix + ".part")
        shutil.copy2(src, tmp)
        tmp.rename(dst)

    def _extract_archive(self, src: Path, dst_dir: Path) -> None:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as zf:
                zf.extractall(dst_dir)
            return
        if tarfile.is_tarfile(src):
            with tarfile.open(src) as tf:
                tf.extractall(dst_dir)
            return
        # rar/7z non supportés dans l’environnement → on signale
        raise RuntimeError(f"Archive non supportée sans 7z/unrar: {src.suffix}")

    def _copy_cue_outputs(self, cue_path: Path, rel_root: Path) -> None:
        converted_dir = split_cue_and_convert_ffmpeg(str(cue_path), logger=self.logger)
        if not converted_dir:
            raise RuntimeError(
                "Conversion CUE a échoué (répertoire de sortie introuvable)"
            )
        converted_dir = Path(converted_dir)
        # copie vers imports/{rel_root}/
        for src_file in converted_dir.rglob("*"):
            if src_file.is_file():
                dest = (self.imports_root / rel_root / src_file.name).resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)

    def process_batch(self, nb_limit: int) -> int:
        """
        Process a batch of files to stage based on the provided repository and logger.

        This method iterates through the specified number of rows in the database,
        extracting, copying, or staging each file according to its type. The results
        are logged accordingly.

        Args:
            nb_limit (int): The maximum number of items to process in this batch.

        Returns:
            int: The total number of files staged successfully.
        """
        rows = self.repo.list_files_to_stage(nb_limit)
        done = 0
        for r in rows:
            rel = r["relpath"]
            save_path = r.get("save_path")
            src = self._src_abs(rel, save_path)
            dst = self._dst_abs(rel)
            try:
                if not src.exists():
                    raise FileNotFoundError(f"Source introuvable: {src}")

                ext = src.suffix.lower()
                if ext in {".zip", ".tar", ".tgz", ".tar.gz", ".tbz2", ".tar.bz2"}:
                    # extraire dans imports/<rel_dir>/
                    dst_dir = (self.imports_root / Path(rel).parent).resolve()
                    self._extract_archive(src, dst_dir)
                elif ext == ".cue":
                    # on place les pistes converties dans le dossier du torrent
                    rel_dir = Path(rel).parent
                    self._copy_cue_outputs(src, rel_dir)
                elif ext in {".rar", ".7z"}:
                    raise RuntimeError("RAR/7Z non supportés (7z/unrar absents)")
                else:
                    # copie simple
                    self._safe_copy(src, dst)

                self.repo.mark_staged_ok(r["id"])
                done += 1
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.exception("Staging KO pour %s: %s", rel, exc)
                self.repo.mark_staged_error(r["id"], str(exc))
        return done
