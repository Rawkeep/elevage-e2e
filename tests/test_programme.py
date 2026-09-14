"""Zwei Blätter für dieselbe Tierart — wählbar, nie zusammengelegt."""

from datetime import date

import pytest

from elevage.models import OFFENES_ENDE, Herde, Kategorie, Tierart
from elevage.plan import baue_termine, offene_issues, schritte_fuer
from elevage.programme import (
    PROGRAMM_LEGEHENNE,
    PROGRAMM_LEGEHENNE_VETO,
    PROGRAMME,
    alle_programme,
    programm,
    programm_konflikt,
    vorgabe_programm,
)
from elevage.takt import rechne


def _herde(programm_id=None, tierart=Tierart.LEGEHENNE):
    return Herde(
        tenant_id="t",
        herde_id="H1",
        name="Stall",
        tierart=tierart,
        einstalldatum=date(2026, 1, 1),
        tierzahl=500,
        programm_id=programm_id,
    )


def test_jede_tierart_hat_genau_eine_vorgabe():
    """Ohne Wahl darf nie eine Herde ohne Plan dastehen — und nie mit zweien."""
    for tierart in Tierart:
        vorgaben = [p for p in PROGRAMME if p.tierart is tierart and p.vorgabe]
        assert len(vorgaben) == 1, tierart
        assert vorgabe_programm(tierart) is vorgaben[0]


def test_programmkennungen_sind_eindeutig():
    kennungen = [p.programm_id for p in PROGRAMME]
    assert len(kennungen) == len(set(kennungen))


def test_eine_herde_ohne_wahl_laeuft_wie_vorher():
    """Der Zweck der Migration: bestehende Herden ändern ihren Plan um kein Jota."""
    ohne = schritte_fuer(_herde(), date(2026, 3, 1))
    ausdruecklich = schritte_fuer(_herde("IVOGRAIN_PONDEUSE"), date(2026, 3, 1))
    assert [s.key for s in ohne] == [s.key for s in ausdruecklich]
    assert all(s.key.startswith(("PONDEUSE", "DAUER", "FUTTER", "NOTFALL")) for s in ohne) or ohne


def test_die_wahl_aendert_wirklich_den_plan():
    ivo = {s.key for s in schritte_fuer(_herde("IVOGRAIN_PONDEUSE"), date(2026, 3, 1))}
    veto = {s.key for s in schritte_fuer(_herde("VETO_PONDEUSE"), date(2026, 3, 1))}
    assert ivo != veto
    # Gemeinsam bleibt nur, was keinem Blatt gehört: die Futterwechsel kommen
    # vom Fütterungsplan, nicht vom Tierarzt, und ein ausgelöstes
    # Notfallschema hängt am Vorfall.
    for key in ivo & veto:
        assert key.startswith(("FUTTER", "NOTFALL")), key


def test_gumboro_steht_in_den_blaettern_verschieden():
    """Der handfeste Unterschied, an dem der Betrieb entscheidet."""

    def tage(schritte, wort):
        # Nur die Impfungen selbst: das VETO-Blatt setzt am Tag davor eine
        # Vitamingabe „vor der 2. Gumboro-Impfung“ — die zählt nicht mit.
        return sorted(
            s.von_tag
            for s in schritte
            if wort in s.titel.lower() and s.kategorie is Kategorie.IMPFUNG
        )

    assert tage(PROGRAMM_LEGEHENNE, "gumboro") == [7, 12, 17]
    assert tage(PROGRAMM_LEGEHENNE_VETO, "gumboro") == [7, 14, 21]


def test_eine_unpassende_wahl_faellt_zurueck_und_wird_gemeldet():
    """Still scheitern hieße: eine Herde ohne Plan. Das darf nicht passieren."""
    blatt = programm(Tierart.MASTHUHN, "VETO_PONDEUSE")
    assert blatt.programm_id == "IVOGRAIN_CHAIR"
    meldung = programm_konflikt(Tierart.MASTHUHN, "VETO_PONDEUSE")
    assert meldung and "MASTHUHN" in meldung.text
    assert programm_konflikt(Tierart.LEGEHENNE, "VETO_PONDEUSE") is None
    assert programm_konflikt(Tierart.LEGEHENNE, None) is None


