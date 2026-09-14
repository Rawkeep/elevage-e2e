"""Die Blätter sind französisch — die französische Ansicht auch.

Das Wörterbuch in `sprache.py` deckt die Oberfläche ab: Knöpfe,
Überschriften, Zustände. Die Termine kommen aber als Daten vom Server, und
die liefen bis hierher deutsch durch — ein Loch, das kein Test sah, weil
`test_kein_oberflaechentext_ohne_vokabel` nur ins Markup schaut.

Diese Datei schließt es von der anderen Seite: **jeder Schritt, der auf
dem Bildschirm landen kann, trägt den Wortlaut seines Blattes.**
"""

from datetime import date

from elevage.models import Herde, Tierart
from elevage.notfall import futterwechsel_schritte, schritte_fuer_vorfall
from elevage.plan import baue_termine
from elevage.programme import PROGRAMME
from elevage.rezepte import REZEPTE


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


def test_jeder_schritt_jedes_blattes_hat_seinen_wortlaut():
    fehlt = [
        (blatt.programm_id, s.key) for blatt in PROGRAMME for s in blatt.schritte if not s.titel_fr
    ]
    assert not fehlt, f"ohne französischen Wortlaut: {fehlt}"


def test_jede_dauerregel_hat_ihren_wortlaut():
    fehlt = [
        (blatt.programm_id, r.key)
        for blatt in PROGRAMME
        for r in blatt.dauerregeln
        if not r.titel_fr
    ]
    assert not fehlt, f"ohne französischen Wortlaut: {fehlt}"


def test_auch_die_hergeleiteten_schritte_haben_ihn():
    """Futterwechsel und Notfallschema stehen im NB-Kasten der Blätter —
    sie kommen nicht aus der Tabelle, landen aber in derselben Liste."""
    for s in futterwechsel_schritte(_herde()):
        assert s.titel_fr, s.key


def test_das_notfallschema_spricht_die_sprache_des_blattes():
    from elevage.models import Ereignis, EreignisArt

    ereignis = Ereignis(
        tenant_id="t",
        herde_id="H1",
        ereignis_id="V1",
        art=EreignisArt.GUMBORO,
        festgestellt_am=date(2026, 2, 1),
    )
    for s in schritte_fuer_vorfall(ereignis, _herde()):
        assert s.titel_fr, s.key
        assert s.hinweis_fr or not s.hinweis, s.key


def test_kein_termin_faellt_durch():
    """Der eigentliche Test: was der Server ausliefert, ist vollständig."""
    for programm_id in (None, "IVOGRAIN_PONDEUSE", "VETO_PONDEUSE"):
        for t in baue_termine(_herde(programm_id), date(2026, 9, 1)):
            assert t.titel_fr, f"{programm_id}: {t.schritt_key}"
    for t in baue_termine(_herde(tierart=Tierart.MASTHUHN), date(2026, 3, 1)):
        assert t.titel_fr, t.schritt_key


def test_jede_futterphase_hat_ihren_namen_im_blatt():
    for r in REZEPTE:
        assert r.name_fr, r.key


def test_der_wortlaut_ist_nicht_der_deutsche_titel():
    """Sonst wäre das Feld gefüllt und die Ansicht trotzdem deutsch."""
    gleich = [
        (blatt.programm_id, s.key)
        for blatt in PROGRAMME
        for s in blatt.schritte
        if s.titel_fr == s.titel
    ]
    assert not gleich, f"Wortlaut gleich dem deutschen Titel: {gleich}"


def test_die_praeparate_haben_keine_zweite_sprache():
    """VIGOSINE heißt in beiden Sprachen VIGOSINE. Ein Feld `praeparate_fr`
    wäre eine Einladung, Handelsnamen zu übersetzen."""
    from elevage.models import Schritt

    assert "praeparate_fr" not in Schritt.model_fields
    assert "praeparate" in Schritt.model_fields


def test_nur_eine_zeile_traegt_ihre_mittel_im_titel():
    """Und zwar die, deren Überschrift dem Präparat widerspricht: das Blatt
    schreibt „ANTI-STRESS“ über COX B3. Ohne die Mittel im Wortlaut wäre der
    Widerspruch im französischen Text unsichtbar."""
    mit_mitteln = [
        s.key
        for blatt in PROGRAMME
        for s in blatt.schritte
        if any(mittel in (s.titel_fr or "") for mittel in s.praeparate)
    ]
    assert mit_mitteln == ["VETO_J17_ANTIKOKZIDIUM"]


def test_der_widerspruch_bleibt_im_wortlaut_stehen():
    """Das IVOGRAIN-Blatt nennt J12 UND J17 „2ème Vaccin GUMBORO“. Wer das
    im französischen Text stillschweigend zu „3ème“ korrigiert, hat den
    Befund weggeräumt, den der deutsche Titel meldet."""
    blatt = next(b for b in PROGRAMME if b.programm_id == "IVOGRAIN_PONDEUSE")
    dritter = next(s for s in blatt.schritte if s.key == "PONDEUSE_J17_GUMBORO_3")
    assert dritter.titel_fr is not None and dritter.titel_fr.startswith("2ème")
    assert dritter.titel.startswith("3.")
