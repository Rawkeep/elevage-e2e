"""Zweisprachigkeit: die Oberfläche, nicht die Daten."""

import json
import re

from elevage.seite import ANMELDESEITE, ERSTER_BENUTZER, SEITE, UEBERSETZER
from elevage.sprache import FRANZOESISCH, SPRACHEN, VORGABE, uebersetze, woerterbuch


def test_fehlende_vokabel_faellt_auf_deutsch_zurueck():
    """Kein leeres Feld und kein Schlüsselname."""
    assert uebersetze("Gibt es nicht", "fr") == "Gibt es nicht"
    assert uebersetze("Überfällig", "fr") == "En retard"
    assert uebersetze("Überfällig", "de") == "Überfällig"


def test_franzoesisch_ist_die_vorgabe():
    """Die Blätter sind französisch, der Stall auch — Deutsch wäre die
    Sprache des Werkzeugbauers, nicht die der Arbeit."""
    assert VORGABE == "fr" and set(SPRACHEN) == {"de", "fr"}
    assert uebersetze("Überfällig") == "En retard"
    # Deutsch bleibt die Sprache des Quelltextes und der Rückfall.
    assert uebersetze("Gibt es nicht") == "Gibt es nicht"


def test_das_woerterbuch_ist_gueltiges_json_und_nur_franzoesisch():
    geladen = json.loads(woerterbuch())
    assert set(geladen) == {"fr"}
    assert geladen["fr"]["Herde"] == "Bande"


GLEICH_IN_BEIDEN = {"Version"}
"""Wörter, die im Französischen genauso heißen. Ausdrücklich gelistet,
damit „übersetzt wie im Deutschen" nicht zur bequemen Ausrede wird."""


def test_keine_vokabel_ist_leer_oder_unuebersetzt():
    for deutsch, franzoesisch in FRANZOESISCH.items():
        assert franzoesisch.strip(), deutsch
        if deutsch in GLEICH_IN_BEIDEN:
            continue
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


# Sprachnamen und Krankheitsnamen sind Daten, keine Oberfläche.
KEINE_OBERFLAECHE = {"Deutsch", "Français", "Gumboro"}


def _sichtbarer_text(seite: str) -> list[str]:
    """Was im Markup zwischen den Tags steht — ohne Stil und ohne Kommandos."""
    roh = seite.split("<script>")[0]
    roh = re.sub(r"<style>.*?</style>", "", roh, flags=re.S)
    roh = re.sub(r"<code>.*?</code>", "", roh, flags=re.S)
    texte = []
    for stueck in re.findall(r">([^<>{}]+)<", roh):
        text = " ".join(stueck.split())
        if text and re.search(r"[A-Za-zÄÖÜäöüß]{2}", text):
            texte.append(text)
    return texte


def _txt_aufrufe(seite: str) -> list[str]:
    """Jede Zeichenkette, die im Skript durch txt() geht."""
    js = seite[seite.index("<script>") :]
    raus = list(re.findall(r'txt\(\s*"([^"]+)"', js))
    for block in re.findall(r"txt\(\s*\{([^}]+)\}", js):
        raus += re.findall(r':\s*"([^"]+)"', block)
    for frage in re.findall(
        r'txt\(\s*\n?\s*[\w.]+ === "[^"]+"\s*\?\s*"([^"]+)"\s*\n?\s*:\s*"([^"]+)"', js
    ):
        raus += list(frage)
    return raus


def test_kein_oberflaechentext_ohne_vokabel():
    """Der Lackmustest der Zweisprachigkeit: was auf dem Bildschirm steht,
    muss übersetzbar sein — sonst bleibt die französische Ansicht halb
    deutsch, und genau das war der Zustand vorher."""
    fehlt = []
    for seite in (SEITE, ANMELDESEITE, ERSTER_BENUTZER):
        for text in _sichtbarer_text(seite):
            if text not in KEINE_OBERFLAECHE and text not in FRANZOESISCH:
                fehlt.append(text)
    for text in _txt_aufrufe(SEITE):
        if text not in FRANZOESISCH:
            fehlt.append(text)
    assert not fehlt, f"ohne Vokabel: {sorted(set(fehlt))}"


def test_alle_drei_seiten_teilen_denselben_uebersetzer():
    """Drei Kopien liefen garantiert auseinander."""
    for seite in (SEITE, ANMELDESEITE, ERSTER_BENUTZER):
        assert seite.count("function uebersetzeSeite") == 1
        assert UEBERSETZER.split("WOERTERBUCH_HIER")[1][:80] in seite


def test_kommandos_werden_nicht_uebersetzt():
    """Eine übersetzte Kommandozeile funktioniert nicht mehr."""
    assert '"CODE", "PRE", "SAMP", "KBD"' in UEBERSETZER
    assert "elevage benutzer --anlegen" in ERSTER_BENUTZER
