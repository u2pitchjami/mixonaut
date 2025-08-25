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
# extensions audio considérées comme “déjà présentes”
AUDIO_EXTS_DEST = {".flac", ".wav", ".mp3", ".m4a", ".ogg", ".aac"}


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

        # 🔎 ici tu peux vérifier que ffmpeg est dispo

        if which(self.ffmpeg_bin) is None:
            raise RuntimeError(
                f"ffmpeg introuvable dans le PATH (reçu: {self.ffmpeg_bin})"
            )

        if self.audio_target_codec not in {"flac", "alac", "mp3"}:
            raise ValueError("audio_target_codec must be one of: flac | alac | mp3")

    # -------------------- path helpers --------------------

    def _normalize_relpath(self, relpath: str) -> Path:
        p = Path(relpath)
        if p.is_absolute():
            p = Path(os.path.relpath(p, "/"))
        return Path(os.path.normpath(str(p)))

    def _src_abs(self, relpath: str, save_path: str | None) -> Path:
        """
        Calcule le chemin source absolu.

        - Si save_path est un fichier absolu → retourne ce fichier (ignore relpath).
        - Si save_path est un dossier absolu → join(save_path, relpath).
        - Sinon → join(self.default_source_root, relpath).
        """
        rel_norm = self._normalize_relpath(relpath)

        if save_path:
            p = Path(save_path)
            try:
                p_abs = p.resolve()
            except Exception:
                p_abs = p  # fallback

            if p_abs.is_file():
                return p_abs

            if p_abs.is_dir():
                return (p_abs / rel_norm).resolve()

            # si inexistant mais semble pointer vers un fichier (a une extension)
            if p_abs.suffix:
                return p_abs  # on tente tel quel (cas : fichier pas encore présent)
            # sinon on le traite comme base-dir
            return (p_abs / rel_norm).resolve()

        # fallback ancien comportement
        return (self.default_source_root / rel_norm).resolve()

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

    def _dest_has_audio(self, rel_root: Path) -> bool:
        """
        Vérifie s’il y a déjà des fichiers audio dans imports/<rel_root>/.
        """
        dest_dir = (self.imports_root / rel_root).resolve()
        if not dest_dir.exists():
            return False
        for p in dest_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS_DEST:
                return True
        return False

    def _find_cue_audio_file(self, cue_path: Path) -> Path | None:
        """
        Parse minimal de la CUE pour récupérer le premier fichier audio référencé (ligne FILE).

        Gère guillemets ou non, et quelques encodages courants.
        """
        candidates = ("utf-8", "cp1252", "latin-1")
        text: str | None = None
        for enc in candidates:
            try:
                text = cue_path.read_text(encoding=enc)
                break
            except Exception:
                continue
        if text is None:
            return None

        # Exemple de lignes :
        # FILE "Album.wav" WAVE
        # FILE track.flac FLAC
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.upper().startswith("FILE "):
                continue
            # entre guillemets
            if '"' in line:
                try:
                    name = line.split('"', 2)[1]
                except Exception:
                    continue
            else:
                # sans guillemets : FILE filename.ext TYPE
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                else:
                    continue
            audio = (cue_path.parent / name).resolve()
            return audio
        return None

    def _copy_cue_outputs(self, cue_path: Path, rel_root: Path) -> bool:
        """
        Convertit via CUE si nécessaire.

        Retourne True si conversion/copie effectuée, False si on a sciemment skip (déjà présent, source manquante).
        """
        # 1) si on a déjà des fichiers audio dans la destination → skip
        if self._dest_has_audio(rel_root):
            self.logger.debug(
                "CUE skip: audio déjà présent dans %s", (self.imports_root / rel_root)
            )
            return False

        # 2) retrouver le fichier audio référencé par la CUE
        audio_file = self._find_cue_audio_file(cue_path)
        if not audio_file or not audio_file.exists():
            self.logger.info(
                "CUE skip: fichier audio référencé introuvable (%s) pour %s",
                audio_file,
                cue_path,
            )
            return False

        # 3) lancer la conversion via utilitaire existant
        converted_dir = split_cue_and_convert_ffmpeg(str(cue_path), logger=self.logger)
        if not converted_dir:
            raise RuntimeError(
                "Conversion CUE a échoué (répertoire de sortie introuvable)"
            )
        converted_dir = Path(converted_dir)

        # 4) copie des sorties converties vers imports/<rel_root>/
        any_copied = False
        for src_file in converted_dir.rglob("*"):
            if src_file.is_file():
                dest = (self.imports_root / rel_root / src_file.name).resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src_file, dest)
                    any_copied = True

        return any_copied

    # -------------------- audio conversion --------------------

    def _container_for_target(self) -> str:
        if self.audio_target_codec == "flac":
            return "flac"  # conteneur FLAC
        if self.audio_target_codec == "alac":
            return "ipod"  # m4a/mp4; "ipod" est le muxer adapté pour ALAC
        return "mp3"  # conteneur MP3

    def _ffmpeg_cmd(self, src: Path, dst: Path) -> list[str]:
        base = [
            self.ffmpeg_bin,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(src),
            "-map",
            "0:a:0",
            "-vn",
        ]
        if self.audio_target_codec == "flac":
            codec = ["-c:a", "flac"]
        elif self.audio_target_codec == "alac":
            codec = ["-c:a", "alac"]
        else:
            codec = ["-c:a", "libmp3lame", "-q:a", "2"]

        # 👇 forcer le muxer, car l'extension se termine par .part
        container = ["-f", self._container_for_target()]
        return base + codec + container + [str(dst)]

    def _target_ext(self) -> str:
        if self.audio_target_codec == "flac":
            return ".flac"
        if self.audio_target_codec == "alac":
            return ".m4a"
        return ".mp3"

    def _convert_audio(self, src: Path, dst_dir: Path) -> None:
        """
        Convertit src -> dst_dir ; idempotent (skip si cible existe).

        Logue toujours la stderr d'ffmpeg en cas d'échec.
        """
        dst_dir.mkdir(parents=True, exist_ok=True)
        base = src.stem
        dst = (dst_dir / f"{base}{self._target_ext()}").resolve()

        # déjà converti ?
        if dst.exists():
            self.logger.debug("Conversion skip (déjà présent) : %s", dst)
            return

        # flac -> flac, sans réencodage (option)
        if (
            src.suffix.lower() == ".flac"
            and self.audio_target_codec == "flac"
            and not self.reencode_flac
        ):
            self._safe_copy(src, dst)
            return

        tmp = dst.with_suffix(dst.suffix + ".part")
        cmd = self._ffmpeg_cmd(src, tmp)
        self.logger.debug("ffmpeg cmd: %s", " ".join(cmd))

        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            # Nettoyage du .part si échec
            tmp.unlink(missing_ok=True)

            # Catégorisation d'erreurs fréquentes pour aide au debug
            stderr = (proc.stderr or "").strip()
            if "Unknown encoder 'flac'" in stderr:
                hint = "ffmpeg compilé sans encoder flac ? (installez un build complet)"
            elif "No such file or directory" in stderr:
                hint = "Chemin source/destination invalide ou non accessible."
            elif "Permission denied" in stderr:
                hint = "Droits insuffisants sur le dossier destination."
            elif "No space left on device" in stderr:
                hint = "Plus d'espace disque sur la destination."
            else:
                hint = "Voir stderr ci-dessous."

            raise RuntimeError(
                f"ffmpeg failed rc={proc.returncode} src={src.name} -> {dst.name}\n"
                f"hint: {hint}\n"
                f"stderr:\n{stderr}"
            )

        # Rename final
        tmp.rename(dst)

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
                    try:
                        _ = self._copy_cue_outputs(src, rel_dir)
                        # quel que soit le résultat (converti ou skip), on marque OK
                        self.repo.mark_staged_ok(r["id"])
                        done += 1
                        continue
                    except Exception as exc:
                        self.logger.exception("CUE KO pour %s: %s", rel, exc)
                        self.repo.mark_staged_error(r["id"], str(exc))
                        continue

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
