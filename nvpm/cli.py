"""Interface en ligne de commande de nvpm."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, colors
from .config import BIN_DIR, ensure_dirs
from .installer import InstallError, Installer
from .package import NvPackageError
from .registry import Registry
from .remover import RemoveError, Remover
from .updater import UpdateError, Updater


HEADER = f"nvpm v{__version__}"


def _print_header() -> None:
    print(colors.bold(colors.info(HEADER)))


# ---------------------------------------------------------------------------- #
# Construction du parseur
# ---------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Construit l'``argparse.ArgumentParser`` pour nvpm."""
    parser = argparse.ArgumentParser(
        prog="nvpm",
        description="Gestionnaire de paquets pour fichiers .nv",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    sub = parser.add_subparsers(dest="command", metavar="<commande>")

    install = sub.add_parser("install", help="Installer un paquet depuis un .nv")
    install.add_argument("nv_path", help="Chemin vers le fichier .nv")
    install.add_argument(
        "--force", action="store_true", help="Réinstalle même si déjà présent"
    )

    remove = sub.add_parser("remove", help="Supprimer un paquet installé")
    remove.add_argument("name", help="Nom du paquet")

    sub.add_parser("list", help="Lister les paquets installés")

    info = sub.add_parser("info", help="Afficher les détails d'un paquet")
    info.add_argument("name", help="Nom du paquet")

    sub.add_parser("init", help="Créer interactivement un nouveau fichier .nv")

    update = sub.add_parser("update", help="Mettre à jour un ou tous les paquets")
    update.add_argument("name", nargs="?", help="Nom du paquet (ignoré avec --all)")
    update.add_argument(
        "--all", dest="update_all", action="store_true",
        help="Mettre à jour tous les paquets installés",
    )
    update.add_argument(
        "--from", dest="from_nv", help="Utiliser un .nv local au lieu de l'URL distante"
    )

    run = sub.add_parser("run", help="Exécuter le binaire ou script d'un paquet")
    run.add_argument("name", help="Nom du paquet")
    run.add_argument(
        "args", nargs=argparse.REMAINDER, help="Arguments passés au programme"
    )

    return parser


# ---------------------------------------------------------------------------- #
# Implémentations des sous-commandes
# ---------------------------------------------------------------------------- #
def cmd_install(args: argparse.Namespace) -> int:
    """Implémente ``nvpm install``."""
    try:
        Installer().install(args.nv_path, force=args.force)
    except (InstallError, NvPackageError) as exc:
        print(colors.error(f"✗ {exc}"))
        return 1
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """Implémente ``nvpm remove``."""
    try:
        Remover().remove(args.name)
    except RemoveError as exc:
        print(colors.error(f"✗ {exc}"))
        return 1
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    """Implémente ``nvpm list`` avec un tableau formaté."""
    packages = Registry().list_all()
    if not packages:
        print(colors.info("Aucun paquet installé."))
        return 0

    headers = ("Nom", "Version", "Type", "Description")
    rows: List[tuple[str, str, str, str]] = []
    for entry in packages.values():
        rows.append((
            str(entry.get("name", "")),
            str(entry.get("version", "")),
            str(entry.get("type", "script")),
            str(entry.get("description", "") or ""),
        ))

    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]

    def fmt(row: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(colors.bold(fmt(headers)))
    print(colors.info("  ".join("-" * w for w in widths)))
    for row in rows:
        print(fmt(row))
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Implémente ``nvpm info``."""
    entry = Registry().get(args.name)
    if entry is None:
        print(colors.error(f"✗ Paquet '{args.name}' non installé."))
        return 1
    print(colors.bold(f"{entry['name']} v{entry.get('version', '?')}"))
    for key in (
        "type", "language", "description", "author", "entry",
        "installed_at", "update_url", "update_check",
    ):
        if key in entry and entry[key]:
            print(f"  {key}: {entry[key]}")
    return 0


def cmd_init(_args: argparse.Namespace) -> int:
    """Implémente ``nvpm init`` en mode interactif."""
    print(colors.bold("Assistant de création d'un fichier .nv"))
    print(colors.info("Appuyez sur Entrée pour accepter la valeur par défaut."))

    name = _ask("Nom du paquet", required=True)
    version = _ask("Version", default="1.0.0")
    description = _ask("Description", default="")
    author = _ask("Auteur", default="")
    pkg_type = _ask("Type (script/binary)", default="script")
    if pkg_type not in ("script", "binary"):
        print(colors.warning("Type invalide, 'script' utilisé."))
        pkg_type = "script"
    language = _ask("Langage", default="python" if pkg_type == "script" else "c")

    system_deps_raw = _ask(
        "Dépendances système (séparées par des virgules)", default=""
    )
    system_deps = [dep.strip() for dep in system_deps_raw.split(",") if dep.strip()]

    files_raw = _ask(
        "Fichiers/dossiers à inclure (séparés par des virgules)",
        default="main.py" if pkg_type == "script" else "src/",
        required=True,
    )
    files = [item.strip() for item in files_raw.split(",") if item.strip()]

    entry = _ask(
        "Point d'entrée",
        default="main.py" if pkg_type == "script" else name,
        required=True,
    )

    manifest = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "type": pkg_type,
        "language": language,
        "dependencies": [],
        "files": files,
        "entry": entry,
    }
    if system_deps:
        manifest["system_deps"] = system_deps

    if pkg_type == "binary":
        command = _ask("Commande de build", required=True)
        output = _ask("Fichier de sortie", default=name, required=True)
        manifest["build"] = {"command": command, "output": output}

    update_url = _ask("URL de mise à jour (optionnel)", default="")
    if update_url:
        manifest["update"] = {"url": update_url, "check": "remote"}

    target = Path.cwd() / f"{name}.nv"
    with target.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(colors.success(f"✓ Fichier créé : {target}"))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Implémente ``nvpm update`` et ``nvpm update --all``."""
    updater = Updater()
    try:
        if args.update_all:
            updater.update_all()
            return 0
        if not args.name:
            print(colors.error("✗ Un nom de paquet ou --all est requis."))
            return 1
        updater.update(args.name, new_nv_path=args.from_nv)
    except (UpdateError, InstallError, RemoveError, NvPackageError) as exc:
        print(colors.error(f"✗ {exc}"))
        return 1
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Implémente ``nvpm run``."""
    registry = Registry()
    if not registry.is_installed(args.name):
        print(colors.error(f"✗ Paquet '{args.name}' non installé."))
        return 1

    executable = BIN_DIR / args.name
    if not executable.exists() and not executable.is_symlink():
        print(colors.error(f"✗ Exécutable introuvable : {executable}"))
        return 1

    forwarded = list(args.args or [])
    # argparse.REMAINDER peut laisser un "--" initial selon les versions.
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    print(colors.info(f"→ Exécution de {executable}"))
    try:
        result = subprocess.run([str(executable), *forwarded], check=False)
    except OSError as exc:
        print(colors.error(f"✗ Échec de l'exécution : {exc}"))
        return 1
    return result.returncode


# ---------------------------------------------------------------------------- #
# Aide interactive
# ---------------------------------------------------------------------------- #
def _ask(prompt: str, *, default: str = "", required: bool = False) -> str:
    """Invite l'utilisateur et retourne une réponse validée."""
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            value = input(f"{prompt}{suffix}: ").strip()
        except EOFError:
            value = ""
        if not value:
            value = default
        if required and not value:
            print(colors.warning("Cette valeur est requise."))
            continue
        return value


# ---------------------------------------------------------------------------- #
# Point d'entrée
# ---------------------------------------------------------------------------- #
COMMANDS = {
    "install": cmd_install,
    "remove": cmd_remove,
    "list": cmd_list,
    "info": cmd_info,
    "init": cmd_init,
    "update": cmd_update,
    "run": cmd_run,
}


def main(argv: Optional[List[str]] = None) -> int:
    """Point d'entrée exposé via ``console_scripts``."""
    ensure_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)

    _print_header()

    if args.command is None:
        parser.print_help()
        return 0

    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
