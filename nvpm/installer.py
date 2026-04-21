"""Installation de paquets ``.nv`` sur le système local."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .config import PACKAGES_DIR, ensure_dirs
from .package import NvPackage, NvPackageError
from .registry import Registry

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


class InstallerError(Exception):
    """Erreur levée lorsque l'installation d'un paquet échoue."""


class Installer:
    """Installe un paquet décrit par un fichier ``.nv``.

    L'installation copie les fichiers listés dans le manifeste vers
    ``~/.nvpm/packages/<nom>/`` puis enregistre le paquet dans le registre.
    """

    def __init__(self, registry: Registry | None = None) -> None:
        """Initialise l'installateur.

        :param registry: Instance de :class:`Registry`. Si ``None``,
            une nouvelle instance est créée.
        """
        self.registry = registry or Registry()

    def install(self, nv_path: str | Path) -> None:
        """Installe le paquet décrit par ``nv_path``.

        :param nv_path: Chemin vers le fichier ``.nv``.
        :raises InstallerError: En cas d'échec (fichier introuvable, paquet
            déjà installé, fichier source manquant, etc.).
        """
        ensure_dirs()
        source_nv = Path(nv_path)

        print(f"{CYAN}→ Lecture du manifeste : {source_nv}{RESET}")
        try:
            package = NvPackage.from_file(source_nv)
        except NvPackageError as exc:
            raise InstallerError(str(exc)) from exc

        if self.registry.is_installed(package.name):
            raise InstallerError(
                f"Le paquet '{package.name}' est déjà installé. "
                "Utilisez 'nvpm remove' avant de réinstaller."
            )

        source_dir = source_nv.parent
        target_dir = PACKAGES_DIR / package.name

        missing_files = [
            rel for rel in package.files if not (source_dir / rel).is_file()
        ]
        if missing_files:
            raise InstallerError(
                "Fichiers sources manquants : " + ", ".join(missing_files)
            )

        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"{CYAN}→ Installation de {package.name} "
            f"v{package.version}...{RESET}"
        )
        for rel in package.files:
            src = source_dir / rel
            dst = target_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  {GREEN}✓{RESET} {rel}")

        installed_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        info = package.to_dict()
        info["installed_at"] = installed_at
        info["install_path"] = str(target_dir)
        self.registry.add(package.name, package.version, info)

        print(
            f"{GREEN}✓ Paquet '{package.name}' v{package.version} "
            f"installé avec succès.{RESET}"
        )
