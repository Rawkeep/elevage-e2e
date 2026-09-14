"""Die Verzehrkurve: gemessen schlägt Richtwert, Lücken werden benannt."""

from datetime import date

from elevage.models import Herde, Quelle, Tierart
from elevage.verzehr import (
    FUTTER_VORLAUF_TAGE,
    aus_mischungen,
    kombiniere,
    prognose,
    richtwert,
)

EINSTALL = date(2026, 3, 2)


def herde(tierzahl: int = 1000) -> Herde:
    return Herde(
        tenant_id="hof",
        herde_id="H1",
        name="Stall 1",
        tierart=Tierart.LEGEHENNE,
        einstalldatum=EINSTALL,
        tierzahl=tierzahl,
    )


def test_verbrauch_zwischen_zwei_mischungen_ergibt_die_zahl():
    """140 kg auf 1000 Tiere in 7 Tagen = 20 g/Tier/Tag."""
    kurve, _ = aus_mischungen(
        Tierart.LEGEHENNE,
        1000,
        EINSTALL,
        [(date(2026, 3, 9), 140.0), (date(2026, 3, 16), 200.0)],
    )
    assert [p.gramm_je_tier_tag for p in kurve.punkte] == [20.0]
    assert kurve.punkte[0].quelle is Quelle.GEMESSEN
    assert "140 kg über 7 Tage" in (kurve.punkte[0].basis or "")


def test_die_letzte_mischung_ist_noch_im_trog():
    """Sie hat kein Ende — gezählt, nicht als Verbrauch verbucht."""
    kurve, issues = aus_mischungen(Tierart.LEGEHENNE, 1000, EINSTALL, [(date(2026, 3, 9), 140.0)])
    assert kurve.punkte == []
    assert any("nicht in die Kurve eingerechnet" in i.text for i in issues)


def test_zu_kurzer_abstand_und_unplausibles_fliegen_raus():
    kurve, issues = aus_mischungen(
        Tierart.LEGEHENNE,
        1000,
        EINSTALL,
        [
            (date(2026, 3, 9), 140.0),
            (date(2026, 3, 10), 140.0),  # ein Tag Abstand: keine Messung
            (date(2026, 3, 17), 9000.0),  # Vorratsmischung, nicht Tagesverbrauch
            (date(2026, 3, 24), 200.0),
        ],
    )
    assert [p.woche for p in kurve.punkte] == [2]
    assert any("nicht in die Kurve" in i.text for i in issues)


def test_tierzahl_null_liefert_keine_erfundene_kurve():
    kurve, issues = aus_mischungen(Tierart.LEGEHENNE, 0, EINSTALL, [])
    assert kurve.punkte == []
    assert any("Tierzahl 0" in i.text for i in issues)


def test_gemessen_schlaegt_richtwert_nur_in_seiner_woche():
    gemessen, _ = aus_mischungen(
        Tierart.LEGEHENNE,
        1000,
        EINSTALL,
        [(date(2026, 3, 9), 140.0), (date(2026, 3, 16), 200.0)],
    )
    kurve = kombiniere(gemessen, richtwert(Tierart.LEGEHENNE))
    assert kurve.fuer_woche(2).quelle is Quelle.GEMESSEN
    assert kurve.fuer_woche(1).quelle is Quelle.RICHTWERT
    assert kurve.fuer_woche(10).quelle is Quelle.RICHTWERT


def test_die_kurve_haelt_zwischen_den_stuetzstellen():
    kurve = richtwert(Tierart.LEGEHENNE)
    assert kurve.fuer_woche(9).woche == 8  # Woche 9 hat keinen eigenen Punkt
    assert kurve.fuer_woche(99).woche == 26  # über das Ende hinaus: letzter Punkt
    assert kurve.fuer_woche(0) is None  # davor: nichts erfinden


def test_prognose_sagt_worauf_sie_steht():
    p = prognose(herde(), date(2026, 3, 20), 3, richtwert(Tierart.LEGEHENNE))
    assert p.quelle is Quelle.RICHTWERT
    assert any("Richtwerten" in i.text for i in p.issues)
    assert p.bedarf_je_tag_kg == 27.0  # 27 g × 1000 Tiere
    assert p.bedarf_bis_horizont_kg == 378.0  # × 14 Tage


def test_reichweite_und_bestelltag():
    p = prognose(herde(), date(2026, 3, 20), 3, richtwert(Tierart.LEGEHENNE), vorrat_kg=270.0)
    assert p.reicht_bis == date(2026, 3, 30)  # 270 kg / 27 kg je Tag
    assert (p.reicht_bis - p.bestellen_ab).days == FUTTER_VORLAUF_TAGE


def test_angebrochener_vorlauf_wird_gemeldet():
    p = prognose(herde(), date(2026, 3, 20), 3, richtwert(Tierart.LEGEHENNE), vorrat_kg=54.0)
    assert any("Bestellvorlauf" in i.text for i in p.issues)


def test_ohne_punkt_gibt_es_keine_zahl_sondern_einen_befund():
    p = prognose(herde(), date(2026, 3, 3), 0, richtwert(Tierart.LEGEHENNE))
    assert p.bedarf_je_tag_kg is None
    assert any("Keine Verzehrzahl" in i.text for i in p.issues)
