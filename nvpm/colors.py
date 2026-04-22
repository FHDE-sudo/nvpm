"""Petites aides pour l'affichage coloré ANSI dans le terminal."""
from __future__ import annotations

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def _supports_color() -> bool:
    """Détecte si le terminal courant supporte les couleurs ANSI."""
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Entoure ``text`` des codes ANSI pour ``color`` si supporté."""
    if not _supports_color():
        return text
    return f"{color}{text}{RESET}"


def success(text: str) -> str:
    """Formate un message de succès en vert."""
    return colorize(text, GREEN)


def error(text: str) -> str:
    """Formate un message d'erreur en rouge."""
    return colorize(text, RED)


def warning(text: str) -> str:
    """Formate un avertissement en jaune."""
    return colorize(text, YELLOW)


def info(text: str) -> str:
    """Formate un message d'information en bleu."""
    return colorize(text, BLUE)


def bold(text: str) -> str:
    """Formate un texte en gras."""
    return colorize(text, BOLD)
