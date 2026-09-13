"""Die Naht zwischen Archiv und Taktgeber.

`takt.rechne()` kennt keine Datenbank und `archiv` kennt keinen Taktgeber —
hier werden beide zusammengeführt. Eine eigene Datei, damit die Kopplung
sichtbar an einer Stelle liegt und nicht in der Oberfläche versickert.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from elevage import archiv
from elevage.models import Tagesbild, Verzehrkurve
from elevage.takt import rechne
from elevage.verzehr import aus_mischungen, kombiniere, richtwert


def verzehrkurve(
    conn: sqlite3.Connection, tenant_id: str, herde_id: str
) -> tuple[Verzehrkurve, list[str]]:
    """Die Kurve dieses Betriebs: gemessen wo möglich, Richtwert wo nötig."""
    herde = archiv.lade_herde(conn, tenant_id, herde_id)
    if herde is None:
        raise KeyError(f"Unbekannte Herde: {herde_id}")
    mischungen = archiv.mischungen_fuer(conn, tenant_id, herde_id)
    gemessen, issues = aus_mischungen(
        herde.tierart, herde.tierzahl, herde.einstalldatum, mischungen
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
    herde = archiv.lade_herde(conn, tenant_id, herde_id)
    if herde is None:
        raise KeyError(f"Unbekannte Herde: {herde_id}")
    kurve, kurven_issues = verzehrkurve(conn, tenant_id, herde_id)
    return rechne(
        herde,
        stichtag,
        archiv.quittungen_fuer(conn, tenant_id, herde_id),
        archiv.ereignisse_fuer(conn, tenant_id, herde_id),
        kurve=kurve,
        vorrat_kg=vorrat_kg,
        kurven_issues=kurven_issues,
    )
