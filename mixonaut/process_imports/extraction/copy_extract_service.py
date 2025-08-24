"""
2020-08-20 module de copie des extractions dans le dossiers d'imports de beets.
"""

# process_imports/extraction/copy_extract_service.py
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from shutil import which

from mixonaut.db.imports.torrent_repo import TorrentRepo
from mixonaut.process_imports.extraction.extract_cue import split_cue_and_convert_ffmpeg
from mixonaut.utils.logger import LoggerProtocol, ensure_logger

AUDIO_ARCHIVES = {".zip", ".tar", ".tgz", ".tar.gz", ".tbz2", ".tar.bz2", ".iso"}
UNSUPPORTED_ARCHIVES = {".rar", ".7z"}  # gérés via 7z si tu actives plus tard
CUE_EXT = {".cue"}
AUDIO_CONVERT_EXT = {".wav", ".flac"}


class CopyExtractService:
    """
    Copie/extrait/convertit les fichiers listés par la DB vers le dossier imports (idempotent).
    """

    def __init__(
        self,
        default_source_root: Path,
        imports_root: Path,
        repo: TorrentRepo,
        *,
        audio_target_codec: str = "flac",  # "flac" | "alac" | "mp3"
        reencode_flac: bool = False,  # False → .flac copiés tels quels si cible "flac"
        ffmpeg_bin: str = "ffmpeg",
        logger: LoggerProtocol | None = None,
    ):
        logger = ensure_logger(logger, __name__)
        self.default_source_root = Path(default_source_root).resolve()
        self.imports_root = Path(imports_root).resolve()
        self.repo = repo
        self.logger = logger
        self.audio_target_codec = audio_target_codec.lower()
        self.reencode_flac = reencode_flac
        self.ffmpeg_bin = ffmpeg_bin

        if self.audio_target_codec not in {"flac", "alac", "mp3"}:
            raise ValueError("audio_target_codec must be one of: flac | alac | mp3")

    # -------------------- path helpers --------------------

    def _normalize_relpath(self, relpath: str) -> Path:
        p = Path(relpath)
        if p.is_absolute():
            p = Path(os.path.relpath(p, "/"))
        return Path(os.path.normpath(str(p)))

    def _src_abs(self, relpath: str, save_path: str | None) -> Path:
        base = Path(save_path).resolve() if save_path else self.default_source_root
        rel_norm = self._normalize_relpath(relpath)
        src = (base / rel_norm).resolve()
        return src

    def _dst_abs(self, relpath: str) -> Path:
        rel_norm = self._normalize_relpath(relpath)
        dst = (self.imports_root / rel_norm).resolve()
        if self.imports_root not in dst.parents and self.imports_root != dst:
            raise RuntimeError(f"Destination hors imports_root: {dst}")
        return dst

    # -------------------- basic ops --------------------

    def _safe_copy(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return
        tmp = dst.with_suffix(dst.suffix + ".part")
        shutil.copy2(src, tmp)
        tmp.rename(dst)

    # -------------------- archive extraction --------------------

    def _safe_extract_zip(self, archive: Path, dst_dir: Path) -> None:
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                name = Path(member.filename)
                if name.is_absolute() or ".." in name.parts:
                    raise RuntimeError(f"Entrée ZIP suspecte: {member.filename}")
                target = (dst_dir / name).resolve()
                if (
                    self.imports_root not in target.parents
                    and self.imports_root != target
                ):
                    raise RuntimeError(f"Extraction hors imports_root: {target}")
            zf.extractall(dst_dir)

    def _safe_extract_tar(self, archive: Path, dst_dir: Path) -> None:
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                name = Path(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise RuntimeError(f"Entrée TAR suspecte: {member.name}")
                target = (dst_dir / name).resolve()
                if (
                    self.imports_root not in target.parents
                    and self.imports_root != target
                ):
                    raise RuntimeError(f"Extraction hors imports_root: {target}")
            tf.extractall(dst_dir)

    def _extract_iso(self, src: Path, dst_dir: Path) -> None:
        """
        Extraction ISO via 7z si disponible.
        """
        if which("7z") is None:
            raise RuntimeError(
                "Extraction .iso indisponible: '7z' non trouvé dans PATH"
            )
        dst_dir.mkdir(parents=True, exist_ok=True)
        # 7z x <archive> -o<dst> -y
        subprocess.run(["7z", "x", str(src), f"-o{str(dst_dir)}", "-y"], check=True)

    def _extract_archive(self, src: Path, dst_dir: Path) -> None:
        dst_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        if ext == ".iso":
            self._extract_iso(src, dst_dir)
            return
        if zipfile.is_zipfile(src):
            self._safe_extract_zip(src, dst_dir)
            return
        try:
            if tarfile.is_tarfile(src):
                self._safe_extract_tar(src, dst_dir)
                return
        except tarfile.TarError as exc:
            raise RuntimeError(f"Archive TAR invalide: {src}") from exc
        # rar/7z → optionnel via 7z (non activé ici)
        if ext in {".rar", ".7z"} and which("7z") is not None:
            subprocess.run(["7z", "x", str(src), f"-o{str(dst_dir)}", "-y"], check=True)
            return
        raise RuntimeError(f"Archive non supportée: {src.suffix}")

    # -------------------- CUE handling --------------------

    def _copy_cue_outputs(self, cue_path: Path, rel_root: Path) -> None:
        converted_dir = split_cue_and_convert_ffmpeg(str(cue_path), logger=self.logger)
        if not converted_dir:
            raise RuntimeError(
                "Conversion CUE a échoué (répertoire de sortie introuvable)"
            )
        converted_dir = Path(converted_dir)
        for src_file in converted_dir.rglob("*"):
            if src_file.is_file():
                dest = (self.imports_root / rel_root / src_file.name).resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)

    # -------------------- audio conversion --------------------

    def _ffmpeg_cmd(self, src: Path, dst: Path) -> list[str]:
        """
        Construit la commande ffmpeg selon self.audio_target_codec.
        """
        if self.audio_target_codec == "flac":
            # lossless, compression level par défaut (5-8)
            return [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(src),
                "-vn",
                "-c:a",
                "flac",
                str(dst),
            ]
        if self.audio_target_codec == "alac":
            # Apple Lossless → conteneur m4a
            return [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(src),
                "-vn",
                "-c:a",
                "alac",
                str(dst),
            ]
        # mp3 (VBR qualité 2 ~ 190kbps)
        return [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(dst),
        ]

    def _target_ext(self) -> str:
        if self.audio_target_codec == "flac":
            return ".flac"
        if self.audio_target_codec == "alac":
            return ".m4a"
        return ".mp3"

    def _convert_audio(self, src: Path, dst_dir: Path) -> None:
        """
        Convertit src -> dst_dir avec extension cible; .flac copiés si cible=flac et reencode_flac=False.
        """
        dst_dir.mkdir(parents=True, exist_ok=True)
        base = src.stem  # sans extension
        dst = (dst_dir / f"{base}{self._target_ext()}").resolve()

        # Optimisation : .flac → .flac sans ré-encodage
        if (
            src.suffix.lower() == ".flac"
            and self.audio_target_codec == "flac"
            and not self.reencode_flac
        ):
            self._safe_copy(src, dst)
            return

        tmp = dst.with_suffix(dst.suffix + ".part")
        cmd = self._ffmpeg_cmd(src, tmp)
        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
            tmp.rename(dst)
        except subprocess.CalledProcessError as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"ffmpeg conversion failed: {src.name} → {dst.name} ({exc})"
            ) from exc

    # -------------------- main loop --------------------

    def process_batch(self, nb_limit: int | None = None) -> int:
        """
        Traite jusqu'à nb_limit entrées à stager depuis la DB.

        Retourne le nombre d'éléments traités avec succès.
        """
        # Essayez d'utiliser list_files_to_stage(limit=?), sinon fallback slicing
        try:
            rows = self.repo.list_files_to_stage(limit=nb_limit)
        except TypeError:
            rows = self.repo.list_files_to_stage()
            if nb_limit is not None and nb_limit > 0:
                rows = rows[:nb_limit]

        done = 0
        for r in rows:
            rel = r["relpath"]
            save_path = r.get("save_path")
            src = self._src_abs(rel, save_path if isinstance(save_path, str) else None)
            dst = self._dst_abs(rel)

            try:
                if not src.exists():
                    raise FileNotFoundError(f"Source introuvable: {src}")

                ext = src.suffix.lower()
                if ext in AUDIO_ARCHIVES:
                    # extraire dans imports/<rel_dir>/
                    dst_dir = (self.imports_root / Path(rel).parent).resolve()
                    self._extract_archive(src, dst_dir)

                elif ext in CUE_EXT:
                    # placer les pistes converties dans le dossier du torrent
                    rel_dir = Path(rel).parent
                    self._copy_cue_outputs(src, rel_dir)

                elif ext in AUDIO_CONVERT_EXT:
                    # conversion audio → dossier de destination du fichier
                    dst_dir = (self.imports_root / Path(rel).parent).resolve()
                    self._convert_audio(src, dst_dir)

                elif ext in {".rar", ".7z"}:
                    # si 7z est dispo on peut activer ci‑dessous; par défaut on refuse
                    if which("7z") is not None:
                        dst_dir = (self.imports_root / Path(rel).parent).resolve()
                        subprocess.run(
                            ["7z", "x", str(src), f"-o{str(dst_dir)}", "-y"], check=True
                        )
                    else:
                        raise RuntimeError("RAR/7Z non supportés (7z/unrar absents)")

                else:
                    # copie simple (mp3/ogg/m4a... ou sidecars .jpg, .nfo, etc.)
                    self._safe_copy(src, dst)

                self.repo.mark_staged_ok(r["id"])
                done += 1

            except Exception as exc:  # pylint: disable=broad-except
                self.logger.exception("Staging KO pour %s: %s", rel, exc)
                self.repo.mark_staged_error(r["id"], str(exc))

        return done
