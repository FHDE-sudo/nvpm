"""Constantes et chemins utilisés par nvpm."""
from __future__ import annotations

from pathlib import Path

#: Dossier racine où nvpm stocke ses données.
NVPM_HOME: Path = Path.home() / ".nvpm"

#: Dossier contenant les paquets installés (un sous-dossier par paquet).
PACKAGES_DIR: Path = NVPM_HOME / "packages"

#: Dossier contenant les liens symboliques des binaires et les wrappers de scripts.
BIN_DIR: Path = NVPM_HOME / "bin"

#: Fichier JSON qui liste les paquets installés et leurs métadonnées.
REGISTRY_FILE: Path = NVPM_HOME / "registry.json"

#: Extension attendue pour les manifestes de paquets.
NV_EXTENSION: str = ".nv"


def ensure_dirs() -> None:
    """Crée ``NVPM_HOME``, ``PACKAGES_DIR`` et ``BIN_DIR`` s'ils n'existent pas."""
    for directory in (NVPM_HOME, PACKAGES_DIR, BIN_DIR):
        directory.mkdir(parents=True, exist_ok=True)
