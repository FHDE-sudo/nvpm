"""Interface en ligne de commande pour nvpm."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .config import NV_EXTENSION
from .installer import Installer, InstallerError
from .package import NvPackageError
from .registry import Registry
from .remover import Remover, RemoverError

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _print_header() -> None:
    """Affiche l'entête avec le numéro de version."""
    print(f"{BOLD}{CYAN}nvpm v{__version__}{RESET}")


def _print_error(message: str) -> None:
    """Affiche un message d'erreur en rouge."""
    print(f"{RED}✗ {message}{RESET}", file=sys.stderr)


def _print_warning(message: str) -> None:
    """Affiche un avertissement en jaune."""
    print(f"{YELLOW}! {message}{RESET}")


def _print_success(message: str) -> None:
    """Affiche un message de succès en vert."""
    print(f"{GREEN}✓ {message}{RESET}")


def _build_parser() -> argparse.ArgumentParser:
    """Construit le parseur d'arguments pour la CLI."""
    parser = argparse.ArgumentParser(
        prog="nvpm",
        description="Gestionnaire de paquets pour fichiers .nv",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"nvpm {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="<commande>")

    install_p = sub.add_parser("install", help="Installer un paquet .nv")
    install_p.add_argument("path", help="Chemin vers le fichier .nv")

    remove_p = sub.add_parser("remove", help="Supprimer un paquet installé")
    remove_p.add_argument("name", help="Nom du paquet à supprimer")

    sub.add_parser("list", help="Lister les paquets installés")

    info_p = sub.add_parser("info", help="Afficher les détails d'un paquet")
    info_p.add_argument("name", help="Nom du paquet")

    sub.add_parser("init", help="Créer un nouveau fichier .nv (interactif)")

    return parser


def _cmd_install(path: str) -> int:
    """Gère la commande ``nvpm install``."""
    try:
        Installer().install(path)
        return 0
    except InstallerError as exc:
        _print_error(str(exc))
        return 1
    except NvPackageError as exc:
        _print_error(str(exc))
        return 1


def _cmd_remove(name: str) -> int:
    """Gère la commande ``nvpm remove``."""
    try:
        Remover().remove(name)
        return 0
    except RemoverError as exc:
        _print_error(str(exc))
        return 1


def _cmd_list() -> int:
    """Gère la commande ``nvpm list``."""
    registry = Registry()
    packages = registry.list_all()
    if not packages:
        _print_warning("Aucun paquet installé.")
        return 0

    name_w = max(len("Nom"), max(len(n) for n in packages))
    ver_w = max(
        len("Version"),
        max(len(str(info.get("version", ""))) for info in packages.values()),
    )
    desc_w = max(
        len("Description"),
        max(len(str(info.get("description", ""))) for info in packages.values()),
    )

    header = (
        f"{BOLD}{'Nom'.ljust(name_w)}  "
        f"{'Version'.ljust(ver_w)}  "
        f"{'Description'.ljust(desc_w)}{RESET}"
    )
    print(header)
    print("-" * (name_w + ver_w + desc_w + 4))
    for name in sorted(packages):
        info = packages[name]
        print(
            f"{name.ljust(name_w)}  "
            f"{str(info.get('version', '')).ljust(ver_w)}  "
            f"{str(info.get('description', '')).ljust(desc_w)}"
        )
    return 0


def _cmd_info(name: str) -> int:
    """Gère la commande ``nvpm info``."""
    info = Registry().get(name)
    if info is None:
        _print_error(f"Le paquet '{name}' n'est pas installé.")
        return 1

    print(f"{BOLD}Nom        :{RESET} {info.get('name', name)}")
    print(f"{BOLD}Version    :{RESET} {info.get('version', '')}")
    print(f"{BOLD}Auteur     :{RESET} {info.get('author', '')}")
    print(f"{BOLD}Description:{RESET} {info.get('description', '')}")
    print(f"{BOLD}Entrée     :{RESET} {info.get('entry', '')}")
    files = info.get("files", []) or []
    print(f"{BOLD}Fichiers   :{RESET} {', '.join(files) if files else '(aucun)'}")
    deps = info.get("dependencies", []) or []
    print(
        f"{BOLD}Dépendances:{RESET} {', '.join(deps) if deps else '(aucune)'}"
    )
    print(f"{BOLD}Installé le:{RESET} {info.get('installed_at', '')}")
    install_path = info.get("install_path", "")
    if install_path:
        print(f"{BOLD}Chemin     :{RESET} {install_path}")
    return 0


def _prompt(label: str, default: str = "") -> str:
    """Demande une valeur à l'utilisateur avec une valeur par défaut."""
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def _cmd_init() -> int:
    """Gère la commande interactive ``nvpm init``."""
    print(f"{CYAN}Assistant de création d'un fichier .nv{RESET}")
    name = _prompt("Nom du paquet")
    if not name:
        _print_error("Le nom est requis.")
        return 1
    version = _prompt("Version", "1.0.0")
    description = _prompt("Description", "")
    author = _prompt("Auteur", "")
    entry = _prompt("Point d'entrée (fichier)", "main.py")

    manifest = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "dependencies": [],
        "files": [entry],
        "entry": entry,
    }

    output = Path.cwd() / f"{name}{NV_EXTENSION}"
    if output.exists():
        _print_warning(f"Le fichier {output} existe déjà et sera écrasé.")

    with output.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    _print_success(f"Fichier créé : {output}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Point d'entrée principal de la CLI nvpm.

    :param argv: Arguments de la ligne de commande (par défaut ``sys.argv[1:]``).
    :return: Code de sortie (0 en cas de succès, non nul en cas d'erreur).
    """
    _print_header()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "install":
        return _cmd_install(args.path)
    if args.command == "remove":
        return _cmd_remove(args.name)
    if args.command == "list":
        return _cmd_list()
    if args.command == "info":
        return _cmd_info(args.name)
    if args.command == "init":
        return _cmd_init()

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
