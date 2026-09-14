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


def _einstallen(tmp_path, *extra: str) -> int:
    return lauf(
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
        *extra,
    )


def test_das_blatt_laesst_sich_beim_einstallen_waehlen(tmp_path, capsys):
    assert _einstallen(tmp_path, "--programm", "VETO_PONDEUSE") == 0
    assert "VETO-NEGOCES" in capsys.readouterr().out
    assert lauf(tmp_path, "herden") == 0
    assert "VETO-NEGOCES" in capsys.readouterr().out


def test_ein_blatt_der_falschen_tierart_wird_abgewiesen(tmp_path, capsys):
    """Kein stiller Rückfall beim Anlegen: hier ist noch Zeit, es zu merken."""
    code = lauf(
        tmp_path,
        "einstallen",
        "--herde",
        "H2",
        "--name",
        "Mast",
        "--tierart",
        "MASTHUHN",
        "--einstall",
        "2026-03-02",
        "--tiere",
        "500",
        "--programm",
        "VETO_PONDEUSE",
    )
    assert code == 2
    assert "MASTHUHN" in capsys.readouterr().out


def test_das_blatt_laesst_sich_nachtraeglich_wechseln(tmp_path, capsys):
    _einstallen(tmp_path)
    capsys.readouterr()
    assert lauf(tmp_path, "programm", "--herde", "H1", "--waehlen", "VETO_PONDEUSE") == 0
    ausgabe = capsys.readouterr().out
    assert "VETO-NEGOCES" in ausgabe
    assert "Abgehakte Schritte bleiben abgehakt" in ausgabe
    # Exit 2 heißt „rote Lage“, nicht „Fehler“ — die Konvention des Hauses.
    assert lauf(tmp_path, "tagesbild", "--herde", "H1", "--stichtag", "2026-03-11") in (0, 2)
    tagesbild = capsys.readouterr().out
    assert "Programm: Legehenne — VETO-NEGOCES" in tagesbild
    assert "RUHE:" in tagesbild


def test_ohne_wahl_geht_es_zurueck_auf_die_vorgabe(tmp_path, capsys):
    _einstallen(tmp_path, "--programm", "VETO_PONDEUSE")
    capsys.readouterr()
    assert lauf(tmp_path, "programm", "--herde", "H1") == 0
    assert "IVOGRAIN" in capsys.readouterr().out


def test_die_gegenueberstellung_druckt_die_unterschiede(tmp_path, capsys):
    code = lauf(tmp_path, "programm", "--vergleich", "IVOGRAIN_PONDEUSE", "VETO_PONDEUSE")
    assert code == 0
    ausgabe = capsys.readouterr().out
    assert "Impfung: Gumboro" in ausgabe
    assert "J7 · J12 · J17" in ausgabe and "J7 · J14 · J21" in ausgabe
    assert "entscheidet der Betrieb" in ausgabe


def test_ein_blatt_laesst_sich_ganz_ausdrucken(tmp_path, capsys):
    assert lauf(tmp_path, "programm", "--zeigen", "VETO_PONDEUSE") == 0
    ausgabe = capsys.readouterr().out
    assert "Dr. BANGUE" in ausgabe
    assert "MERKSÄTZE DES BLATTES" in ausgabe
    assert "ab J128" in ausgabe  # das offene Ende
    assert "Dosis: VITAFLASH 1 g/l" in ausgabe


def test_der_tierarzt_wird_hinterlegt_und_erscheint_im_tagesbild(tmp_path, capsys):
    _einstallen(tmp_path)
    capsys.readouterr()
    assert lauf(tmp_path, "tierarzt") == 0
    assert "Kein Tierarzt hinterlegt" in capsys.readouterr().out
    assert lauf(tmp_path, "tierarzt", "--name", "Dr. Beispiel", "--telefon", "0000") == 0
    capsys.readouterr()
    assert lauf(tmp_path, "tagesbild", "--herde", "H1", "--stichtag", "2026-03-20") in (0, 2)
    assert "TIERARZT: Dr. Beispiel · 0000" in capsys.readouterr().out
