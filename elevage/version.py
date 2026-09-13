"""Ein Versionsstempel, damit man weiß, welcher Stand lief, als es passierte.

Die Zahl steht im `pyproject.toml` und wird hier gelesen, nicht ein zweites
Mal geschrieben — zwei Versionsangaben laufen garantiert auseinander. Der
Commit kommt als Umgebungsvariable dazu, gesetzt beim Bauen des Bildes.
"""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version

PAKET = "elevage-e2e"
UNBEKANNT = "unbekannt"


def paketversion() -> str:
    try:
        return version(PAKET)
    except PackageNotFoundError:
        return UNBEKANNT


def commit() -> str:
    """Kurzer Commit-Hash, wenn das Bild ihn mitbekommen hat."""
    return os.environ.get("ELEVAGE_COMMIT", UNBEKANNT)[:12] or UNBEKANNT


def stempel() -> dict[str, str]:
    return {"version": paketversion(), "commit": commit()}
