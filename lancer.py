"""Point d'entree pour l'executable autonome construit par PyInstaller."""

import sys

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
