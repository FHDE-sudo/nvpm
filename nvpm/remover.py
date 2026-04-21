"""Suppression de paquets installés."""
from __future__ import annotations

import shutil
from pathlib import Path

from .config import PACKAGES_DIR
from .registry import Registry

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class RemoverError(Exception):
    """Erreur levée lorsqu'un paquet ne peut pas être supprimé."""


class Remover:
    """Supprime un paquet installé du système et du registre."""

    def __init__(self, registry: Registry | None = None) -> None:
        """Initialise le suppresseur.

        :param registry: Instance de :class:`Registry`. Si ``None``,
            une nouvelle instance est créée.
        """
        self.registry = registry or Registry()

    def remove(self, name: str) -> None:
        """Supprime un paquet installé.

        :param name: Nom du paquet à supprimer.
        :raises RemoverError: Si le paquet n'est pas installé.
        """
        if not self.registry.is_installed(name):
            raise RemoverError(f"Le paquet '{name}' n'est pas installé.")

        target_dir: Path = PACKAGES_DIR / name
        if target_dir.exists():
            shutil.rmtree(target_dir)

        self.registry.remove(name)
        print(f"{GREEN}✓ Paquet '{name}' supprimé avec succès.{RESET}")
