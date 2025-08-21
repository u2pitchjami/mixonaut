# #!/usr/bin/env python3
# """
# fix_imports.py — Préfixe automatiquement les imports locaux par 'mixonaut.'
# Sécurisé : parse AST, gère Import et ImportFrom, ne touche pas ce qui est déjà 'mixonaut.'
# Usage :
#   python tools/fix_imports.py --root . --package mixonaut
# """

# from __future__ import annotations

# import argparse
# import ast
# import logging
# from collections.abc import Iterable
# from pathlib import Path

# LOGGER = logging.getLogger("fix_imports")


# def find_local_packages(package_dir: Path) -> set[str]:
#     """
#     Retourne la liste des sous-packages/directoires de mixonaut/ (1er niveau).
#     """
#     result: set[str] = set()
#     if not package_dir.exists():
#         return result
#     for entry in package_dir.iterdir():
#         if entry.is_dir() and (entry / "__init__.py").exists():
#             result.add(entry.name)
#         # Autoriser aussi des modules .py au 1er niveau (ex: utils.py)
#         if entry.is_file() and entry.suffix == ".py":
#             result.add(entry.stem)
#     return result


# def rewrite_imports(
#     src: str, allowed_roots: set[str], pkg_name: str
# ) -> tuple[str, bool]:
#     """
#     Réécrit les imports en préfixant 'mixonaut.' si le 1er segment est local.

#     Retourne (nouveau_source, modified?).
#     """
#     try:
#         tree = ast.parse(src)
#     except SyntaxError as exc:
#         LOGGER.warning("SyntaxError: %s", exc)
#         return src, False

#     lines = src.splitlines()
#     modified = False

#     def patch_line(idx: int, old: str, new: str) -> None:
#         nonlocal modified, lines
#         if old != new:
#             lines[idx] = new
#             modified = True

#     for node in tree.body:
#         # from x.y import z
#         if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
#             line_idx = node.lineno - 1
#             original = lines[line_idx]
#             first_seg = node.module.split(".")[0]
#             if first_seg == pkg_name:
#                 continue  # déjà ok
#             if first_seg in allowed_roots:
#                 new_module = f"{pkg_name}.{node.module}"
#                 new_line = original.replace(
#                     f"from {node.module} import", f"from {new_module} import", 1
#                 )
#                 patch_line(line_idx, original, new_line)

#         # import x, y as z
#         elif isinstance(node, ast.Import):
#             line_idx = node.lineno - 1
#             original = lines[line_idx]
#             new_line = original
#             for alias in node.names:
#                 name = alias.name  # ex: "db", "db.access"
#                 first_seg = name.split(".")[0]
#                 if first_seg == pkg_name:
#                     continue
#                 if first_seg in allowed_roots:
#                     new_line = new_line.replace(
#                         f"import {name}", f"import {pkg_name}.{name}"
#                     )
#             patch_line(line_idx, original, new_line)

#     return "\n".join(lines) + ("\n" if src.endswith("\n") else ""), modified


# def iter_python_files(root: Path) -> Iterable[Path]:
#     for path in root.rglob("*.py"):
#         if any(p in {".venv", "venv", "__pycache__", ".git"} for p in path.parts):
#             continue
#         yield path


# def main() -> int:
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--root", type=str, default=".")
#     parser.add_argument("--package", type=str, default="mixonaut")
#     args = parser.parse_args()

#     logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

#     project_root = Path(args.root).resolve()
#     pkg_dir = project_root / args.package
#     allowed_roots = find_local_packages(pkg_dir)

#     if not allowed_roots:
#         LOGGER.error("Aucun sous-package détecté dans %s", pkg_dir)
#         return 1

#     LOGGER.info("Sous-packages détectés: %s", ", ".join(sorted(allowed_roots)))

#     modified_any = False
#     for pyfile in iter_python_files(project_root):
#         try:
#             text = pyfile.read_text(encoding="utf-8")
#         except OSError as exc:
#             LOGGER.warning("Lecture impossible %s: %s", pyfile, exc)
#             continue

#         new_text, modified = rewrite_imports(text, allowed_roots, args.package)
#         if modified:
#             try:
#                 pyfile.write_text(new_text, encoding="utf-8")
#                 LOGGER.info("Patch: %s", pyfile)
#                 modified_any = True
#             except OSError as exc:
#                 LOGGER.error("Écriture impossible %s: %s", pyfile, exc)

#     if not modified_any:
#         LOGGER.info("Aucun changement requis. Imports déjà conformes ?")
#     return 0


# if __name__ == "__main__":
#     raise SystemExit(main())
