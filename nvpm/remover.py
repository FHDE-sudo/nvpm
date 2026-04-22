"""Logique de suppression d'un paquet installé."""
from __future__ import annotations

import shutil

from . import colors
from .config import BIN_DIR, PACKAGES_DIR
from .registry import Registry


class RemoveError(RuntimeError):
    """Erreur levée lorsqu'une suppression ne peut aboutir."""


class Remover:
    """Supprime un paquet installé et nettoie ses liens."""

    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or Registry()

    def remove(self, name: str) -> None:
        """Supprime le paquet ``name`` (dossier, lien et entrée de registre)."""
        if not self.registry.is_installed(name):
            raise RemoveError(f"Le paquet '{name}' n'est pas installé.")

        package_dir = PACKAGES_DIR / name
        if package_dir.exists():
            shutil.rmtree(package_dir)
            print(colors.info(f"  ✓ Dossier supprimé : {package_dir}"))

        link_path = BIN_DIR / name
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
            print(colors.info(f"  ✓ Lien supprimé : {link_path}"))

        self.registry.remove(name)
        print(colors.success(f"✓ Paquet '{name}' désinstallé."))
