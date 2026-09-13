"""Zweisprachigkeit: die Oberfläche, nicht die Daten."""

import json

from elevage.seite import SEITE
from elevage.sprache import FRANZOESISCH, SPRACHEN, VORGABE, uebersetze, woerterbuch


def test_fehlende_vokabel_faellt_auf_deutsch_zurueck():
    """Kein leeres Feld und kein Schlüsselname."""
    assert uebersetze("Gibt es nicht", "fr") == "Gibt es nicht"
    assert uebersetze("Überfällig", "fr") == "En retard"
    assert uebersetze("Überfällig", "de") == "Überfällig"
    assert uebersetze("Überfällig") == "Überfällig"  # Vorgabe ist Deutsch
    assert VORGABE == "de" and set(SPRACHEN) == {"de", "fr"}


def test_das_woerterbuch_ist_gueltiges_json_und_nur_franzoesisch():
    geladen = json.loads(woerterbuch())
    assert set(geladen) == {"fr"}
    assert geladen["fr"]["Herde"] == "Bande"


def test_keine_vokabel_ist_leer_oder_unuebersetzt():
    for deutsch, franzoesisch in FRANZOESISCH.items():
        assert franzoesisch.strip(), deutsch
        assert franzoesisch != deutsch, f"{deutsch} ist nicht übersetzt"


def test_die_daten_werden_nicht_uebersetzt():
    """Präparatnamen, Rohstoffe und Befunde bleiben, wie sie sind."""
    for begriff in ("Mais", "COVIT", "Gumboro", "CEVAC IBIRD", "Son cube"):
        assert begriff not in FRANZOESISCH, begriff


def test_die_seite_traegt_das_woerterbuch_und_die_wahl():
    assert "En retard" in SEITE
    assert "WOERTERBUCH_HIER" not in SEITE
    assert 'id="sprache"' in SEITE
    assert 'value="fr"' in SEITE
    assert "taktgeber-sprache" in SEITE
    assert "function uebersetzeSeite()" in SEITE


def test_die_sprache_lebt_im_browser_nicht_im_konto():
    """Sie gehört dem Menschen vor dem Gerät, nicht dem Anmeldenamen."""
    assert 'localStorage.getItem("taktgeber-sprache")' in SEITE
    # Keine Anfrage an den Server trägt die Sprache mit — sie ist keine
    # Eigenschaft des Kontos und gehört in keine Tabelle.
    koerper = " ".join(z for z in SEITE.splitlines() if "JSON.stringify({" in z)
    assert "sprache" not in koerper.lower()
