"""Persistenz: Migrationen, Mandantentrennung, idempotente Quittungen."""

from datetime import date
from pathlib import Path

import pytest

from elevage.archiv import (
    MIGRATIONEN,
    lade_herde,
    liste_herden,
    migriere,
    oeffne,
    protokolliere_mischung,
    quittiere,
    quittungen_fuer,
    spalten,
    speichere_herde,
    stalle_aus,
    tabellen,
)
from elevage.mischung import baue_mischauftrag
from elevage.models import Herde, Quittung, Tierart
from elevage.rezepte import REZEPT_DEMARRAGE, REZEPT_PONTE


@pytest.fixture()
def conn(tmp_path: Path):
    with oeffne(tmp_path / "test.db") as c:
        yield c


def herde(tenant="betrieb-1", herde_id="H1", **kw) -> Herde:
    daten = dict(
        tenant_id=tenant,
        herde_id=herde_id,
        name="Stall 1",
        tierart=Tierart.LEGEHENNE,
        einstalldatum=date(2026, 3, 2),
        tierzahl=1000,
    )
    daten.update(kw)
    return Herde(**daten)


def test_jede_fachtabelle_hat_eine_tenant_id(conn):
    """Fitness-Function: Mandantentrennung kann nicht vergessen werden."""
    for tabelle in tabellen(conn):
        assert "tenant_id" in spalten(conn, tabelle), f"{tabelle} ohne tenant_id"


def test_migration_ist_wiederholbar_und_zaehlt_vorwaerts(conn):
    stand = migriere(conn)
    assert stand == max(nummer for nummer, _ in MIGRATIONEN)
    assert migriere(conn) == stand  # zweiter Lauf ändert nichts


def test_herde_speichern_und_wiederfinden(conn):
    speichere_herde(conn, herde())
    zurueck = lade_herde(conn, "betrieb-1", "H1")
    assert zurueck == herde()


def test_speichern_ist_ein_update_kein_zweiter_datensatz(conn):
    speichere_herde(conn, herde())
    speichere_herde(conn, herde(name="Stall Nord", tierzahl=1200))
    alle = liste_herden(conn, "betrieb-1")
    assert len(alle) == 1
    assert alle[0].name == "Stall Nord" and alle[0].tierzahl == 1200


def test_ein_mandant_sieht_den_anderen_nicht(conn):
    speichere_herde(conn, herde(tenant="betrieb-1"))
    speichere_herde(conn, herde(tenant="betrieb-2", name="Fremder Stall"))
    assert [h.name for h in liste_herden(conn, "betrieb-1")] == ["Stall 1"]
    assert lade_herde(conn, "betrieb-1", "H1").name == "Stall 1"
    assert lade_herde(conn, "betrieb-3", "H1") is None


def test_ausstallen_loescht_nicht(conn):
    speichere_herde(conn, herde())
    stalle_aus(conn, "betrieb-1", "H1")
    assert liste_herden(conn, "betrieb-1") == []
    assert liste_herden(conn, "betrieb-1", nur_aktive=False) != []
    assert lade_herde(conn, "betrieb-1", "H1") is not None


def quittung(**kw) -> Quittung:
    daten = dict(
        tenant_id="betrieb-1",
        herde_id="H1",
        schritt_key="PONDEUSE_J7_GUMBORO_1",
        quittung_id="q-1",
        erledigt_am=date(2026, 3, 8),
        lot="LOT-4711",
    )
    daten.update(kw)
    return Quittung(**daten)


def test_dieselbe_quittung_zweimal_ist_folgenlos(conn):
    """Das Handy darf seine Warteschlange beliebig oft abschicken."""
    assert quittiere(conn, quittung()) is True
    assert quittiere(conn, quittung()) is False
    assert len(quittungen_fuer(conn, "betrieb-1", "H1")) == 1


def test_quittung_kommt_vollstaendig_zurueck(conn):
    quittiere(conn, quittung(durch="Kofi", bemerkung="Wasser vorher angesäuert"))
    zurueck = quittungen_fuer(conn, "betrieb-1", "H1")[0]
    assert zurueck.lot == "LOT-4711"
    assert zurueck.durch == "Kofi"
    assert zurueck.bemerkung == "Wasser vorher angesäuert"


def test_quittungen_bleiben_beim_eigenen_mandanten(conn):
    quittiere(conn, quittung(tenant_id="betrieb-2", quittung_id="q-fremd"))
    assert quittungen_fuer(conn, "betrieb-1", "H1") == []
    assert len(quittungen_fuer(conn, "betrieb-2", "H1")) == 1


def test_freigegebene_mischung_wird_protokolliert(conn):
    auftrag = baue_mischauftrag(REZEPT_DEMARRAGE, 500)
    assert protokolliere_mischung(conn, "betrieb-1", "M-1", "H1", date(2026, 3, 8), auftrag) is True
    # zweimal dieselbe Nummer: kein zweiter Eintrag
    assert (
        protokolliere_mischung(conn, "betrieb-1", "M-1", "H1", date(2026, 3, 8), auftrag) is False
    )


def test_gesperrte_mischung_wird_nicht_protokolliert(conn):
    """Was nicht freigegeben ist, wurde nicht gemischt."""
    auftrag = baue_mischauftrag(REZEPT_PONTE, 1000)
    with pytest.raises(ValueError):
        protokolliere_mischung(conn, "betrieb-1", "M-2", "H1", date(2026, 3, 8), auftrag)
