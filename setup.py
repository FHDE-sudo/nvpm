"""Script d'installation pour le paquet nvpm."""
from setuptools import find_packages, setup

setup(
    name="nvpm",
    version="1.0.0",
    description="Gestionnaire de paquets pour fichiers .nv (scripts et binaires)",
    author="FHDE",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "nvpm = nvpm.cli:main",
        ],
    },
    python_requires=">=3.8",
)
