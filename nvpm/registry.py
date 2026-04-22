"""Gestion du registre des paquets installés (``registry.json``)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import REGISTRY_FILE, ensure_dirs


class Registry:
    """Registre persistant des paquets installés par nvpm."""

    def __init__(self) -> None:
        ensure_dirs()
        self._data: Dict[str, Any] = self._load()

    # ------------------------------------------------------------------ #
    # Persistance
    # ------------------------------------------------------------------ #
    def _load(self) -> Dict[str, Any]:
        """Charge le registre depuis disque ou initialise une structure vide."""
        if not REGISTRY_FILE.exists():
            return {"packages": {}}
        try:
            with REGISTRY_FILE.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (json.JSONDecodeError, OSError):
            return {"packages": {}}
        if not isinstance(data, dict) or "packages" not in data:
            return {"packages": {}}
        return data

    def save(self) -> None:
        """Écrit le registre sur disque au format JSON indenté."""
        ensure_dirs()
        with REGISTRY_FILE.open("w", encoding="utf-8") as stream:
            json.dump(self._data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")

    # ------------------------------------------------------------------ #
    # API publique
    # ------------------------------------------------------------------ #
    def add(self, name: str, version: str, info: Dict[str, Any]) -> None:
        """Ajoute ou remplace une entrée dans le registre.

        ``info`` peut contenir ``type``, ``description``, ``author``,
        ``update_url`` et tout autre métadonnée utile.
        """
        entry: Dict[str, Any] = {
            "name": name,
            "version": version,
            "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        entry.update(info)
        self._data["packages"][name] = entry
        self.save()

    def remove(self, name: str) -> None:
        """Supprime un paquet du registre (silencieux s'il n'existe pas)."""
        if name in self._data["packages"]:
            del self._data["packages"][name]
            self.save()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Retourne l'entrée d'un paquet ou ``None`` s'il n'est pas installé."""
        entry = self._data["packages"].get(name)
        return dict(entry) if entry else None

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Retourne une copie de toutes les entrées indexées par nom."""
        return {name: dict(entry) for name, entry in self._data["packages"].items()}

    def is_installed(self, name: str) -> bool:
        """Indique si un paquet est présent dans le registre."""
        return name in self._data["packages"]
