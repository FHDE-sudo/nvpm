"""Registre persistant des paquets installés."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .config import REGISTRY_FILE, ensure_dirs


class Registry:
    """Gère le registre JSON des paquets installés.

    Le registre est persisté dans le fichier :data:`nvpm.config.REGISTRY_FILE`.
    Il contient un unique objet JSON de la forme ``{"packages": {...}}``.
    """

    def __init__(self) -> None:
        """Charge le registre depuis le disque ou l'initialise à vide."""
        ensure_dirs()
        self._data: Dict[str, Any] = {"packages": {}}
        self._load()

    def _load(self) -> None:
        """Charge le contenu du registre depuis le disque."""
        if not REGISTRY_FILE.exists():
            self._data = {"packages": {}}
            self.save()
            return

        try:
            with REGISTRY_FILE.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict) and isinstance(loaded.get("packages"), dict):
                self._data = loaded
            else:
                self._data = {"packages": {}}
        except (OSError, json.JSONDecodeError):
            self._data = {"packages": {}}

    def save(self) -> None:
        """Écrit le registre courant sur le disque."""
        ensure_dirs()
        with REGISTRY_FILE.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def add(self, name: str, version: str, info: Dict[str, Any]) -> None:
        """Ajoute ou remplace un paquet dans le registre.

        :param name: Nom du paquet.
        :param version: Version installée.
        :param info: Informations complémentaires à enregistrer
            (description, auteur, fichiers, date d'installation, etc.).
        """
        entry = dict(info)
        entry["name"] = name
        entry["version"] = version
        self._data["packages"][name] = entry
        self.save()

    def remove(self, name: str) -> None:
        """Supprime une entrée du registre.

        :param name: Nom du paquet à supprimer.
        """
        self._data["packages"].pop(name, None)
        self.save()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Retourne les informations d'un paquet ou ``None``.

        :param name: Nom du paquet.
        :return: Dictionnaire d'informations ou ``None`` si absent.
        """
        entry = self._data["packages"].get(name)
        if entry is None:
            return None
        return dict(entry)

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Retourne une copie de toutes les entrées du registre."""
        return {name: dict(info) for name, info in self._data["packages"].items()}

    def is_installed(self, name: str) -> bool:
        """Indique si un paquet est présent dans le registre.

        :param name: Nom du paquet.
        :return: ``True`` si le paquet est enregistré.
        """
        return name in self._data["packages"]
