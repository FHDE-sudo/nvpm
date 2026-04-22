"""Parsing et validation des fichiers de manifeste ``.nv``."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class NvPackageError(Exception):
    """Erreur levée lorsqu'un fichier ``.nv`` est invalide."""


class NvPackage:
    """Représente un paquet décrit par un fichier ``.nv``.

    Un paquet nvpm est un fichier JSON contenant au minimum les champs
    ``name``, ``version``, ``files`` et ``entry``. Les champs ``description``,
    ``author`` et ``dependencies`` sont optionnels.
    """

    REQUIRED_FIELDS = ("name", "version", "files", "entry")

    def __init__(
        self,
        name: str,
        version: str,
        files: List[str],
        entry: str,
        description: str = "",
        author: str = "",
        dependencies: Optional[List[str]] = None,
        source_path: Optional[Path] = None,
    ) -> None:
        """Initialise un paquet à partir de ses champs déjà validés.

        :param name: Nom du paquet.
        :param version: Version du paquet.
        :param files: Liste des fichiers sources (chemins relatifs au ``.nv``).
        :param entry: Point d'entrée principal du paquet.
        :param description: Description humaine (optionnelle).
        :param author: Auteur du paquet (optionnel).
        :param dependencies: Liste de dépendances (optionnelle).
        :param source_path: Chemin du fichier ``.nv`` d'origine.
        """
        self.name = name
        self.version = version
        self.files = files
        self.entry = entry
        self.description = description
        self.author = author
        self.dependencies = dependencies or []
        self.source_path = source_path

    @classmethod
    def from_file(cls, path: str | Path) -> "NvPackage":
        """Lit et valide un fichier ``.nv`` depuis le disque.

        :param path: Chemin vers le fichier ``.nv``.
        :raises NvPackageError: Si le fichier est introuvable, mal formé ou
            si un champ requis est manquant ou invalide.
        :return: Une instance de :class:`NvPackage`.
        """
        file_path = Path(path)
        if not file_path.is_file():
            raise NvPackageError(f"Fichier .nv introuvable : {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise NvPackageError(
                f"Fichier .nv invalide (JSON mal formé) : {file_path} — {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise NvPackageError(
                f"Fichier .nv invalide : le contenu doit être un objet JSON ({file_path})"
            )

        missing = [field for field in cls.REQUIRED_FIELDS if field not in data]
        if missing:
            raise NvPackageError(
                "Champs requis manquants dans "
                f"{file_path} : {', '.join(missing)}"
            )

        if not isinstance(data["files"], list) or not all(
            isinstance(item, str) for item in data["files"]
        ):
            raise NvPackageError(
                f"Le champ 'files' doit être une liste de chaînes ({file_path})"
            )

        for field in ("name", "version", "entry"):
            if not isinstance(data[field], str) or not data[field]:
                raise NvPackageError(
                    f"Le champ '{field}' doit être une chaîne non vide ({file_path})"
                )

        dependencies = data.get("dependencies", [])
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise NvPackageError(
                f"Le champ 'dependencies' doit être une liste de chaînes ({file_path})"
            )

        return cls(
            name=data["name"],
            version=data["version"],
            files=list(data["files"]),
            entry=data["entry"],
            description=data.get("description", "") or "",
            author=data.get("author", "") or "",
            dependencies=dependencies,
            source_path=file_path,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le paquet sous forme de dictionnaire.

        :return: Dictionnaire contenant tous les champs du paquet.
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": list(self.dependencies),
            "files": list(self.files),
            "entry": self.entry,
        }
