"""Der Versionsstempel: eine Quelle, nicht zwei."""

import re
from pathlib import Path

from elevage.version import UNBEKANNT, commit, paketversion, stempel

WURZEL = Path(__file__).resolve().parents[1]


def test_die_version_steht_nur_im_pyproject():
    """Zwei Versionsangaben laufen garantiert auseinander.

    Gelesen wird mit einer Regel statt mit `tomllib` — das gibt es erst ab
    Python 3.11, und das Paket verspricht 3.10. Ein Test, der die
    Versionszusage des Pakets selbst bricht, ist ein schlechter Test.
    """
    text = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
    treffer = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert treffer, "Keine Version im pyproject gefunden"
    assert paketversion() in (treffer.group(1), UNBEKANNT)


def test_ohne_commit_wird_nichts_erfunden(monkeypatch):
    monkeypatch.delenv("ELEVAGE_COMMIT", raising=False)
    assert commit() == UNBEKANNT


def test_der_commit_kommt_aus_der_umgebung(monkeypatch):
    monkeypatch.setenv("ELEVAGE_COMMIT", "abcdef1234567890")
    assert commit() == "abcdef123456"  # gekürzt, wie im Footer
    assert stempel()["commit"] == "abcdef123456"
