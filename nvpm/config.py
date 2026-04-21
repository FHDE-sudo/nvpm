"""Constantes et utilitaires de configuration pour nvpm."""
from __future__ import annotations

import os
from pathlib import Path

NVPM_HOME: Path = Path(os.path.expanduser("~/.nvpm"))
"""Répertoire racine où nvpm stocke ses données."""

PACKAGES_DIR: Path = NVPM_HOME / "packages"
"""Répertoire contenant les paquets installés."""

REGISTRY_FILE: Path = NVPM_HOME / "registry.json"
"""Fichier JSON contenant le registre des paquets installés."""

NV_EXTENSION: str = ".nv"
"""Extension des fichiers de manifeste de paquet."""


def ensure_dirs() -> None:
    """Crée les répertoires de travail de nvpm s'ils n'existent pas.

    Appelée au démarrage pour garantir que ``NVPM_HOME`` et ``PACKAGES_DIR``
    existent avant toute opération sur le système de fichiers.
    """
    NVPM_HOME.mkdir(parents=True, exist_ok=True)
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
