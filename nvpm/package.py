"""Modélisation et parsing d'un fichier manifeste ``.nv``."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import NV_EXTENSION


class NvPackageError(ValueError):
    """Erreur levée lors de la validation d'un fichier ``.nv``."""


REQUIRED_FIELDS = ("name", "version", "files", "entry")
VALID_TYPES = ("script", "binary")


@dataclass
class NvPackage:
    """Représente le contenu d'un fichier ``.nv``.

    Champs requis : ``name``, ``version``, ``files``, ``entry``.
    Champs optionnels : ``description``, ``author``, ``dependencies``,
    ``type`` (``"script"`` par défaut), ``language``, ``system_deps``,
    ``build`` (``{"command", "output"}``) et ``update``
    (``{"url", "check"}``).
    """

    name: str
    version: str
    files: List[str]
    entry: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    type: str = "script"
    language: str = ""
    system_deps: List[str] = field(default_factory=list)
    build: Optional[Dict[str, str]] = None
    update: Optional[Dict[str, str]] = None
    source_path: Optional[Path] = None

    # ------------------------------------------------------------------ #
    # Constructeurs et sérialisation
    # ------------------------------------------------------------------ #
    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_path: Optional[Path] = None) -> "NvPackage":
        """Construit un ``NvPackage`` depuis un dictionnaire JSON validé."""
        missing = [key for key in REQUIRED_FIELDS if key not in data]
        if missing:
            raise NvPackageError(
                "Champs manquants dans le fichier .nv : " + ", ".join(missing)
            )

        if not isinstance(data["files"], list) or not data["files"]:
            raise NvPackageError("Le champ 'files' doit être une liste non vide.")

        pkg_type = data.get("type", "script")
        if pkg_type not in VALID_TYPES:
            raise NvPackageError(
                f"Type invalide '{pkg_type}' (attendu : {', '.join(VALID_TYPES)})."
            )

        build = data.get("build")
        if pkg_type == "binary":
            if not isinstance(build, dict) or "command" not in build or "output" not in build:
                raise NvPackageError(
                    "Un paquet de type 'binary' doit définir 'build' avec "
                    "'command' et 'output'."
                )

        update = data.get("update")
        if update is not None and not isinstance(update, dict):
            raise NvPackageError("Le champ 'update' doit être un objet JSON.")

        return cls(
            name=str(data["name"]),
            version=str(data["version"]),
            files=list(data["files"]),
            entry=str(data["entry"]),
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            dependencies=list(data.get("dependencies", [])),
            type=pkg_type,
            language=str(data.get("language", "")),
            system_deps=list(data.get("system_deps", [])),
            build=dict(build) if isinstance(build, dict) else None,
            update=dict(update) if isinstance(update, dict) else None,
            source_path=source_path,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "NvPackage":
        """Lit et valide un fichier ``.nv`` sur disque."""
        nv_path = Path(path).expanduser().resolve()
        if not nv_path.is_file():
            raise NvPackageError(f"Fichier introuvable : {nv_path}")
        if nv_path.suffix != NV_EXTENSION:
            raise NvPackageError(
                f"Extension attendue '{NV_EXTENSION}', reçue '{nv_path.suffix}'."
            )
        try:
            with nv_path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except json.JSONDecodeError as exc:
            raise NvPackageError(f"JSON invalide dans {nv_path} : {exc}") from exc

        if not isinstance(data, dict):
            raise NvPackageError("Le fichier .nv doit contenir un objet JSON.")

        return cls.from_dict(data, source_path=nv_path)

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le paquet en dictionnaire prêt pour JSON."""
        data: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "type": self.type,
            "language": self.language,
            "dependencies": list(self.dependencies),
            "system_deps": list(self.system_deps),
            "files": list(self.files),
            "entry": self.entry,
        }
        if self.build is not None:
            data["build"] = dict(self.build)
        if self.update is not None:
            data["update"] = dict(self.update)
        return data

    # ------------------------------------------------------------------ #
    # Aides
    # ------------------------------------------------------------------ #
    @property
    def source_dir(self) -> Path:
        """Dossier contenant le fichier ``.nv`` d'origine (si connu)."""
        if self.source_path is None:
            raise NvPackageError("Le paquet n'a pas de fichier source connu.")
        return self.source_path.parent
