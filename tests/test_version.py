"""Der Versionsstempel: eine Quelle, nicht zwei."""

from pathlib import Path

import tomllib

from elevage.version import UNBEKANNT, commit, paketversion, stempel

WURZEL = Path(__file__).resolve().parents[1]


def test_die_version_steht_nur_im_pyproject():
    """Zwei Versionsangaben laufen garantiert auseinander."""
    with (WURZEL / "pyproject.toml").open("rb") as datei:
        erwartet = tomllib.load(datei)["project"]["version"]
    assert paketversion() in (erwartet, UNBEKANNT)


def test_ohne_commit_wird_nichts_erfunden(monkeypatch):
    monkeypatch.delenv("ELEVAGE_COMMIT", raising=False)
    assert commit() == UNBEKANNT


def test_der_commit_kommt_aus_der_umgebung(monkeypatch):
    monkeypatch.setenv("ELEVAGE_COMMIT", "abcdef1234567890")
    assert commit() == "abcdef123456"  # gekürzt, wie im Footer
    assert stempel()["commit"] == "abcdef123456"
