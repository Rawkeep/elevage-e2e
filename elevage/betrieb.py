"""Die Naht zwischen Archiv und Taktgeber.

`takt.rechne()` kennt keine Datenbank und `archiv` kennt keinen Taktgeber —
hier werden beide zusammengeführt. Eine eigene Datei, damit die Kopplung
sichtbar an einer Stelle liegt und nicht in der Oberfläche versickert.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from elevage import archiv
from elevage.anpassung import wirksames_rezept
from elevage.bestand import mittlere_tierzahl
from elevage.einstellung import ausgleichsart
from elevage.mischung import baue_mischauftrag, vermerk_text
from elevage.models import (
    Ausgleichsart,
    Herde,
    Mischauftrag,
    Pruefvermerk,
    Rezept,
    Tagesbild,
    Verzehrkurve,
)
from elevage.takt import rechne
from elevage.verzehr import aus_mischungen, kombiniere, richtwert

VERMERK_AUSGLEICH = "ausgleich"
"""Vermerk-Nummern sind sprechend und stabil, damit derselbe Punkt nur einmal liegt."""


def _herde(conn: sqlite3.Connection, tenant_id: str, herde_id: str) -> Herde:
    herde = archiv.lade_herde(conn, tenant_id, herde_id)
    if herde is None:
        raise KeyError(f"Unbekannte Herde: {herde_id}")
    return herde


def verzehrkurve(
    conn: sqlite3.Connection, tenant_id: str, herde_id: str
) -> tuple[Verzehrkurve, list[str]]:
    """Die Kurve dieses Betriebs: gemessen wo möglich, Richtwert wo nötig."""
    herde = _herde(conn, tenant_id, herde_id)
    mischungen = archiv.mischungen_fuer(conn, tenant_id, herde_id)
    bewegungen = archiv.bewegungen_fuer(conn, tenant_id, herde_id)
    gemessen, issues = aus_mischungen(
        herde.tierart,
        herde.tierzahl,
        herde.einstalldatum,
        mischungen,
        lambda von, bis: mittlere_tierzahl(herde, von, bis, bewegungen),
    )
    if not gemessen.punkte:
        issues.append(
            "Noch keine protokollierte Mischung — die Kurve steht komplett auf "
            "Richtwerten. Mit 'elevage gemischt' schärft sie sich von selbst."
        )
    return kombiniere(gemessen, richtwert(herde.tierart)), issues


def tagesbild(
    conn: sqlite3.Connection,
    tenant_id: str,
    herde_id: str,
    stichtag: date,
    *,
    vorrat_kg: float | None = None,
) -> Tagesbild:
    """Alles, was der Betrieb über diese Herde weiß, an diesem Stichtag."""
    herde = _herde(conn, tenant_id, herde_id)
    kurve, kurven_issues = verzehrkurve(conn, tenant_id, herde_id)
    return rechne(
        herde,
        stichtag,
        archiv.quittungen_fuer(conn, tenant_id, herde_id),
        archiv.ereignisse_fuer(conn, tenant_id, herde_id),
        kurve=kurve,
        vorrat_kg=vorrat_kg,
        kurven_issues=kurven_issues,
        einstellungen=archiv.einstellungen_fuer(conn, tenant_id),
        anpassungen=archiv.anpassungen_fuer(conn, tenant_id),
        vermerke=archiv.vermerke_fuer(conn, tenant_id),
        praeparate=archiv.praeparate_fuer(conn, tenant_id),
        bewegungen=archiv.bewegungen_fuer(conn, tenant_id, herde_id),
    )


def wirksames_rezept_fuer(conn: sqlite3.Connection, tenant_id: str, basis: Rezept) -> Rezept:
    """Blatt plus die Anpassungen dieses Betriebs."""
    return wirksames_rezept(basis, archiv.anpassungen_fuer(conn, tenant_id))


def _lege_ausgleichsvermerk_an(
    conn: sqlite3.Connection,
    tenant_id: str,
    rezept: Rezept,
    auftrag: Mischauftrag,
    am: date,
) -> None:
    """Ein Ausgleich bleibt als Aufgabe liegen, bis ein Mensch ihn abhakt."""
    if auftrag.ausgleich is not Ausgleichsart.AUSGLEICH or auftrag.ausgleich_posten is None:
        return
    alt = next(p.kg_je_100 for p in rezept.posten if p.artikel_id == auftrag.ausgleich_posten)
    neu = next(
        z.kg / (auftrag.ziel_kg / 100.0)
        for z in auftrag.zeilen
        if z.artikel_id == auftrag.ausgleich_posten
    )
    archiv.lege_vermerk_an(
        conn,
        Pruefvermerk(
            tenant_id=tenant_id,
            vermerk_id=f"{VERMERK_AUSGLEICH}:{rezept.key}",
            betrifft=f"Rezept {rezept.key}",
            text=vermerk_text(rezept, auftrag.ausgleich_posten, alt, neu),
            angelegt_am=am,
        ),
    )


def mischauftrag(
    conn: sqlite3.Connection,
    tenant_id: str,
    herde_id: str,
    ziel_kg: float,
    am: date,
    *,
    art: Ausgleichsart | None = None,
    buchen: bool = False,
    nummer: str | None = None,
) -> tuple[Mischauftrag | None, bool]:
    """Mischauftrag nach dem wirksamen Rezept — mit Vermerk und auf Wunsch gebucht."""
    bild = tagesbild(conn, tenant_id, herde_id, am)
    if bild.phase is None:
        return None, False
    gewaehlt = art or ausgleichsart(archiv.einstellungen_fuer(conn, tenant_id))
    auftrag = baue_mischauftrag(bild.phase, ziel_kg, art=gewaehlt)
    _lege_ausgleichsvermerk_an(conn, tenant_id, bild.phase, auftrag, am)
    if not buchen:
        return auftrag, False
    if not auftrag.freigegeben:
        raise ValueError("Gesperrter Mischauftrag wird nicht protokolliert")
    gebucht = archiv.protokolliere_mischung(
        conn, tenant_id, nummer or f"{herde_id}:{am.isoformat()}", herde_id, am, auftrag
    )
    return auftrag, gebucht
