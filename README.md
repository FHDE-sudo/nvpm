# nvpm

**nvpm** (nv Package Manager) est un gestionnaire de paquets léger pour les fichiers `.nv`.
Il supporte à la fois les **scripts Python/interprétés** et les **projets compilés**
(C, C++, etc.) grâce à un système de build et de dépendances système.

Un fichier `.nv` est un manifeste JSON qui décrit un paquet : son nom, sa version,
ses fichiers sources, son point d'entrée, ses dépendances système et la commande
de compilation pour les projets natifs.

## Installation

Cloner le dépôt puis installer localement avec `pip` :

```bash
git clone https://github.com/FHDE-sudo/nvpm.git
cd nvpm
pip install .
```

Python 3.8 ou supérieur est requis. La dépendance `requests` est installée
automatiquement pour la gestion des mises à jour distantes.

Après installation, la commande `nvpm` est disponible dans votre `PATH`. Les
binaires et scripts installés par nvpm sont placés dans `~/.nvpm/bin/`, qu'il
est recommandé d'ajouter à votre `PATH` :

```bash
export PATH="$HOME/.nvpm/bin:$PATH"
```

## Structure d'un fichier `.nv`

Un fichier `.nv` est un document JSON.

### Exemple — script Python

```json
{
  "name": "hello",
  "version": "1.0.0",
  "description": "Un paquet exemple simple",
  "author": "FHDE",
  "type": "script",
  "language": "python",
  "dependencies": [],
  "files": ["main.py"],
  "entry": "main.py"
}
```

### Exemple — projet C compilé (GTK4 / WebKit)

```json
{
  "name": "navigateur",
  "version": "1.0.0",
  "description": "Navigateur web basé sur GTK4 et WebKit",
  "author": "FHDE",
  "type": "binary",
  "language": "c",
  "system_deps": ["gtk4", "webkit2gtk-6.0", "gcc", "pkg-config"],
  "build": {
    "command": "gcc -o navigateur src/main.c $(pkg-config --cflags --libs gtk4 webkit2gtk-6.0)",
    "output": "navigateur"
  },
  "files": ["src/"],
  "entry": "navigateur",
  "update": {
    "url": "https://github.com/FHDE-sudo/navigateur/releases/latest",
    "check": "remote"
  }
}
```

### Champs

Champs requis :

- `name` — nom du paquet
- `version` — version au format libre (recommandé : sémantique)
- `files` — liste des fichiers et/ou dossiers à copier
- `entry` — point d'entrée (script à exécuter ou nom du binaire produit)

Champs optionnels :

- `description` — description courte
- `author` — auteur du paquet
- `dependencies` — paquets nvpm requis
- `type` — `"script"` (défaut) ou `"binary"`
- `language` — langage principal (`python`, `c`, `cpp`, …)
- `system_deps` — dépendances système à vérifier avant installation
- `build` — objet `{ "command": "...", "output": "..." }` (requis si `type == "binary"`)
- `update` — objet `{ "url": "...", "check": "remote" }` pour les mises à jour

## Commandes

| Commande | Description |
|----------|-------------|
| `nvpm install <chemin.nv>` | Installe un paquet depuis un fichier `.nv` |
| `nvpm remove <nom>` | Supprime un paquet installé |
| `nvpm list` | Liste tous les paquets installés |
| `nvpm info <nom>` | Affiche les détails d'un paquet installé |
| `nvpm init` | Assistant interactif pour générer un nouveau `.nv` |
| `nvpm update <nom>` | Met à jour un paquet (depuis son URL distante) |
| `nvpm update --all` | Met à jour tous les paquets |
| `nvpm run <nom>` | Exécute le binaire ou le script d'un paquet |

## Exemples

Installer et exécuter l'exemple Python :

```bash
nvpm install examples/hello/hello.nv
nvpm list
nvpm info hello
nvpm run hello
nvpm remove hello
```

Installer l'exemple C/GTK4 (nécessite `gtk4`, `webkit2gtk-6.0`, `gcc`, `pkg-config`) :

```bash
nvpm install examples/navigateur/navigateur.nv
nvpm run navigateur
```

## Emplacement des données

nvpm stocke ses données dans `~/.nvpm/` :

- `~/.nvpm/packages/<nom>/` — fichiers des paquets installés
- `~/.nvpm/bin/` — liens symboliques des binaires et wrappers de scripts
- `~/.nvpm/registry.json` — registre des paquets installés