def test_der_befund_wandert_bis_ins_tagesbild():
    issues = offene_issues(_herde("GIBT_ES_NICHT"), date(2026, 3, 1))
    assert any("unbekannt" in i.text for i in issues)


def test_eine_pause_ist_keine_aufgabe():
    """„EAU SIMPLE“ steht im Stand, nicht in der Liste — sonst hakt jemand
    fünfzig Tage lang „einfaches Wasser“ ab."""
    bild = rechne(_herde("VETO_PONDEUSE"), date(2026, 1, 10))
    assert bild.ruhe and bild.ruhe[0].kategorie is Kategorie.PAUSE
    for topf in (bild.ueberfaellig, bild.heute, bild.demnaechst, bild.bestellen, bild.erledigt):
        assert all(t.kategorie is not Kategorie.PAUSE for t in topf)


def test_pausen_bleiben_trotzdem_termine():
    """Sie ganz wegzulassen hieße: niemand sieht, dass die Lücke gewollt ist."""
    termine = baue_termine(_herde("VETO_PONDEUSE"), date(2026, 1, 10))
    assert any(t.kategorie is Kategorie.PAUSE for t in termine)


def test_das_offene_ende_laeuft_bis_zur_ausstallung():
    """„J128 à la Réforme“ hat kein Datum — und darf keins erfinden."""
    letzter = next(s for s in PROGRAMM_LEGEHENNE_VETO if s.von_tag == 128)
    assert letzter.bis_tag >= OFFENES_ENDE
    bild = rechne(_herde("VETO_PONDEUSE"), date(2029, 1, 1))
    assert not any(t.schritt_key == letzter.key for t in bild.ueberfaellig)


def test_die_dauerregel_faengt_an_ihrem_tag_an():
    """Das IVOGRAIN-Blatt rechnet in Wochen, das VETO-Blatt nennt einen Tag."""
    schritte = schritte_fuer(_herde("VETO_PONDEUSE"), date(2026, 6, 1))
    dauer = [s for s in schritte if s.key.startswith("VETO_DAUER_")]
    assert dauer and min(s.von_tag for s in dauer) == 128


def test_das_veto_blatt_meldet_seine_widersprueche():
    """Verbatim übernehmen heißt: melden, nicht glattziehen."""
    alle = [i.text for s in PROGRAMM_LEGEHENNE_VETO for i in s.issues]
    assert any("ANTI-STRESS" in i for i in alle)  # J17 trägt die falsche Überschrift
    assert any("CORYMINE" in i for i in alle)  # Schreibweise J120 gegen J84
    assert any("Réforme" in i for i in alle)  # kein Enddatum
    assert len(alle) >= 4


def test_die_dosis_steht_am_schritt_nicht_im_fliesstext():
    erste = PROGRAMM_LEGEHENNE_VETO[0]
    assert erste.dosis_je_liter and "1 g/l" in erste.dosis_je_liter


def test_alle_programme_laesst_sich_filtern():
    assert {p.tierart for p in alle_programme(Tierart.LEGEHENNE)} == {Tierart.LEGEHENNE}
    assert len(alle_programme()) == len(PROGRAMME)


def test_jeder_schritt_nennt_sein_blatt():
    """Im Tagesbild muss sichtbar bleiben, wessen Blatt gerade gilt."""
    assert all(s.quelle == "VETO-NEGOCES" for s in PROGRAMM_LEGEHENNE_VETO)
    assert all(s.quelle == "IVOGRAIN" for s in PROGRAMM_LEGEHENNE)


def test_das_tagesbild_nennt_das_geltende_blatt():
    bild = rechne(_herde("VETO_PONDEUSE"), date(2026, 2, 1))
    assert bild.programm_id == "VETO_PONDEUSE"
    assert "VETO" in bild.programm_titel


@pytest.mark.parametrize("blatt", PROGRAMME, ids=lambda p: p.programm_id)
def test_kein_schritt_endet_vor_seinem_anfang(blatt):
    for s in blatt.schritte:
        assert s.von_tag <= s.bis_tag, s.key
        assert s.tierart is blatt.tierart, s.key
