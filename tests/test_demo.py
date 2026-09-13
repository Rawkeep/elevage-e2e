"""Die Pages-Demo ist dieselbe Seite — sie darf nicht abdriften."""

import json
import re
from pathlib import Path

from elevage.seite import SEITE
from tests.test_seite import SVG_NAMENSRAUM
from tools.baue_demo import ZIEL, baue_daten, baue_seite

GEBAUT = baue_seite()


def test_die_demo_ist_deterministisch():
    """Gleicher Lauf, gleiche Datei — sonst rauscht jeder Commit."""
    assert baue_seite() == GEBAUT


def test_die_ausgelieferte_datei_ist_aktuell():
    """Wer seite.py ändert, muss die Demo neu bauen."""
    abgelegt = Path(ZIEL)
    assert abgelegt.exists(), "docs/index.html fehlt — 'python3 -m tools.baue_demo'"
    assert abgelegt.read_text(encoding="utf-8") == GEBAUT, (
        "docs/index.html ist veraltet — 'python3 -m tools.baue_demo' laufen lassen"
    )


def test_es_gibt_nur_eine_oberflaeche():
    """Die Demo ist die Anwendung, nicht ihr Zwilling."""
    kern = SEITE[SEITE.index("<style>") : SEITE.index("</style>")]
    assert kern in GEBAUT


def test_die_demo_holt_nichts_aus_dem_netz():
    ohne = GEBAUT.replace(SVG_NAMENSRAUM, "").replace("https://github.com/Rawkeep/elevage-e2e", "")
    for muster in (r"https?://", r"src=[\"']//", r"cdn\.", r"fonts\.g"):
        assert not re.search(muster, ohne), f"externer Verweis: {muster}"


def test_die_demo_sagt_was_sie_ist():
    """Erfundene Daten müssen als solche dastehen, bevor jemand sie glaubt."""
    assert "Demo mit erfundenen Betriebsdaten" in GEBAUT
    assert "es wird nichts gespeichert" in GEBAUT
    assert "https://github.com/Rawkeep/elevage-e2e" in GEBAUT


def test_die_zahlen_kommen_aus_der_engine():
    daten = baue_daten()
    bild = daten["tagesbild"]
    assert bild["herde"]["tierzahl"] == 1200
    assert bild["futter"]["quelle"] == "GEMESSEN"  # aus den Demo-Mischungen gelernt
    assert any("Gumboro-Schema" in t["titel"] for t in bild["heute"])
    assert bild["vermerke"], "der Ausgleich muss als Prüfvermerk sichtbar sein"


def test_alle_drei_ausgleichswege_sind_vorgerechnet():
    auftraege = baue_daten()["auftraege"]
    for art in ("AUSGLEICH", "VERBATIM", "ANTEILIG"):
        for menge in (500, 1000):
            assert f"{art}:{menge}" in auftraege
    # Démarrage (Woche 8): 101,1 kg je 100 kg, Ausgleich über Mais
    assert auftraege["AUSGLEICH:1000"]["istEinwaageKg"] == 1000.0
    assert auftraege["VERBATIM:1000"]["istEinwaageKg"] == 1011.0


def test_die_demo_rechnet_nicht_mit_der_uhr():
    """Sonst zeigt die Seite morgen andere Zahlen als der Test heute."""
    assert "new Date().toISOString()" not in GEBAUT
    assert json.loads(re.search(r"const DEMO = (\{.*?\});", GEBAUT, re.S).group(1))["stichtag"]
