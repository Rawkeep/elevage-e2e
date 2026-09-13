"""Durchstich: einstallen → tagesbild → quittieren → tagesbild."""

from pathlib import Path

from elevage.cli import main


def lauf(tmp_path: Path, befehl: str, *args: str) -> int:
    """--db und --betrieb stehen hinter dem Unterbefehl, wie in der Praxis."""
    return main([befehl, "--db", str(tmp_path / "cli.db"), "--betrieb", "hof", *args])


def test_runde_durch_die_datenbank(tmp_path, capsys):
    assert (
        lauf(
            tmp_path,
            "einstallen",
            "--herde",
            "H1",
            "--name",
            "Stall Nord",
            "--tierart",
            "LEGEHENNE",
            "--einstall",
            "2026-03-02",
            "--tiere",
            "1200",
        )
        == 0
    )

    # Überfälliges färbt das Bild rot ⇒ Exit 2, damit ein Wächter daran hängen kann
    assert lauf(tmp_path, "tagesbild", "--herde", "H1", "--stichtag", "2026-03-06") == 2
    vorher = capsys.readouterr().out
    assert "Newcastle + Bronchite lebend" in vorher

    lauf(
        tmp_path,
        "quittieren",
        "--herde",
        "H1",
        "--schritt",
        "PONDEUSE_J1_ND_IB_LEBEND",
        "--am",
        "2026-03-02",
        "--lot",
        "LOT-4711",
    )
    lauf(tmp_path, "tagesbild", "--herde", "H1", "--stichtag", "2026-03-06")
    nachher = capsys.readouterr().out
    assert "ERLEDIGT" in nachher and "LOT-4711" in nachher


def test_unbekannte_herde_meldet_sich_statt_zu_stuerzen(tmp_path, capsys):
    assert lauf(tmp_path, "tagesbild", "--herde", "XX", "--stichtag", "2026-03-06") == 1
    assert "Unbekannte Herde" in capsys.readouterr().out


def test_mandant_sieht_die_herde_des_anderen_nicht(tmp_path, capsys):
    lauf(
        tmp_path,
        "einstallen",
        "--herde",
        "H1",
        "--name",
        "Stall Nord",
        "--tierart",
        "LEGEHENNE",
        "--einstall",
        "2026-03-02",
        "--tiere",
        "1200",
    )
    capsys.readouterr()
    assert main(["herden", "--db", str(tmp_path / "cli.db"), "--betrieb", "fremder"]) == 0
    assert "Keine Herden" in capsys.readouterr().out
