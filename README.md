# nvpm

**nvpm** (nv Package Manager) est un gestionnaire de paquets léger pour les fichiers `.nv`.
Un fichier `.nv` est un manifeste JSON qui décrit un petit paquet : son nom, sa version, ses
fichiers sources et son point d'entrée.

## Installation

Cloner le dépôt puis installer localement :

```bash
git clone https://github.com/FHDE-sudo/nvpm.git
cd nvpm
pip install .
```

Python 3.8 ou supérieur est requis.

Après installation, la commande `nvpm` est disponible dans votre `PATH`.

## Structure d'un fichier `.nv`

Un fichier `.nv` est un document JSON. Exemple minimal :

```json
{
  "name": "hello",
  "version": "1.0.0",
  "description": "Un paquet exemple pour nvpm",
  "author": "FHDE",
  "dependencies": [],
  "files": ["main.py"],
  "entry": "main.py"
}
```

Champs requis : `name`, `version`, `files`, `entry`.
Champs optionnels : `description`, `author`, `dependencies`.

## Commandes

| Commande | Description |
|----------|-------------|
| `nvpm install <chemin.nv>` | Installe un paquet depuis un fichier `.nv` |
| `nvpm remove <nom>` | Supprime un paquet installé |
| `nvpm list` | Liste tous les paquets installés |
| `nvpm info <nom>` | Affiche les détails d'un paquet installé |
| `nvpm init` | Assistant interactif pour générer un nouveau `.nv` |

## Exemple

```bash
nvpm install example/hello.nv
nvpm list
nvpm info hello
nvpm remove hello
```

## Emplacement des données

nvpm stocke ses données dans `~/.nvpm/` :

- `~/.nvpm/packages/<nom>/` — fichiers des paquets installés
- `~/.nvpm/registry.json` — registre des paquets installés
