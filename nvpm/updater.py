"""Logique de mise à jour des paquets installés."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import colors
from .installer import Installer
from .package import NvPackage
from .registry import Registry
from .remover import Remover


class UpdateError(RuntimeError):
    """Erreur levée lorsqu'une mise à jour ne peut aboutir."""


class Updater:
    """Gère la vérification et l'application des mises à jour de paquets."""

    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or Registry()

    # ------------------------------------------------------------------ #
    # Vérification
    # ------------------------------------------------------------------ #
    def check_update(self, name: str) -> Tuple[bool, Optional[str]]:
        """Vérifie si une nouvelle version distante est disponible.

        Retourne ``(disponible, nouvelle_version)``. Si aucune URL de mise à
        jour n'est configurée, retourne ``(False, None)``.
        """
        entry = self.registry.get(name)
        if entry is None:
            raise UpdateError(f"Le paquet '{name}' n'est pas installé.")

        url = entry.get("update_url")
        check = entry.get("update_check")
        if not url or check != "remote":
            return False, None

        remote_version = self._fetch_remote_version(url)
        if remote_version is None:
            return False, None

        current_version = str(entry.get("version", ""))
        return remote_version != current_version, remote_version

    def _fetch_remote_version(self, url: str) -> Optional[str]:
        """Récupère la version distante via ``requests`` (typiquement GitHub)."""
        try:
            import requests  # Import paresseux pour garder le module léger.
        except ImportError as exc:
            raise UpdateError(
                "Le module 'requests' est requis pour les mises à jour distantes."
            ) from exc

        headers = {"Accept": "application/vnd.github+json"}
        try:
            response = requests.get(url, headers=headers, timeout=15)
        except requests.RequestException as exc:
            print(colors.warning(f"  ⚠ Impossible de contacter {url} : {exc}"))
            return None

        if response.status_code >= 400:
            print(colors.warning(
                f"  ⚠ Réponse HTTP {response.status_code} depuis {url}"
            ))
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        # Format typique GitHub releases : {"tag_name": "v1.2.3", "name": "..."}.
        tag = payload.get("tag_name") or payload.get("name") or payload.get("version")
        if isinstance(tag, str):
            return tag.lstrip("v")
        return None

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    def update(self, name: str, new_nv_path: Optional[str | Path] = None) -> None:
        """Met à jour un paquet via un nouveau ``.nv`` local ou distant."""
        entry = self.registry.get(name)
        if entry is None:
            raise UpdateError(f"Le paquet '{name}' n'est pas installé.")
        old_version = str(entry.get("version", "?"))

        nv_path: Path
        tmp_dir: Optional[tempfile.TemporaryDirectory[str]] = None
        if new_nv_path is not None:
            nv_path = Path(new_nv_path).expanduser().resolve()
        else:
            tmp_dir, nv_path = self._download_manifest(name, entry)

        try:
            new_pkg = NvPackage.from_file(nv_path)
            print(colors.info(
                f"→ Mise à jour '{name}' : {old_version} → {new_pkg.version}"
            ))
            Remover(self.registry).remove(name)
            Installer(self.registry).install(nv_path)
            print(colors.success(
                f"✓ '{name}' mis à jour : {old_version} → {new_pkg.version}"
            ))
        finally:
            if tmp_dir is not None:
                tmp_dir.cleanup()

    def update_all(self) -> None:
        """Vérifie et applique les mises à jour pour tous les paquets."""
        packages = self.registry.list_all()
        if not packages:
            print(colors.info("Aucun paquet installé."))
            return

        updated: list[str] = []
        for name in packages:
            try:
                available, remote_version = self.check_update(name)
            except UpdateError as exc:
                print(colors.error(f"✗ {name} : {exc}"))
                continue

            if not available:
                print(colors.info(f"  = {name} à jour"))
                continue

            print(colors.warning(
                f"  ↑ {name} : nouvelle version {remote_version} disponible"
            ))
            try:
                self.update(name)
                updated.append(name)
            except UpdateError as exc:
                print(colors.error(f"✗ {name} : {exc}"))

        if updated:
            print(colors.success(f"✓ {len(updated)} paquet(s) mis à jour."))
        else:
            print(colors.info("Aucune mise à jour appliquée."))

    # ------------------------------------------------------------------ #
    # Téléchargement du manifeste
    # ------------------------------------------------------------------ #
    def _download_manifest(
        self, name: str, entry: Dict[str, object]
    ) -> Tuple[tempfile.TemporaryDirectory[str], Path]:
        """Télécharge un ``.nv`` distant et le place dans un dossier temporaire."""
        url = entry.get("update_url")
        if not isinstance(url, str) or not url:
            raise UpdateError(
                f"Aucune URL de mise à jour configurée pour '{name}'."
            )

        try:
            import requests
        except ImportError as exc:
            raise UpdateError(
                "Le module 'requests' est requis pour télécharger un .nv."
            ) from exc

        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as exc:
            raise UpdateError(f"Téléchargement impossible : {exc}") from exc

        if response.status_code >= 400:
            raise UpdateError(
                f"Réponse HTTP {response.status_code} lors du téléchargement."
            )

        # Accepte soit un .nv brut, soit une release GitHub listant les assets.
        tmp_dir = tempfile.TemporaryDirectory(prefix=f"nvpm-update-{name}-")
        nv_path = Path(tmp_dir.name) / f"{name}.nv"

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            assets = payload.get("assets") or []
            for asset in assets:
                if isinstance(asset, dict) and str(asset.get("name", "")).endswith(
                    ".nv"
                ):
                    asset_url = asset.get("browser_download_url")
                    if isinstance(asset_url, str):
                        asset_response = requests.get(asset_url, timeout=60)
                        nv_path.write_bytes(asset_response.content)
                        return tmp_dir, nv_path
            # Pas d'asset : on tente de reconstruire un .nv minimal depuis le JSON.
            if "tag_name" in payload:
                nv_path.write_text(
                    json.dumps({
                        "name": name,
                        "version": str(payload.get("tag_name", "")).lstrip("v"),
                        "files": [],
                        "entry": str(entry.get("entry", name)),
                    }),
                    encoding="utf-8",
                )
                return tmp_dir, nv_path

        # Fallback : on suppose que la réponse est un .nv brut.
        nv_path.write_bytes(response.content)
        return tmp_dir, nv_path
