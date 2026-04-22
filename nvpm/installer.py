"""Logique d'installation des paquets ``.nv``."""
from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from . import colors
from .config import BIN_DIR, NV_EXTENSION, PACKAGES_DIR, ensure_dirs
from .package import NvPackage, NvPackageError
from .registry import Registry


class InstallError(RuntimeError):
    """Erreur levée lorsqu'une installation ne peut aboutir."""


class Installer:
    """Installe un paquet décrit par un fichier ``.nv``."""

    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or Registry()

    # ------------------------------------------------------------------ #
    # Point d'entrée principal
    # ------------------------------------------------------------------ #
    def install(self, nv_path: str | Path, *, force: bool = False) -> NvPackage:
        """Installe le paquet décrit par ``nv_path``.

        Si ``force`` est vrai, un paquet déjà installé sera remplacé.
        """
        ensure_dirs()
        package = NvPackage.from_file(nv_path)

        print(colors.info(f"→ Lecture de {package.source_path}"))
        print(colors.info(f"→ Paquet : {package.name} v{package.version} ({package.type})"))

        if self.registry.is_installed(package.name) and not force:
            raise InstallError(
                f"Le paquet '{package.name}' est déjà installé. "
                "Utilisez 'nvpm update' ou 'nvpm remove' d'abord."
            )

        if package.system_deps:
            self._check_system_deps(package.system_deps)

        target_dir = PACKAGES_DIR / package.name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        self._copy_files(package, target_dir)
        self._copy_manifest(package, target_dir)

        if package.type == "binary":
            self._build_and_link(package, target_dir)
        else:
            self._create_script_wrapper(package, target_dir)

        info_payload = {
            "type": package.type,
            "language": package.language,
            "description": package.description,
            "author": package.author,
            "entry": package.entry,
            "update_url": (package.update or {}).get("url"),
            "update_check": (package.update or {}).get("check"),
        }
        self.registry.add(package.name, package.version, info_payload)

        print(colors.success(
            f"✓ Paquet '{package.name}' v{package.version} installé avec succès."
        ))
        print(colors.info(f"  Dossier : {target_dir}"))
        print(colors.info(f"  Exécutable : {BIN_DIR / package.name}"))
        return package

    # ------------------------------------------------------------------ #
    # Étapes internes
    # ------------------------------------------------------------------ #
    def _check_system_deps(self, deps: Iterable[str]) -> None:
        """Vérifie via ``pkg-config`` ou ``which`` que les dépendances existent."""
        print(colors.info("→ Vérification des dépendances système…"))
        missing: list[str] = []
        for dep in deps:
            if self._has_pkg_config(dep) or self._has_executable(dep):
                print(colors.success(f"  ✓ {dep}"))
            else:
                print(colors.error(f"  ✗ {dep}"))
                missing.append(dep)
        if missing:
            raise InstallError(
                "Dépendances système manquantes : " + ", ".join(missing)
            )

    @staticmethod
    def _has_pkg_config(name: str) -> bool:
        """Retourne ``True`` si ``pkg-config --exists <name>`` réussit."""
        if shutil.which("pkg-config") is None:
            return False
        try:
            result = subprocess.run(
                ["pkg-config", "--exists", name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except OSError:
            return False

    @staticmethod
    def _has_executable(name: str) -> bool:
        """Retourne ``True`` si ``name`` est trouvé dans le ``PATH``."""
        return shutil.which(name) is not None

    @staticmethod
    def _copy_files(package: NvPackage, target_dir: Path) -> None:
        """Copie les fichiers et dossiers listés dans ``package.files``."""
        print(colors.info("→ Copie des fichiers…"))
        base = package.source_dir
        for item in package.files:
            source = (base / item).resolve()
            if not str(source).startswith(str(base.resolve())):
                raise InstallError(
                    f"Le chemin '{item}' sort du dossier source du paquet."
                )
            if not source.exists():
                raise InstallError(f"Fichier ou dossier introuvable : {source}")
            destination = target_dir / Path(item).name
            if source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            print(colors.success(f"  ✓ {item}"))

    @staticmethod
    def _copy_manifest(package: NvPackage, target_dir: Path) -> None:
        """Copie le fichier ``.nv`` d'origine dans le dossier du paquet."""
        if package.source_path is None:
            return
        shutil.copy2(package.source_path, target_dir / package.source_path.name)

    @staticmethod
    def _build_and_link(package: NvPackage, target_dir: Path) -> None:
        """Exécute la commande de build puis crée le lien vers ``BIN_DIR``."""
        build = package.build or {}
        command = build.get("command")
        output = build.get("output")
        if not command or not output:
            raise InstallError(
                "Configuration de build invalide : 'command' et 'output' requis."
            )

        print(colors.info(f"→ Compilation : {command}"))
        result = subprocess.run(command, shell=True, cwd=target_dir)
        if result.returncode != 0:
            raise InstallError(
                f"La compilation a échoué (code {result.returncode})."
            )

        output_path = (target_dir / output).resolve()
        if not output_path.exists():
            raise InstallError(
                f"Fichier de sortie attendu introuvable : {output_path}"
            )

        # S'assurer que le binaire est exécutable.
        mode = output_path.stat().st_mode
        output_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        link_path = BIN_DIR / package.name
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(output_path)
        print(colors.success(f"  ✓ Lien créé : {link_path} → {output_path}"))

    @staticmethod
    def _create_script_wrapper(package: NvPackage, target_dir: Path) -> None:
        """Crée un wrapper shell qui exécute le script Python du paquet."""
        entry_path = (target_dir / package.entry).resolve()
        if not entry_path.exists():
            raise InstallError(f"Point d'entrée introuvable : {entry_path}")

        wrapper_path = BIN_DIR / package.name
        if wrapper_path.exists() or wrapper_path.is_symlink():
            wrapper_path.unlink()

        python_exe = sys.executable or "python3"
        wrapper_content = (
            "#!/usr/bin/env sh\n"
            f'exec "{python_exe}" "{entry_path}" "$@"\n'
        )
        wrapper_path.write_text(wrapper_content, encoding="utf-8")
        wrapper_path.chmod(
            wrapper_path.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        print(colors.success(f"  ✓ Wrapper créé : {wrapper_path}"))


__all__ = ["Installer", "InstallError", "NvPackageError"]
