"""Die Gegenüberstellung: gerechnet, nicht formuliert."""

from elevage.models import Kategorie, Tierart
from elevage.programme import programm
from elevage.vergleich import BEGLEITEND, vergleichbare, vergleiche, vergleiche_ids

IVO = "IVOGRAIN_PONDEUSE"
VETO = "VETO_PONDEUSE"


def _zeile(v, thema):
    return next((z for z in v.zeilen if z.thema == thema), None)


def test_gumboro_steht_zeile_an_zeile():
    """Der Kern: derselbe Erreger, zwei Termine — sichtbar nebeneinander."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    z = _zeile(v, "Impfung: Gumboro")
    assert z is not None
    assert z.links == "J7 · J12 · J17"
    assert z.rechts == "J7 · J14 · J21"
    assert not z.gleich


def test_impfungen_werden_nach_erreger_gruppiert_nicht_nach_titel():
    """Über den Titel verglichen stünde jede Gabe allein — und nichts
    stünde je nebeneinander. Genau das war der erste Anlauf."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    gegenuebergestellt = [z for z in v.zeilen if z.links and z.rechts]
    assert len(gegenuebergestellt) >= 5
    assert _zeile(v, "Impfung: Newcastle").links and _zeile(v, "Impfung: Newcastle").rechts


def test_ein_kombiimpfstoff_steht_in_mehreren_zeilen():
    """CORYMUNE 7K schützt gegen sechs Dinge — eine Zeile wäre eine Lüge."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    for thema in ("Impfung: Coryza", "Impfung: Newcastle", "Impfung: Legedepression (EDS)"):
        z = _zeile(v, thema)
        assert z is not None and z.rechts and "J120" in z.rechts, thema


def test_der_takt_der_dauerregeln_wird_gemeldet():
    """Ein Faktor sechs im Auffrischungsintervall fällt in keiner Tageszeile auf."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    z = _zeile(v, "Dauerregel: Impfung")
    assert z is not None
    assert z.links == "alle 30 / 90 Tage"
    assert z.rechts == "alle 180 Tage"
    assert any("Rundungsfrage" in i.text for i in v.issues)


def test_begleitendes_wird_gezaehlt_statt_aufgezaehlt():
    """Fünfzehn Anti-Stress-Zeilen gegen nichts wären Lärm."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    z = _zeile(v, "Anti-Stress")
    assert z is not None and z.rechts and "×" in z.rechts
    assert Kategorie.ANTI_STRESS in BEGLEITEND


def test_nur_auf_einer_seite_wird_benannt():
    """Das VETO-Blatt kennt kein Débecquage, das IVOGRAIN-Blatt keine Pausen."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    assert "Eingriff" in v.nur_links
    assert "Pause (einfaches Wasser)" in v.nur_rechts
    assert "Leberschutz" in v.nur_rechts


def test_das_offene_ende_steht_als_offen_da():
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    z = _zeile(v, "Hygiene / Stallführung")
    assert z is not None and z.rechts == "ab J128 (offen)"


def test_zwei_tierarten_werden_nicht_verglichen():
    """Eine Tabelle darüber wäre Scheinpräzision."""
    v = vergleiche(programm(Tierart.MASTHUHN), programm(Tierart.LEGEHENNE))
    assert not v.zeilen
    assert any("nicht vergleichbar" in i.text for i in v.issues)


def test_ein_blatt_mit_sich_selbst_ist_ueberall_gleich():
    v = vergleiche_ids(Tierart.LEGEHENNE, VETO, VETO)
    assert all(z.gleich for z in v.zeilen)
    assert not v.nur_links and not v.nur_rechts


def test_der_vergleich_urteilt_nicht():
    """Er stellt nebeneinander. Welches Blatt gilt, entscheidet der Betrieb."""
    v = vergleiche_ids(Tierart.LEGEHENNE, IVO, VETO)
    text = " ".join(i.text for i in v.issues).lower()
    for wort in ("empfehl", "besser", "richtig", "sollte"):
        assert wort not in text, wort


def test_vergleichbare_nennt_die_auswahl():
    assert len(vergleichbare(Tierart.LEGEHENNE)) == 2
    assert len(vergleichbare(Tierart.MASTHUHN)) == 1
