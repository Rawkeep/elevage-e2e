"""Notfallschema und Futterwechsel — beides hängt an einem Ereignis."""

from datetime import date

from elevage.models import Ereignis, EreignisArt, Herde, Kategorie, Tierart
from elevage.notfall import (
    DOSIS_JE_LITER,
    ERHOLUNG_TAGE,
    SCHEMA_TAGE,
    futterwechsel_schritte,
    schritte_fuer_vorfall,
    wechseltage,
)

EINSTALL = date(2026, 3, 2)


def herde(tierart=Tierart.LEGEHENNE) -> Herde:
    return Herde(
        tenant_id="hof",
        herde_id="H1",
        name="Stall 1",
        tierart=tierart,
        einstalldatum=EINSTALL,
        tierzahl=1000,
    )


def vorfall(am: date = date(2026, 3, 16)) -> Ereignis:
    return Ereignis(
        tenant_id="hof",
        herde_id="H1",
        ereignis_id="V1",
        art=EreignisArt.GUMBORO,
        festgestellt_am=am,
    )


def test_schema_startet_am_tag_des_vorfalls_und_laeuft_vier_tage():
    schritte = schritte_fuer_vorfall(vorfall(), herde())
    desinfektion = schritte[0]
    assert desinfektion.von_tag == 15  # 16.03. ist Lebenstag 15
    assert desinfektion.bis_tag - desinfektion.von_tag + 1 == SCHEMA_TAGE


def test_der_leberschutz_folgt_direkt_auf_das_schema():
    desinfektion, erholung = schritte_fuer_vorfall(vorfall(), herde())
    assert erholung.von_tag == desinfektion.bis_tag + 1
    assert erholung.bis_tag - erholung.von_tag + 1 == ERHOLUNG_TAGE
    assert erholung.folgt_auf == desinfektion.key
    assert "VIGOSINE" in erholung.praeparate


def test_die_beiden_blaetter_nennen_zwei_dosen():
    """Verbatim erhalten — der Widerspruch wird gemeldet, nicht geglättet."""
    assert DOSIS_JE_LITER[Tierart.MASTHUHN] == "0,5 g/l"
    assert DOSIS_JE_LITER[Tierart.LEGEHENNE] == "1 g/l"
    mast = schritte_fuer_vorfall(vorfall(), herde(Tierart.MASTHUHN))[0]
    lege = schritte_fuer_vorfall(vorfall(), herde())[0]
    assert "0,5 g/l" in mast.titel and "1 g/l" in lege.titel
    assert any("zwei Dosen" in i for i in lege.issues)


def test_jeder_vorfall_bekommt_eigene_schluessel():
    """Zwei Ausbrüche in derselben Herde dürfen sich nicht überschreiben."""
    a = schritte_fuer_vorfall(vorfall(), herde())
    b = schritte_fuer_vorfall(
        Ereignis(
            tenant_id="hof",
            herde_id="H1",
            ereignis_id="V2",
            art=EreignisArt.GUMBORO,
            festgestellt_am=date(2026, 4, 20),
        ),
        herde(),
    )
    assert {s.key for s in a}.isdisjoint({s.key for s in b})


def test_wechseltage_kommen_aus_den_rezepten_nicht_aus_konstanten():
    assert [tag for tag, _, _ in wechseltage(Tierart.LEGEHENNE)] == [57, 148]
    assert wechseltage(Tierart.MASTHUHN) == []


def test_leberschutz_umrahmt_den_futterwechsel():
    schritte = futterwechsel_schritte(herde())
    assert [(s.von_tag, s.bis_tag) for s in schritte] == [(56, 59), (147, 150)]
    assert all(s.kategorie is Kategorie.FUTTERWECHSEL for s in schritte)


def test_masthuhn_hat_keinen_futterwechsel_weil_kein_blatt_da_ist():
    assert futterwechsel_schritte(herde(Tierart.MASTHUHN)) == []
